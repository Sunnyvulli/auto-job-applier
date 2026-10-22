"""Versioned data-only backups. Never export vault secrets or browser sessions."""
import hashlib
import json
import os
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from .core import canonical_url, STATES, now

SETTINGS={'profile','preferences','boards','theme','planned_queue','resume_pdf','facts'}
COLUMNS={
    'answer_memory':('id','scope','role','location','question','kind','choices','answer','profile_hash','source_job','status','uses','updated'),
    'drafts':('job_id','payload','context_hash','updated'),
    'jobs':('id','url','company','title','location','description','status','note','updated'),
    'events':('id','job_id','kind','detail','at'),
    'messages':('id','job_id','sender','subject','body','stage','at'),
}
MAX_DATA=64*1024*1024
MAX_PDF=20*1024*1024

def create_backup(store,path):
    path=Path(path)
    if path.resolve()==store.db.resolve():raise ValueError('Choose a separate backup file.')
    with store.connect() as c:
        c.execute('BEGIN')
        data={table:[dict(r) for r in c.execute('SELECT * FROM '+table)] for table in COLUMNS}
        data['settings']={r['key']:json.loads(r['value']) for r in c.execute('SELECT * FROM settings') if r['key'] in SETTINGS}
    source=data['settings'].pop('resume_pdf',None)
    if source and path.resolve()==Path(source).resolve():raise ValueError('Choose a backup file separate from your resume.')
    valid_ids={row['id'] for row in data['jobs']}
    data['settings']['planned_queue']=list(dict.fromkeys(jid for jid in data['settings'].get('planned_queue',[]) if jid in valid_ids))[:50]
    payload=json.dumps(data,ensure_ascii=False).encode('utf-8')
    if len(payload)>MAX_DATA:raise ValueError('Backup data exceeds 64 MB. Export a smaller workspace.')
    files={'data.json':payload}
    if source:
        source=Path(source)
        if not source.is_file():raise ValueError('Original resume PDF is missing. Reimport it or disable it before backing up.')
        if source.stat().st_size>MAX_PDF:raise ValueError('Original resume PDF exceeds 20 MB.')
        files['resume.pdf']=source.read_bytes()
    manifest={'format':'ApplyPilot backup','version':1,'created':now(),'files':{n:hashlib.sha256(v).hexdigest() for n,v in files.items()}}
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent,suffix='.tmp',delete=False) as f:temporary=Path(f.name)
        with zipfile.ZipFile(temporary,'w',compression=zipfile.ZIP_DEFLATED) as z:
            z.writestr('manifest.json',json.dumps(manifest))
            for name,value in files.items():z.writestr(name,value)
        os.replace(temporary,path)
    finally:
        if temporary and temporary.exists():temporary.unlink()
    return path

def read_backup(path):
    with zipfile.ZipFile(path) as z:
        entries=z.infolist();names=[e.filename for e in entries]
        if len(names)!=len(set(names)) or set(names) not in ({'manifest.json','data.json'},{'manifest.json','data.json','resume.pdf'}):raise ValueError('Backup has unexpected or duplicate files.')
        limits={'manifest.json':4096,'data.json':MAX_DATA,'resume.pdf':MAX_PDF}
        if any(e.file_size>limits[e.filename] for e in entries):raise ValueError('Backup exceeds size limits.')
        manifest=json.loads(z.read('manifest.json'))
        if manifest.get('format')!='ApplyPilot backup' or manifest.get('version')!=1:raise ValueError('Unsupported backup format.')
        files={n:z.read(n) for n in names if n!='manifest.json'}
        if manifest.get('files')!={n:hashlib.sha256(v).hexdigest() for n,v in files.items()}:raise ValueError('Backup integrity check failed.')
        data=json.loads(files['data.json']);validate_data(data)
        if 'resume.pdf' in files:
            from io import BytesIO
            from pypdf import PdfReader
            reader=PdfReader(BytesIO(files['resume.pdf']))
            if reader.is_encrypted or len(reader.pages)>20:raise ValueError('Unsupported resume in backup.')
        return data,files.get('resume.pdf')

def validate_data(data):
    if isinstance(data,dict) and set(COLUMNS)-{'drafts','answer_memory'}<=set(data) and set(data)<=set(COLUMNS)|{'settings'}:
        data.setdefault('drafts',[]);data.setdefault('answer_memory',[])
    if not isinstance(data,dict) or set(data)!=set(COLUMNS)|{'settings'}:raise ValueError('Invalid backup data.')
    settings=data['settings']
    if not isinstance(settings,dict) or not set(settings)<=SETTINGS-{'resume_pdf'}:raise ValueError('Invalid backup settings.')
    if not isinstance(settings.get('profile',{}),dict) or not isinstance(settings.get('preferences',{}),dict):raise ValueError('Invalid profile or preferences.')
    profile=settings.get('profile',{})
    if any(not isinstance(v,str) for k,v in profile.items() if k!='answers') or not isinstance(profile.get('answers',{}),dict) or any(not isinstance(k,str) or not isinstance(v,str) for k,v in profile.get('answers',{}).items()):raise ValueError('Invalid profile fields.')
    prefs=settings.get('preferences',{})
    if any(not isinstance(prefs.get(k,''),str) for k in ('titles','locations','exclude','browser')):raise ValueError('Invalid preference fields.')
    if not 0<=int(prefs.get('min_skills',0))<=50 or not 1<=int(prefs.get('queue_limit',10))<=50:raise ValueError('Invalid preference limits.')
    if any(type(prefs[k]) is not bool for k in ('exclude_senior','low_resource') if k in prefs):raise ValueError('Invalid preference flags.')
    if prefs.get('browser','auto') not in {'auto','bundled','msedge','chrome'}:raise ValueError('Invalid browser preference.')
    boards=settings.get('boards',[])
    if not isinstance(boards,list) or len(boards)>1000:raise ValueError('Invalid source list.')
    from .sources import PROVIDERS,board_identifier
    for board in boards:
        if not isinstance(board,dict) or set(board)!={'provider','company','region'} or board['provider'] not in PROVIDERS or board['region'] not in {'global','eu'}:raise ValueError('Invalid source.')
        board_identifier(board['provider'],board['company'])
    if settings.get('theme','light') not in {'light','dark'}:raise ValueError('Invalid theme.')
    facts=settings.get('facts',{})
    from .tailoring import FACTS
    if not isinstance(facts,dict) or not set(facts)<=set(FACTS) or any(not isinstance(v,str) or len(v)>1000 for v in facts.values()):raise ValueError('Invalid fact bank.')
    ids=set()
    for table,columns in COLUMNS.items():
        rows=data[table]
        if not isinstance(rows,list) or len(rows)>100000:raise ValueError('Invalid backup row count.')
        primary=set()
        for row in rows:
            if not isinstance(row,dict) or set(row)!=set(columns):raise ValueError('Invalid '+table+' record.')
            for key,value in row.items():
                if (table=='events' and key=='id') or (table=='answer_memory' and key=='uses'):
                    if type(value) is not int or value<(0 if key=='uses' else 1):raise ValueError('Invalid event ID.')
                elif value is not None and not isinstance(value,str):raise ValueError('Invalid record value.')
            identity=row['job_id'] if table=='drafts' else row['id']
            if identity is None:raise ValueError('Missing record ID.')
            if identity in primary:raise ValueError('Duplicate backup record.')
            primary.add(identity)
            if table=='jobs':
                if any(not isinstance(row[k],str) for k in columns):raise ValueError('Invalid job value.')
                if row['status'] not in STATES or hashlib.sha256(canonical_url(row['url']).encode()).hexdigest()[:20]!=row['id']:raise ValueError('Invalid job identity or status.')
                ids.add(row['id'])
    from .learning import KINDS,BLOCKED
    for row in data['answer_memory']:
        if row['source_job'] not in ids or row['kind'] not in KINDS or BLOCKED.search(row['question']) or not row['answer'] or len(row['answer'])>20000:raise ValueError('Invalid learned answer.')
        choices=json.loads(row['choices'])
        if not isinstance(choices,list) or any(not isinstance(v,str) for v in choices):raise ValueError('Invalid learned choices.')
        if row['kind'] in {'select','radio'} and row['answer'] not in choices:raise ValueError('Invalid learned selection.')
        if row['status'] not in {'active','disabled','pending'}:raise ValueError('Invalid memory status.')
        row['status']='disabled'
    for row in data['drafts']:
        if row['job_id'] not in ids or not isinstance(row['payload'],str):raise ValueError('Invalid draft job.')
        payload=json.loads(row['payload'])
        if not isinstance(payload,dict):raise ValueError('Invalid draft payload.')
        # Restored drafts are editable proposals; all approvals must be renewed.
        payload['approved_resume']=False;payload['approved_answers']={}
        if not isinstance(payload.get('resume'),dict) or set(payload['resume'])!=set(('summary','skills','experience','projects','education')) or any(not isinstance(v,str) for v in payload['resume'].values()):raise ValueError('Invalid draft resume.')
        if not isinstance(payload.get('cover_letter'),str) or not isinstance(payload.get('questions'),dict) or not isinstance(payload.get('gaps'),list) or not isinstance(payload.get('evidence'),dict):raise ValueError('Invalid draft content.')
        if type(payload.get('use_tailored')) is not bool or any(not isinstance(v,str) for v in payload['gaps']):raise ValueError('Invalid draft options.')
        for question,proposal in payload['questions'].items():
            if not isinstance(question,str) or not isinstance(proposal,dict) or not isinstance(proposal.get('answer'),str) or any(not isinstance(proposal.get(k),list) or any(not isinstance(v,str) for v in proposal[k]) for k in ('evidence','missing')):raise ValueError('Invalid question draft.')
        row['payload']=json.dumps(payload)
    queue=settings.get('planned_queue',[])
    if not isinstance(queue,list) or any(not isinstance(jid,str) or jid not in ids for jid in queue) or len(queue)!=len(set(queue)) or len(queue)>50:raise ValueError('Invalid saved queue.')

def restore_backup(store,path):
    """Caller must stop workers first. Validate all input before any mutation."""
    data,pdf=read_backup(path)
    safety=create_backup(store,store.folder/'backups'/('before-restore-'+datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S-%f')+'.applypilot'))
    resume=None;archived=None
    documents=store.folder/'documents'
    try:
        if pdf:
            with tempfile.NamedTemporaryFile(dir=store.folder,prefix='restored-resume-',suffix='.pdf',delete=False) as f:
                f.write(pdf);resume=Path(f.name)
        if documents.exists():
            archived=store.folder/'backups'/(safety.stem+'-documents')
            documents.rename(archived)
        with store.connect() as c:
            for table in COLUMNS:
                c.execute('DELETE FROM '+table)
                columns=COLUMNS[table]
                c.executemany('INSERT INTO '+table+'('+','.join(columns)+') VALUES('+','.join('?' for _ in columns)+')',[[row[k] for k in columns] for row in data[table]])
            c.execute('DELETE FROM settings')
            settings=dict(data['settings'],auto_submit=False,learn_answers=False,repeat_sources=False,repeat_mail=False,resume_pdf=str(resume) if resume else None)
            c.executemany('INSERT INTO settings VALUES (?,?)',[(k,json.dumps(v)) for k,v in settings.items()])
            c.execute("UPDATE jobs SET status='uncertain',note='Restored interrupted application: check portal before retrying.' WHERE status IN ('running','needs_attention')")
        return safety
    except Exception:
        if resume:resume.unlink(missing_ok=True)
        if archived and archived.exists():archived.rename(documents)
        raise

def daily_backup(store):
    folder=store.folder/'backups';folder.mkdir(exist_ok=True)
    path=folder/('daily-'+datetime.now(timezone.utc).strftime('%Y%m%d')+'.applypilot')
    if path.exists():return None
    create_backup(store,path)
    for old in sorted(folder.glob('daily-*.applypilot'),reverse=True)[5:]:old.unlink()
    return 'Daily local recovery backup saved. Backups contain personal data; protect your Windows account.'
