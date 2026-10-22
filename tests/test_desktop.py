import os
import sys
import pytest
pytestmark=pytest.mark.skipif(not os.getenv('DISPLAY') and sys.platform!='win32',reason='Desktop display required')

@pytest.fixture(scope='module')
def desktop_root():
    # Share the interpreter to match the single-instance app lifecycle.
    import tkinter as tk
    root=tk.Tk();root.withdraw()
    yield root
    root.destroy()

def close_window(root):
    for callback in root.tk.call('after','info'):root.after_cancel(callback)
    root.destroy()

def test_dashboard_preferences_answers_and_pagination(tmp_path,desktop_root):
    import tkinter as tk
    from applypilot.desktop import App
    root=tk.Toplevel(desktop_root);app=App(root,tmp_path)
    try:
        for k,v in [('name','Test User'),('email','test@example.com'),('skills','Python, SQL')]:app.fields[k].insert('1.0',v)
        app.qa_question.set('Do you need sponsorship?');app.qa_answer.set('Yes');app.add_answer();app.save_profile()
        assert app.store.setting('profile')['answers']=={'Do you need sponsorship?':'Yes'}
        app.pref_fields['titles'].set('Data Engineer');app.pref_fields['min_skills'].set('1');app.pref_fields['queue_limit'].set('5');app.save_preferences()
        app.store.add_many([dict(url=f'https://example.com/{i}',company='Acme',title='Data Engineer',description='Python SQL') for i in range(220)])
        app.refresh();assert len(app.tree.get_children())==100
        app.page_move(1);assert app.offset==100 and len(app.tree.get_children())==100
        app.low_resource.set(True);app.save_preferences();app.offset=0;app.refresh();assert len(app.tree.get_children())==50
        app.starter_sources();assert len(app.store.setting('boards'))==4
        app.source_provider.set('Greenhouse');app.source_company.set('databricks');app.save_sources();assert len(app.store.setting('boards'))==4
        app.source_tree.selection_set('0');app.remove_source();assert len(app.store.setting('boards'))==3
        for size in ['1240x820','1024x700','960x640']:
            root.geometry(size)
            for page in app.pages:app.show_page(page);root.update()
        app.toggle_theme();root.update();assert app.store.setting('theme')=='dark'
    finally:close_window(root)


def test_queue_controls_recheck_and_remove(tmp_path,monkeypatch,desktop_root):
    import tkinter as tk
    from applypilot.desktop import App
    root=tk.Toplevel(desktop_root);app=App(root,tmp_path)
    try:
        app.store.save_setting('profile',{'name':'Test User','email':'test@example.com'})
        app.store.save_setting('preferences',{'titles':'Data Engineer','min_skills':0})
        keep=app.store.add(dict(url='https://example.com/keep',company='Acme',title='Data Engineer'))
        exclude=app.store.add(dict(url='https://example.com/exclude',company='Acme',title='Developer'))
        app.queued_ids=[keep,exclude];started=[]
        monkeypatch.setattr(app.worker,'start',lambda ids,auto:started.extend(ids))
        app.start_reviewed_queue();assert started==[keep] and app.queued_ids==[keep]
        app.queue_tree.selection_set(keep);app.remove_from_queue()
        assert app.queued_ids==[] and app.store.setting('planned_queue')==[]
        app.busy_count=1
        with pytest.raises(ValueError,match='background tasks'):app.restore_data()
    finally:close_window(root)


def test_draft_studio_fact_bank_review_and_invalidation(tmp_path,desktop_root):
    import tkinter as tk
    from applypilot.desktop import App
    from applypilot.tailoring import current_draft
    from applypilot.core import documents
    root=tk.Toplevel(desktop_root);app=App(root,tmp_path)
    try:
        for k,v in [('name','Test User'),('email','test@example.com'),('skills','Python, SQL'),('summary','Built data pipelines.'),('projects','Used Python and SQL for analytics.')]:app.fields[k].insert('1.0',v)
        app.save_profile();app.fact_category.set('Salary expectation (include currency/period)');app.fact_value.set('100000 USD/year');app.save_fact()
        jid=app.store.add(dict(url='https://example.com/job',title='Data Engineer',company='Acme',description='Python SQL pipelines'))
        studio=app.tailor(jid);root.update();assert studio.payload and not studio.payload['approved_resume']
        studio.editors['summary'].delete('1.0','end');studio.editors['summary'].insert('1.0','My reviewed summary.');studio.use_tailored.set(True);studio.approve_resume()
        job=app.store.job(jid);p=app.store.setting('profile');dest=documents(app.store,p,job)
        assert 'My reviewed summary.' in (dest/'resume.txt').read_text()
        studio.question.set('What is your salary expectation?');studio.draft_answer();assert '100000' in studio.answer.get('1.0','end')
        studio.approve_answer();assert current_draft(app.store,p,job)['approved_answers']['what is your salary expectation?']=='100000 USD/year'
        studio.revoke_answer();assert current_draft(app.store,p,job)['approved_answers']=={}
        studio.editors['summary'].insert('end',' Unsaved edit.');studio.show_changes();assert not studio.payload['approved_resume']
        app.store.save_setting('facts',{'salary':'110000 USD/year'})
        with pytest.raises(ValueError,match='changed'):studio.approve_resume()
        studio.window.destroy()
    finally:close_window(root)


def test_learning_memory_review_and_global_promotion(tmp_path,desktop_root):
    import tkinter as tk
    from applypilot.desktop import App
    from applypilot.learning import remember_corrections,confirm_learning,memories
    root=tk.Toplevel(desktop_root);app=App(root,tmp_path)
    try:
        for k,v in [('name','Test User'),('email','test@example.com')]:app.fields[k].insert('1.0',v)
        app.save_profile();jid=app.store.add(dict(url='https://jobs.lever.co/acme/test/apply',company='Acme',title='Engineer'))
        before={'custom question':dict(kind='text',choices=[],answer='',valid=False)};after={'custom question':dict(kind='text',choices=[],answer='Verified answer',valid=True)}
        job=app.store.job(jid);remember_corrections(app.store,job,job['url'],before,after);confirm_learning(app.store,jid)
        window=app.learned_answers();root.update();identity=window.tree.get_children()[0]
        window.tree.selection_set(identity);window.details();assert 'Verified answer' in window.detail.get('1.0','end')
        window.change('disable');assert memories(app.store)[0]['status']=='disabled'
        window.tree.selection_set(identity);window.change('enable');assert memories(app.store)[0]['status']=='active'
        window.tree.selection_set(identity);window.promote();assert app.store.setting('profile')['answers']['custom question']=='Verified answer'
        window.tree.selection_set(identity);window.change('delete');assert not memories(app.store)
        window.window.destroy()
    finally:close_window(root)


def test_discover_jobs_import_and_start_current_results(tmp_path,monkeypatch,desktop_root):
    import tkinter as tk
    from applypilot.desktop import App
    from applypilot import discovery
    root=tk.Toplevel(desktop_root);app=App(root,tmp_path)
    try:
        app.store.save_setting('profile',{'name':'Alex','email':'alex@example.com','skills':'SQL'})
        app.pref_fields['titles'].set('Data Engineer');app.pref_fields['countries'].set('India')
        app.pref_fields['cities'].set('');app.pref_fields['min_skills'].set('0');app.save_preferences()
        monkeypatch.setattr(discovery,'CATALOG',{'Lever':('acme',)})
        monkeypatch.setattr(discovery,'import_board',lambda *a:[dict(url='https://jobs.lever.co/acme/1',company='Acme',title='Data Engineer',location='Hyderabad | India',description='SQL')])
        old=app.store.add(dict(url='https://example.com/old',company='Other',title='Data Engineer',location='India',description='SQL'))
        app.queued_ids=[old]
        # Deterministic task execution, while exercising the normal event pump.
        monkeypatch.setattr(app,'background',lambda fn:app.queue.put(fn()))
        started=[];monkeypatch.setattr(app.worker,'start',lambda ids,auto:started.append((ids,auto)))
        app.find_jobs(True);app.pump()
        assert len(started)==1 and old not in started[0][0] and not started[0][1]
        assert app.store.setting('discovery_report')['added']==1
        assert '1 matching' in app.discovery_log.get('1.0','end')
        assert not app.import_lock.locked()
        started.clear()
        monkeypatch.setattr(discovery,'import_board',lambda *a:[])
        app.find_jobs(True);app.pump();assert started==[]
        def failed(*a):raise ValueError('Offline')
        monkeypatch.setattr(discovery,'import_board',failed)
        app.find_jobs(True);app.pump();assert started==[]
        assert 'FAILED: Offline' in app.discovery_log.get('1.0','end')
    finally:close_window(root)
