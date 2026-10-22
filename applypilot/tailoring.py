"""Local, evidence-based application drafts. No model API or invented credentials."""
import difflib
import hashlib
import json
import re
from pathlib import Path
from .core import match, now, _skill_pattern

RESUME_FIELDS=('summary','skills','experience','projects','education')
FACTS={
    'us_work_authorization':'US work authorization (Yes/No)',
    'us_sponsorship':'US sponsorship, now or in future (Yes/No)',
    'salary':'Salary expectation (include currency/period)',
    'notice':'Notice period',
    'start_date':'Available start date',
    'relocation':'Relocation preference',
    'travel':'Travel availability',
    'years':'Total professional experience (years)',
}
CATALOG=('Python','SQL','Java','JavaScript','TypeScript','AWS','Azure','GCP','Spark','PySpark','Kafka','Airflow','dbt','Snowflake','Databricks','Docker','Kubernetes','Terraform','PostgreSQL','Oracle','Spring Boot','Angular','React','PyTorch','TensorFlow','MLflow','scikit-learn','Git','CI/CD','ETL','REST')

def normalized(label):return re.sub(r'\s+',' ',re.sub(r'[*:]+$','',label.strip())).strip().lower()

def context_hash(store,profile,job):
    source=store.setting('resume_pdf');signature=None
    if source:
        path=Path(source)
        signature=(source,path.stat().st_size,path.stat().st_mtime_ns) if path.is_file() else (source,None)
    data={'version':1,'profile':profile,'facts':store.setting('facts',{}),'job':{k:job.get(k,'') for k in ('url','title','company','description')},'original':signature}
    return hashlib.sha256(json.dumps(data,sort_keys=True).encode()).hexdigest()

def load_draft(store,jid):
    with store.connect() as c:row=c.execute('SELECT * FROM drafts WHERE job_id=?',(jid,)).fetchone()
    if not row:return None
    return {'context_hash':row['context_hash'],'payload':json.loads(row['payload']),'updated':row['updated']}

_ANY=object()
class DraftConflict(ValueError):pass

def save_draft(store,jid,payload,context,expected_updated=_ANY):
    store.job(jid)
    if len(json.dumps(payload))>1024*1024:raise ValueError('Draft exceeds 1 MB.')
    updated=now()
    with store.connect() as c:
        c.execute('BEGIN IMMEDIATE')
        previous=c.execute('SELECT updated FROM drafts WHERE job_id=?',(jid,)).fetchone()
        if expected_updated is not _ANY and (previous['updated'] if previous else None)!=expected_updated:raise DraftConflict('Draft changed in another window or browser step. Close and reopen Tailor application.')
        c.execute('INSERT OR REPLACE INTO drafts VALUES (?,?,?,?)',(jid,json.dumps(payload),context,updated))
    return updated

def current_draft(store,profile,job):
    record=load_draft(store,job['id'])
    return record['payload'] if record and record['context_hash']==context_hash(store,profile,job) else None

def clear_draft(store,jid):
    with store.connect() as c:c.execute('DELETE FROM drafts WHERE job_id=?',(jid,))

def paragraphs(value):return [p.strip() for p in re.split(r'\n\s*\n',value.strip()) if p.strip()]

def suggest_answer(question,profile,job,facts=None):
    """Returns a proposal only. Browser use requires separate per-job approval."""
    key=normalized(question);facts=facts or {}
    exact={normalized(k):str(v) for k,v in profile.get('answers',{}).items()}
    if key in exact:return {'answer':exact[key],'evidence':['Saved exact answer'],'missing':[]}
    sensitive=re.search(r'sponsor|authoriz|visa|salary|compensation|pay range|notice|start date|available to start|relocat|travel|how many years|years of|citizen|disabil|gender|ethnic|race|veteran|criminal|convict|security clearance|certif|degree|gpa|graduat|licen[cs]|reference|background check|consent|agree|attest|accept.*terms|confirm.*accurate',key)
    fact=None
    # US legal facts are never transferred to another country's question.
    us=bool(re.search(r'\b(united states|usa|u\.s\.?)\b',key) or re.search(r'\bUS\b',question))
    if us and re.search(r'sponsor',key) and re.search(r'now',key) and re.search(r'future',key):fact='us_sponsorship'
    elif us and re.search(r'legally authorized|authorized to work|work authorization',key) and 'sponsor' not in key:fact='us_work_authorization'
    elif re.search(r'salary|compensation|pay range',key):fact='salary'
    elif 'notice period' in key:fact='notice'
    elif re.search(r'start date|available to start',key):fact='start_date'
    elif 'relocat' in key:fact='relocation'
    elif 'travel' in key:fact='travel'
    elif re.fullmatch(r'how many years of (?:total )?(?:professional|work) experience do you have\??',key):fact='years'
    if fact:
        value=str(facts.get(fact,'')).strip()
        return {'answer':value,'evidence':['Verified fact: '+FACTS[fact]] if value else [],'missing':[] if value else ['Add '+FACTS[fact]]}
    if sensitive:return {'answer':'','evidence':[],'missing':['Your explicit answer is required; no eligibility or numeric inference.']}
    if re.search(r'why.*(company|join|us\b)|what.*motivat|why.*interest',key):return {'answer':'','evidence':[],'missing':['Add your personal reason for this employer or role.']}
    if re.search(r'describe|tell us|tell me|experience|background|project|skills|qualif|strength|fit',key):
        requested=[s for s in CATALOG if _skill_pattern(s).search(key)]
        verified=[s.strip() for s in profile.get('skills','').split(',') if s.strip()]
        if requested and not all(any(s.lower()==v.lower() for v in verified) for s in requested):return {'answer':'','evidence':[],'missing':['Requested technology is not verified in your saved skills.']}
        targets=requested or match(profile,job)['skills']
        evidence=[]
        fields=('projects',) if 'project' in key else ('experience','projects')
        for field in fields:
            for block in paragraphs(profile.get(field,'')):
                if targets and any(_skill_pattern(s).search(block.lower()) for s in targets):evidence.append((field,block))
        if evidence:
            chosen=evidence[:2]
            return {'answer':'\n\n'.join(block for _,block in chosen),'evidence':[field+': '+block for field,block in chosen],'missing':[]}
        return {'answer':'','evidence':[],'missing':['Add a relevant factual example in Profile.']}
    return {'answer':'','evidence':[],'missing':['Question needs your own verified answer.']}

def generate_draft(store,profile,job,questions=None):
    if not profile.get('name') or '@' not in profile.get('email',''):raise ValueError('Save your profile name and email first.')
    if not job.get('description','').strip():raise ValueError('Add the job description before drafting.')
    found=match(profile,job)['skills'];skills=[s.strip() for s in profile.get('skills','').split(',') if s.strip()]
    ordered=found+[s for s in skills if s not in found]
    projects=paragraphs(profile.get('projects',''))
    projects.sort(key=lambda block:sum(bool(_skill_pattern(s).search(block.lower())) for s in found),reverse=True)
    resume={k:profile.get(k,'') for k in RESUME_FIELDS}
    resume['skills']=', '.join(ordered);resume['projects']='\n\n'.join(projects)
    if found:resume['summary']=(profile.get('summary','').strip()+'\nRelevant strengths for this application: '+', '.join(found)+'.').strip()
    cover=f"Dear Hiring Team,\n\nI am applying for the {job['title']} position at {job['company']}."
    if profile.get('summary'):cover+='\n\n'+profile['summary']
    if found:cover+='\n\nRelevant skills from my background include '+', '.join(found)+'.'
    relevant=[block for block in projects if any(_skill_pattern(s).search(block.lower()) for s in found)]
    if relevant:cover+='\n\n'+relevant[0]
    cover+='\n\nThank you for considering my application.\n\nSincerely,\n'+profile['name']
    known=' '.join(profile.get(k,'') for k in ('skills','experience','projects','summary','education')).lower()
    gaps=[s for s in CATALOG if _skill_pattern(s).search(job['description'].lower()) and not _skill_pattern(s).search(known)]
    proposals={q:suggest_answer(q,profile,job,store.setting('facts',{})) for q in dict.fromkeys(questions or [])}
    return {'resume':resume,'cover_letter':cover,'questions':proposals,'approved_answers':{},'approved_resume':False,'use_tailored':not bool(store.setting('resume_pdf')),'gaps':gaps,'evidence':{'skills':found,'experience':'Preserved in full to retain employer/date context.','projects':'Only existing paragraphs reordered; no facts rewritten.'}}

def changes(profile,payload):
    result=[]
    for field in RESUME_FIELDS:
        before=profile.get(field,'');after=payload['resume'].get(field,'')
        if before!=after:result.extend(difflib.unified_diff(before.splitlines(),after.splitlines(),fromfile='Saved '+field,tofile='Draft '+field,lineterm=''))
    return '\n'.join(result) or 'Resume sections are unchanged.'

def approved_profile(store,profile,job):
    draft=current_draft(store,profile,job)
    if not draft:return profile
    return dict(profile,answers=dict(profile.get('answers',{}),**draft.get('approved_answers',{})))

def capture_questions(store,profile,job,labels):
    labels=list(dict.fromkeys(label for label in labels if label.strip()))[:100]
    record=load_draft(store,job['id'])
    draft=record['payload'] if record and record['context_hash']==context_hash(store,profile,job) else None
    if not draft:
        if job.get('description','').strip():draft=generate_draft(store,profile,job)
        else:draft={'resume':{k:profile.get(k,'') for k in RESUME_FIELDS},'cover_letter':'','questions':{},'approved_answers':{},'approved_resume':False,'use_tailored':False,'gaps':[],'evidence':{'missing':'Add the job description before tailoring the resume.'}}
    for label in labels:
        if label not in draft['questions']:draft['questions'][label]=suggest_answer(label,profile,job,store.setting('facts',{}))
    try:save_draft(store,job['id'],draft,context_hash(store,profile,job),expected_updated=record['updated'] if record else None)
    except DraftConflict:pass
