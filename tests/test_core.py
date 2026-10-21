import json
import pytest
from applypilot.core import Store, canonical_url, documents, match, import_board
from applypilot.browser import answers, normalize, known_portal
from applypilot.mail import ingest, classify

@pytest.fixture
def store(tmp_path): return Store(tmp_path)
@pytest.fixture
def job(store):
    jid=store.add(dict(url='https://jobs.lever.co/acme/123/apply',company='Acme',title='Python Engineer',description='Python SQL'))
    return store.job(jid)

def test_dedup(store,job):
    assert store.add(job)==job['id'];assert len(store.jobs())==1

def test_atomic_claim(store,job):
    store.claim(job['id'])
    with pytest.raises(ValueError):store.claim(job['id'])

def test_no_resubmit(store,job):
    store.state(job['id'],'submitted')
    with pytest.raises(ValueError):store.claim(job['id'])

def test_recovery(store,job):
    store.claim(job['id']); reopened=Store(store.folder)
    assert reopened.job(job['id'])['status']=='uncertain'
    with pytest.raises(ValueError):reopened.claim(job['id'])

@pytest.mark.parametrize('url',['http://example.com','file:///etc/passwd','javascript:alert(1)','https://a:b@example.com','https://localhost/apply'])
def test_invalid_url(url):
    with pytest.raises(ValueError):canonical_url(url)

def test_exact_answers_only():
    a=answers({'name':'First Last','email':'a@example.com','answers':{'Are you authorized to work?':'No'}})
    assert a['first name']=='First';assert a['are you authorized to work?']=='No'
    assert 'will you need sponsorship?' not in a
    assert normalize('Email *')=='email'

def test_domain_boundaries():
    assert known_portal('https://jobs.lever.co/acme/a')
    assert not known_portal('https://jobs.lever.co.evil.example/acme')

def test_documents_extract_only(store,job):
    from pypdf import PdfReader
    p={'name':'Test Person','email':'test@example.com','skills':'Python, SQL','summary':'Built a local project.','projects':'Verified project text.'}
    dest=documents(store,p,job)
    text=' '.join(x.extract_text() for x in PdfReader(dest/'resume.pdf').pages)
    assert 'Test Person' in text and 'Verified project text.' in text
    assert 'PhD' not in text
    assert json.loads((dest/'manifest.json').read_text())['job_url']==job['url']

def test_keywords_not_substrings(job):
    assert match({'skills':'Java, Python'},job)['skills']==['Python']

def test_unknown_status(store,job):
    with pytest.raises(ValueError):store.state(job['id'],'success')

def test_email_duplicate_and_advisory(store,job):
    raw=b'From: hiring@acme.test\r\nSubject: Acme interview invitation\r\nContent-Type: text/plain; charset=utf-8\r\n\r\nPlease schedule your interview.'
    ingest(store,raw);ingest(store,raw)
    with store.connect() as c:
        rows=c.execute('SELECT * FROM messages').fetchall()
    assert len(rows)==1 and rows[0]['job_id']==job['id']
    assert store.job(job['id'])['status']=='saved'

def test_ambiguous_mail_no_match(store,job):
    store.add(dict(url='https://jobs.lever.co/acme/456',company='Acme',title='Other role'))
    ingest(store,b'From: hiring@acme.test\r\nSubject: Acme update\r\n\r\nHello')
    with store.connect() as c:assert c.execute('SELECT job_id FROM messages').fetchone()[0] is None

def test_rejection_before_interview():
    assert classify('Interview update','Unfortunately we are proceeding with other candidates')=='possible rejection'

def test_board_validation():
    with pytest.raises(ValueError):import_board('Lever','../../etc')

def test_import_greenhouse(monkeypatch):
    monkeypatch.setattr('applypilot.core.fetch_json',lambda _:dict(jobs=[dict(absolute_url='https://example.com/job',title='Engineer',content='<b>SQL</b>',location={'name':'Remote'})]))
    jobs=import_board('Greenhouse','acme')
    assert jobs[0]['description']=='SQL' and jobs[0]['location']=='Remote'

def test_import_lever_eu(monkeypatch):
    captured=[]
    def fetch(url):
        captured.append(url);return [dict(applyUrl='https://jobs.eu.lever.co/acme/1/apply',text='Engineer',descriptionPlain='Python',categories={'location':'Berlin'})]
    monkeypatch.setattr('applypilot.core.fetch_json',fetch)
    assert import_board('Lever','acme','eu')[0]['location']=='Berlin'
    assert captured[0].startswith('https://api.eu.lever.co/')

def test_large_board_response_not_truncated(monkeypatch):
    from applypilot.core import fetch_json
    payload=b'{"description":"'+b'x'*8_000_001+b'"}'
    class Response:
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def raise_for_status(self):pass
        def iter_content(self,chunk_size):
            for i in range(0,len(payload),chunk_size):yield payload[i:i+chunk_size]
    class Session:
        def get(self,*args,**kwargs):return Response()
    monkeypatch.setattr('applypilot.core._http_session',Session)
    assert len(fetch_json('https://example.com')['description'])==8_000_001
