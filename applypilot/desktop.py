import csv
import json
import os
import queue
import re
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import ttk, filedialog, messagebox, simpledialog
from .core import Store, documents, import_board, match
from .browser import BrowserWorker
from . import mail
from .sources import PROVIDERS, board_identifier
from . import accounts, google_mail

FIELDS=['name','email','phone','location','linkedin','website','skills','summary','experience','projects','education']

class App:
    def __init__(self,root,folder=None):
        self.root=root
        self.store=Store(folder or Path(os.getenv('LOCALAPPDATA',str(Path.home()/'.local/share')))/'ApplyPilot')
        self.queue=queue.Queue();self.worker=BrowserWorker(self.store,self.queue.put)
        root.title('ApplyPilot 0.2 · Your local job application assistant');root.geometry('1180x820');root.minsize(940,650)
        style=ttk.Style();style.theme_use('clam');style.configure('TFrame',background='#f4f6fa');style.configure('TLabel',background='#f4f6fa',font=('Segoe UI',10));style.configure('TButton',font=('Segoe UI',10),padding=8);style.configure('Treeview',rowheight=30,font=('Segoe UI',10));style.configure('Title.TLabel',font=('Segoe UI',23,'bold'),foreground='#172448');style.configure('Accent.TButton',foreground='white',background='#345be8')
        header=ttk.Frame(root,padding=18);header.pack(fill='x');ttk.Label(header,text='ApplyPilot',style='Title.TLabel').pack(side='left');ttk.Label(header,text='LOCAL FIRST  /  NO PAID API REQUIRED').pack(side='right')
        self.tabs=ttk.Notebook(root);self.tabs.pack(fill='both',expand=True,padx=16,pady=5)
        self.profile_tab();self.jobs_tab();self.mail_tab();self.activity_tab();self.settings_tab()
        self.import_lock=threading.Lock();self.mail_sync_lock=threading.Lock()
        self.status=tk.StringVar(value='Start by saving your verified profile. No applications run until you click Start.')
        ttk.Label(root,textvariable=self.status,padding=12,wraplength=1100).pack(fill='x')
        self.refresh();self.pump();root.after(900000,self.scheduled_refresh);root.after(300000,self.scheduled_mail);root.protocol('WM_DELETE_WINDOW',self.close)
    def tab(self,name):
        t=ttk.Frame(self.tabs,padding=16);self.tabs.add(t,text=name);return t
    def guard(self,fn):
        try: return fn()
        except Exception as e: messagebox.showerror('ApplyPilot',str(e))
    def background(self,fn):
        def run():
            try: self.queue.put(str(fn()))
            except Exception as e: self.queue.put('Error: '+str(e))
        threading.Thread(target=run,daemon=True).start()
    def profile_tab(self):
        t=self.tab('1  Profile')
        ttk.Label(t,text='Use only information you can stand behind. Blank fields stay unanswered.').pack(anchor='w',pady=5)
        pane=ttk.Frame(t);pane.pack(fill='both',expand=True)
        canvas=tk.Canvas(pane,highlightthickness=0,background='#f4f6fa');scroll=ttk.Scrollbar(pane,orient='vertical',command=canvas.yview);inner=ttk.Frame(canvas)
        inner.bind('<Configure>',lambda e:canvas.configure(scrollregion=canvas.bbox('all')));canvas.create_window((0,0),window=inner,anchor='nw');canvas.configure(yscrollcommand=scroll.set);canvas.pack(side='left',fill='both',expand=True);scroll.pack(side='right',fill='y')
        self.fields={};p=self.store.setting('profile',{})
        for i,key in enumerate(FIELDS):
            ttk.Label(inner,text=key.replace('_',' ').title(),width=18).grid(row=i,column=0,sticky='nw',pady=6)
            h=4 if key in {'summary','experience','projects','education'} else 1
            box=tk.Text(inner,height=h,width=92,font=('Segoe UI',10),wrap='word',relief='solid',borderwidth=1)
            box.insert('1.0',p.get(key,''));box.grid(row=i,column=1,pady=6,sticky='ew');self.fields[key]=box
        ttk.Label(inner,text='Exact question → answer\n(JSON object)',width=18).grid(row=len(FIELDS),column=0,sticky='nw')
        self.answers=tk.Text(inner,height=5,width=92,font=('Consolas',10));self.answers.insert('1.0',json.dumps(p.get('answers',{}),indent=2));self.answers.grid(row=len(FIELDS),column=1)
        buttons=ttk.Frame(t);buttons.pack(fill='x',pady=10)
        ttk.Button(buttons,text='Save profile',style='Accent.TButton',command=lambda:self.guard(self.save_profile)).pack(side='left')
        ttk.Button(buttons,text='Import profile JSON',command=lambda:self.guard(self.import_profile)).pack(side='left',padx=8)
        ttk.Button(buttons,text='Open private data folder',command=lambda:self.open_path(self.store.folder)).pack(side='right')
    def save_profile(self):
        p={k:v.get('1.0','end').strip() for k,v in self.fields.items()};p['answers']=json.loads(self.answers.get('1.0','end'))
        if not isinstance(p['answers'],dict): raise ValueError('Answers must be a JSON object')
        if not p['name'] or '@' not in p['email']: raise ValueError('Name and valid email are required')
        self.store.save_setting('profile',p);self.status.set('Profile saved locally.')
    def import_profile(self):
        path=filedialog.askopenfilename(filetypes=[('JSON','*.json')])
        if not path:return
        p=json.loads(Path(path).read_text(encoding='utf-8'))
        for k,box in self.fields.items():box.delete('1.0','end');box.insert('1.0',str(p.get(k,'')))
        self.answers.delete('1.0','end');self.answers.insert('1.0',json.dumps(p.get('answers',{}),indent=2))
    def jobs_tab(self):
        t=self.tab('2  Jobs & applications')
        top=ttk.Frame(t);top.pack(fill='x')
        self.provider=tk.StringVar(value='Greenhouse');ttk.Combobox(top,textvariable=self.provider,values=PROVIDERS,width=14,state='readonly').pack(side='left')
        self.board=tk.StringVar();ttk.Entry(top,textvariable=self.board,width=25).pack(side='left',padx=6)
        self.region=tk.StringVar(value='global');ttk.Combobox(top,textvariable=self.region,values=['global','eu'],width=8,state='readonly').pack(side='left')
        ttk.Button(top,text='Import company board',command=self.import_jobs).pack(side='left',padx=6)
        ttk.Button(top,text='+ Add job link',command=lambda:self.guard(self.add_job)).pack(side='left')
        ttk.Label(t,text='Enter a company board identifier above. Keyword overlap is not an eligibility decision.').pack(anchor='w',pady=8)
        filterbar=ttk.Frame(t);filterbar.pack(fill='x');ttk.Label(filterbar,text='Filter title / location / company').pack(side='left')
        self.filter=tk.StringVar();self.filter.trace_add('write',lambda *a:self.refresh());ttk.Entry(filterbar,textvariable=self.filter,width=45).pack(side='left',padx=8)
        self.tree=ttk.Treeview(t,columns=('company','title','location','skills','status'),show='headings',selectmode='extended')
        for col,w in [('company',130),('title',310),('location',180),('skills',70),('status',150)]:self.tree.heading(col,text=col.title());self.tree.column(col,width=w)
        self.tree.pack(fill='both',expand=True,pady=10);self.tree.bind('<Double-1>',lambda e:self.guard(self.details))
        actions=ttk.Frame(t);actions.pack(fill='x')
        ttk.Button(actions,text='Prepare PDFs',command=lambda:self.guard(self.prepare)).pack(side='left')
        ttk.Button(actions,text='Start selected',style='Accent.TButton',command=lambda:self.guard(self.start)).pack(side='left',padx=6)
        ttk.Button(actions,text='Resume browser',command=self.worker.resume).pack(side='left')
        ttk.Button(actions,text='Stop',command=self.worker.stop).pack(side='left',padx=6)
        ttk.Button(actions,text='Refresh',command=self.refresh).pack(side='right')
        ttk.Button(actions,text='Set status',command=lambda:self.guard(self.set_status)).pack(side='right',padx=6)
        helpers=ttk.Frame(t);helpers.pack(fill='x',pady=4)
        ttk.Button(helpers,text='Fill saved account',command=lambda:self.guard(lambda:self.worker.request('account'))).pack(side='left')
        ttk.Button(helpers,text='Fetch email code',command=lambda:self.guard(lambda:self.worker.request('otp'))).pack(side='left',padx=6)
        ttk.Button(helpers,text='Account tools',command=lambda:self.guard(self.account_tools)).pack(side='left')
        self.auto=tk.BooleanVar(value=False);ttk.Checkbutton(t,text='Automatically submit on recognized Lever / Greenhouse pages when all required fields are resolved',variable=self.auto).pack(anchor='w',pady=10)
        ttk.Label(t,text='Login, account creation, CAPTCHA and complex questions use the visible browser. Complete them there, then Resume.').pack(anchor='w')
    def selected(self):
        ids=list(self.tree.selection())
        if not ids:raise ValueError('Select one or more jobs first')
        return ids
    def refresh(self):
        if not hasattr(self,'tree'):return
        selected=self.tree.selection();self.tree.delete(*self.tree.get_children());p=self.store.setting('profile',{})
        for j in self.store.jobs():
            if self.filter.get().lower() not in (' '.join([j['company'],j['title'],j['location'],j['status']])).lower():continue
            self.tree.insert('', 'end',iid=j['id'],values=(j['company'],j['title'],j['location'],match(p,j)['overlap'],j['status']))
        self.tree.selection_set([x for x in selected if self.tree.exists(x)])
    def add_job(self):
        url=simpledialog.askstring('Add job','HTTPS application URL:')
        if not url:return
        company=simpledialog.askstring('Company','Company name:');title=simpledialog.askstring('Role','Job title:')
        if company and title:self.store.add(dict(url=url,company=company,title=title));self.refresh()
    def import_jobs(self):
        provider=self.provider.get();board=self.board.get().strip();region=self.region.get()
        def work():
            jobs=import_board(provider,board,region)
            for j in jobs:self.store.add(j)
            return f'Imported {len(jobs)} listings. Refresh to see them; select only suitable roles.'
        self.background(work)
    def prepare(self):
        for jid in self.selected():
            j=self.store.job(jid);dest=documents(self.store,self.store.setting('profile',{}),j)
            if j['status']=='saved':self.store.state(jid,'prepared','Documents generated')
        self.open_path(dest);self.refresh()
    def start(self):
        ids=self.selected()
        if not self.store.setting('profile'):raise ValueError('Save your profile first')
        self.worker.start(ids,self.auto.get());self.status.set('Browser starting…')
    def set_status(self):
        state=simpledialog.askstring('Status','saved / prepared / needs_attention / submitted / uncertain / interview / rejected / closed')
        if state:
            if state=='saved' and not messagebox.askyesno('Check before retry','Have you checked that these jobs were not already submitted?'):return
            for jid in self.selected():self.store.state(jid,state,'Manually set by user')
            self.refresh()
    def details(self):
        j=self.store.job(self.selected()[0]);win=tk.Toplevel(self.root);win.title(j['title']);box=tk.Text(win,width=100,height=30,wrap='word');box.pack(fill='both',expand=True);box.insert('1.0',json.dumps(j,indent=2));box.configure(state='disabled')
    def mail_tab(self):
        t=self.tab('3  Email tracker');ttk.Label(t,text='Connect Gmail OAuth, use IMAP with an app password, or import .eml files. Connection remains on your computer.').pack(anchor='w')
        bar=ttk.Frame(t);bar.pack(fill='x',pady=10)
        settings=self.store.setting('mail',{});self.mailprovider=tk.StringVar(value=settings.get('provider','Gmail'));self.address=tk.StringVar(value=settings.get('address',''))
        ttk.Combobox(bar,textvariable=self.mailprovider,values=list(mail.HOSTS)+['Gmail OAuth'],state='readonly',width=12).pack(side='left');ttk.Entry(bar,textvariable=self.address,width=35).pack(side='left',padx=6)
        ttk.Button(bar,text='Save app password',command=lambda:self.guard(self.save_mail)).pack(side='left')
        ttk.Button(bar,text='Sync recent 100 emails',command=self.sync_mail).pack(side='left',padx=6)
        ttk.Button(bar,text='Import .eml',command=lambda:self.guard(self.import_eml)).pack(side='left')
        oauthbar=ttk.Frame(t);oauthbar.pack(fill='x',pady=6)
        ttk.Button(oauthbar,text='Import Google client JSON',command=lambda:self.guard(self.import_google_client)).pack(side='left')
        self.google_send=tk.BooleanVar(value=False);ttk.Checkbutton(oauthbar,text='Allow sending with Gmail OAuth',variable=self.google_send).pack(side='left',padx=6)
        ttk.Button(oauthbar,text='Connect Gmail OAuth',command=self.connect_google).pack(side='left')
        ttk.Button(oauthbar,text='Disconnect OAuth',command=lambda:self.background(google_mail.disconnect)).pack(side='left',padx=6)
        self.mailtree=ttk.Treeview(t,columns=('from','subject','stage'),show='headings')
        for c in ('from','subject','stage'):self.mailtree.heading(c,text=c.title());self.mailtree.column(c,width=300)
        self.mailtree.pack(fill='both',expand=True);self.mailtree.bind('<Double-1>',lambda e:self.guard(self.read_mail))
        ttk.Label(t,text='Email classification is advisory. It does not automatically change application status or send replies.').pack(anchor='w',pady=8)
        ttk.Button(t,text='Compose follow-up',command=self.compose).pack(side='left');ttk.Button(t,text='Refresh messages',command=self.refresh_mail).pack(side='left',padx=8)
        self.repeat_mail=tk.BooleanVar(value=self.store.setting('repeat_mail',False))
        ttk.Checkbutton(t,text='Sync mail every 5 minutes while the app is open',variable=self.repeat_mail,command=lambda:self.store.save_setting('repeat_mail',self.repeat_mail.get())).pack(side='right')
        self.refresh_mail()
    def save_mail(self):
        import keyring
        address=self.address.get().strip()
        if '@' not in address:raise ValueError('Enter your email address')
        if self.mailprovider.get()=='Gmail OAuth':raise ValueError('Use Connect Gmail OAuth for this provider.')
        secret=simpledialog.askstring('Mail app password','Use a provider-generated app password, not your normal account password.',show='*')
        if secret:keyring.set_password('ApplyPilotMail',address,secret);self.store.save_setting('mail',dict(provider=self.mailprovider.get(),address=address));self.status.set('Saved in the operating-system credential store.')
    def sync_mail(self):
        provider=self.mailprovider.get();address=self.address.get().strip()
        self.store.save_setting('mail',dict(provider=provider,address=address))
        self.run_mail_sync(provider,address)
    def run_mail_sync(self,provider,address):
        if not self.mail_sync_lock.acquire(blocking=False):self.status.set('Email sync is already running.');return
        def work():
            try:
                with self.store.connect() as c:before={r[0] for r in c.execute('SELECT id FROM messages')}
                count=mail.sync(self.store,provider,address)
                with self.store.connect() as c:rows=c.execute("SELECT id,stage FROM messages WHERE stage='possible interview/action'").fetchall()
                alerts=sum(r['id'] not in before for r in rows)
                return f'Synced {count} messages. {alerts} new possible interview/action updates.'
            finally:self.mail_sync_lock.release()
        self.background(work)
    def scheduled_mail(self):
        if self.store.setting('repeat_mail',False):
            config=self.store.setting('mail',{})
            if config.get('address'):self.run_mail_sync(config.get('provider','Gmail'),config['address'])
        self.root.after(300000,self.scheduled_mail)
    def import_eml(self):
        paths=filedialog.askopenfilenames(filetypes=[('Email','*.eml')])
        for path in paths:mail.ingest(self.store,Path(path).read_bytes())
        self.refresh_mail()
    def refresh_mail(self):
        self.mailtree.delete(*self.mailtree.get_children())
        with self.store.connect() as c:
            for r in c.execute('SELECT * FROM messages ORDER BY at DESC LIMIT 300'):self.mailtree.insert('','end',iid=r['id'],values=(r['sender'],r['subject'],r['stage']))
    def read_mail(self):
        ids=self.mailtree.selection()
        if not ids:return
        with self.store.connect() as c:r=c.execute('SELECT * FROM messages WHERE id=?',(ids[0],)).fetchone()
        w=tk.Toplevel(self.root);w.title(r['subject']);box=tk.Text(w,width=100,height=30,wrap='word');box.pack(fill='both',expand=True);box.insert('1.0',r['body']);box.configure(state='disabled')
    def compose(self):
        w=tk.Toplevel(self.root);w.title('Compose — nothing sends automatically');entries={}
        for key in ('To','Subject'):
            ttk.Label(w,text=key).pack(anchor='w');entries[key]=ttk.Entry(w,width=80);entries[key].pack(fill='x')
        body=tk.Text(w,width=80,height=20,wrap='word');body.pack();body.insert('1.0','Dear Hiring Team,\n\nI am following up on my application for [role]. I remain interested and would appreciate any update on the recruitment process.\n\nThank you,\n'+self.store.setting('profile',{}).get('name',''))
        def submit():
            if '[role]' in body.get('1.0','end'):raise ValueError('Replace [role] before sending')
            if messagebox.askyesno('Send email',f"Send this message to {entries['To'].get()}?"):
                mail.send(self.mailprovider.get(),self.address.get(),entries['To'].get(),entries['Subject'].get(),body.get('1.0','end'));w.destroy();self.status.set('Email sent.')
        ttk.Button(w,text='Send this email',command=lambda:self.guard(submit)).pack(pady=10)
    def import_google_client(self):
        path=filedialog.askopenfilename(filetypes=[('Google Desktop OAuth client','*.json')])
        if path:google_mail.import_client(path);self.status.set('Google client configuration saved in the OS vault. Connect Gmail OAuth next.')
    def connect_google(self):
        allow_send=self.google_send.get()
        def work():
            result=google_mail.connect(allow_send)
            with google_mail.session() as client:
                info=google_mail.checked(client.get('https://gmail.googleapis.com/gmail/v1/users/me/profile',timeout=25))
            self.store.save_setting('mail',dict(provider='Gmail OAuth',address=info['emailAddress']))
            return result+' Provider/address saved; choose Gmail OAuth in the email controls.'
        self.background(work)
    def account_tools(self):
        w=tk.Toplevel(self.root);w.title('Account tools — exact portal origin');w.geometry('650x440')
        values={}
        defaults={'Portal URL':'','Account email':self.store.setting('profile',{}).get('email',''),'Verification sender':''}
        ids=self.tree.selection()
        if ids:defaults['Portal URL']=self.store.job(ids[0])['url']
        for name in defaults:
            ttk.Label(w,text=name).pack(anchor='w',padx=12,pady=5)
            box=ttk.Entry(w,width=80);box.pack(padx=12,fill='x');box.insert(0,defaults[name]);values[name]=box
        ttk.Label(w,text='Credentials apply only to the exact HTTPS origin. For shared ATS hosts, reuse one account only if the portal does. Enter a different login directly in the browser when accounts are tenant-specific.',wraplength=610).pack(padx=12,pady=10)
        def save(generated):
            url=values['Portal URL'].get();address=values['Account email'].get().strip()
            password=None if generated else simpledialog.askstring('Existing account','Existing portal password',show='*',parent=w)
            if not generated and not password:return
            origin=accounts.account_origin(url)
            configured=self.store.setting('accounts',{})
            if generated and origin in configured and not messagebox.askyesno('Replace stored credential','A credential already exists for this origin. Generate and replace it?',parent=w):return
            sender=values['Verification sender'].get().strip().lower()
            if sender and ('@' not in sender or any(c in sender for c in '\r\n')):raise ValueError('Enter an exact sender email address.')
            origin=accounts.save_account(self.store,url,address,password)
            if sender:
                mapping=self.store.setting('otp_senders',{});mapping[origin]=sender;self.store.save_setting('otp_senders',mapping)
            self.status.set('Credential saved in OS vault. On the portal, use Fill saved account; review and submit account registration there.')
            w.destroy()
        ttk.Button(w,text='Generate password for new account',command=lambda:self.guard(lambda:save(True))).pack(padx=12,pady=5,anchor='w')
        ttk.Button(w,text='Save existing account password',command=lambda:self.guard(lambda:save(False))).pack(padx=12,pady=5,anchor='w')
    def settings_tab(self):
        t=self.tab('5  Saved sources')
        ttk.Label(t,text='One company board per line: provider | identifier or board URL | region (global/eu)').pack(anchor='w')
        self.boards=tk.Text(t,height=15,width=100,font=('Consolas',11));self.boards.pack(fill='both',expand=True,pady=10)
        self.boards.insert('1.0',self.store.setting('board_text',''))
        bar=ttk.Frame(t);bar.pack(fill='x')
        ttk.Button(bar,text='Save sources',command=lambda:self.guard(self.save_sources)).pack(side='left')
        ttk.Button(bar,text='Refresh saved sources',command=self.refresh_sources).pack(side='left',padx=8)
        self.repeat_sources=tk.BooleanVar(value=self.store.setting('repeat_sources',False))
        ttk.Checkbutton(t,text='Refresh these sources every 15 minutes while ApplyPilot is open',variable=self.repeat_sources,command=lambda:self.store.save_setting('repeat_sources',self.repeat_sources.get())).pack(anchor='w',pady=10)
        ttk.Label(t,text='Imports never trigger applications. Select suitable jobs in Jobs & applications before starting a queue.').pack(anchor='w')
    def save_sources(self):
        text=self.boards.get('1.0','end').strip();rows=[]
        for line in text.splitlines():
            if not line.strip():continue
            parts=[p.strip() for p in line.split('|')]
            if len(parts) not in (2,3) or parts[0] not in PROVIDERS:raise ValueError('Use Provider | company | optional region on each line.')
            company=board_identifier(parts[0],parts[1]);region=parts[2] if len(parts)==3 else 'global'
            if region not in ('global','eu'):raise ValueError('Region must be global or eu.')
            rows.append(dict(provider=parts[0],company=company,region=region))
        self.store.save_setting('boards',rows);self.store.save_setting('board_text',text);self.status.set(f'Saved {len(rows)} company sources.')
    def refresh_sources(self):
        if not self.import_lock.acquire(blocking=False):self.status.set('Saved sources are already refreshing.');return
        def work():
            results=[]
            try:
                for board in self.store.setting('boards',[]):
                    try:
                        jobs=import_board(board['provider'],board['company'],board['region'])
                        for job in jobs:self.store.add(job)
                        results.append(board['company']+': '+str(len(jobs)))
                    except Exception as e:results.append(board['company']+': '+str(e)[:100])
                return 'Source refresh complete. '+'; '.join(results)
            finally:self.import_lock.release()
        self.background(work)
    def scheduled_refresh(self):
        if self.store.setting('repeat_sources',False):self.refresh_sources()
        self.root.after(900000,self.scheduled_refresh)
    def activity_tab(self):
        t=self.tab('4  Activity');self.log=tk.Text(t,wrap='word',font=('Consolas',10));self.log.pack(fill='both',expand=True)
        ttk.Button(t,text='Export application CSV',command=lambda:self.guard(self.export)).pack(anchor='w',pady=8)
    def export(self):
        path=filedialog.asksaveasfilename(defaultextension='.csv')
        if not path:return
        rows=self.store.jobs()
        with open(path,'w',newline='',encoding='utf-8-sig') as f:
            writer=csv.DictWriter(f,fieldnames=['id','url','company','title','location','description','status','note','updated']);writer.writeheader()
            # Prevent spreadsheet formula execution from imported listing content.
            for row in rows:writer.writerow({k:("'"+v if isinstance(v,str) and v.startswith(('=','+','-','@')) else v) for k,v in row.items()})
    def open_path(self,path):
        if sys.platform=='win32':os.startfile(str(path))
        elif sys.platform=='darwin':subprocess.Popen(['open',str(path)])
        else:subprocess.Popen(['xdg-open',str(path)])
    def pump(self):
        try:
            while True:
                text=self.queue.get_nowait();self.status.set(text);self.log.insert('end',text+'\n');self.log.see('end');self.refresh();self.refresh_mail()
                if text.startswith('Gmail OAuth connected'):
                    config=self.store.setting('mail',{});self.mailprovider.set(config.get('provider','Gmail OAuth'));self.address.set(config.get('address',''))
                if 'needs' in text.lower() or 'verification' in text.lower() or re.search(r'\b[1-9]\d* new possible interview',text):self.root.bell()
        except queue.Empty:pass
        self.root.after(300,self.pump)
    def close(self):
        self.worker.stop()
        def finish():
            if self.worker.thread and self.worker.thread.is_alive():
                self.status.set('Closing the browser session safely…')
                self.root.after(200,finish)
            else:self.root.destroy()
        finish()

def main():
    from .instance import acquire
    root=tk.Tk()
    folder=Path(os.getenv('LOCALAPPDATA',str(Path.home()/'.local/share')))/'ApplyPilot'
    try:
        lock=acquire(folder)
    except RuntimeError as e:
        root.withdraw();messagebox.showinfo('ApplyPilot',str(e));root.destroy();return
    try:
        App(root,folder);root.mainloop()
    finally:
        lock.close()
