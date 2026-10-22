"""Capture the actual draft editor with synthetic data for visual review."""
import sys
import tempfile
import tkinter as tk
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PIL import ImageGrab
from applypilot.desktop import App

with tempfile.TemporaryDirectory() as folder:
    root=tk.Tk();app=App(root,folder)
    values={'name':'Alex Morgan','email':'alex@example.com','skills':'Java, Python, SQL, AWS','summary':'Data engineer building reliable cloud pipelines.','experience':'Example Labs | Data Engineer | 2022–2025\nBuilt Python and SQL pipelines for operational reporting.','projects':'Java dashboard: Built an internal reporting interface.\n\nAnalytics pipeline: Used Python, SQL and AWS for daily reporting.','education':'MS Data Engineering'}
    for k,v in values.items():app.fields[k].insert('1.0',v)
    app.save_profile()
    jid=app.store.add(dict(url='https://example.com/job',title='Data Engineer',company='Example Analytics',description='Build reliable pipelines using Python, SQL and AWS. Spark experience is preferred.'))
    root.update()
    studio=app.tailor(jid);root.withdraw();studio.window.deiconify();studio.window.lift();root.update()
    assert studio.window.winfo_viewable(), 'Draft window did not become visible'
    output=Path('screenshots');output.mkdir(exist_ok=True)
    for name,page in [('resume',studio.resume_page),('changes',studio.diff_page),('questions',studio.qa_page)]:
        studio.tabs.select(page)
        if name=='questions':studio.question.set('Describe your Python experience');studio.draft_answer()
        root.update();w=studio.window
        ImageGrab.grab(bbox=(w.winfo_rootx(),w.winfo_rooty(),w.winfo_rootx()+w.winfo_width(),w.winfo_rooty()+w.winfo_height())).save(output/(name+'.png'))
    from applypilot.learning import remember_corrections,confirm_learning
    job=app.store.job(jid)
    before={'years of python experience':dict(kind='number',choices=[],answer='',valid=False)}
    after={'years of python experience':dict(kind='number',choices=[],answer='3',valid=True)}
    remember_corrections(app.store,job,job['url'],before,after);confirm_learning(app.store,jid)
    studio.window.withdraw();memory=app.learned_answers();root.update();memory.window.lift();root.update()
    memory.tree.selection_set(memory.tree.get_children()[0]);memory.details();root.update();w=memory.window
    ImageGrab.grab(bbox=(w.winfo_rootx(),w.winfo_rooty(),w.winfo_rootx()+w.winfo_width(),w.winfo_rooty()+w.winfo_height())).save(output/'learning.png')
    memory.window.destroy()
    app.store.save_setting('preferences',dict(titles='Data Engineer, Machine Learning Engineer',countries='United States, India',cities=''))
    app.store.save_setting('discovery_report',dict(finished='Synthetic UI preview',roles='Data Engineer, Machine Learning Engineer',countries='United States, India',cities='',scanned=1200,matched=18,added=12,invalid=0,coverage='Example report — built-in employer catalog plus saved sources',sources=[dict(provider='Lever',company='example',found=240,matched=8,added=5,error='')]))
    app.show_discovery_report();root.deiconify();root.geometry('1024x700');app.show_page('Discover jobs');root.lift();root.update();w=root
    ImageGrab.grab(bbox=(w.winfo_rootx(),w.winfo_rooty(),w.winfo_rootx()+w.winfo_width(),w.winfo_rooty()+w.winfo_height())).save(output/'discovery.png')

    for callback in root.tk.call('after','info'):root.after_cancel(callback)
    studio.window.destroy();root.destroy()
