import os
import sys
import pytest
pytestmark=pytest.mark.skipif(not os.getenv('DISPLAY') and sys.platform!='win32',reason='Desktop display required')

def test_dashboard_preferences_answers_and_pagination(tmp_path):
    import tkinter as tk
    from applypilot.desktop import App
    root=tk.Tk();app=App(root,tmp_path)
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
    finally:root.destroy()
