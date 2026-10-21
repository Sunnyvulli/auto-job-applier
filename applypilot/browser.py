"""Visible browser worker. No anti-bot evasion and no guessed answers."""
import json
import re
import threading
from pathlib import Path
from urllib.parse import urlsplit
from .core import documents, now

CONFIRMATION = re.compile(r'(thank you for applying|application (?:has been |was )?(?:successfully )?(?:submitted|received)|we have received your application)', re.I)

def known_portal(url):
    h = urlsplit(url).hostname or ''
    return h in {'jobs.lever.co','jobs.eu.lever.co','boards.greenhouse.io','job-boards.greenhouse.io'}

def answers(profile):
    name = profile.get('name','').split(' ',1)
    result = {'first name':name[0] if name else '', 'last name':name[1] if len(name)>1 else '',
              'full name':profile.get('name',''),'name':profile.get('name',''),'email':profile.get('email',''),
              'email address':profile.get('email',''),'phone':profile.get('phone',''),'phone number':profile.get('phone',''),
              'linkedin':profile.get('linkedin',''),'linkedin profile':profile.get('linkedin',''),
              'linkedin url':profile.get('linkedin',''),'website':profile.get('website','')}
    custom = profile.get('answers',{})
    result.update({normalize(k):str(v) for k,v in custom.items()})
    return result

def normalize(label):
    return re.sub(r'\s+', ' ', re.sub(r'[*:]+$', '',label.strip())).strip().lower()

def fill_page(page, profile, dest):
    mapping=answers(profile)
    unresolved=[]
    for frame in page.frames:
        for el in frame.locator('input,textarea,select').all():
            if not el.is_visible() or not el.is_enabled(): continue
            typ=(el.get_attribute('type') or '').lower()
            if typ in {'hidden','submit','button','reset'}: continue
            label=el.evaluate('''e => { const l=[...(e.labels||[])].map(x=>{const c=x.cloneNode(true);c.querySelectorAll('input,select,textarea,button').forEach(n=>n.remove());return c.textContent;}).join(' '); return l || e.getAttribute('aria-label') || e.getAttribute('placeholder') || e.name || ''; }''')
            required=el.get_attribute('required') is not None or el.get_attribute('aria-required')=='true' or '*' in label
            key=normalize(label)
            if typ=='file':
                target = dest / ('cover-letter.pdf' if 'cover' in key else 'resume.pdf')
                if 'cover' in key or 'resume' in key or 'cv' in key:
                    el.set_input_files(str(target))
                elif required: unresolved.append(label or 'Unlabelled upload')
                continue
            if typ in {'password','checkbox','radio'}:
                if required: unresolved.append(label or typ)
                continue
            value=mapping.get(key)
            if value:
                try:
                    if el.evaluate('e=>e.tagName')=='SELECT': el.select_option(label=value)
                    else: el.fill(value)
                except Exception:
                    unresolved.append(label or 'Field could not be filled')
            elif required:
                try:
                    if not el.input_value().strip(): unresolved.append(label or 'Unlabelled required field')
                except Exception: unresolved.append(label or 'Required control')
    return sorted(set(unresolved))

class BrowserWorker:
    def __init__(self, store, notify):
        self.store=store; self.notify=notify
        self.resume_event=threading.Event(); self.stop_event=threading.Event(); self.thread=None
    def start(self, job_ids, auto=False):
        if self.thread and self.thread.is_alive(): raise ValueError('A browser session is already running.')
        self.stop_event.clear(); self.resume_event.clear()
        self.thread=threading.Thread(target=self.run,args=(job_ids,auto),daemon=True)
        self.thread.start()
    def resume(self): self.resume_event.set()
    def stop(self): self.stop_event.set(); self.resume_event.set()
    def pause(self,jid,message):
        self.resume_event.clear()
        self.store.state(jid,'needs_attention',message)
        self.notify(message+' Complete it in the browser, then click Resume.')
        while not self.resume_event.wait(.3):
            if self.stop_event.is_set(): return False
        if self.stop_event.is_set(): return False
        self.store.state(jid,'running','Resumed by user')
        return True
    def run(self, ids, auto):
        active=None
        try:
            from playwright.sync_api import sync_playwright
            profile=self.store.setting('profile',{})
            with sync_playwright() as p:
                context=p.chromium.launch_persistent_context(str(self.store.folder/'browser-session'),headless=False,accept_downloads=False)
                page=context.pages[0] if context.pages else context.new_page()
                for jid in ids:
                    if self.stop_event.is_set(): break
                    self.store.claim(jid); active=jid
                    job=self.store.job(jid)
                    dest=documents(self.store,profile,job)
                    page.goto(job['url'],wait_until='domcontentloaded',timeout=45000)
                    # Lever has a dedicated /apply URL. Greenhouse form layouts vary.
                    if known_portal(page.url) and 'lever.co' in (urlsplit(page.url).hostname or '') and not urlsplit(page.url).path.endswith('/apply'):
                        link=page.get_by_role('link',name=re.compile('apply for this job',re.I))
                        if link.count(): link.first.click()
                    missing=fill_page(page,profile,dest)
                    initial_text=page.locator('body').inner_text()
                    self.notify(f"{job['company']}: filled known fields. {len(missing)} unresolved required fields.")
                    # Visible CAPTCHA/login/account prompts are always handled in this same browser session.
                    if not auto or missing or not known_portal(page.url):
                        if not self.pause(jid,'Review the application, complete verification/unknown fields, and submit it yourself if needed. '+', '.join(missing)[:300]): break
                    else:
                        if page.locator('iframe[src*="captcha"],iframe[title*="challenge" i],.g-recaptcha,.h-captcha').count():
                            if not self.pause(jid,'Verification detected. Complete verification and review the application.'): break
                        # Re-check all native validation and never submit through an unknown host or iframe.
                        missing=fill_page(page,profile,dest)
                        invalid=page.locator('input:invalid,select:invalid,textarea:invalid').count()
                        if missing or invalid:
                            if not self.pause(jid,'Required information is still missing; finish and submit in the browser.'): break
                        elif known_portal(page.url):
                            button=page.get_by_role('button',name=re.compile(r'^(submit application|submit your application|apply|submit)$',re.I))
                            if button.count()==1:
                                button.click(timeout=15000)
                            elif not self.pause(jid,'Submission button is ambiguous. Review and submit manually.'): break
                    # Wait for a positive receipt. Absence of a receipt is never called success.
                    try: page.wait_for_function("() => /thank you for applying|application (?:has been |was )?(?:successfully )?(?:submitted|received)|we have received your application/i.test(document.body.innerText)",timeout=15000)
                    except Exception: pass
                    text=page.locator('body').inner_text()
                    status='submitted' if CONFIRMATION.search(text) and text != initial_text and not page.locator('input:not([type=hidden]):not([type=submit]):visible,textarea:visible,select:visible').count() else 'uncertain'
                    receipt={'at':now(),'url':page.url,'status':status,'text':text[:100000]}
                    (dest/'receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
                    self.store.state(jid,status,'Positive confirmation detected' if status=='submitted' else 'No positive confirmation. Check portal/email before retrying.')
                    active=None
                    self.notify(f"{job['company']}: {status}")
                context.close()
        except Exception as e:
            if active: self.store.state(active,'uncertain','Browser error; check portal before retrying. '+type(e).__name__)
            self.notify('Browser stopped: '+str(e)[:400])
        finally:
            if active and self.store.job(active)['status'] in {'running','needs_attention'}:
                self.store.state(active,'uncertain','Stopped: check portal before retrying.')
            self.notify('Queue finished. Refresh the dashboard for results.')
