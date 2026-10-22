import json
import pytest
from applypilot.core import Store,documents
from applypilot.tailoring import (generate_draft,context_hash,save_draft,current_draft,approved_profile,suggest_answer,capture_questions,load_draft,changes,DraftConflict)
from applypilot.recovery import create_backup,restore_backup

@pytest.fixture
def sample(tmp_path):
    store=Store(tmp_path/'data')
    profile={'name':'Alex Morgan','email':'alex@example.com','skills':'Java, Python, SQL','summary':'Built reliable enterprise software.','experience':'Acme, Engineer, 2022–2024\nBuilt Java services and improved latency by 15%.','projects':'Dashboard: Built Java interfaces.\n\nPipelines: Used Python and SQL to process sales data.','education':'MS Data Engineering','answers':{}}
    store.save_setting('profile',profile)
    jid=store.add(dict(url='https://example.com/job',title='Data Engineer',company='Example',description='Python SQL pipelines. Spark experience is required.'))
    return store,profile,store.job(jid)


def test_grounded_resume_draft_preserves_facts_and_reports_gaps(sample):
    store,p,j=sample;draft=generate_draft(store,p,j)
    assert draft['resume']['skills']=='Python, SQL, Java'
    assert draft['resume']['experience']==p['experience']
    assert draft['resume']['education']==p['education']
    assert draft['resume']['projects'].startswith('Pipelines:')
    assert 'Spark' in draft['gaps'] and 'Spark' not in draft['resume']['skills']
    assert '15%' in draft['resume']['experience'] and 'PhD' not in json.dumps(draft)
    assert 'Example' in draft['cover_letter'] and not draft['approved_resume']
    assert 'Draft summary' in changes(p,draft)


def test_unapproved_edits_never_reach_documents_or_answers(sample):
    store,p,j=sample;draft=generate_draft(store,p,j)
    draft['resume']['summary']='UNAPPROVED EDIT';draft['questions']['Question']={'answer':'Proposal','evidence':[],'missing':[]}
    save_draft(store,j['id'],draft,context_hash(store,p,j))
    dest=documents(store,p,j)
    assert 'UNAPPROVED EDIT' not in (dest/'resume.txt').read_text()
    assert 'Question' not in approved_profile(store,p,j)['answers']


def test_reviewed_documents_override_original_only_when_selected(sample,tmp_path):
    store,p,j=sample;original=documents(store,p,j)/'resume.pdf'
    original_copy=tmp_path/'original.pdf';original_copy.write_bytes(original.read_bytes());store.save_setting('resume_pdf',str(original_copy))
    draft=generate_draft(store,p,j);draft['resume']['summary']='User reviewed summary';draft['approved_resume']=True
    save_draft(store,j['id'],draft,context_hash(store,p,j));dest=documents(store,p,j)
    assert (dest/'resume.pdf').read_bytes()==original_copy.read_bytes()
    draft['use_tailored']=True;save_draft(store,j['id'],draft,context_hash(store,p,j));documents(store,p,j)
    assert 'User reviewed summary' in (dest/'resume.txt').read_text()
    from pypdf import PdfReader
    assert 'User reviewed summary' in ''.join(page.extract_text() for page in PdfReader(dest/'resume.pdf').pages)
    assert (dest/'resume.pdf').read_bytes()!=original_copy.read_bytes()
    assert json.loads((dest/'manifest.json').read_text())['mode']=='reviewed job-specific draft'
    assert store.setting('profile')==p


@pytest.mark.parametrize('change',['profile','job','facts','original'])
def test_approval_invalidated_by_context_change(sample,change):
    store,p,j=sample;draft=generate_draft(store,p,j);draft['approved_resume']=True;draft['approved_answers']={'custom question':'Approved'}
    save_draft(store,j['id'],draft,context_hash(store,p,j))
    if change=='profile':p=dict(p,summary='New facts')
    if change=='job':
        with store.connect() as c:c.execute('UPDATE jobs SET description=? WHERE id=?',('New role requirements',j['id']))
        j=store.job(j['id'])
    if change=='original':store.save_setting('resume_pdf',str(store.folder/'new.pdf'))
    if change=='facts':store.save_setting('facts',{'salary':'100000 USD/year'})
    assert current_draft(store,p,j) is None
    assert 'custom question' not in approved_profile(store,p,j)['answers']
    with pytest.raises(ValueError,match='outdated'):documents(store,p,j)


def test_answer_drafts_require_explicit_sensitive_facts(sample):
    store,p,j=sample
    for q in ['Do you require sponsorship?','What is your salary expectation?','How many years of Python experience do you have?','What is your gender?','Why do you want to join our company?']:
        result=suggest_answer(q,p,j);assert not result['answer'] and result['missing']
    q='Will you now or in the future require sponsorship in the United States?'
    assert suggest_answer(q,p,j,{'us_sponsorship':'Yes'})['answer']=='Yes'
    assert not suggest_answer('Are you authorized to work in Canada?',p,j,{'us_work_authorization':'Yes'})['answer']
    assert not suggest_answer('Are you authorized to work for us?',p,j,{'us_work_authorization':'Yes'})['answer']
    assert not suggest_answer('How many years of professional experience in finance do you have?',p,j,{'years':'10'})['answer']


def test_evidence_answer_and_unknown_skill(sample):
    store,p,j=sample
    result=suggest_answer('Describe your experience with Python and SQL',p,j)
    assert 'Pipelines:' in result['answer'] and result['evidence']
    assert not suggest_answer('Describe your Spark experience',p,j)['answer']
    assert not suggest_answer('Describe your Python certifications',p,j)['answer']


def test_capture_and_per_job_exact_answer_scope(sample):
    store,p,j=sample;capture_questions(store,p,j,['Describe your SQL experience','Describe your SQL experience'])
    assert len(load_draft(store,j['id'])['payload']['questions'])==1
    draft=current_draft(store,p,j);draft['approved_answers']={'describe your sql experience':'Reviewed answer'}
    save_draft(store,j['id'],draft,context_hash(store,p,j))
    assert approved_profile(store,p,j)['answers']['describe your sql experience']=='Reviewed answer'
    other=store.add(dict(url='https://example.com/other',title='Engineer',company='Other'))
    assert not approved_profile(store,p,store.job(other))['answers']
    capture_questions(store,p,j,['Additional question'])
    assert current_draft(store,p,j)['approved_answers']['describe your sql experience']=='Reviewed answer'


def test_capture_questions_without_description(sample):
    store,p,j=sample
    with store.connect() as c:c.execute('UPDATE jobs SET description=? WHERE id=?',('',j['id']))
    j=store.job(j['id']);capture_questions(store,p,j,['What is your salary expectation?'])
    draft=current_draft(store,p,j)
    assert 'What is your salary expectation?' in draft['questions'] and not draft['approved_resume']


def test_optimistic_revision_prevents_lost_or_revoked_approval(sample):
    store,p,j=sample;draft=generate_draft(store,p,j);context=context_hash(store,p,j)
    first=save_draft(store,j['id'],draft,context,expected_updated=None)
    draft['approved_answers']={'test':'approved'};save_draft(store,j['id'],draft,context,expected_updated=first)
    with pytest.raises(DraftConflict):save_draft(store,j['id'],draft,context,expected_updated=first)
    assert current_draft(store,p,j)['approved_answers']=={'test':'approved'}


def test_backup_roundtrip_drafts_and_facts_with_approvals_disabled(sample,tmp_path):
    store,p,j=sample;store.save_setting('facts',{'salary':'100000 USD/year'});draft=generate_draft(store,p,j)
    draft['approved_resume']=True;draft['approved_answers']={'test':'approved'};save_draft(store,j['id'],draft,context_hash(store,p,j))
    path=create_backup(store,tmp_path/'backup.applypilot');target=Store(tmp_path/'target');restore_backup(target,path)
    restored=load_draft(target,j['id'])['payload']
    assert restored['resume']==draft['resume'] and not restored['approved_resume'] and restored['approved_answers']=={}
    assert target.setting('facts')=={'salary':'100000 USD/year'}


def test_legacy_backup_without_drafts_is_accepted(sample,tmp_path):
    import hashlib,zipfile
    store,p,j=sample;path=create_backup(store,tmp_path/'legacy.applypilot')
    with zipfile.ZipFile(path) as z:files={n:z.read(n) for n in z.namelist()}
    data=json.loads(files['data.json']);data.pop('drafts');files['data.json']=json.dumps(data).encode()
    manifest=json.loads(files['manifest.json']);manifest['files']['data.json']=hashlib.sha256(files['data.json']).hexdigest();files['manifest.json']=json.dumps(manifest).encode()
    with zipfile.ZipFile(path,'w') as z:
        for n,b in files.items():z.writestr(n,b)
    target=Store(tmp_path/'target');restore_backup(target,path)
    assert target.job(j['id'])['company']=='Example' and load_draft(target,j['id']) is None
