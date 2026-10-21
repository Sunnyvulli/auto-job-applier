import hashlib
import html
import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, urlopen

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
            c.executescript('''
            CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY, url TEXT UNIQUE NOT NULL,
            company TEXT NOT NULL, title TEXT NOT NULL, location TEXT NOT NULL DEFAULT '',
            description TEXT NOT NULL DEFAULT '', status TEXT NOT NULL DEFAULT 'saved',
            note TEXT NOT NULL DEFAULT '', updated TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY, job_id TEXT, kind TEXT, detail TEXT, at TEXT);
            CREATE TABLE IF NOT EXISTS messages(id TEXT PRIMARY KEY, job_id TEXT, sender TEXT, subject TEXT, body TEXT, stage TEXT, at TEXT);
            ''')
            c.execute("UPDATE jobs SET status='uncertain', note='Interrupted session: check portal before retrying.' WHERE status='running'")
    def connect(self):
        c = sqlite3.connect(self.db, timeout=20)
        c.row_factory = sqlite3.Row
        return c
    def setting(self, key, default=None):
        with self.connect() as c:
            r = c.execute('SELECT value FROM settings WHERE key=?', (key,)).fetchone()
            return json.loads(r[0]) if r else default
    def save_setting(self, key, value):
        with self.connect() as c:
            c.execute('INSERT OR REPLACE INTO settings VALUES (?,?)', (key, json.dumps(value)))
    def add(self, job):
        url = canonical_url(job['url'])
        jid = hashlib.sha256(url.encode()).hexdigest()[:20]
        with self.connect() as c:
            c.execute('INSERT OR IGNORE INTO jobs(id,url,company,title,location,description,updated) VALUES(?,?,?,?,?,?,?)',
                      (jid, url, job['company'], job['title'], job.get('location',''), job.get('description',''), now()))
        return jid
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

def fetch_json(url):
    req = Request(url, headers={'User-Agent':'ApplyPilot/0.1 personal job assistant'})
    with urlopen(req, timeout=25) as r:
        limit=32 * 1024 * 1024
        payload=r.read(limit+1)
        if len(payload)>limit: raise ValueError('Company board exceeds the 32 MiB import limit. Add selected job URLs manually.')
        return json.loads(payload)

def import_board(provider, company, region='global'):
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,100}', company):
        raise ValueError('Enter the board identifier, not a URL.')
    if provider == 'Greenhouse':
        data = fetch_json(f'https://boards-api.greenhouse.io/v1/boards/{company}/jobs?content=true')
        return [dict(url=j['absolute_url'],company=company,title=j['title'],location=j.get('location',{}).get('name',''),description=plain(j.get('content',''))) for j in data['jobs']]
    if provider == 'Lever':
        host = 'api.eu.lever.co' if region == 'eu' else 'api.lever.co'
        data = fetch_json(f'https://{host}/v0/postings/{company}?mode=json')
        return [dict(url=j['applyUrl'],company=company,title=j['text'],location=j.get('categories',{}).get('location',''),description=plain(j.get('descriptionPlain',j.get('description','')))+' '+plain(' '.join(x.get('content','') for x in j.get('lists',[])))) for j in data]
    raise ValueError('Unsupported provider')

def match(profile, job):
    text = (job['title']+' '+job.get('description','')).lower()
    skills = [s.strip() for s in profile.get('skills','').split(',') if s.strip()]
    found = [s for s in skills if re.search(r'(?<!\w)'+re.escape(s.lower())+r'(?!\w)',text)]
    return {'overlap':len(found), 'skills':found, 'note':'Keyword overlap only; eligibility and sponsorship must be checked.'}

def documents(store, profile, job):
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    if not profile.get('name') or not profile.get('email'):
        raise ValueError('Save your name and email in Profile first.')
    dest = store.folder / 'documents' / job['id']
    dest.mkdir(parents=True, exist_ok=True)
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
    (dest/'manifest.json').write_text(json.dumps({'created':now(),'job_url':job['url'],'profile_sha256':hashlib.sha256(json.dumps(profile,sort_keys=True).encode()).hexdigest(),'mode':'extractive templates; no invented facts'},indent=2),encoding='utf-8')
    return dest
