"""Review and approve a job-specific draft before it reaches application forms."""
import copy
import tkinter as tk
from tkinter import ttk
from .tailoring import (RESUME_FIELDS,generate_draft,context_hash,current_draft,save_draft,clear_draft,changes,suggest_answer,normalized,load_draft)
from .theme import UI_FONT

class DraftStudio:
    def __init__(self,app,jid):
        self.app=app;self.store=app.store;self.jid=jid;self.profile=self.store.setting('profile',{});self.job=self.store.job(jid)
        if not self.profile.get('name') or '@' not in self.profile.get('email',''):raise ValueError('Save your profile name and email before tailoring.')
        self.baseline=context_hash(self.store,self.profile,self.job);self.payload=current_draft(self.store,self.profile,self.job)
        record=load_draft(self.store,jid);self.revision=record['updated'] if record else None
        stale=bool(record and not self.payload)
        if stale:
            self.payload=copy.deepcopy(record['payload']);self.payload['approved_resume']=False;self.payload['approved_answers']={}
            self.payload['questions']={q:suggest_answer(q,self.profile,self.job,self.store.setting('facts',{})) for q in self.payload.get('questions',{})}
        self.window=tk.Toplevel(app.root);self.window.title('Tailor application — '+self.job['company']);self.window.geometry(f'{min(940,app.root.winfo_screenwidth()-80)}x{min(800,app.root.winfo_screenheight()-100)}')
        self.window.minsize(min(700,app.root.winfo_screenwidth()-60),min(560,app.root.winfo_screenheight()-80))
        outer=ttk.Frame(self.window,padding=18);outer.pack(fill='both',expand=True)
        ttk.Label(outer,text=self.job['title'],style='Section.TLabel',wraplength=800).pack(anchor='w')
        ttk.Label(outer,text='Local drafts use saved facts. Review every edit and answer before approval.',wraplength=800).pack(anchor='w',pady=(6,12))
        self.state=tk.StringVar(value='Add a job description, then generate a draft.');ttk.Label(outer,textvariable=self.state,wraplength=800,style='Muted.TLabel').pack(anchor='w',pady=(0,10))
        self.tabs=ttk.Notebook(outer);self.tabs.pack(fill='both',expand=True)
        self.jd_page=ttk.Frame(self.tabs,padding=12);self.resume_page=ttk.Frame(self.tabs,padding=12);self.qa_page=ttk.Frame(self.tabs,padding=12);self.diff_page=ttk.Frame(self.tabs,padding=12)
        for page,label in [(self.jd_page,'Job description'),(self.resume_page,'Resume & letter'),(self.qa_page,'Questions'),(self.diff_page,'Changes & evidence')]:self.tabs.add(page,text=label)
        self.description=self.text(self.jd_page,self.job.get('description',''),12)
        ttk.Button(self.jd_page,text='Save description + generate draft',style='Accent.TButton',command=lambda:app.guard(self.generate)).pack(anchor='w',pady=10)
        ttk.Label(self.resume_page,text='Edit the proposal here. Your saved Profile remains unchanged.',wraplength=760).pack(anchor='w',pady=(0,8))
        holder=ttk.Frame(self.resume_page);holder.pack(fill='both',expand=True)
        canvas=tk.Canvas(holder,highlightthickness=0);canvas.pack(side='left',fill='both',expand=True)
        scroll=ttk.Scrollbar(holder,orient='vertical',command=canvas.yview);scroll.pack(side='right',fill='y');canvas.configure(yscrollcommand=scroll.set)
        inner=ttk.Frame(canvas);win=canvas.create_window((0,0),window=inner,anchor='nw');canvas.bind('<Configure>',lambda e:canvas.itemconfigure(win,width=e.width));inner.bind('<Configure>',lambda e:canvas.configure(scrollregion=canvas.bbox('all')))
        self.editors={}
        for field in (*RESUME_FIELDS,'cover_letter'):
            ttk.Label(inner,text=field.replace('_',' ').title()).pack(anchor='w',pady=(10,4));self.editors[field]=self.text(inner,'',4 if field!='skills' else 2)
        self.use_tailored=tk.BooleanVar(value=False)
        ttk.Checkbutton(self.resume_page,text='Use this generated resume PDF for this job (replaces original-PDF upload for this job only)',variable=self.use_tailored).pack(anchor='w',pady=8)
        ttk.Button(self.resume_page,text='Approve resume & letter',style='Accent.TButton',command=lambda:app.guard(self.approve_resume)).pack(anchor='w')
        ttk.Label(self.qa_page,text='Choose a detected question or paste one. Each answer requires its own approval.',wraplength=760).pack(anchor='w')
        self.question=tk.StringVar();self.question_picker=ttk.Combobox(self.qa_page,textvariable=self.question);self.question_picker.pack(fill='x',pady=8);self.question_picker.bind('<<ComboboxSelected>>',lambda e:self.show_answer())
        ttk.Button(self.qa_page,text='Draft answer',command=lambda:app.guard(self.draft_answer)).pack(anchor='w')
        self.answer=self.text(self.qa_page,'',6);self.answer_note=tk.StringVar();self.answer_evidence=self.text(self.qa_page,'',4);self.answer_evidence.configure(state='disabled')
        ttk.Button(self.qa_page,text='Approve this answer for this job',style='Accent.TButton',command=lambda:app.guard(self.approve_answer)).pack(anchor='w')
        ttk.Button(self.qa_page,text='Revoke this answer',command=lambda:app.guard(self.revoke_answer)).pack(anchor='w',pady=8)
        self.diff=self.text(self.diff_page,'',15);self.diff.configure(state='disabled')
        ttk.Button(self.diff_page,text='Refresh changes from editor',command=lambda:app.guard(self.show_changes)).pack(anchor='w',pady=8)
        bottom=ttk.Frame(outer);bottom.pack(fill='x',pady=(12,0))
        ttk.Button(bottom,text='Save draft without approval',command=lambda:app.guard(self.save_unapproved)).pack(side='left')
        ttk.Button(bottom,text='Clear job draft',command=lambda:app.guard(self.clear)).pack(side='left',padx=8)
        ttk.Button(bottom,text='Close',command=self.window.destroy).pack(side='right')
        if self.payload:
            self.render()
            if stale:self.state.set('Previous draft loaded for review. Old approvals are cleared in this editor. Regenerate or review it against your current facts.')
        elif self.job.get('description','').strip():self.generate()
    def text(self,parent,value,height):
        box=tk.Text(parent,height=height,wrap='word',font=(UI_FONT,10),padx=8,pady=8);box.insert('1.0',value);box.pack(fill='both',expand=True,pady=4);return box
    def fresh(self):
        if context_hash(self.store,self.store.setting('profile',{}),self.store.job(self.jid))!=self.baseline:raise ValueError('Profile, facts, original resume or job changed. Close and reopen Tailor application before approving.')
    def required(self):
        if not self.payload:raise ValueError('Generate a draft first.')
        self.fresh()
    def generate(self):
        self.fresh();description=self.description.get('1.0','end').strip()
        if not description:raise ValueError('Paste the real job description first.')
        if len(description)>100000:raise ValueError('Use a job description under 100,000 characters.')
        with self.store.connect() as c:c.execute('UPDATE jobs SET description=? WHERE id=?',(description,self.jid))
        self.job=self.store.job(self.jid);self.baseline=context_hash(self.store,self.profile,self.job)
        labels=list(self.payload.get('questions',{})) if self.payload else []
        self.payload=generate_draft(self.store,self.profile,self.job,labels);self.persist();self.render();self.tabs.select(self.resume_page)
    def read_editors(self):
        self.required()
        if self.description.get('1.0','end').strip()!=self.job.get('description','').strip():raise ValueError('Save the changed job description and generate a fresh draft before approving or saving edits.')
        resume={k:self.editors[k].get('1.0','end').strip() for k in RESUME_FIELDS};cover=self.editors['cover_letter'].get('1.0','end').strip();use=self.use_tailored.get()
        if resume!=self.payload['resume'] or cover!=self.payload['cover_letter'] or use!=self.payload['use_tailored']:self.payload['approved_resume']=False
        self.payload.update(resume=resume,cover_letter=cover,use_tailored=use)
    def persist(self):self.revision=save_draft(self.store,self.jid,self.payload,self.baseline,expected_updated=self.revision)
    def render(self):
        for field,box in self.editors.items():
            value=self.payload['cover_letter'] if field=='cover_letter' else self.payload['resume'][field]
            box.delete('1.0','end');box.insert('1.0',value)
        self.use_tailored.set(self.payload.get('use_tailored',False));self.question_picker.configure(values=list(self.payload['questions']))
        self.state.set('Resume/letter approved.' if self.payload.get('approved_resume') else 'Draft only — not used until you approve it.')
        self.show_changes()
    def approve_resume(self):
        self.read_editors()
        if not self.job.get('description','').strip() or not self.payload['cover_letter'].strip():raise ValueError('Save a job description and generate a complete draft before approving documents.')
        self.payload['approved_resume']=True;self.persist();self.state.set('Approved for this job. Prepare PDFs or Resume browser to use the reviewed version.');self.show_changes()
    def save_unapproved(self):
        self.read_editors();self.payload['approved_resume']=False;self.persist();self.state.set('Draft saved. Resume edits are not approved for use.')
    def draft_answer(self):
        self.required();q=self.question.get().strip()
        if not q:raise ValueError('Enter the question exactly as shown on the form.')
        if len(q)>2000:raise ValueError('Use a question under 2,000 characters.')
        self.payload['questions'][q]=suggest_answer(q,self.profile,self.job,self.store.setting('facts',{}));self.persist();self.question_picker.configure(values=list(self.payload['questions']));self.show_answer()
    def show_answer(self):
        if not self.payload:return
        q=self.question.get();proposal=self.payload['questions'].get(q,{})
        approved=self.payload.get('approved_answers',{}).get(normalized(q))
        self.answer.delete('1.0','end');self.answer.insert('1.0',approved if approved is not None else proposal.get('answer',''))
        self.answer_note.set(('Approved for this job. ' if approved is not None else 'Proposal only. ')+ '\n'.join(proposal.get('evidence',[])+proposal.get('missing',[])))
        self.answer_evidence.configure(state='normal');self.answer_evidence.delete('1.0','end');self.answer_evidence.insert('1.0',self.answer_note.get());self.answer_evidence.configure(state='disabled')
    def approve_answer(self):
        self.required();q=self.question.get().strip();value=self.answer.get('1.0','end').strip()
        if not q or not value:raise ValueError('Enter the exact question and a verified answer before approving.')
        if len(q)>2000 or len(value)>20000:raise ValueError('Question or answer is too long.')
        self.payload['questions'].setdefault(q,{'answer':value,'evidence':['User-entered answer'],'missing':[]})
        self.payload['approved_answers'][normalized(q)]=value;self.persist();self.show_answer();self.state.set('Answer approved only for this job and exact question label.')
    def revoke_answer(self):
        self.required();self.payload['approved_answers'].pop(normalized(self.question.get()),None);self.persist();self.show_answer()
    def show_changes(self):
        self.read_editors()
        text=changes(self.profile,self.payload)+'\n\nEVIDENCE\n'+'\n'.join(k.title()+': '+(', '.join(v) if isinstance(v,list) else str(v)) for k,v in self.payload['evidence'].items())+'\n\nPOSSIBLE GAPS (fixed vocabulary; not a complete eligibility assessment)\n'+', '.join(self.payload['gaps'])+'\n\nOriginal-PDF mode: '+('Tailored PDF selected for this job' if self.use_tailored.get() else 'Keep original PDF if configured; otherwise use base resume')
        self.diff.configure(state='normal');self.diff.delete('1.0','end');self.diff.insert('1.0',text);self.diff.configure(state='disabled')
    def clear(self):
        clear_draft(self.store,self.jid);self.state.set('Job-specific approvals cleared. Base profile and original-PDF preference remain.');self.window.destroy()
