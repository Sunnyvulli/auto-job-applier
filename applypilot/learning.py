"""Explicit Resume learns changed visible answers; confirmation enables later reuse."""
import hashlib
import json
import re
from urllib.parse import urlsplit
from datetime import datetime,timedelta,timezone
from .core import now

BLOCKED=re.compile(r'password|passcode|one.time|verification|security code|captcha|authenticat|token|secret|social security|\bssn\b|passport|national.*id|tax.*id|bank|account number|credit card|debit card|birth|\bdob\b|gender|ethnic|\brace\b|veteran|disabil|religion|sexual|medical|consent|\bagree\b|terms|privacy|attest|certify|signature|criminal|background check|reference|\bname\b|\be.?mail\b|phone|address|routing|iban|swift|driver.?s?.?licen[cs]e|national insurance|taxpayer|government.*id|document number|activation code|confirmation code|two.factor|2fa|\botp\b|\bpin\b|^\s*(?:enter\s+)?code\s*[:*]?\s*$',re.I)
KINDS={'text','textarea','select','email','tel','url','number','date','radio'}

def norm(value):return re.sub(r'\s+',' ',re.sub(r'[*:]+$','',value.strip())).strip().lower()

def profile_hash(store):
    return hashlib.sha256(json.dumps({'profile':store.setting('profile',{}),'facts':store.setting('facts',{})},sort_keys=True).encode()).hexdigest()

def employer_scope(url,job):
    p=urlsplit(url)
    if p.scheme!='https' or not p.hostname or p.username or p.password:return None
    origin='https://'+p.netloc.lower();parts=[v for v in p.path.split('/') if v]
    ats={'jobs.lever.co','jobs.eu.lever.co','boards.greenhouse.io','job-boards.greenhouse.io','jobs.ashbyhq.com','jobs.smartrecruiters.com'}
    if p.hostname in ats and (not parts or parts[0].lower() in {'embed','login','signin','sign_in','register','auth'}):return None
    employer=parts[0].lower() if p.hostname in ats and parts else norm(job['company'])
    if not employer:return None
    return origin+' | '+employer

def snapshot(page):
    from .browser import form_frames,field_label,radio_groups
    result={};duplicates=set()
    for frame in form_frames(page):
        for el in frame.locator('input,textarea,select').all():
            try:
                if not el.is_visible() or not el.is_enabled():continue
                tag=el.evaluate('e=>e.tagName.toLowerCase()');kind=tag if tag in {'select','textarea'} else (el.get_attribute('type') or 'text').lower()
                if (kind=='select' and el.get_attribute('multiple') is not None) or kind=='radio' or kind not in KINDS or (el.get_attribute('autocomplete') or '').lower() in {'one-time-code','current-password','new-password'}:continue
                label=field_label(el);question=norm(label)
                if not question or len(question)>2000 or BLOCKED.search(question):continue
                valid=el.evaluate('e=>!e.validity || e.validity.valid')
                choices=el.locator('option').evaluate_all('options=>options.filter(o=>!o.disabled).map(o=>o.textContent.trim())') if kind=='select' else []
                value=el.evaluate('e=>e.tagName==="SELECT"?(e.value?(e.selectedOptions[0]?.textContent||"").trim():""):e.value')
                if len(value)>20000:continue
                key=question
                if key in result:duplicates.add(key)
                result[key]={'question':question,'label':label,'kind':kind,'choices':choices,'answer':value,'maxlength':el.get_attribute('maxlength'),'valid':valid}
            except Exception:continue
    for group in radio_groups(page):
        label=group['label'];key=norm(label)
        if not key or len(key)>2000 or BLOCKED.search(key):continue
        options=group['options'];choices=[name for name,_ in options]
        selected=[name for name,el in options if el.is_checked()]
        if key in result:duplicates.add(key)
        result[key]={'question':key,'label':label,'kind':'radio','choices':choices,'answer':selected[0] if len(selected)==1 else '', 'maxlength':None,'valid':all(el.evaluate('e=>e.validity.valid') for _,el in options)}
    for key in duplicates:result.pop(key,None)
    return result

def remember_corrections(store,job,url,before,after):
    scope=employer_scope(url,job)
    if not scope or not store.setting('learn_answers',True):return 0
    context=profile_hash(store);role=norm(job['title']);location=norm(job.get('location',''));count=0
    with store.connect() as c:
        for question,new in after.items():
            old=before.get(question)
            if not new.get('valid',True) or not old or new['kind']!=old['kind'] or new['choices']!=old['choices'] or new['answer']==old['answer'] or not new['answer'].strip():continue
            if BLOCKED.search(question) or new['kind'] not in KINDS:continue
            choices=json.dumps(new['choices']);value=new['answer']
            identity=hashlib.sha256(json.dumps([scope,role,location,question,new['kind'],choices,context,job['id']]).encode()).hexdigest()[:32]
            # Correcting a reused answer immediately retires its old value.
            c.execute("UPDATE answer_memory SET status='disabled' WHERE scope=? AND role=? AND location=? AND question=? AND kind=? AND choices=? AND status='active'",(scope,role,location,question,new['kind'],choices))
            c.execute('INSERT OR REPLACE INTO answer_memory VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)',(identity,scope,role,location,question,new['kind'],choices,value,context,job['id'],'pending',0,now()));count+=1
    return count

def matching_answers(store,job,url,fields,exclude=()):
    if not store.setting('learn_answers',True):return {},[]
    scope=employer_scope(url,job)
    if not scope:return {},[]
    context=profile_hash(store);cutoff=(datetime.now(timezone.utc)-timedelta(days=90)).isoformat()
    with store.connect() as c:
        rows=[dict(r) for r in c.execute("SELECT * FROM answer_memory WHERE scope=? AND role=? AND location=? AND profile_hash=? AND updated>=? AND (status='active' OR (status='pending' AND source_job=?)) ORDER BY updated DESC",(scope,norm(job['title']),norm(job.get('location','')),context,cutoff,job['id']))]
    mapping={};used=[];seen=set()
    for row in rows:
        question=row['question'];field=fields.get(question)
        if question in exclude or question in seen or not field or BLOCKED.search(question):continue
        if row['kind']!=field['kind'] or row['choices']!=json.dumps(field['choices']):continue
        value=row['answer'];maximum=field.get('maxlength')
        try:
            if maximum is not None and int(maximum)>=0 and len(value.encode('utf-16-le'))//2>int(maximum):continue
        except (ValueError,TypeError):continue
        if field['kind'] in {'select','radio'} and value not in field['choices']:continue
        mapping[question]=value;used.append(row['id']);seen.add(question)
    return mapping,used

def confirm_learning(store,jid,since=None):
    context=profile_hash(store)
    cutoff=since or (datetime.now(timezone.utc)-timedelta(days=1)).isoformat()
    with store.connect() as c:
        pending=c.execute("SELECT * FROM answer_memory WHERE source_job=? AND status='pending' AND profile_hash=? AND updated>=?",(jid,context,cutoff)).fetchall()
        for row in pending:
            c.execute("UPDATE answer_memory SET status='disabled' WHERE scope=? AND role=? AND location=? AND question=? AND kind=? AND choices=? AND id!=?",tuple(row[k] for k in ('scope','role','location','question','kind','choices','id')))
            c.execute("UPDATE answer_memory SET status='active',updated=? WHERE id=?",(now(),row['id']))
        return len(pending)

def disable_used(store,ids):
    with store.connect() as c:c.executemany("UPDATE answer_memory SET status='disabled',updated=? WHERE id=?",[(now(),i) for i in ids])

def record_use(store,ids):
    with store.connect() as c:c.executemany('UPDATE answer_memory SET uses=uses+1 WHERE id=?',[(i,) for i in ids])

def memories(store):
    with store.connect() as c:return [dict(r) for r in c.execute('SELECT * FROM answer_memory ORDER BY updated DESC LIMIT 500')]

def update_memory(store,ids,action):
    if action not in {'delete','disable','enable'}:raise ValueError('Invalid memory action.')
    with store.connect() as c:
        for identity in ids:
            if action=='delete':c.execute('DELETE FROM answer_memory WHERE id=?',(identity,))
            else:c.execute('UPDATE answer_memory SET status=?,profile_hash=?,updated=? WHERE id=?',('active' if action=='enable' else 'disabled',profile_hash(store),now(),identity))
