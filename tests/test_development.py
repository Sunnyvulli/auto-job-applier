import json
import pytest
from datetime import datetime,timezone,timedelta
from email.message import EmailMessage
from email.utils import format_datetime
from applypilot.core import Store,import_board
from applypilot.sources import board_identifier
from applypilot import accounts,mail,google_mail
from applypilot.verification import extract_code,find_code,fill_code

@pytest.fixture
def vault(monkeypatch):
    import keyring
    data={}
    monkeypatch.setattr(keyring,'set_password',lambda s,u,p:data.__setitem__((s,u),p))
    monkeypatch.setattr(keyring,'get_password',lambda s,u:data.get((s,u)))
    monkeypatch.setattr(keyring,'delete_password',lambda s,u:data.pop((s,u),None))
    return data

def test_board_url_normalization():
    assert board_identifier('Ashby','https://jobs.ashbyhq.com/acme')=='acme'
    assert board_identifier('Lever','https://jobs.eu.lever.co/acme/123')=='acme'
    with pytest.raises(ValueError):board_identifier('Ashby','https://jobs.ashbyhq.com.evil.test/acme')

def test_ashby_listed_only(monkeypatch):
    monkeypatch.setattr('applypilot.sources.fetch_json',lambda _: {'jobs':[dict(title='Engineer',applyUrl='https://jobs.ashbyhq.com/acme/1/apply',descriptionPlain='SQL',location='Remote'),dict(title='Hidden',jobUrl='https://example.com',isListed=False)]})
    jobs=import_board('Ashby','acme');assert len(jobs)==1 and jobs[0]['description']=='SQL'

def test_smartrecruiters_pagination(monkeypatch):
    calls=[]
    def fetch(url):
        calls.append(url);i=len(calls)
        return {'totalFound':2,'content':[{'id':str(i),'name':'Engineer','location':{'city':'Pune','country':'IN'}}]}
    monkeypatch.setattr('applypilot.sources.fetch_json',fetch)
    jobs=import_board('SmartRecruiters','acme')
    assert len(jobs)==2 and 'offset=1' in calls[1]
    assert jobs[0]['url']=='https://jobs.smartrecruiters.com/acme/1'

def test_repeated_page_fails(monkeypatch):
    monkeypatch.setattr('applypilot.sources.fetch_json',lambda _:{'totalFound':200,'content':[{'id':'1','name':'Role'}]})
    with pytest.raises(ValueError,match='repeated'):import_board('SmartRecruiters','acme')

def test_account_password_not_in_database(tmp_path,vault):
    store=Store(tmp_path);origin=accounts.save_account(store,'https://careers.example.com/signup','me@example.com')
    password=vault[('ApplyPilotPortal:'+origin,'me@example.com')]
    assert len(password)==24 and password.encode() not in store.db.read_bytes()
    assert store.setting('accounts')=={origin:'me@example.com'}

@pytest.mark.parametrize('url',['http://portal.example.com','https://user:pass@portal.example.com','https://portal.example.com:8443'])
def test_account_rejects_unsafe_origins(url):
    with pytest.raises(ValueError):accounts.account_origin(url)

def raw_code(sender='verify@employer.example',recipient='me@example.com',date=None,text='Your verification code is 123456'):
    msg=EmailMessage();msg['From']=sender;msg['To']=recipient;msg['Date']=format_datetime(date or datetime.now(timezone.utc));msg['Subject']='Verify your email';msg.set_content(text);return msg.as_bytes()

def test_code_fresh_exact_sender_recipient():
    start=datetime.now(timezone.utc).isoformat()
    assert extract_code(raw_code(),'me@example.com','verify@employer.example',start)=='123456'
    assert extract_code(raw_code(sender='bad@employer.example'),'me@example.com','verify@employer.example',start) is None
    assert extract_code(raw_code(recipient='other@example.com'),'me@example.com','verify@employer.example',start) is None

def test_code_stale_and_ambiguous_rejected():
    start=datetime.now(timezone.utc).isoformat()
    assert extract_code(raw_code(date=datetime.now(timezone.utc)-timedelta(hours=1)),'me@example.com','verify@employer.example',start) is None
    with pytest.raises(ValueError):find_code([raw_code(),raw_code(text='Your verification code is 654321')],'me@example.com','verify@employer.example',start)

def test_code_not_extracted_from_ordinary_mail():
    msg=raw_code(text='Invoice 123456 and report 654321')
    assert extract_code(msg,'me@example.com','verify@employer.example',datetime.now(timezone.utc).isoformat()) is None

def test_html_email_classification():
    msg=EmailMessage();msg['Subject']='Update';msg.set_content('<p>Your application received. Thank you for applying</p>',subtype='html')
    m=mail.parse_message(msg.as_bytes());assert '<p>' not in m['body'] and mail.classify(m['subject'],m['body'])=='confirmation'

def test_google_config_validation(tmp_path,vault):
    path=tmp_path/'client.json';path.write_text(json.dumps({'installed':{'auth_uri':'https://evil.example','token_uri':'https://oauth2.googleapis.com/token','client_id':'a.apps.googleusercontent.com'}}))
    with pytest.raises(ValueError):google_mail.import_client(path)
    cfg={'installed':{'auth_uri':'https://accounts.google.com/o/oauth2/auth','token_uri':'https://oauth2.googleapis.com/token','client_id':'a.apps.googleusercontent.com','client_secret':'synthetic'}}
    path.write_text(json.dumps(cfg));google_mail.import_client(path)
    assert ('ApplyPilotGoogle','client-config') in vault

def test_db_context_closes(tmp_path):
    store=Store(tmp_path)
    with store.connect() as connection:connection.execute('SELECT 1')
    import sqlite3
    with pytest.raises(sqlite3.ProgrammingError):connection.execute('SELECT 1')

def test_smartrecruiters_selected_job_details(tmp_path,monkeypatch):
    from applypilot.sources import hydrate_job
    store=Store(tmp_path)
    jid=store.add(dict(url='https://jobs.smartrecruiters.com/Acme/123-role',company='Acme',title='Role'))
    urls=[]
    def fetch(url):
        urls.append(url);return {'jobAd':{'sections':{'jobDescription':{'text':'<p>SQL pipelines</p>'},'qualifications':{'text':'Python'}}}}
    monkeypatch.setattr('applypilot.sources.fetch_json',fetch)
    job=hydrate_job(store,store.job(jid))
    assert 'SQL pipelines' in job['description'] and 'Python' in store.job(jid)['description']
    assert urls==['https://api.smartrecruiters.com/v1/companies/Acme/postings/123']

def test_oauth_connect_scopes_and_loopback(vault,monkeypatch):
    from google_auth_oauthlib.flow import InstalledAppFlow
    vault[('ApplyPilotGoogle','client-config')]='{"installed":{}}'
    captured={}
    class Credentials:
        def to_json(self):return '{"token":"synthetic"}'
    class Flow:
        def run_local_server(self,**kwargs):captured['loopback']=kwargs;return Credentials()
    def factory(config,scopes,**kwargs):captured['scopes']=scopes;captured['pkce']=kwargs;return Flow()
    monkeypatch.setattr(InstalledAppFlow,'from_client_config',factory)
    google_mail.connect(False)
    assert captured['scopes']==[google_mail.READ] and captured['pkce']['autogenerate_code_verifier']
    assert captured['loopback']['host']=='127.0.0.1' and captured['loopback']['port']==0
    assert captured['loopback']['timeout_seconds']==180
    google_mail.connect(True);assert google_mail.SEND in captured['scopes']
    assert ('ApplyPilotGoogle','token') in vault

def test_gmail_raw_sync_readonly_endpoints(monkeypatch,tmp_path):
    import base64
    store=Store(tmp_path);requests=[]
    raw=b'From: hiring@example.com\r\nSubject: Interview invitation\r\n\r\nPlease schedule your interview.'
    class Response:
        ok=True;status_code=200
        def __init__(self,data):self.data=data
        def json(self):return self.data
    class Session:
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def get(self,url,**kwargs):
            requests.append((url,kwargs))
            return Response({'messages':[{'id':'abc'}]} if url.endswith('/messages') else {'raw':base64.urlsafe_b64encode(raw).decode()})
    monkeypatch.setattr(google_mail,'session',Session)
    assert google_mail.sync(store)==1
    assert all('/gmail/v1/users/me/messages' in url for url,_ in requests)
    with store.connect() as c:assert c.execute('SELECT stage FROM messages').fetchone()[0]=='possible interview/action'

def test_gmail_send_uses_verified_account(monkeypatch):
    import base64,email
    captured={}
    class Response:
        ok=True;status_code=200
        def __init__(self,data):self.data=data
        def json(self):return self.data
    class Session:
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def get(self,*a,**k):return Response({'emailAddress':'verified@example.com'})
        def post(self,url,**kwargs):captured.update(kwargs);return Response({'id':'sent'})
    monkeypatch.setattr(google_mail,'session',Session)
    google_mail.send('recruiter@example.com','Follow-up','My approved message')
    msg=email.message_from_bytes(base64.urlsafe_b64decode(captured['json']['raw']))
    assert msg['From']=='verified@example.com' and msg['To']=='recruiter@example.com'
    with pytest.raises(ValueError):google_mail.send('a@example.com','Header\r\nBcc: x@example.com','body')
