"""Inspect and control the local answer memory."""
import tkinter as tk
from tkinter import ttk
from .learning import memories,profile_hash,update_memory
from .theme import UI_FONT

class MemoryWindow:
    def __init__(self,app):
        self.app=app;self.store=app.store;self.window=tk.Toplevel(app.root);self.window.title('Learned answers');self.window.geometry(f'{min(1000,app.root.winfo_screenwidth()-80)}x{min(700,app.root.winfo_screenheight()-100)}')
        panel=ttk.Frame(self.window,padding=18);panel.pack(fill='both',expand=True)
        ttk.Label(panel,text='Teach once. Reuse where it matches.',style='Section.TLabel').pack(anchor='w')
        ttk.Label(panel,text='Fill a paused form, then click Resume before Next/Submit. Confirmation activates the changed answers. Profile/fact changes and 90 days without review stop automatic reuse.',wraplength=860).pack(anchor='w',pady=8)
        ttk.Checkbutton(panel,text='Learn manual corrections and reuse matching answers',variable=app.learn_answers,command=lambda:self.store.save_setting('learn_answers',app.learn_answers.get())).pack(anchor='w',pady=8)
        table=ttk.Frame(panel);table.pack(fill='both',expand=True);table.grid_columnconfigure(0,weight=1);table.grid_rowconfigure(0,weight=1)
        self.tree=ttk.Treeview(table,columns=('question','answer','scope','role','status','uses'),show='headings',height=6)
        for key,width in [('question',240),('answer',160),('scope',220),('role',160),('status',100),('uses',60)]:self.tree.heading(key,text=key.title());self.tree.column(key,width=width,minwidth=60)
        self.tree.grid(row=0,column=0,sticky='nsew');self.tree.bind('<<TreeviewSelect>>',lambda e:self.details())
        vertical=ttk.Scrollbar(table,orient='vertical',command=self.tree.yview);vertical.grid(row=0,column=1,sticky='ns');self.tree.configure(yscrollcommand=vertical.set)
        horizontal=ttk.Scrollbar(table,orient='horizontal',command=self.tree.xview);horizontal.grid(row=1,column=0,sticky='ew');self.tree.configure(xscrollcommand=horizontal.set)
        self.detail=tk.Text(panel,height=5,wrap='word',font=(UI_FONT,10),state='disabled');self.detail.pack(fill='x',pady=10)
        bar=ttk.Frame(panel);bar.pack(fill='x')
        for label,action in [('Enable reviewed','enable'),('Disable','disable'),('Forget','delete')]:ttk.Button(bar,text=label,command=lambda a=action:app.guard(lambda:self.change(a))).pack(side='left',padx=(0,6))
        ttk.Button(bar,text='Refresh',command=self.refresh).pack(side='right')
        ttk.Button(panel,text='Copy selected to Profile answers — reuse across employers',command=lambda:app.guard(self.promote)).pack(anchor='w',pady=10)
        ttk.Label(panel,text='Global Profile answers lose employer/role/location restrictions. Copy only answers that are valid across those contexts. Consent, credentials and verification are never learned.',wraplength=860,style='Muted.TLabel').pack(anchor='w')
        self.refresh()
    def refresh(self):
        self.rows={row['id']:row for row in memories(self.store)};self.tree.delete(*self.tree.get_children());current=profile_hash(self.store)
        for row in self.rows.values():
            status='needs review' if row['profile_hash']!=current else row['status']
            self.tree.insert('','end',iid=row['id'],values=(row['question'],row['answer'][:100],row['scope'],row['role'],status,row['uses']))
    def details(self):
        selected=self.tree.selection()
        if not selected:return
        row=self.rows[selected[0]];text='Question: '+row['question']+'\nAnswer: '+row['answer']+'\nEmployer: '+row['scope']+'\nRole: '+row['role']+' | Location: '+row['location']+'\nStatus: '+row['status']+' | Last reviewed: '+row['updated']
        self.detail.configure(state='normal');self.detail.delete('1.0','end');self.detail.insert('1.0',text);self.detail.configure(state='disabled')
    def change(self,action):
        ids=self.tree.selection()
        if not ids:raise ValueError('Select at least one learned answer.')
        update_memory(self.store,ids,action);self.refresh();self.app.status.set('Learned answers updated.')
    def promote(self):
        ids=self.tree.selection()
        if not ids:raise ValueError('Select answers that are valid across employers first.')
        import json
        profile=self.store.setting('profile',{});answers=profile.setdefault('answers',{})
        for identity in ids:
            row=self.rows[identity];answers[row['question']]=row['answer']
        self.store.save_setting('profile',profile)
        self.app.answers.delete('1.0','end');self.app.answers.insert('1.0',json.dumps(answers));self.app.render_answers()
        self.refresh();self.app.status.set('Answers copied to Profile for global reuse. Existing job drafts and scoped memory need review after this profile change.')
