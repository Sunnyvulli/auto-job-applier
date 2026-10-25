"""Regressions from shared startup recruiting forms; synthetic values only."""
import pytest
from applypilot.core import Store
from applypilot.learning import employer_scope, remember_corrections, matching_answers


def test_shared_yc_host_uses_observed_employer():
    job={'company':'Incorrect caller label'}
    a=employer_scope('https://www.ycombinator.com/companies/acme/jobs/one',job)
    b=employer_scope('https://www.ycombinator.com/companies/beta/jobs/two',job)
    assert a!=b
    assert a.endswith(' | acme')
    assert employer_scope('https://www.workatastartup.com/application?signup_job_id=1',job) is None
    assert employer_scope('https://www.ycombinator.com/jobs',job) is None


@pytest.mark.parametrize('question',[
    'Do you or will you require sponsorship for a US employment visa?',
    'Are you legally authorized to work in the United States?',
    'Work authorization', 'CPT eligibility', 'OPT expiration',
])
def test_work_eligibility_never_learned_or_reused(tmp_path,question):
    store=Store(tmp_path)
    jid=store.add({'url':'https://www.ycombinator.com/companies/acme/jobs/one',
                   'company':'Acme','title':'Engineer'})
    job=store.job(jid)
    field={'kind':'radio','choices':['Yes','No'],'answer':'','valid':True}
    corrected={**field,'answer':'No'}
    assert remember_corrections(store,job,job['url'],{question:field},{question:corrected})==0
    assert matching_answers(store,job,job['url'],{question:field})==({},[])
