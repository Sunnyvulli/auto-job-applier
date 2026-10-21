import pytest
from playwright.sync_api import sync_playwright
from applypilot.browser import fill_page

@pytest.fixture
def page():
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        page=browser.new_page();yield page;browser.close()

def test_real_browser_known_fields_and_unknown(page,tmp_path):
    page.set_content('''<label>First name *<input required></label><label>Email *<input type=email required></label><label>Do you need sponsorship? *<select required><option value="">Choose</option><option>Yes</option><option>No</option></select></label><label>Password<input type=password required></label>''')
    missing=fill_page(page,{'name':'Alex Smith','email':'alex@example.com'},tmp_path)
    assert page.locator('input').nth(0).input_value()=='Alex'
    assert page.locator('input').nth(1).input_value()=='alex@example.com'
    assert any('sponsorship' in x for x in missing)
    assert 'Password' in missing
    assert page.locator('select').input_value()==''

def test_real_browser_exact_select_and_escaping(page,tmp_path):
    page.set_content('<label>Work authorization *<select required><option value="">Choose</option><option>No</option><option>Yes</option></select></label><label>Full name<input></label>')
    missing=fill_page(page,{'name':'<script>alert(1)</script>','answers':{'Work authorization':'No'}},tmp_path)
    assert page.locator('select').input_value()=='No'
    assert page.locator('input').input_value()=='<script>alert(1)</script>'
    assert not missing

def test_real_browser_does_not_click_consent(page,tmp_path):
    page.set_content('<label>Accept terms *<input type=checkbox required></label><button>Submit</button>')
    assert fill_page(page,{},tmp_path)
    assert not page.locator('input').is_checked()

def test_real_browser_uploads_correct_documents(page,tmp_path):
    (tmp_path/'resume.pdf').write_bytes(b'resume');(tmp_path/'cover-letter.pdf').write_bytes(b'cover')
    page.set_content('<label>Resume<input type=file></label><label>Cover letter<input type=file></label>')
    fill_page(page,{},tmp_path)
    assert page.locator('input').nth(0).evaluate('e=>e.files[0].name')=='resume.pdf'
    assert page.locator('input').nth(1).evaluate('e=>e.files[0].name')=='cover-letter.pdf'

def test_full_automatic_queue_receipt(tmp_path,monkeypatch):
    import playwright.sync_api as api
    from applypilot.browser import BrowserWorker
    from applypilot.core import Store
    real=api.sync_playwright
    class Chromium:
        def __init__(self,engine):self.engine=engine
        def launch_persistent_context(self,path,**kwargs):
            ctx=self.engine.launch_persistent_context(path,headless=True)
            ctx.route('**/*',lambda route:route.fulfill(content_type='text/html',body='''<label>Full name<input required></label><label>Email<input type=email required></label><button onclick="document.body.innerHTML='Thank you for applying. Application submitted.'">Submit application</button>'''))
            return ctx
    class Manager:
        def __enter__(self):
            self.manager=real();self.p=self.manager.__enter__();self.chromium=Chromium(self.p.chromium);return self
        def __exit__(self,*args):return self.manager.__exit__(*args)
    monkeypatch.setattr(api,'sync_playwright',Manager)
    store=Store(tmp_path/'data');store.save_setting('profile',{'name':'Test User','email':'test@example.com'})
    jid=store.add({'url':'https://jobs.lever.co/acme/test/apply','company':'Acme','title':'Test'})
    log=[];worker=BrowserWorker(store,log.append);worker.run([jid],auto=True)
    assert store.job(jid)['status']=='submitted',log
    assert (store.folder/'documents'/jid/'receipt.json').exists()
    with pytest.raises(ValueError):store.claim(jid)

def test_single_instance_lock(tmp_path):
    from applypilot.instance import acquire
    first=acquire(tmp_path)
    try:
        with pytest.raises(RuntimeError):acquire(tmp_path)
    finally:first.close()
    acquire(tmp_path).close()

def test_hidden_resume_upload(page,tmp_path):
    (tmp_path/'resume.pdf').write_bytes(b'resume')
    page.set_content('<label for="resume">Resume</label><input id="resume" type=file style="display:none">')
    assert not fill_page(page,{},tmp_path)
    assert page.locator('input').evaluate('e=>e.files.length')==1

def test_required_custom_dropdown_blocks_auto(page,tmp_path):
    page.set_content('<div role=combobox aria-required=true aria-label="Country">Select</div>')
    assert 'Country' in fill_page(page,{},tmp_path)

def test_account_fill_exact_origin_and_no_iframe(page,tmp_path,monkeypatch):
    import keyring
    from applypilot.core import Store
    from applypilot.accounts import fill_account
    store=Store(tmp_path/'store');store.save_setting('accounts',{'https://portal.example.com':'me@example.com'})
    monkeypatch.setattr(keyring,'get_password',lambda *a:'saved-password')
    page.route('**/*',lambda route:route.fulfill(content_type='text/html',body='<input type=email><input type=password><iframe srcdoc="<input type=password>"></iframe>'))
    page.goto('https://portal.example.com/login')
    assert fill_account(page,store)==2
    assert page.locator('input[type=password]').input_value()=='saved-password'
    assert page.frames[1].locator('input').input_value()==''
    page.goto('https://other.example.com/login')
    with pytest.raises(ValueError):fill_account(page,store)

def test_code_field_explicit_only(page):
    from applypilot.verification import fill_code
    page.set_content('<input autocomplete=one-time-code><input type=password>')
    fill_code(page,'123456');assert page.locator('input').first.input_value()=='123456'
    assert page.locator('input[type=password]').input_value()==''
    page.set_content('<input placeholder="Anything">')
    with pytest.raises(ValueError):fill_code(page,'123456')

def test_multistep_browser_process(page,tmp_path):
    from applypilot.core import Store
    from applypilot.browser import BrowserWorker
    store=Store(tmp_path/'db');jid=store.add(dict(url='https://jobs.lever.co/acme/1/apply',company='Acme',title='Role'))
    page.route('**/*',lambda r:r.fulfill(content_type='text/html',body='''<label>Full name<input required></label><button onclick="document.body.innerHTML='<label>Email<input type=email required></label><button onclick=finish()>Submit application</button>'">Next</button><script>function finish(){document.body.innerHTML='Thank you for applying'}</script>'''))
    page.goto('https://jobs.lever.co/acme/1/apply')
    worker=BrowserWorker(store,lambda _:None)
    assert worker.process(page,jid,store.job(jid),{'name':'Test User','email':'test@example.com'},tmp_path,True)=='submitted'
