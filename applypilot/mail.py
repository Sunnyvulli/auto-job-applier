import email
import hashlib
import imaplib
import re
import smtplib
import ssl
from email.message import EmailMessage
from email.policy import default
from .core import now, plain

HOSTS={'Gmail':('imap.gmail.com','smtp.gmail.com'),'Outlook':('outlook.office365.com','smtp.office365.com')}

def parse_message(raw):
    msg=email.message_from_bytes(raw,policy=default)
    part=msg.get_body(preferencelist=('plain','html')) if msg.is_multipart() else msg
    body=part.get_content() if part and part.get_content_type() in {'text/plain','text/html'} else ''
    if part and part.get_content_type()=='text/html':body=plain(body)
    return {'id':hashlib.sha256(raw).hexdigest(),'sender':str(msg.get('From','')),'subject':str(msg.get('Subject','')),'body':str(body)[:50000]}

def classify(subject,body):
    text=(subject+' '+body).lower()
    if re.search(r'not (?:be )?(?:moving|proceeding)|unfortunately|other candidates|not selected',text): return 'possible rejection'
    if re.search(r'interview|schedule a call|availability|assessment invitation',text): return 'possible interview/action'
    if re.search(r'application (?:received|submitted)|thank you for applying',text): return 'confirmation'
    return 'unclassified'

def ingest(store,raw):
    m=parse_message(raw)
    text=(m['subject']+' '+m['body']).lower()
    matches=[j for j in store.jobs() if j['url'].lower() in text or (len(j['company'])>=3 and re.search(r'\b'+re.escape(j['company'].lower())+r'\b',text))]
    jid=matches[0]['id'] if len(matches)==1 else None
    stage=classify(m['subject'],m['body'])
    with store.connect() as c:
        c.execute('INSERT OR IGNORE INTO messages VALUES(?,?,?,?,?,?,?)',(m['id'],jid,m['sender'],m['subject'],m['body'],stage,now()))
    return stage

def recent_raw(provider,address,limit=100):
    import keyring
    password=keyring.get_password('ApplyPilotMail',address)
    if not password:raise ValueError('Save a mail app password first, or select Gmail OAuth.')
    host=HOSTS[provider][0]
    with imaplib.IMAP4_SSL(host,ssl_context=ssl.create_default_context()) as client:
        client.login(address,password);client.select('INBOX',readonly=True)
        status,data=client.uid('search',None,'ALL')
        if status!='OK':raise ValueError('Inbox search failed')
        for uid in reversed(data[0].split()[-limit:]):
            status,items=client.uid('fetch',uid,'(BODY.PEEK[])')
            if status=='OK':
                for item in items:
                    if isinstance(item,tuple):yield item[1]

def sync(store, provider, address):
    if provider=='Gmail OAuth':
        from .google_mail import sync as gmail_sync
        return gmail_sync(store)
    count=0
    for raw in recent_raw(provider,address):ingest(store,raw);count+=1
    return count

def send(provider,address,to,subject,body):
    if provider=='Gmail OAuth':
        from .google_mail import send as gmail_send
        return gmail_send(to,subject,body)
    import keyring
    from email.utils import parseaddr
    if any('\n' in s or '\r' in s for s in (address,to,subject)): raise ValueError('Invalid mail header')
    if not parseaddr(to)[1] or '@' not in parseaddr(to)[1]: raise ValueError('Enter a recipient email')
    password=keyring.get_password('ApplyPilotMail',address)
    if not password: raise ValueError('No saved app password')
    msg=EmailMessage();msg['From']=address;msg['To']=to;msg['Subject']=subject;msg.set_content(body)
    with smtplib.SMTP(HOSTS[provider][1],587,timeout=25) as server:
        server.starttls(context=ssl.create_default_context());server.login(address,password);server.send_message(msg)
