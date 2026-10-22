from contextlib import contextmanager
from functools import lru_cache
import hashlib
import html
import json
import re
import sqlite3
import shutil
import threading
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

STATES = {'saved', 'prepared', 'running', 'needs_attention', 'submitted', 'uncertain', 'interview', 'rejected', 'closed'}

def now():
    return datetime.now(timezone.utc).isoformat()

def canonical_url(url):
    p = urlsplit(url.strip())
    if p.scheme != 'https' or not p.hostname or p.username or p.password:
        raise ValueError('Use a public HTTPS job URL.')
    if p.hostname in {'localhost', '127.0.0.1', '::1'}:
        raise ValueError('Local addresses are not job portals.')
    return urlunsplit(('https', p.netloc.lower(), p.path.rstrip('/'), p.query, ''))

def plain(s):
    return html.unescape(re.sub('<[^>]+>', ' ', s or '')).strip()

class Store:
    def __init__(self, folder):
        self.folder = Path(folder)
        self.folder.mkdir(parents=True, exist_ok=True)
        self.db = self.folder / 'applypilot.sqlite3'
        with self.connect() as c:
            c.execute('PRAGMA journal_mode=WAL')
            c.executescript('''
            CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY, url TEXT UNIQUE NOT NULL,
            company TEXT NOT NULL, title TEXT NOT NULL, location TEXT NOT NULL DEFAULT '',
            description TEXT NOT NULL DEFAULT '', status TEXT NOT NULL DEFAULT 'saved',
            note TEXT NOT NULL DEFAULT '', updated TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY, job_id TEXT, kind TEXT, detail TEXT, at TEXT);
            CREATE TABLE IF NOT EXISTS messages(id TEXT PRIMARY KEY, job_id TEXT, sender TEXT, subject TEXT, body TEXT, stage TEXT, at TEXT);
            ''')
            c.execute('CREATE TABLE IF NOT EXISTS answer_memory(id TEXT PRIMARY KEY,scope TEXT NOT NULL,role TEXT NOT NULL,location TEXT NOT NULL,question TEXT NOT NULL,kind TEXT NOT NULL,choices TEXT NOT NULL,answer TEXT NOT NULL,profile_hash TEXT NOT NULL,source_job TEXT NOT NULL,status TEXT NOT NULL,uses INTEGER NOT NULL,updated TEXT NOT NULL)')
            c.execute('CREATE INDEX IF NOT EXISTS memory_scope ON answer_memory(scope,role,location,profile_hash,status)')
            c.execute('CREATE TABLE IF NOT EXISTS drafts(job_id TEXT PRIMARY KEY, payload TEXT NOT NULL, context_hash TEXT NOT NULL, updated TEXT NOT NULL)')
            c.executescript('CREATE INDEX IF NOT EXISTS jobs_updated ON jobs(updated DESC,id); CREATE INDEX IF NOT EXISTS jobs_status_updated ON jobs(status,updated DESC); CREATE INDEX IF NOT EXISTS messages_time ON messages(at DESC);')
            c.execute("UPDATE jobs SET status='uncertain', note='Interrupted session: check portal before retrying.' WHERE status='running'")
    @contextmanager
    def connect(self):
        c = sqlite3.connect(self.db, timeout=20)
        c.row_factory = sqlite3.Row
        try:
            with c:
                yield c
        finally:
            c.close()
    def setting(self, key, default=None):
        with self.connect() as c:
            r = c.execute('SELECT value FROM settings WHERE key=?', (key,)).fetchone()
            return json.loads(r[0]) if r else default
    def save_setting(self, key, value):
        with self.connect() as c:
            c.execute('INSERT OR REPLACE INTO settings VALUES (?,?)', (key, json.dumps(value)))
    def add(self,job):
        self.add_many([job])
        return hashlib.sha256(canonical_url(job['url']).encode()).hexdigest()[:20]
    def add_many(self,jobs):
        rows=[]
        for job in jobs:
            url=canonical_url(job['url'])
            rows.append((hashlib.sha256(url.encode()).hexdigest()[:20],url,job['company'],job['title'],job.get('location',''),job.get('description',''),now()))
        with self.connect() as c:
            before=c.total_changes
            c.executemany('INSERT OR IGNORE INTO jobs(id,url,company,title,location,description,updated) VALUES(?,?,?,?,?,?,?)',rows)
            return c.total_changes-before
    def page(self,search='',status='',limit=100,offset=0):
        limit=max(1,min(200,int(limit)));offset=max(0,int(offset))
        clauses=[];params=[]
        if search:
            escaped=search.replace('!','!!').replace('%','!%').replace('_','!_')
            clauses.append("(company LIKE ? ESCAPE '!' OR title LIKE ? ESCAPE '!' OR location LIKE ? ESCAPE '!')")
            params.extend(['%'+escaped+'%']*3)
        if status:clauses.append('status=?');params.append(status)
        where=' WHERE '+' AND '.join(clauses) if clauses else ''
        with self.connect() as c:
            total=c.execute('SELECT COUNT(*) FROM jobs'+where,params).fetchone()[0]
            # List view never loads large descriptions; detail and document views fetch them on demand.
            rows=[dict(r) for r in c.execute('SELECT id,url,company,title,location,status,note,updated FROM jobs'+where+' ORDER BY updated DESC,id LIMIT ? OFFSET ?',params+[limit,offset])]
        return rows,total
    def counts(self):
        with self.connect() as c:return {r['status']:r['n'] for r in c.execute('SELECT status,COUNT(*) n FROM jobs GROUP BY status')}
    def candidates(self):
        with self.connect() as c:
            cursor=c.execute("SELECT * FROM jobs WHERE status IN ('saved','prepared') ORDER BY updated DESC,id")
            while True:
                rows=cursor.fetchmany(100)
                if not rows:break
                for row in rows:yield dict(row)
    def jobs(self):
        with self.connect() as c:
            return [dict(r) for r in c.execute('SELECT * FROM jobs ORDER BY updated DESC')]
    def job(self, jid):
        with self.connect() as c:
            row = c.execute('SELECT * FROM jobs WHERE id=?', (jid,)).fetchone()
            if not row: raise ValueError('Job not found')
            return dict(row)
    def state(self, jid, state, note=''):
        if state not in STATES: raise ValueError('Invalid status')
        with self.connect() as c:
            c.execute('UPDATE jobs SET status=?,note=?,updated=? WHERE id=?', (state,note,now(),jid))
            c.execute('INSERT INTO events(job_id,kind,detail,at) VALUES(?,?,?,?)', (jid,state,note,now()))
    def claim(self, jid):
        with self.connect() as c:
            changed = c.execute("UPDATE jobs SET status='running',updated=? WHERE id=? AND status IN ('saved','prepared','needs_attention')", (now(),jid)).rowcount
            if not changed: raise ValueError('Already running, submitted, or uncertain. Check the portal before resetting.')
    def events(self):
        with self.connect() as c:
            return [dict(r) for r in c.execute('SELECT * FROM events ORDER BY id DESC LIMIT 300')]

_http_local=threading.local()

def _http_session():
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
    if not hasattr(_http_local,'session'):
        session=requests.Session();session.headers['User-Agent']='ApplyPilot/0.6 personal job assistant'
        adapter=HTTPAdapter(pool_connections=4,pool_maxsize=4,max_retries=Retry(total=2,backoff_factor=.5,status_forcelist=[429,502,503,504],allowed_methods=frozenset(['GET']),respect_retry_after_header=False))
        session.mount('https://',adapter);_http_local.session=session
    return _http_local.session

def fetch_json(url):
    limit=32*1024*1024
    with _http_session().get(url,timeout=(8,25),stream=True) as response:
        response.raise_for_status();payload=bytearray()
        for chunk in response.iter_content(chunk_size=65536):
            payload.extend(chunk)
            if len(payload)>limit:raise ValueError('Company board exceeds the 32 MiB import limit. Add selected job URLs manually.')
        return json.loads(payload)

def import_board(provider, company, region='global'):
    from .sources import board_identifier, extended_board
    company=board_identifier(provider,company)
    if provider in {'Ashby','SmartRecruiters'}:return extended_board(provider,company)
    if provider == 'Greenhouse':
        data = fetch_json(f'https://boards-api.greenhouse.io/v1/boards/{company}/jobs?content=true')
        return [dict(url=j['absolute_url'],company=company,title=j['title'],location=j.get('location',{}).get('name',''),description=plain(j.get('content',''))) for j in data['jobs']]
    if provider == 'Lever':
        host = 'api.eu.lever.co' if region == 'eu' else 'api.lever.co'
        data = fetch_json(f'https://{host}/v0/postings/{company}?mode=json')
        return [dict(url=j['applyUrl'],company=company,title=j['text'],location=j.get('categories',{}).get('location',''),description=plain(j.get('descriptionPlain',j.get('description','')))+' '+plain(' '.join(x.get('content','') for x in j.get('lists',[])))) for j in data]
    raise ValueError('Unsupported provider')

@lru_cache(maxsize=256)
def _skill_pattern(skill):
    return re.compile(r'(?<!\w)'+re.escape(skill.lower())+r'(?!\w)')

def match(profile, job):
    text = (job['title']+' '+job.get('description','')).lower()
    skills = [s.strip() for s in profile.get('skills','').split(',') if s.strip()]
    found = [s for s in skills if _skill_pattern(s).search(text)]
    return {'overlap':len(found), 'skills':found, 'note':'Keyword overlap only; eligibility and sponsorship must be checked.'}

def documents(store, profile, job):
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    if not profile.get('name') or not profile.get('email'):
        raise ValueError('Save your name and email in Profile first.')
    from .sources import hydrate_job
    job=hydrate_job(store,job)
    from .tailoring import current_draft,load_draft
    draft=current_draft(store,profile,job);saved=load_draft(store,job['id'])
    if saved and not draft and saved['payload'].get('approved_resume'):raise ValueError('Your reviewed job draft is outdated. Open Tailor application to review it again or clear it.')
    reviewed=draft if draft and draft.get('approved_resume') else None
    base_profile=profile
    if reviewed and reviewed.get('use_tailored'):profile=dict(profile,**reviewed['resume'])
    dest = store.folder / 'documents' / job['id']
    dest.mkdir(parents=True, exist_ok=True)
    source=None if reviewed and reviewed.get('use_tailored') else store.setting('resume_pdf')
    source_path=Path(source) if source else None
    if source_path and not source_path.is_file():raise ValueError('Your selected original resume PDF is missing. Reimport it in Profile before preparing or applying.')
    source_hash=hashlib.sha256(source_path.read_bytes()).hexdigest() if source_path and source_path.is_file() else None
    fingerprint=hashlib.sha256(json.dumps({'template_version':5,'reviewed':{k:reviewed[k] for k in ('resume','cover_letter','use_tailored')} if reviewed else None,'profile':profile,'job':{k:job.get(k,'') for k in ('title','company','description','url')},'source_hash':source_hash},sort_keys=True).encode()).hexdigest()
    manifest_path=dest/'manifest.json'
    if manifest_path.exists():
        try:
            previous=json.loads(manifest_path.read_text(encoding='utf-8'))
            if previous.get('fingerprint')==fingerprint and all((dest/name).is_file() and hashlib.sha256((dest/name).read_bytes()).hexdigest()==digest for name,digest in previous.get('files',{}).items()) and len(previous.get('files',{}))==4:return dest
        except (OSError,ValueError):pass
    evidence = match(profile, job)
    skills = evidence['skills'] + [s.strip() for s in profile.get('skills','').split(',') if s.strip() and s.strip() not in evidence['skills']]
    resume = [profile['name'], ' | '.join(profile.get(k,'') for k in ('email','phone','location') if profile.get(k)), profile.get('linkedin',''),
              'PROFESSIONAL SUMMARY', profile.get('summary',''), 'SKILLS', ', '.join(skills), 'EXPERIENCE',profile.get('experience',''),
              'PROJECTS',profile.get('projects',''), 'EDUCATION',profile.get('education','')]
    letter = [profile['name'],profile['email'],f"Application: {job['title']} — {job['company']}",'Dear Hiring Team,',
              f"I am applying for the {job['title']} position at {job['company']}.",profile.get('summary','')]
    if evidence['skills']: letter += ['Relevant skills from my background include '+', '.join(evidence['skills'])+'.']
    if profile.get('projects'): letter += [profile['projects']]
    letter += ['Thank you for considering my application. I would welcome the opportunity to discuss my experience.', 'Sincerely,',profile['name']]
    if reviewed:letter=[base_profile['name'],base_profile['email'],reviewed['cover_letter']]
    styles = getSampleStyleSheet()
    styles['Normal'].fontSize=10
    styles['Normal'].leading=14
    for name, lines in [('resume',resume),('cover-letter',letter)]:
        blocks=[]
        for i,line in enumerate(lines):
            if not line: continue
            style=styles['Title'] if i==0 else styles['Heading2'] if line.isupper() else styles['Normal']
            blocks.extend([Paragraph(html.escape(line).replace('\n','<br/>'),style),Spacer(1,9)])
        SimpleDocTemplate(str(dest/f'{name}.pdf'),title=name,author=profile['name'],rightMargin=45,leftMargin=45,topMargin=40,bottomMargin=40).build(blocks)
        (dest/f'{name}.txt').write_text('\n\n'.join(lines),encoding='utf-8')
    if source_hash:
        from pypdf import PdfReader
        shutil.copyfile(source_path,dest/'resume.pdf')
        (dest/'resume.txt').write_text('\n'.join(page.extract_text() or '' for page in PdfReader(source_path).pages),encoding='utf-8')
    files={name:hashlib.sha256((dest/name).read_bytes()).hexdigest() for name in ('resume.pdf','resume.txt','cover-letter.pdf','cover-letter.txt')}
    manifest_path.write_text(json.dumps({'created':now(),'job_url':job['url'],'profile_sha256':hashlib.sha256(json.dumps(profile,sort_keys=True).encode()).hexdigest(),'fingerprint':fingerprint,'files':files,'mode':'reviewed job-specific draft' if reviewed else 'original PDF + factual cover letter' if source_hash else 'extractive templates; no invented facts'},indent=2),encoding='utf-8')
    return dest
