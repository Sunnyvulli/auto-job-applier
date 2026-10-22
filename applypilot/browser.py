"""Visible browser worker. No anti-bot evasion and no guessed answers."""
import json
import re
import threading
import queue
import time
from pathlib import Path
from urllib.parse import urlsplit
from .core import documents, now
from .tailoring import approved_profile,capture_questions,current_draft

CONFIRMATION = re.compile(r'(thank you for applying|application (?:has been |was )?(?:successfully )?(?:submitted|received)|we have received your application)', re.I)

def known_portal(url):
    h = urlsplit(url).hostname or ''
    return h in {'jobs.lever.co','jobs.eu.lever.co','boards.greenhouse.io','job-boards.greenhouse.io'}

def answers(profile):
    name = profile.get('name','').split(' ',1)
    result = {'first name':profile.get('first_name') or (name[0] if name else ''), 'last name':profile.get('last_name') or (name[1] if len(name)>1 else ''),
              'full name':profile.get('name',''),'name':profile.get('name',''),'email':profile.get('email',''),
              'email address':profile.get('email',''),'phone':profile.get('phone',''),'phone number':profile.get('phone',''),
              'linkedin':profile.get('linkedin',''),'linkedin profile':profile.get('linkedin',''),
              'linkedin url':profile.get('linkedin',''),'website':profile.get('website','')}
    custom = profile.get('answers',{})
    result.update({normalize(k):str(v) for k,v in custom.items()})
    return result

def normalize(label):
    return re.sub(r'\s+', ' ', re.sub(r'[*✱∗⁎✳:]+$', '',label.strip())).strip().lower()

def same_origin(left,right):
    try:
        a,b=urlsplit(left),urlsplit(right)
        return a.scheme in {'http','https'} and (a.scheme,a.hostname,a.port or (443 if a.scheme=='https' else 80))==(b.scheme,b.hostname,b.port or (443 if b.scheme=='https' else 80))
    except ValueError:return False

def form_frames(page):
    # Embedded external forms require explicit browser entry, including srcdoc/opaque frames.
    return [frame for frame in page.frames if frame==page.main_frame or same_origin(frame.url,page.url)]

def field_label(el):
    return el.evaluate(r"""e => {
        const text=n=>{const c=n.cloneNode(true);c.querySelectorAll('input,select,textarea,button').forEach(n=>n.remove());return c.textContent.trim();};
        const labels=[...(e.labels||[])].map(text).filter(Boolean).join(' ');
        const labelled=(e.getAttribute('aria-labelledby')||'').split(/\s+/).map(id=>e.ownerDocument.getElementById(id)).filter(Boolean).map(text).join(' ');
        return labels || labelled || e.getAttribute('aria-label') || e.getAttribute('placeholder') || e.name || e.id || '';
    }""")


def profile_field_key(label):
    # Bounded aliases for ordinary identity fields; never fuzzy-match questions.
    label=re.sub(r'([a-z])([A-Z])',r'\1 \2',label)
    key=normalize(re.sub(r'\s*\((?:required|optional)\)\s*$','',normalize(label),flags=re.I))
    key=re.sub(r'[_-]+',' ',key);key=re.sub(r'\s+',' ',key).strip()
    key=re.sub(r'\blinked in\b','linkedin',key)
    aliases={'firstname':'first name','given name':'first name','given names':'first name',
             'lastname':'last name','family name':'last name','surname':'last name',
             'fullname':'full name','your name':'full name','e mail':'email','e mail address':'email address',
             'emailaddress':'email address','telephone':'phone','mobile phone':'phone',
             'linkedin profile url':'linkedin','linkedinprofile':'linkedin','personal website':'website',
             'portfolio website':'website'}
    return aliases.get(key,key)


def upload_kind(el):
    # A real Greenhouse file input may be hidden and labelled only "Attach".
    hints=[field_label(el),el.get_attribute('id') or '',el.get_attribute('name') or '',el.get_attribute('aria-label') or '']
    kinds=set()
    for hint in hints:
        hint=re.sub(r'([a-z])([A-Z])',r'\1 \2',hint).lower()
        hint=re.sub(r'[_-]+',' ',hint)
        if re.search(r'\bcover\s*letter\b',hint):kinds.add('cover-letter')
        if re.search(r'\b(?:resume|résumé|cv)\b|\bcurriculum\s+vitae\b',hint):kinds.add('resume')
    return next(iter(kinds)) if len(kinds)==1 else None


def wait_for_application_controls(page,timeout=12):
    deadline=time.monotonic()+timeout
    while True:
        for frame in form_frames(page):
            if frame.locator('input[type=file]').count():return True
            for el in frame.locator('input:not([type=hidden]):not([type=submit]):not([type=button]),textarea,select,[role=combobox]').all():
                if el.is_visible() and el.is_enabled():return True
        if time.monotonic()>=deadline:return False
        page.wait_for_timeout(200)


def custom_selection_present(el):
    # Read a chosen React-select value; typing into its search input is not a selection.
    return el.evaluate("""e=>{
        const container=e.closest('[class*=\"select__container\"],[class*=\"-container\"]');
        if(!container || container.querySelectorAll('[role=combobox]').length!==1)return false;
        return [...container.querySelectorAll('[class*=\"singleValue\"],[class*=\"single-value\"]')].some(n=>n.getBoundingClientRect().width>0 && n.textContent.trim());
    }""")


def radio_groups(page):
    result=[]
    for frame in form_frames(page):
        for fieldset in frame.locator('fieldset').all():
            if not fieldset.is_visible():continue
            legend=fieldset.locator(':scope > legend')
            controls=fieldset.locator('input[type=radio]')
            if legend.count()!=1 or not controls.count():continue
            label=legend.inner_text().strip();items=controls.all()
            names={el.get_attribute('name') for el in items}
            if len(names)!=1 or not next(iter(names)) or any(not el.is_visible() or not el.is_enabled() for el in items):continue
            options=[(field_label(el).strip(),el) for el in items]
            if any(not name for name,_ in options) or len({name for name,_ in options})!=len(options):continue
            result.append({'label':label,'options':options})
    return result

def fill_page(page, profile, dest, report=None):
    mapping=answers(profile)
    if report is None:report={}
    report.update(fields=0,uploads=0)
    unresolved=[]
    from .learning import BLOCKED
    for group in radio_groups(page):
        value=mapping.get(normalize(group['label']))
        if value and not BLOCKED.search(group['label']):
            choices=[el for label,el in group['options'] if label==value]
            if len(choices)==1:
                try:choices[0].check()
                except Exception:unresolved.append(group['label'])
            else:unresolved.append(group['label'])
    for frame in form_frames(page):
        for el in frame.locator('input,textarea,select').all():
            if not el.is_enabled(): continue
            typ=(el.get_attribute('type') or '').lower()
            if typ!='file' and not el.is_visible():continue
            if typ in {'hidden','submit','button','reset'}: continue
            label=field_label(el)
            required=el.get_attribute('required') is not None or el.get_attribute('aria-required')=='true' or '*' in label
            key=normalize(label)
            if typ=='file':
                kind=upload_kind(el)
                if not kind:
                    unresolved.append((label or 'Unlabelled file')+' (upload type unclear; attach manually)');continue
                target=dest/(kind+'.pdf')
                if not target.is_file():
                    unresolved.append(kind+' upload: prepared file is missing; prepare documents again');continue
                try:
                    el.set_input_files(str(target));report['uploads']+=1
                except Exception:
                    unresolved.append(kind+' upload failed; attach manually or retry after Resume')
                continue
            if el.get_attribute('role')=='combobox' and el.evaluate('e=>e.tagName')!='SELECT':
                if required and not custom_selection_present(el):unresolved.append(label or 'Required custom dropdown: select an option manually')
                continue
            if typ in {'password','checkbox','radio'}:
                resolved=el.evaluate('e=>e.validity.valid') if typ=='radio' else el.is_checked() if typ=='checkbox' else bool(el.input_value())
                if required and not resolved:
                    group_label=el.evaluate('e=>e.closest("fieldset")?.querySelector("legend")?.textContent||""') if typ=='radio' else ''
                    unresolved.append(group_label.strip() or label or typ)
                continue
            value=mapping.get(key)
            if value is None:
                alias=profile_field_key(label)
                basic={'first name','last name','full name','name','email','email address','phone','phone number','linkedin','linkedin profile','linkedin url','website'}
                if alias in basic:value=mapping.get(alias)
            if value:
                try:
                    if el.evaluate('e=>e.tagName')=='SELECT': el.select_option(label=value)
                    else:
                        maximum=el.get_attribute('maxlength')
                        if maximum and int(maximum)>=0 and len(value.encode('utf-16-le'))//2>int(maximum):
                            unresolved.append(label+' (approved answer exceeds field length)');continue
                        el.fill(value)
                        if el.input_value()!=value:unresolved.append(label+' (form changed the approved answer)')
                    report['fields']+=1
                except Exception:
                    unresolved.append(label or 'Field could not be filled')
            elif required:
                try:
                    if not el.input_value().strip(): unresolved.append(label or 'Unlabelled required field')
                except Exception: unresolved.append(label or 'Required control')
    for frame in form_frames(page):
        for el in frame.locator('[role=combobox][aria-required=true]').all():
            if el.is_visible() and el.evaluate('e=>e.tagName')!='SELECT' and not custom_selection_present(el):
                unresolved.append(field_label(el) or 'Required custom dropdown: review manually')
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
        self.notify(message+' Fix the issue in the browser, then click Resume. To teach answers, Resume before Next/Submit.')
        while not self.resume_event.wait(.3):
            if self.stop_event.is_set():return False
            try:action=self.actions.get_nowait()
            except queue.Empty:continue
            try:self.handle_action(action)
            except Exception as e:self.notify('Assistance: '+str(e)[:250])
        if self.stop_event.is_set():return False
        self.store.state(jid,'running','Resumed by user');return True
    def wait_for_help(self,page,jid,message):
        from .learning import snapshot,remember_corrections,employer_scope
        before=snapshot(page);job=self.store.job(jid);original_url=page.url;scope=employer_scope(page.url,job)
        accepted=self.pause(jid,message)
        if accepted and self.store.setting('learn_answers',True):
            try:
                if page.url==original_url and employer_scope(page.url,job)==scope:
                    count=remember_corrections(self.store,job,page.url,before,snapshot(page))
                    if count:self.notify(f'Remembered {count} corrected answers for this job. Reuse on later jobs starts after positive submission confirmation.')
            except Exception:self.notify('Could not remember this correction. Your browser session can continue.')
        return accepted
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
        used_memory=set()
        resume_version=resume_signature();draft_version=current_draft(self.store,profile,job)
        for step in range(25):
            if self.stop_event.is_set():return 'uncertain'
            if self.confirmed(page,baseline):return 'submitted'
            if not wait_for_application_controls(page):
                if not self.wait_for_help(page,jid,'No application fields loaded. Open the application form in this same tab, then Resume.'):return 'uncertain'
                continue
            job=self.store.job(jid)
            current=self.store.setting('profile',profile)
            current_resume=resume_signature()
            current_version=current_draft(self.store,current,job)
            if current!=profile or current_resume!=resume_version or current_version!=draft_version:
                dest=documents(self.store,current,job)
                profile=current;resume_version=current_resume;draft_version=current_version
            from .learning import snapshot,matching_answers,record_use,disable_used
            learned,used=matching_answers(self.store,job,page.url,snapshot(page),exclude=(current_version or {}).get('approved_answers',{}))
            effective=approved_profile(self.store,profile,job)
            # Explicit job approvals take precedence over automatically remembered answers.
            overrides={**{normalize(k):str(v) for k,v in effective.get('answers',{}).items()},**learned,**(current_version or {}).get('approved_answers',{})}
            progress={}
            missing=fill_page(page,dict(effective,answers=overrides),dest,progress)
            self.notify(f"Filled {progress['fields']} fields; selected {progress['uploads']} documents for upload. {len(missing)} fields/uploads need review.")
            fresh=set(used)-used_memory
            if fresh:record_use(self.store,fresh);used_memory.update(fresh)
            self.used_memory=used
            passwords=page.locator('input[type=password]:visible').count()
            captcha=page.locator('iframe[src*="captcha"],iframe[title*="challenge" i],.g-recaptcha,.h-captcha').count()
            otp=page.locator('input[autocomplete="one-time-code"]:visible').count()
            if missing or passwords or captcha or otp or not auto or not known_portal(page.url) or submitted:
                detail='Review required fields and complete the current step.'
                if passwords:detail+=' Use Fill saved account for an approved portal.'
                if otp:detail+=' Use Fetch email code if configured.'
                if captcha:detail+=' Human verification is required.'
                if missing:
                    capture_questions(self.store,profile,job,missing)
                    self.notify({'type':'questions','job_id':jid,'count':len(missing)})
                    detail+=' '+', '.join(missing)[:250]+' Review drafts in Tailor application.'
                if not self.wait_for_help(page,jid,detail):return 'uncertain'
                if self.confirmed(page,baseline):return 'submitted'
                if not page.locator('input:visible,select:visible,textarea:visible,button:visible').count():return 'uncertain'
                continue
            if page.locator('input:invalid,select:invalid,textarea:invalid').count():
                if not self.wait_for_help(page,jid,'Native form validation needs attention.'):return 'uncertain'
                continue
            submit=page.get_by_role('button',name=re.compile(r'^(submit application|submit your application|apply|submit)$',re.I))
            advance=page.get_by_role('button',name=re.compile(r'^(next|continue|save and continue)$',re.I))
            button=submit if submit.count()==1 else advance
            if button.count()!=1:
                if not self.wait_for_help(page,jid,'A unique supported action button was not found. Continue manually.'):return 'uncertain'
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
                disable_used(self.store,used)
                if not self.wait_for_help(page,jid,'No progress was detected. Check errors before retrying manually.'):return 'uncertain'
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
                    job=self.store.job(jid)
                    status=self.process(page,jid,job,profile,dest,auto)
                    receipt={'at':now(),'url':page.url,'status':status,'text':page.locator('body').inner_text()[:100000]}
                    (dest/'receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
                    if status=='submitted':
                        from .learning import confirm_learning
                        try:
                            activated=confirm_learning(self.store,jid,self.active_started)
                            if activated:self.notify(f'Confirmed {activated} learned answers for future matching applications.')
                        except Exception:self.notify('Submission confirmed, but learning memory could not be activated.')
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
