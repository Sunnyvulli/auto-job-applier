import copy
import pytest
from applypilot.core import Store
from applypilot.learning import (remember_corrections,matching_answers,confirm_learning,memories,update_memory,employer_scope,profile_hash,disable_used)
from applypilot.recovery import create_backup,restore_backup

@pytest.fixture
def sample(tmp_path):
    store=Store(tmp_path/'data');store.save_setting('profile',{'name':'Test User','email':'test@example.com'})
    def add(suffix,company='Acme',title='Engineer',location='Remote'):
        jid=store.add(dict(url='https://jobs.lever.co/'+company.lower()+'/'+suffix+'/apply',company=company,title=title,location=location));return store.job(jid)
    first=add('first');second=add('second')
    field={'question':'years of python experience','label':'Years of Python experience','kind':'number','choices':[],'answer':'','maxlength':None,'valid':False}
    before={field['question']:field};after=copy.deepcopy(before);after[field['question']].update(answer='3',valid=True)
    return store,first,second,before,after,add


def test_pending_then_confirmed_reuse_and_scope(sample):
    store,first,second,before,after,add=sample
    assert remember_corrections(store,first,first['url'],before,after)==1
    assert matching_answers(store,first,first['url'],before)[0]=={'years of python experience':'3'}
    assert not matching_answers(store,second,second['url'],before)[0]
    assert confirm_learning(store,first['id'])==1
    assert matching_answers(store,second,second['url'],before)[0]=={'years of python experience':'3'}
    for job in [add('other','Other'),add('senior',title='Senior Engineer'),add('dallas',location='Dallas')]:
        assert not matching_answers(store,job,job['url'],before)[0]
    assert not matching_answers(store,second,'https://other.example/job',before)[0]


def test_changed_profile_or_fact_disables_reuse(sample):
    store,first,second,before,after,add=sample
    remember_corrections(store,first,first['url'],before,after);confirm_learning(store,first['id'])
    store.save_setting('facts',{'salary':'100000 USD/year'})
    assert not matching_answers(store,second,second['url'],before)[0]
    ids=[row['id'] for row in memories(store)];update_memory(store,ids,'enable')
    assert matching_answers(store,second,second['url'],before)[0]
    store.save_setting('profile',{'name':'Other User','email':'other@example.com'})
    assert not matching_answers(store,second,second['url'],before)[0]


@pytest.mark.parametrize('question',['Password','Verification code','Social security number','Gender','I agree to terms','Email address','Code','OTP','Routing number'])
def test_forbidden_fields_are_not_remembered(sample,question):
    store,first,second,before,after,add=sample
    old={'kind':'text','choices':[],'answer':'','valid':False};new={**old,'answer':'sensitive','valid':True}
    assert not remember_corrections(store,first,first['url'],{question:old},{question:new})
    assert memories(store)==[]


def test_invalid_unchanged_and_changed_control_not_learned(sample):
    store,first,second,before,after,add=sample
    assert not remember_corrections(store,first,first['url'],before,before)
    invalid=copy.deepcopy(after);invalid['years of python experience']['valid']=False
    assert not remember_corrections(store,first,first['url'],before,invalid)
    changed=copy.deepcopy(after);changed['years of python experience']['kind']='select'
    assert not remember_corrections(store,first,first['url'],before,changed)


def test_choice_changes_length_and_explicit_approval_exclusion(sample):
    store,first,second,before,after,add=sample
    for data in (before,after):data['years of python experience']['kind']='select';data['years of python experience']['choices']=['Choose','3','4']
    remember_corrections(store,first,first['url'],before,after);confirm_learning(store,first['id'])
    assert matching_answers(store,second,second['url'],before)[0]
    assert not matching_answers(store,second,second['url'],before,exclude={'years of python experience'})[0]
    before['years of python experience']['choices']=['Choose','4']
    assert not matching_answers(store,second,second['url'],before)[0]


def test_expiry_disable_and_forget(sample):
    store,first,second,before,after,add=sample
    remember_corrections(store,first,first['url'],before,after);confirm_learning(store,first['id'])
    ids=[row['id'] for row in memories(store)]
    with store.connect() as c:c.execute("UPDATE answer_memory SET updated='2000-01-01T00:00:00+00:00'")
    assert not matching_answers(store,second,second['url'],before)[0]
    update_memory(store,ids,'enable');assert matching_answers(store,second,second['url'],before)[0]
    disable_used(store,ids);assert not matching_answers(store,second,second['url'],before)[0]
    update_memory(store,ids,'delete');assert not memories(store)


def test_learning_off_and_backups_disable_restored_memory(sample,tmp_path):
    store,first,second,before,after,add=sample
    store.save_setting('learn_answers',False)
    assert not remember_corrections(store,first,first['url'],before,after)
    store.save_setting('learn_answers',True);remember_corrections(store,first,first['url'],before,after);confirm_learning(store,first['id'])
    backup=create_backup(store,tmp_path/'backup.applypilot');target=Store(tmp_path/'target');restore_backup(target,backup)
    assert memories(target)[0]['status']=='disabled' and target.setting('learn_answers') is False
    assert not matching_answers(target,second,second['url'],before)[0]


def test_new_correction_retires_old_answer(sample):
    store,first,second,before,after,add=sample
    remember_corrections(store,first,first['url'],before,after);confirm_learning(store,first['id'])
    new=copy.deepcopy(after);new['years of python experience']['answer']='4'
    remember_corrections(store,second,second['url'],after,new)
    assert all(row['status']!='active' for row in memories(store))
    confirm_learning(store,second['id'])
    third=add('third');assert matching_answers(store,third,third['url'],before)[0]['years of python experience']=='4'
