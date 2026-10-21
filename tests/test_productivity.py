import json
import zipfile
import pytest
from applypilot.core import Store,documents
from applypilot.productivity import resume_text,extract_profile,assess,plan_queue
from applypilot.system import browser_order

def test_bulk_insert_and_paginated_views(tmp_path):
    store=Store(tmp_path)
    rows=[dict(url=f'https://example.com/jobs/{i}',company='Acme',title=f'Engineer {i}',location='Remote',description='large '*100) for i in range(300)]
    assert store.add_many(rows)==300 and store.add_many(rows)==0
    first,count=store.page(limit=50);second,_=store.page(limit=50,offset=50)
    assert count==300 and len(first)==50 and not set(j['id'] for j in first)&set(j['id'] for j in second)
    assert 'description' not in first[0]
    assert store.page(search='Engineer 299')[1]==1
    assert store.page(search='%')[1]==0

def test_bulk_validation_atomic(tmp_path):
    store=Store(tmp_path)
    with pytest.raises(ValueError):store.add_many([dict(url='https://example.com/good',company='A',title='Role'),dict(url='javascript:bad',company='B',title='Role')])
    assert store.jobs()==[]

def test_queue_preferences_and_submission_protection(tmp_path):
    store=Store(tmp_path);ids=[]
    for i,title in enumerate(['Data Engineer','Senior Data Engineer','Data Engineer','Python Developer']):
        ids.append(store.add(dict(url=f'https://example.com/{i}',company='Acme',title=title,location='Remote',description='Python SQL AWS')))
    store.state(ids[2],'submitted')
    pref={'titles':'Data Engineer','min_skills':2,'queue_limit':10,'exclude_senior':True}
    assert plan_queue(store,{'skills':'Python, SQL'},pref)==[ids[0]]
    pref['locations']='Dallas';assert plan_queue(store,{'skills':'Python, SQL'},pref)==[]

def test_resume_headings_contact_and_no_fabrication(tmp_path):
    text='Alex Morgan\nalex@example.com\nhttps://linkedin.com/in/alex\nTECHNICAL SKILLS\nPython; SQL\nEXPERIENCE\nBuilt pipelines at Example.\nEDUCATION\nMS Data Engineering'
    path=tmp_path/'resume.txt';path.write_text(text)
    p=extract_profile(resume_text(path))
    assert p['name']=='Alex Morgan' and p['email']=='alex@example.com'
    assert 'Built pipelines' in p['experience'] and 'MS Data' in p['education']
    assert 'PhD' not in json.dumps(p) and 'Python' in p['skills']

def test_docx_import_and_scanned_text_rejection(tmp_path):
    path=tmp_path/'resume.docx'
    xml='<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Alex Morgan</w:t></w:r></w:p><w:p><w:r><w:t>alex@example.com, Data Engineer</w:t></w:r></w:p></w:body></w:document>'
    with zipfile.ZipFile(path,'w') as z:z.writestr('word/document.xml',xml)
    assert 'alex@example.com' in resume_text(path)
    empty=tmp_path/'empty.txt';empty.write_text('Hi')
    with pytest.raises(ValueError):resume_text(empty)

def test_document_cache_invalidates_profile_and_damage(tmp_path):
    store=Store(tmp_path);jid=store.add(dict(url='https://example.com/job',company='Acme',title='Engineer',description='SQL'))
    p={'name':'Alex Morgan','email':'alex@example.com','skills':'SQL'}
    dest=documents(store,p,store.job(jid));first=(dest/'manifest.json').read_bytes();documents(store,p,store.job(jid))
    assert (dest/'manifest.json').read_bytes()==first
    (dest/'resume.pdf').write_bytes(b'corrupt');documents(store,p,store.job(jid))
    assert (dest/'resume.pdf').read_bytes().startswith(b'%PDF')
    documents(store,dict(p,summary='Verified new summary'),store.job(jid))
    assert (dest/'manifest.json').read_bytes()!=first

def test_original_pdf_is_preserved(tmp_path):
    from reportlab.pdfgen.canvas import Canvas
    source=tmp_path/'original.pdf';c=Canvas(str(source));c.drawString(20,700,'My original resume');c.save()
    store=Store(tmp_path/'db');store.save_setting('resume_pdf',str(source));jid=store.add(dict(url='https://example.com/job',company='Acme',title='Engineer'))
    dest=documents(store,{'name':'Alex','email':'alex@example.com'},store.job(jid))
    assert (dest/'resume.pdf').read_bytes()==source.read_bytes()
    assert json.loads((dest/'manifest.json').read_text())['mode'].startswith('original PDF')

def test_browser_choice_rejects_arbitrary_channels():
    assert browser_order('chrome')==['chrome']
    with pytest.raises(ValueError):browser_order('shell-command')
