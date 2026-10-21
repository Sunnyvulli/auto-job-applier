"""Visible browser worker. No anti-bot evasion and no guessed answers."""
import json
import re
import threading
import queue
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

def same_origin(left,right):
    try:
        a,b=urlsplit(left),urlsplit(right)
        return a.scheme in {'http','https'} and (a.scheme,a.hostname,a.port or (443 if a.scheme=='https' else 80))==(b.scheme,b.hostname,b.port or (443 if b.scheme=='https' else 80))
    except ValueError:return False

def form_frames(page):
    # Embedded external forms require explicit browser entry, including srcdoc/opaque frames.
    return [frame for frame in page.frames if frame==page.main_frame or same_origin(frame.url,page.url)]

def fill_page(page, profile, dest):
    mapping=answers(profile)
    unresolved=[]
    for frame in form_frames(page):
        for el in frame.locator('input,textarea,select').all():
            if not el.is_enabled(): continue
            typ=(el.get_attribute('type') or '').lower()
            if typ!='file' and not el.is_visible():continue
            if typ in {'hidden','submit','button','reset'}: continue
            label=el.evaluate('''e => { const l=[...(e.labels||[])].map(x=>{const c=x.cloneNode(true);c.querySelectorAll('input,select,textarea,button').forEach(n=>n.remove());return c.textContent;}).join(' '); return l || e.getAttribute('aria-label') || e.getAttribute('placeholder') || e.name || e.id || ''; }''')
            required=el.get_attribute('required') is not None or el.get_attribute('aria-required')=='true' or '*' in label
            key=normalize(label)
            if typ=='file':
                target = dest / ('cover-letter.pdf' if 'cover' in key else 'resume.pdf')
                if 'cover' in key or 'resume' in key or 'cv' in key:
                    el.set_input_files(str(target))
                elif required: unresolved.append(label or 'Unlabelled upload')
                continue
            if typ in {'password','checkbox','radio'}:
                resolved = el.is_checked() if typ in {'checkbox','radio'} else bool(el.input_value())
                if required and not resolved: unresolved.append(label or typ)
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
    for frame in form_frames(page):
        for el in frame.locator('[role=combobox][aria-required=true]').all():
            if el.is_visible():
                unresolved.append(el.get_attribute('aria-label') or 'Required custom dropdown: review manually')
    return sorted(set(unresolved))

class BrowserWorker:
    def __init__(self, store, notify):
        self.store=store;self.notify=notify
        self.resume_event=threading.Event();self.stop_event=threading.Event();self.thread=None
        self.actions=queue.Queue();self.page=None;self.active_started=None
    def start(self,job_ids,auto=False):
        if self.thread and self.thread.is_alive():raise ValueError('A browser session is already running.')
        self.stop_event.clear();self.resume_event.clear()
        self.thread=threading.Thread(target=self.run,args=(job_ids,auto),daemon=True);self.thread.start()
    def resume(self):self.resume_event.set()
    def stop(self):self.stop_event.set();self.resume_event.set()
    def request(self,action):
        if not self.thread or not self.thread.is_alive():raise ValueError('Start a browser application first.')
        self.actions.put(action)
    def handle_action(self,action):
        if action=='account':
            from .accounts import fill_account
            count=fill_account(self.page,self.store)
            self.notify(f'Filled {count} account fields for the exact approved origin. Review and continue in the browser.')
        elif action=='otp':
            from .accounts import account_origin
            from .verification import find_code,fill_code
            from . import mail
            origin=account_origin(self.page.url)
            sender=self.store.setting('otp_senders',{}).get(origin)
            config=self.store.setting('mail',{})
            if not sender:raise ValueError('Configure an approved verification sender for this exact origin in Account tools.')
            address=config.get('address','')
            if config.get('provider')=='Gmail OAuth':
                from .google_mail import recent_raw
                raw=recent_raw(limit=15)
            else:raw=mail.recent_raw(config.get('provider','Gmail'),address,limit=15)
            code=find_code(raw,address,sender,self.active_started)
            fill_code(self.page,code)
            self.notify('Filled a unique recent email code. Review and continue in the browser. The code was not logged.')
    def pause(self,jid,message):
        self.resume_event.clear();self.store.state(jid,'needs_attention',message)
        self.notify(message+' Complete the step in the browser, then click Resume.')
        while not self.resume_event.wait(.3):
            if self.stop_event.is_set():return False
            try:action=self.actions.get_nowait()
            except queue.Empty:continue
            try:self.handle_action(action)
            except Exception as e:self.notify('Assistance: '+str(e)[:250])
        if self.stop_event.is_set():return False
        self.store.state(jid,'running','Resumed by user');return True
    def confirmed(self,page,baseline):
        text=page.locator('body').inner_text()
        return bool(CONFIRMATION.search(text) and text!=baseline and not page.locator('input:not([type=hidden]):not([type=submit]):visible,textarea:visible,select:visible').count())
    def process(self,page,jid,job,profile,dest,auto):
        baseline=page.locator('body').inner_text();submitted=False
        def resume_signature():
            source=self.store.setting('resume_pdf')
            if not source:return None
            path=Path(source)
            return (source,path.stat().st_mtime_ns,path.stat().st_size) if path.is_file() else (source,None)
        resume_version=resume_signature()
        for step in range(25):
            if self.stop_event.is_set():return 'uncertain'
            if self.confirmed(page,baseline):return 'submitted'
            current=self.store.setting('profile',profile)
            current_resume=resume_signature()
            if current!=profile or current_resume!=resume_version:
                dest=documents(self.store,current,job)
                profile=current;resume_version=current_resume
            missing=fill_page(page,profile,dest)
            passwords=page.locator('input[type=password]:visible').count()
            captcha=page.locator('iframe[src*="captcha"],iframe[title*="challenge" i],.g-recaptcha,.h-captcha').count()
            otp=page.locator('input[autocomplete="one-time-code"]:visible').count()
            if missing or passwords or captcha or otp or not auto or not known_portal(page.url) or submitted:
                detail='Review required fields and complete the current step.'
                if passwords:detail+=' Use Fill saved account for an approved portal.'
                if otp:detail+=' Use Fetch email code if configured.'
                if captcha:detail+=' Human verification is required.'
                if missing:detail+=' '+', '.join(missing)[:250]
                if not self.pause(jid,detail):return 'uncertain'
                if self.confirmed(page,baseline):return 'submitted'
                if not page.locator('input:visible,select:visible,textarea:visible,button:visible').count():return 'uncertain'
                continue
            if page.locator('input:invalid,select:invalid,textarea:invalid').count():
                if not self.pause(jid,'Native form validation needs attention.'):return 'uncertain'
                continue
            submit=page.get_by_role('button',name=re.compile(r'^(submit application|submit your application|apply|submit)$',re.I))
            advance=page.get_by_role('button',name=re.compile(r'^(next|continue|save and continue)$',re.I))
            button=submit if submit.count()==1 else advance
            if button.count()!=1:
                if not self.pause(jid,'A unique supported action button was not found. Continue manually.'):return 'uncertain'
                continue
            before=page.locator('body').inner_text();before_url=page.url
            final=submit.count()==1
            button.click(timeout=15000)
            if final:submitted=True
            try:
                page.wait_for_function('(before)=>document.body.innerText!==before',arg=before,timeout=10000)
            except Exception:pass
            if self.confirmed(page,baseline):return 'submitted'
            if page.url==before_url and page.locator('body').inner_text()==before:
                if not self.pause(jid,'No progress was detected. Check errors before retrying manually.'):return 'uncertain'
        return 'uncertain'
    def run(self,ids,auto):
        active=None
        try:
            from playwright.sync_api import sync_playwright
            profile=self.store.setting('profile',{})
            with sync_playwright() as p:
                from .system import launch_context
                context=launch_context(p.chromium,self.store.folder,self.store.setting('preferences',{}).get('browser','auto'))
                page=context.pages[0] if context.pages else context.new_page();self.page=page
                for jid in ids:
                    if self.stop_event.is_set():break
                    try:self.store.claim(jid)
                    except ValueError:
                        self.notify('Skipped a running, submitted or uncertain job.');continue
                    active=jid;self.active_started=now()
                    while not self.actions.empty():self.actions.get_nowait()
                    profile=self.store.setting('profile',{})
                    job=self.store.job(jid);dest=documents(self.store,profile,job)
                    page.goto(job['url'],wait_until='domcontentloaded',timeout=45000)
                    if known_portal(page.url) and 'lever.co' in (urlsplit(page.url).hostname or '') and not urlsplit(page.url).path.endswith('/apply'):
                        link=page.get_by_role('link',name=re.compile('apply for this job',re.I))
                        if link.count():link.first.click()
                    status=self.process(page,jid,job,profile,dest,auto)
                    receipt={'at':now(),'url':page.url,'status':status,'text':page.locator('body').inner_text()[:100000]}
                    (dest/'receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
                    self.store.state(jid,status,'Positive confirmation detected' if status=='submitted' else 'Check portal/email before retrying.')
                    active=None;self.notify(f"{job['company']}: {status}")
                context.close()
        except Exception as e:
            if active:self.store.state(active,'uncertain','Browser error; check portal before retrying. '+type(e).__name__)
            self.notify('Browser stopped: '+str(e)[:400])
        finally:
            self.page=None
            if active and self.store.job(active)['status'] in {'running','needs_attention'}:self.store.state(active,'uncertain','Stopped: check portal before retrying.')
            self.notify('Queue finished. Refresh the dashboard for results.')
