import csv
import json
import os
import queue
import re
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import tkinter as tk
from pathlib import Path
from tkinter import ttk, filedialog, messagebox, simpledialog
from .core import Store, documents, import_board, match
from .browser import BrowserWorker
from . import mail
from .sources import PROVIDERS, board_identifier
from . import accounts, google_mail
from .productivity import resume_text, extract_profile, plan_queue, assess
from .system import capabilities
from .theme import apply_style, UI_FONT, CODE_FONT

FIELDS=['name','email','phone','location','linkedin','website','skills','summary','experience','projects','education']

class App:
    def __init__(self,root,folder=None):
        self.root=root
        self.store=Store(folder or Path(os.getenv('LOCALAPPDATA',str(Path.home()/'.local/share')))/'ApplyPilot')
        self.queue=queue.Queue();self.worker=BrowserWorker(self.store,self.queue.put)
        self.auto=tk.BooleanVar(value=self.store.setting('auto_submit',False))
        self.import_lock=threading.Lock();self.mail_sync_lock=threading.Lock()
        self.busy_count=0;self.offset=0;self.total_jobs=0;self.filter_timer=None
        self.queued_ids=self.store.setting('planned_queue',[]);self.pages={};self.nav={};self.current_page=''
        self.status=tk.StringVar(value='Welcome. Import your resume once, then set your job preferences.')
        root.title('ApplyPilot 0.3');root.geometry(f'{min(1240,root.winfo_screenwidth()-60)}x{min(820,root.winfo_screenheight()-90)}');root.minsize(min(960,root.winfo_screenwidth()-40),min(640,root.winfo_screenheight()-60))
        self.colors=apply_style(root,self.store.setting('theme','light'))
        root.grid_rowconfigure(0,weight=1);root.grid_columnconfigure(1,weight=1)
        c=self.colors
        self.sidebar=tk.Frame(root,bg=c['nav'],width=185);self.sidebar.grid(row=0,column=0,sticky='nsew');self.sidebar.pack_propagate(False)
        brand=tk.Frame(self.sidebar,bg=c['nav']);brand.pack(fill='x',padx=20,pady=(28,8))
        logo=tk.Canvas(brand,width=32,height=32,bg=c['nav'],highlightthickness=0);logo.pack(side='left',padx=(0,8));logo.create_polygon(5,26,16,4,28,26,21,26,16,15,11,26,fill='#9183FF',outline='')
        tk.Label(brand,text='ApplyPilot',font=(UI_FONT,16,'bold'),bg=c['nav'],fg='white').pack(side='left')
        tk.Label(self.sidebar,text='CAREER WORKSPACE',font=(UI_FONT,8,'bold'),bg=c['nav'],fg=c['navtext']).pack(anchor='w',padx=23,pady=(2,28))
        self.nav_area=tk.Frame(self.sidebar,bg=c['nav']);self.nav_area.pack(fill='x')
        footer=tk.Frame(self.sidebar,bg=c['nav']);footer.pack(side='bottom',fill='x',padx=20,pady=22)
        tk.Label(footer,text='LOCAL  /  PRIVATE  /  FREE',font=(UI_FONT,8,'bold'),bg=c['nav'],fg=c['navtext']).pack(anchor='w')
        tk.Label(footer,text='Version 0.3 preview',font=(UI_FONT,9),bg=c['nav'],fg=c['navtext']).pack(anchor='w',pady=(6,0))
        shell=ttk.Frame(root,padding=(24,18,24,12));shell.grid(row=0,column=1,sticky='nsew');shell.grid_rowconfigure(1,weight=1);shell.grid_columnconfigure(0,weight=1)
        top=ttk.Frame(shell);top.grid(row=0,column=0,sticky='ew',pady=(0,18))
        self.page_title=tk.StringVar(value='Overview');ttk.Label(top,textvariable=self.page_title,style='Section.TLabel').pack(side='left')
        ttk.Button(top,text='Theme',command=self.toggle_theme).pack(side='right');ttk.Label(top,text='Everything stays on your laptop',style='Muted.TLabel').pack(side='right',padx=12)
        self.tabs=ttk.Frame(shell);self.tabs.grid(row=1,column=0,sticky='nsew');self.tabs.grid_columnconfigure(0,weight=1);self.tabs.grid_rowconfigure(0,weight=1);self.tabs.grid_propagate(False)
        self.home_tab();self.profile_tab();self.jobs_tab();self.mail_tab();self.settings_tab();self.preferences_tab();self.activity_tab();self.diagnostics_tab()
        bottom=ttk.Frame(shell);bottom.grid(row=2,column=0,sticky='ew',pady=(12,0));bottom.grid_columnconfigure(0,weight=1)
        ttk.Label(bottom,textvariable=self.status,wraplength=700,style='Muted.TLabel').grid(row=0,column=0,sticky='w')
        self.progress=ttk.Progressbar(bottom,mode='indeterminate',length=100);self.progress.grid(row=0,column=1,padx=(10,0));self.progress.grid_remove()
        self.recolor_widgets();self.refresh();self.show_page('Overview');self.pump();root.after(900000,self.scheduled_refresh);root.after(300000,self.scheduled_mail);root.protocol('WM_DELETE_WINDOW',self.close)

    def tab(self,name):
        name=re.sub(r'^\d\s+','',name)
        name={'Jobs & applications':'Job library','Email tracker':'Inbox','Saved sources':'Sources'}.get(name,name)
        outer=ttk.Frame(self.tabs);outer.grid(row=0,column=0,sticky='nsew');outer.grid_columnconfigure(0,weight=1);outer.grid_rowconfigure(0,weight=1)
        canvas=tk.Canvas(outer,highlightthickness=0,bg=self.colors['bg']);canvas.grid(row=0,column=0,sticky='nsew')
        scroll=ttk.Scrollbar(outer,orient='vertical',command=canvas.yview);scroll.grid(row=0,column=1,sticky='ns');canvas.configure(yscrollcommand=scroll.set)
        t=ttk.Frame(canvas);window=canvas.create_window((0,0),window=t,anchor='nw')
        def layout(event=None):
            width=max(1,canvas.winfo_width());height=max(t.winfo_reqheight(),canvas.winfo_height())
            canvas.itemconfigure(window,width=width,height=height);canvas.configure(scrollregion=(0,0,width,height))
            if t.winfo_reqheight()>canvas.winfo_height()+2:scroll.grid()
            else:scroll.grid_remove()
        t.bind('<Configure>',layout);canvas.bind('<Configure>',layout)
        self.pages[name]=outer
        button=tk.Button(self.nav_area,text='  '+name,anchor='w',font=(UI_FONT,10),relief='flat',bd=0,highlightthickness=0,padx=15,pady=12,bg=self.colors['nav'],fg=self.colors['navtext'],activebackground='#283453',activeforeground='white',command=lambda:self.show_page(name),cursor='hand2')
        button.pack(fill='x',padx=12,pady=2);self.nav[name]=button
        return t
    def show_page(self,name):
        self.pages[name].tkraise();self.current_page=name;self.page_title.set(name)
        for key,button in self.nav.items():button.configure(bg='#283453' if key==name else self.colors['nav'],fg='white' if key==name else self.colors['navtext'])
    def toggle_theme(self):
        mode='dark' if self.store.setting('theme','light')=='light' else 'light'
        self.store.save_setting('theme',mode);self.colors=apply_style(self.root,mode)
        self.recolor_widgets();self.status.set('Theme changed.')
    def recolor_widgets(self,widget=None):
        widget=widget or self.root
        if isinstance(widget,tk.Canvas) and widget.winfo_reqwidth()>100:widget.configure(bg=self.colors['bg'])
        if isinstance(widget,tk.Text):widget.configure(bg=self.colors['surface'],fg=self.colors['ink'],insertbackground=self.colors['ink'])
        for child in widget.winfo_children():self.recolor_widgets(child)
    def guard(self,fn):
        try: return fn()
        except Exception as e: messagebox.showerror('ApplyPilot',str(e))
    def background(self,fn):
        self.busy_count+=1
        def run():
            try:
                result=fn()
                if result is not None:self.queue.put(result)
            except Exception as e:self.queue.put('Error: '+str(e))
            finally:self.queue.put({'type':'task_done'})
        threading.Thread(target=run,daemon=True).start()

    def profile_tab(self):
        t=self.tab('1  Profile')
        ttk.Label(t,text='Use only information you can stand behind. Blank fields stay unanswered.').pack(anchor='w',pady=5)
        pane=ttk.Frame(t);pane.pack(fill='both',expand=True)
        canvas=tk.Canvas(pane,highlightthickness=0,background='#f4f6fa');scroll=ttk.Scrollbar(pane,orient='vertical',command=canvas.yview);inner=ttk.Frame(canvas)
        inner.bind('<Configure>',lambda e:canvas.configure(scrollregion=canvas.bbox('all')));window=canvas.create_window((0,0),window=inner,anchor='nw');inner.grid_columnconfigure(1,weight=1);canvas.bind('<Configure>',lambda e:canvas.itemconfigure(window,width=e.width));canvas.configure(yscrollcommand=scroll.set);canvas.pack(side='left',fill='both',expand=True);scroll.pack(side='right',fill='y')
        self.fields={};p=self.store.setting('profile',{})
        for i,key in enumerate(FIELDS):
            ttk.Label(inner,text=key.replace('_',' ').title(),width=18).grid(row=i,column=0,sticky='nw',pady=6)
            h=4 if key in {'summary','experience','projects','education'} else 1
            box=tk.Text(inner,height=h,width=45,font=(UI_FONT,10),wrap='word',relief='flat',borderwidth=0,padx=8,pady=6,highlightthickness=1,highlightbackground=self.colors['line'],highlightcolor=self.colors['accent'])
            box.insert('1.0',p.get(key,''));box.grid(row=i,column=1,pady=6,sticky='ew');self.fields[key]=box
        ttk.Label(inner,text='Reusable answers',width=18).grid(row=len(FIELDS),column=0,sticky='nw',pady=8)
        answer_panel=ttk.Frame(inner);answer_panel.grid(row=len(FIELDS),column=1,sticky='ew')
        self.answers=tk.Text(inner,height=1);self.answers.insert('1.0',json.dumps(p.get('answers',{})))
        self.answer_list=ttk.Treeview(answer_panel,columns=('question','answer'),show='headings',height=4)
        self.answer_list.heading('question',text='Question');self.answer_list.heading('answer',text='Your verified answer');self.answer_list.column('question',width=240);self.answer_list.column('answer',width=180)
        self.answer_list.pack(fill='x')
        self.qa_question=tk.StringVar();self.qa_answer=tk.StringVar()
        ttk.Label(answer_panel,text='Question exactly as shown on the form',style='Muted.TLabel').pack(anchor='w',pady=(8,2));ttk.Entry(answer_panel,textvariable=self.qa_question).pack(fill='x')
        ttk.Label(answer_panel,text='Your answer',style='Muted.TLabel').pack(anchor='w',pady=(8,2));ttk.Entry(answer_panel,textvariable=self.qa_answer).pack(fill='x')
        qa_buttons=ttk.Frame(answer_panel);qa_buttons.pack(fill='x',pady=6)
        ttk.Button(qa_buttons,text='Add / update answer',command=lambda:self.guard(self.add_answer)).pack(side='left')
        ttk.Button(qa_buttons,text='Remove selected',command=lambda:self.guard(self.remove_answer)).pack(side='left',padx=6)
        self.render_answers()
        canvas.bind('<Enter>',lambda e:canvas.bind_all('<MouseWheel>',lambda event:canvas.yview_scroll(-int(event.delta/120) if abs(event.delta)>=120 else (-1 if event.delta>0 else 1),'units')))
        canvas.bind('<Leave>',lambda e:canvas.unbind_all('<MouseWheel>'))
        buttons=ttk.Frame(t);buttons.pack(fill='x',pady=10)
        ttk.Button(buttons,text='Save profile',style='Accent.TButton',command=lambda:self.guard(self.save_profile)).pack(side='left')
        ttk.Button(buttons,text='Import resume',command=lambda:self.guard(self.import_resume)).pack(side='left',padx=6)
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
        self.answers.delete('1.0','end');self.answers.insert('1.0',json.dumps(p.get('answers',{}),indent=2));self.render_answers()
    def render_answers(self):
        self.answer_list.delete(*self.answer_list.get_children())
        for question,answer in json.loads(self.answers.get('1.0','end')).items():self.answer_list.insert('','end',values=(question,answer))
    def add_answer(self):
        question=self.qa_question.get().strip();answer=self.qa_answer.get().strip()
        if not question or not answer:raise ValueError('Enter a question and your verified answer.')
        data=json.loads(self.answers.get('1.0','end'));data[question]=answer
        self.answers.delete('1.0','end');self.answers.insert('1.0',json.dumps(data));self.render_answers();self.qa_question.set('');self.qa_answer.set('')
        self.status.set('Answer added to the editor. Choose Save profile to reuse it.')
    def remove_answer(self):
        data=json.loads(self.answers.get('1.0','end'))
        for item in self.answer_list.selection():data.pop(self.answer_list.item(item,'values')[0],None)
        self.answers.delete('1.0','end');self.answers.insert('1.0',json.dumps(data));self.render_answers()
    def jobs_tab(self):
        t=self.tab('Job library')
        ttk.Label(t,text='Find the roles worth your time.',style='Title.TLabel').pack(anchor='w')
        ttk.Label(t,text='Import company openings, narrow your list, and build your next queue.',style='Muted.TLabel').pack(anchor='w',pady=(4,16))
        top=ttk.Frame(t);top.pack(fill='x')
        self.provider=tk.StringVar(value='Greenhouse');ttk.Combobox(top,textvariable=self.provider,values=PROVIDERS,width=15,state='readonly').pack(side='left')
        self.board=tk.StringVar();ttk.Entry(top,textvariable=self.board,width=24).pack(side='left',padx=6)
        self.region=tk.StringVar(value='global');ttk.Combobox(top,textvariable=self.region,values=['global','eu'],width=7,state='readonly').pack(side='left')
        ttk.Button(top,text='Import',style='Accent.TButton',command=self.import_jobs).pack(side='left',padx=6)
        ttk.Button(top,text='+ Job link',command=lambda:self.guard(self.add_job)).pack(side='left')
        bar=ttk.Frame(t);bar.pack(fill='x',pady=12)
        self.filter=tk.StringVar();self.filter.trace_add('write',self.schedule_search)
        ttk.Label(bar,text='Search').pack(side='left');ttk.Entry(bar,textvariable=self.filter,width=28).pack(side='left',padx=8)
        self.status_filter=tk.StringVar();ttk.Combobox(bar,textvariable=self.status_filter,values=['','saved','prepared','needs_attention','submitted','uncertain','interview','rejected','closed'],width=17,state='readonly').pack(side='left')
        self.status_filter.trace_add('write',self.schedule_search)
        ttk.Button(bar,text='Select page',command=lambda:self.tree.selection_set(self.tree.get_children())).pack(side='right')
        table=ttk.Frame(t);table.pack(fill='both',expand=True)
        self.tree=ttk.Treeview(table,columns=('company','title','location','status'),show='headings',selectmode='extended',height=4)
        for col,w in [('company',135),('title',290),('location',180),('status',135)]:self.tree.heading(col,text=col.title());self.tree.column(col,width=w,minwidth=90)
        self.tree.grid(row=0,column=0,sticky='nsew');table.grid_rowconfigure(0,weight=1);table.grid_columnconfigure(0,weight=1)
        ttk.Scrollbar(table,orient='vertical',command=self.tree.yview).grid(row=0,column=1,sticky='ns');self.tree.configure(yscrollcommand=lambda *a:table.grid_slaves(row=0,column=1)[0].set(*a))
        scroll=ttk.Scrollbar(table,orient='horizontal',command=self.tree.xview);scroll.grid(row=1,column=0,sticky='ew');self.tree.configure(xscrollcommand=scroll.set)
        self.tree.bind('<Double-1>',lambda e:self.guard(self.details))
        pager=ttk.Frame(t);pager.pack(fill='x',pady=8);self.page_label=tk.StringVar();ttk.Label(pager,textvariable=self.page_label,style='Muted.TLabel').pack(side='left')
        ttk.Button(pager,text='Next',command=lambda:self.page_move(1)).pack(side='right');ttk.Button(pager,text='Previous',command=lambda:self.page_move(-1)).pack(side='right',padx=6)
        actions=ttk.Frame(t);actions.pack(fill='x',pady=(4,8))
        ttk.Button(actions,text='Start selected',style='Accent.TButton',command=lambda:self.guard(self.start)).pack(side='left')
        ttk.Button(actions,text='Prepare PDFs',command=lambda:self.guard(self.prepare)).pack(side='left',padx=6)
        ttk.Button(actions,text='Account tools',command=lambda:self.guard(self.account_tools)).pack(side='left')
        ttk.Button(actions,text='Set status',command=lambda:self.guard(self.set_status)).pack(side='right')
        ttk.Button(actions,text='Refresh',command=self.refresh).pack(side='right',padx=6)
        ttk.Checkbutton(t,text='Submit supported applications automatically after filling known answers',variable=self.auto,command=lambda:self.store.save_setting('auto_submit',self.auto.get())).pack(anchor='w')
        ttk.Label(t,text='Only supported Lever / Greenhouse forms. Verification and unknown questions pause for you.',style='Muted.TLabel').pack(anchor='w',pady=(4,0))

    def selected(self):
        ids=list(self.tree.selection())
        if not ids:raise ValueError('Select one or more jobs first')
        return ids
    def refresh(self):
        if not hasattr(self,'tree'):return
        selected=set(self.tree.selection());preferences=self.store.setting('preferences',{})
        size=50 if preferences.get('low_resource',False) else 100
        rows,total=self.store.page(self.filter.get(),self.status_filter.get(),size,self.offset);self.total_jobs=total
        if self.offset>=total and self.offset:
            self.offset=max(0,((total-1)//size)*size);rows,total=self.store.page(self.filter.get(),self.status_filter.get(),size,self.offset)
        wanted=[j['id'] for j in rows]
        for jid in self.tree.get_children():
            if jid not in wanted:self.tree.delete(jid)
        for index,j in enumerate(rows):
            values=(j['company'],j['title'],j['location'],j['status'].replace('_',' '))
            if self.tree.exists(j['id']):self.tree.item(j['id'],values=values);self.tree.move(j['id'],'',index)
            else:self.tree.insert('','end',iid=j['id'],values=values)
        self.tree.selection_set([x for x in selected if self.tree.exists(x)])
        self.page_label.set(f'{self.offset+1 if rows else 0}–{self.offset+len(rows)} of {total:,} jobs')
        counts=self.store.counts()
        for key,var in self.stat_vars.items():var.set(str(sum(counts.values())) if key=='all' else str(counts.get(key,0)))
        profile=self.store.setting('profile',{})
        ready=sum(bool(profile.get(k)) for k in ('name','email','skills','education'))
        self.setup_label.set(f'Profile {ready}/4 essentials  ·  {len(self.store.setting("boards",[]))} saved sources  ·  {len(self.queued_ids)} jobs in your queue')
    def schedule_search(self,*args):
        self.offset=0
        if self.filter_timer:self.root.after_cancel(self.filter_timer)
        self.filter_timer=self.root.after(250,self.refresh)
    def page_move(self,delta):
        size=50 if self.store.setting('preferences',{}).get('low_resource',False) else 100
        self.offset=max(0,min(max(0,self.total_jobs-1),self.offset+delta*size));self.refresh()

    def add_job(self):
        url=simpledialog.askstring('Add job','HTTPS application URL:')
        if not url:return
        company=simpledialog.askstring('Company','Company name:');title=simpledialog.askstring('Role','Job title:')
        if company and title:self.store.add(dict(url=url,company=company,title=title));self.refresh()
    def import_jobs(self):
        if not self.import_lock.acquire(blocking=False):self.status.set('A source import is already running.');return
        provider=self.provider.get();board=self.board.get().strip();region=self.region.get()
        def work():
            try:
                jobs=import_board(provider,board,region);added=self.store.add_many(jobs)
                return f'Imported {len(jobs):,} openings; {added:,} new jobs added.'
            finally:self.import_lock.release()
        self.background(work)
    def prepare(self):
        ids=self.selected();profile=self.store.setting('profile',{})
        def work():
            for jid in ids:
                j=self.store.job(jid);documents(self.store,profile,j)
                if j['status']=='saved':self.store.state(jid,'prepared','Documents generated')
            return f'Prepared {len(ids)} document sets. Use Documents on the overview to open them.'
        self.background(work)

    def start(self):
        ids=self.selected()
        if not self.store.setting('profile'):raise ValueError('Save your profile first')
        self.queued_ids=ids;self.store.save_setting('planned_queue',ids);self.render_queue()
        self.worker.start(ids,self.auto.get());self.status.set('Browser starting…');self.show_page('Overview')

    def set_status(self):
        state=simpledialog.askstring('Status','saved / prepared / needs_attention / submitted / uncertain / interview / rejected / closed')
        if state:
            if state=='saved' and not messagebox.askyesno('Check before retry','Have you checked that these jobs were not already submitted?'):return
            for jid in self.selected():self.store.state(jid,state,'Manually set by user')
            self.refresh()
    def details(self,jid=None):
        j=self.store.job(jid or self.selected()[0]);w=tk.Toplevel(self.root);w.title(j['title']);w.geometry('820x650')
        panel=ttk.Frame(w,padding=22);panel.pack(fill='both',expand=True)
        ttk.Label(panel,text=j['title'],style='Section.TLabel',wraplength=740).pack(anchor='w')
        ttk.Label(panel,text=j['company']+'  /  '+j['location'],style='Muted.TLabel').pack(anchor='w',pady=8)
        ttk.Label(panel,text='Status: '+j['status'].replace('_',' ')).pack(anchor='w',pady=(0,12))
        box=tk.Text(panel,wrap='word',font=(UI_FONT,10),relief='flat',padx=14,pady=14,bg=self.colors['surface'],fg=self.colors['ink']);box.pack(fill='both',expand=True)
        box.insert('1.0',(j['description'] or 'Description is available on the employer page.')+('\n\nLatest note: '+j['note'] if j['note'] else ''));box.configure(state='disabled')
        bar=ttk.Frame(panel);bar.pack(fill='x',pady=(12,0))
        def open_job():
            import webbrowser
            webbrowser.open(j['url'])
        ttk.Button(bar,text='View employer page',style='Accent.TButton',command=open_job).pack(side='left')
        ttk.Button(bar,text='Open documents',command=lambda:self.guard(lambda:self.open_path(self.store.folder/'documents'/j['id']))).pack(side='left',padx=8)
    def mail_tab(self):
        t=self.tab('3  Email tracker');ttk.Label(t,text='Connect Gmail OAuth, use IMAP with an app password, or import .eml files. Connection remains on your computer.').pack(anchor='w')
        bar=ttk.Frame(t);bar.pack(fill='x',pady=10)
        settings=self.store.setting('mail',{});self.mailprovider=tk.StringVar(value=settings.get('provider','Gmail'));self.address=tk.StringVar(value=settings.get('address',''))
        ttk.Combobox(bar,textvariable=self.mailprovider,values=list(mail.HOSTS)+['Gmail OAuth'],state='readonly',width=12).pack(side='left');ttk.Entry(bar,textvariable=self.address,width=25).pack(side='left',padx=6)
        ttk.Button(bar,text='App password',command=lambda:self.guard(self.save_mail)).pack(side='left')
        ttk.Button(bar,text='Sync',command=self.sync_mail).pack(side='left',padx=6)
        ttk.Button(bar,text='Import email',command=lambda:self.guard(self.import_eml)).pack(side='left')
        oauthbar=ttk.Frame(t);oauthbar.pack(fill='x',pady=6)
        ttk.Button(oauthbar,text='Google client JSON',command=lambda:self.guard(self.import_google_client)).pack(side='left')
        self.google_send=tk.BooleanVar(value=False);ttk.Checkbutton(oauthbar,text='Allow sending',variable=self.google_send).pack(side='left',padx=6)
        ttk.Button(oauthbar,text='Connect Google',command=self.connect_google).pack(side='left')
        ttk.Button(oauthbar,text='Disconnect',command=lambda:self.background(google_mail.disconnect)).pack(side='left',padx=6)
        self.mailtree=ttk.Treeview(t,columns=('from','subject','stage'),show='headings')
        for c in ('from','subject','stage'):self.mailtree.heading(c,text=c.title());self.mailtree.column(c,width=230)
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
        t=self.tab('Sources')
        ttk.Label(t,text='Follow companies, not browser tabs.',style='Title.TLabel').pack(anchor='w')
        ttk.Label(t,text='Add a supported company board. Saved sources refresh together.',style='Muted.TLabel').pack(anchor='w',pady=(6,18))
        bar=ttk.Frame(t);bar.pack(fill='x')
        self.source_provider=tk.StringVar(value='Greenhouse');ttk.Combobox(bar,textvariable=self.source_provider,values=PROVIDERS,width=15,state='readonly').pack(side='left')
        self.source_company=tk.StringVar();ttk.Entry(bar,textvariable=self.source_company,width=26).pack(side='left',padx=6)
        self.source_region=tk.StringVar(value='global');ttk.Combobox(bar,textvariable=self.source_region,values=['global','eu'],width=7,state='readonly').pack(side='left')
        ttk.Button(bar,text='Add company',style='Accent.TButton',command=lambda:self.guard(self.save_sources)).pack(side='left',padx=6)
        ttk.Label(t,text='Enter a company identifier or paste its Greenhouse, Lever, Ashby or SmartRecruiters board URL.',style='Muted.TLabel',wraplength=700).pack(anchor='w',pady=(8,16))
        self.source_tree=ttk.Treeview(t,columns=('provider','company','region'),show='headings',height=5)
        for k,w in [('provider',170),('company',320),('region',100)]:self.source_tree.heading(k,text=k.title());self.source_tree.column(k,width=w)
        self.source_tree.pack(fill='both',expand=True)
        actions=ttk.Frame(t);actions.pack(fill='x',pady=12)
        ttk.Button(actions,text='Refresh sources',style='Accent.TButton',command=self.refresh_sources).pack(side='left')
        ttk.Button(actions,text='Add starter companies',command=self.starter_sources).pack(side='left',padx=6)
        ttk.Button(actions,text='Remove selected',command=self.remove_source).pack(side='left')
        self.repeat_sources=tk.BooleanVar(value=self.store.setting('repeat_sources',False))
        ttk.Checkbutton(t,text='Refresh sources every 15 minutes while ApplyPilot is open',variable=self.repeat_sources,command=lambda:self.store.save_setting('repeat_sources',self.repeat_sources.get())).pack(anchor='w',pady=8)
        ttk.Label(t,text='Imports do not submit applications. Your preferences decide which jobs enter a queue.',style='Muted.TLabel',wraplength=700).pack(anchor='w')
        self.render_sources()
    def render_sources(self):
        self.source_tree.delete(*self.source_tree.get_children())
        for i,board in enumerate(self.store.setting('boards',[])):self.source_tree.insert('','end',iid=str(i),values=(board['provider'],board['company'],board['region']))
    def save_sources(self):
        provider=self.source_provider.get();company=board_identifier(provider,self.source_company.get());region=self.source_region.get()
        boards=self.store.setting('boards',[]);board=dict(provider=provider,company=company,region=region)
        if board not in boards:boards.append(board)
        self.store.save_setting('boards',boards);self.source_company.set('');self.render_sources();self.refresh();self.status.set('Company saved. Refresh sources to import its openings.')
    def starter_sources(self):
        boards=self.store.setting('boards',[])
        for provider,company in [('Greenhouse','databricks'),('Lever','palantir'),('Ashby','ramp'),('SmartRecruiters','BoschGroup')]:
            board=dict(provider=provider,company=company,region='global')
            if board not in boards:boards.append(board)
        self.store.save_setting('boards',boards);self.render_sources();self.refresh();self.status.set('Starter companies added. Refresh sources to fetch current openings.')
    def remove_source(self):
        removed={int(item) for item in self.source_tree.selection()};boards=self.store.setting('boards',[])
        self.store.save_setting('boards',[board for i,board in enumerate(boards) if i not in removed]);self.render_sources();self.refresh()
    def refresh_sources(self):
        if not self.import_lock.acquire(blocking=False):self.status.set('Sources are already refreshing.');return
        def work():
            results=[];boards=self.store.setting('boards',[])
            workers=1 if self.store.setting('preferences',{}).get('low_resource',False) else 3
            try:
                def fetch(board):return board,import_board(board['provider'],board['company'],board['region'])
                with ThreadPoolExecutor(max_workers=workers) as pool:
                    futures={pool.submit(fetch,board):board for board in boards}
                    for future in as_completed(futures):
                        board=futures[future]
                        try:
                            _,jobs=future.result();added=self.store.add_many(jobs);results.append(f"{board['company']}: {added:,} new / {len(jobs):,} found")
                        except Exception as e:results.append(board['company']+': '+str(e)[:100])
                return 'Sources refreshed. '+'; '.join(results)
            finally:self.import_lock.release()
        self.background(work)

    def scheduled_refresh(self):
        if self.store.setting('repeat_sources',False):self.refresh_sources()
        self.root.after(900000,self.scheduled_refresh)
    def activity_tab(self):
        t=self.tab('4  Activity');self.log=tk.Text(t,wrap='word',font=(CODE_FONT,10));self.log.pack(fill='both',expand=True)
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
        Path(path).mkdir(parents=True,exist_ok=True)
        if sys.platform=='win32':os.startfile(str(path))
        elif sys.platform=='darwin':subprocess.Popen(['open',str(path)])
        else:subprocess.Popen(['xdg-open',str(path)])
    def pump(self):
        changed=False
        for _ in range(100):
            try:event=self.queue.get_nowait()
            except queue.Empty:break
            if isinstance(event,dict):
                if event['type']=='task_done':self.busy_count=max(0,self.busy_count-1)
                elif event['type']=='resume_import':self.review_resume(event)
                elif event['type'] in {'planned','start_planned'}:
                    self.queued_ids=event['ids'];self.store.save_setting('planned_queue',self.queued_ids);self.render_queue()
                    self.status.set(f'{len(self.queued_ids)} jobs matched your preferences. Verify eligibility before applying.')
                    if event['type']=='start_planned' and self.queued_ids:
                        try:self.worker.start(self.queued_ids,self.auto.get())
                        except Exception as e:self.status.set(str(e))
                changed=True;continue
            text=str(event);self.status.set(text);self.log.insert('end',text+'\n');self.log.see('end');changed=True
            if int(self.log.index('end-1c').split('.')[0])>600:self.log.delete('1.0','100.0')
            if text.startswith('Gmail OAuth connected'):
                config=self.store.setting('mail',{});self.mailprovider.set(config.get('provider','Gmail OAuth'));self.address.set(config.get('address',''))
            if 'needs' in text.lower() or 'verification' in text.lower() or re.search(r'\b[1-9]\d* new possible interview',text):self.root.bell()
        if changed:self.refresh();self.refresh_mail();self.render_queue()
        busy=self.busy_count>0 or (self.worker.thread is not None and self.worker.thread.is_alive())
        if busy and not getattr(self,'animating',False):self.progress.grid();self.progress.start(25);self.animating=True
        elif not busy and getattr(self,'animating',False):self.progress.stop();self.progress.grid_remove();self.animating=False
        self.root.after(200,self.pump)

    def close(self):
        self.worker.stop()
        def finish():
            if self.worker.thread and self.worker.thread.is_alive():
                self.status.set('Closing the browser session safely…')
                self.root.after(200,finish)
            else:self.root.destroy()
        finish()

    def home_tab(self):
        t=self.tab('Overview')
        hero=tk.Frame(t,bg='#6558E8',padx=26,pady=22);hero.pack(fill='x',pady=(0,18))
        tk.Label(hero,text='LESS REPETITION. MORE MOMENTUM.',font=(UI_FONT,8,'bold'),bg='#6558E8',fg='#DBD7FF').pack(anchor='w')
        tk.Label(hero,text='Your next role starts here.',font=(UI_FONT,25,'bold'),bg='#6558E8',fg='white').pack(anchor='w',pady=(10,6))
        tk.Label(hero,text='Prepare once. Find relevant openings. Keep every application in view.',font=(UI_FONT,10),bg='#6558E8',fg='#EFEDFF',wraplength=700,justify='left').pack(anchor='w')
        stats=ttk.Frame(t);stats.pack(fill='x',pady=(0,18));self.stat_vars={}
        for i,(key,label) in enumerate([('all','IN YOUR LIBRARY'),('prepared','DOCUMENTS READY'),('needs_attention','NEEDS YOUR INPUT'),('submitted','SUBMITTED')]):
            stats.grid_columnconfigure(i,weight=1,uniform='stats')
            card=ttk.Frame(stats,style='Card.TFrame',padding=16);card.grid(row=0,column=i,sticky='ew',padx=(0,10 if i<3 else 0))
            var=tk.StringVar(value='0');self.stat_vars[key]=var
            ttk.Label(card,text=label,style='CardMuted.TLabel',font=(UI_FONT,8,'bold')).pack(anchor='w')
            ttk.Label(card,textvariable=var,style='Card.TLabel',font=(UI_FONT,26,'bold')).pack(anchor='w',pady=(5,0))
        bar=ttk.Frame(t);bar.pack(fill='x',pady=(0,10));ttk.Label(bar,text='Your application queue',style='Section.TLabel').pack(side='left')
        ttk.Button(bar,text='Start my queue',style='Accent.TButton',command=lambda:self.guard(lambda:self.build_queue(True))).pack(side='right')
        ttk.Button(bar,text='Build queue',command=lambda:self.guard(lambda:self.build_queue(False))).pack(side='right',padx=8)
        self.setup_label=tk.StringVar();ttk.Label(t,textvariable=self.setup_label,style='Muted.TLabel').pack(anchor='w',pady=(0,10))
        queue_panel=ttk.Frame(t);queue_panel.pack(fill='both',expand=True);queue_panel.grid_rowconfigure(0,weight=1);queue_panel.grid_columnconfigure(0,weight=1)
        self.queue_tree=ttk.Treeview(queue_panel,columns=('title','company','status'),show='headings',height=3)
        for key,width in [('title',330),('company',160),('status',160)]:self.queue_tree.heading(key,text=key.title());self.queue_tree.column(key,width=width,minwidth=80)
        self.queue_tree.grid(row=0,column=0,sticky='nsew');self.queue_tree.bind('<Double-1>',lambda e:self.guard(lambda:self.details(self.queue_tree.selection()[0])))
        queue_scroll=ttk.Scrollbar(queue_panel,orient='vertical',command=self.queue_tree.yview);queue_scroll.grid(row=0,column=1,sticky='ns');self.queue_tree.configure(yscrollcommand=queue_scroll.set)
        helpers=ttk.Frame(t);helpers.pack(fill='x',pady=10)
        ttk.Button(helpers,text='Resume browser',command=self.worker.resume).pack(side='left')
        ttk.Button(helpers,text='Fill account',command=lambda:self.guard(lambda:self.worker.request('account'))).pack(side='left',padx=5)
        ttk.Button(helpers,text='Fetch email code',command=lambda:self.guard(lambda:self.worker.request('otp'))).pack(side='left')
        ttk.Button(helpers,text='Stop',command=self.worker.stop).pack(side='right')
        ttk.Button(helpers,text='Documents',command=lambda:self.open_path(self.store.folder/'documents')).pack(side='right',padx=6)
        ttk.Checkbutton(t,text='Submit supported forms automatically using my saved answers',variable=self.auto,command=lambda:self.store.save_setting('auto_submit',self.auto.get())).pack(anchor='w')
        ttk.Label(t,text='First time? Import your resume in Profile, save Preferences, then add company Sources.',style='Muted.TLabel',wraplength=700).pack(anchor='w',pady=(7,0))
        self.render_queue()
    def render_queue(self):
        self.queue_tree.delete(*self.queue_tree.get_children())
        valid=[]
        for jid in self.queued_ids:
            try:j=self.store.job(jid)
            except ValueError:continue
            valid.append(jid);self.queue_tree.insert('','end',iid=jid,values=(j['title'],j['company'],j['status'].replace('_',' ')))
        self.queued_ids=valid
    def build_queue(self,start=False):
        if self.worker.thread and self.worker.thread.is_alive():raise ValueError('A browser queue is already running.')
        profile=self.store.setting('profile',{});preferences=self.store.setting('preferences',{})
        if not profile.get('name') or '@' not in profile.get('email',''):
            self.show_page('Profile');raise ValueError('Save your profile name and email first.')
        if not preferences.get('titles','').strip():
            self.show_page('Preferences');raise ValueError('Save target role keywords before building a queue.')
        if start and self.queued_ids:
            pending=[jid for jid in self.queued_ids if self.store.job(jid)['status'] in {'saved','prepared'}]
            if pending:
                self.worker.start(pending,self.auto.get());self.status.set('Starting your reviewed queue…');return
        def work():return {'type':'start_planned' if start else 'planned','ids':plan_queue(self.store,profile,preferences)}
        self.background(work)
    def preferences_tab(self):
        t=self.tab('Preferences')
        ttk.Label(t,text='Make your search yours.',style='Title.TLabel').pack(anchor='w')
        ttk.Label(t,text='Set these once. Matching will prepare a bounded queue each time you start.',style='Muted.TLabel',wraplength=700).pack(anchor='w',pady=(5,20))
        p=self.store.setting('preferences',{});self.pref_fields={}
        form=ttk.Frame(t);form.pack(fill='x');form.grid_columnconfigure(1,weight=1)
        for i,(key,label,default) in enumerate([('titles','Target titles, comma separated',''),('locations','Locations, optional',''),('exclude','Exclude companies, optional',''),('min_skills','Minimum matching skills','1'),('queue_limit','Maximum jobs per queue (1–50)','10')]):
            ttk.Label(form,text=label).grid(row=i,column=0,sticky='w',pady=10,padx=(0,16))
            var=tk.StringVar(value=str(p.get(key,default)));self.pref_fields[key]=var;ttk.Entry(form,textvariable=var).grid(row=i,column=1,sticky='ew',pady=10)
        self.exclude_senior=tk.BooleanVar(value=p.get('exclude_senior',True));ttk.Checkbutton(t,text='Exclude senior / staff / manager roles',variable=self.exclude_senior).pack(anchor='w',pady=12)
        automatic=capabilities(self.store.folder)['low_resource_recommended']
        self.low_resource=tk.BooleanVar(value=p.get('low_resource',automatic));ttk.Checkbutton(t,text='Low resource mode: smaller pages and one source import at a time',variable=self.low_resource).pack(anchor='w',pady=8)
        browser=ttk.Frame(t);browser.pack(fill='x',pady=12);ttk.Label(browser,text='Application browser').pack(side='left')
        self.browser_choice=tk.StringVar(value=p.get('browser','auto'));ttk.Combobox(browser,textvariable=self.browser_choice,values=['auto','bundled','msedge','chrome'],state='readonly',width=18).pack(side='left',padx=15)
        ttk.Button(t,text='Save preferences',style='Accent.TButton',command=lambda:self.guard(self.save_preferences)).pack(anchor='w',pady=18)
        ttk.Label(t,text='Matching uses title, location and skill keywords. It does not establish eligibility, sponsorship or employer acceptance.',style='Muted.TLabel',wraplength=700).pack(anchor='w')
    def save_preferences(self):
        p={k:var.get().strip() for k,var in self.pref_fields.items()}
        p['min_skills']=int(p['min_skills']);p['queue_limit']=int(p['queue_limit'])
        if not 0<=p['min_skills']<=50 or not 1<=p['queue_limit']<=50:raise ValueError('Use 0–50 skills and 1–50 jobs per queue.')
        p.update(exclude_senior=self.exclude_senior.get(),low_resource=self.low_resource.get(),browser=self.browser_choice.get())
        self.store.save_setting('preferences',p);self.refresh();self.status.set('Preferences saved. Build a queue from Overview when ready.')
    def import_resume(self):
        path=filedialog.askopenfilename(filetypes=[('Resume','*.pdf *.docx *.txt *.md')])
        if not path:return
        def work():
            text=resume_text(path)
            return {'type':'resume_import','profile':extract_profile(text),'text':text,'path':path}
        self.background(work)
    def review_resume(self,event):
        w=tk.Toplevel(self.root);w.title('Review your imported resume');w.geometry('760x620')
        ttk.Label(w,text='Your resume, ready to reuse.',style='Section.TLabel').pack(anchor='w',padx=18,pady=14)
        ttk.Label(w,text='Review these extracted sections. You can edit them in Profile before saving.',wraplength=700).pack(anchor='w',padx=18)
        box=tk.Text(w,font=(UI_FONT,10),wrap='word',padx=14,pady=14);box.pack(fill='both',expand=True,padx=18,pady=12)
        parsed=event['profile']
        for key,value in parsed.items():box.insert('end',key.upper()+'\n'+value+'\n\n')
        box.configure(state='disabled')
        original=tk.BooleanVar(value=Path(event['path']).suffix.lower()=='.pdf')
        if Path(event['path']).suffix.lower()=='.pdf':ttk.Checkbutton(w,text='Use this PDF for applications and preserve its original formatting',variable=original).pack(anchor='w',padx=18,pady=4)
        def apply():
            for k,value in parsed.items():
                if k in self.fields and isinstance(value,str) and value.strip():self.fields[k].delete('1.0','end');self.fields[k].insert('1.0',value.strip())
            if original.get():
                import shutil
                dest=self.store.folder/'resume-source.pdf';shutil.copyfile(event['path'],dest);self.store.save_setting('resume_pdf',str(dest))
            else:self.store.save_setting('resume_pdf',None)
            self.show_page('Profile');self.status.set('Resume imported. Check the fields and choose Save profile.');w.destroy()
        ttk.Button(w,text='Use these details',style='Accent.TButton',command=lambda:self.guard(apply)).pack(anchor='e',padx=18,pady=(0,18))
    def diagnostics_tab(self):
        t=self.tab('Diagnostics')
        ttk.Label(t,text='A clear view of your setup.',style='Title.TLabel').pack(anchor='w')
        ttk.Label(t,text='No remote diagnostics or telemetry. This report is generated locally.',style='Muted.TLabel').pack(anchor='w',pady=(5,18))
        self.diagnostic_text=tk.Text(t,height=18,wrap='word',font=(CODE_FONT,11),relief='flat',padx=18,pady=18);self.diagnostic_text.pack(fill='both',expand=True)
        ttk.Button(t,text='Refresh diagnostics',command=self.update_diagnostics).pack(anchor='w',pady=12);self.update_diagnostics()
    def update_diagnostics(self):
        data=capabilities(self.store.folder);data['jobs']=sum(self.store.counts().values());data['saved_sources']=len(self.store.setting('boards',[]));data['email_configured']=bool(self.store.setting('mail',{}).get('address'))
        self.diagnostic_text.configure(state='normal');self.diagnostic_text.delete('1.0','end');self.diagnostic_text.insert('1.0',json.dumps(data,indent=2));self.diagnostic_text.configure(state='disabled')

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
