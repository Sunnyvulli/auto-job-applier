import pytest
from applypilot.core import Store
from applypilot.discovery import discover, discovery_matches, geography_matches, validate_search, report_text
from applypilot.productivity import plan_queue, queue_preflight

PREF={'titles':'Data Engineer, Machine Learning Engineer','countries':'US, India','cities':'','min_skills':0}
def job(url='https://example.com/jobs/1',**kw):
    return dict(url=url,company='Acme',title='Data Engineer',location='Bengaluru | India',description='SQL',**kw)

@pytest.mark.parametrize('location,country,expected',[
    ('Austin | United States','US',True),('Bengaluru | India','IN',True),
    ('San Jose, CA','Canada',False),('Austin, TX','United States',False),
    ('Australia','US',False),('Remote','US',False),('Worldwide','India',False),
    ('London, United Kingdom','UK',True),('London, Ontario | Canada','CA',True),
    ('Remote - USA','US',True),('London | GB','UK',True)])
def test_country_evidence(location,country,expected):
    assert geography_matches({'location':location},{'countries':country})==expected


def test_role_boundaries_and_optional_city():
    j=job();assert discovery_matches(j,PREF)
    assert not discovery_matches(dict(j,title='Metadata Engineer'),PREF)
    assert discovery_matches(dict(j,title='Senior Data-Engineer'),PREF)
    assert not discovery_matches(dict(j,title='Senior Data Engineer'),dict(PREF,exclude_senior=True))
    assert not discovery_matches(j,dict(PREF,cities='Dallas'))
    mixed=dict(j,location='New York | United States; London | United Kingdom')
    assert not geography_matches(mixed,dict(countries='US',cities='London'))
    assert geography_matches(mixed,dict(countries='UK',cities='London'))


def test_discovery_partial_failure_dedup_and_queue(tmp_path,monkeypatch):
    from applypilot import discovery
    store=Store(tmp_path);store.save_setting('boards',[dict(provider='Lever',company='acme',region='global')])
    monkeypatch.setattr(discovery,'CATALOG',{'Lever':('acme','failed')})
    calls=[]
    def feed(p,c,r):
        calls.append(c)
        if c=='failed':raise ValueError('Feed unavailable')
        return [job(),dict(job(),url='https://example.com/jobs/2',location='Remote'),
                dict(job(),url='https://example.com/jobs/3',title='Sales'),
                dict(job(),url='javascript:bad')]
    monkeypatch.setattr(discovery,'import_board',feed)
    report=discover(store,PREF)
    assert sorted(calls)==['acme','failed']
    assert report['scanned']==4 and report['matched']==1 and report['added']==1 and report['invalid']==1
    assert 'FAILED: Feed unavailable' in report_text(report)
    assert store.setting('discovery_report')==report
    assert discover(store,PREF)['added']==0
    ids=plan_queue(store,{},PREF);assert len(ids)==1
    valid,skipped=queue_preflight(store,ids,{},dict(PREF,countries='Canada'))
    assert not valid and skipped
    store.state(ids[0],'submitted');assert plan_queue(store,{},PREF)==[]


def test_search_requires_role_country():
    for pref in ({},{'titles':'Engineer'},{'countries':'India'}):
        with pytest.raises(ValueError):validate_search(pref)
    validate_search(PREF)
    with pytest.raises(ValueError):validate_search(dict(PREF,countries='XX'))


def test_structured_provider_country_locations(monkeypatch):
    from applypilot.core import import_board
    monkeypatch.setattr('applypilot.core.fetch_json',lambda _:[dict(applyUrl='https://jobs.lever.co/acme/1',text='Engineer',country='US',categories={'location':'Austin, TX'})])
    assert import_board('Lever','acme')[0]['location']=='Austin, TX | United States'
    monkeypatch.setattr('applypilot.sources.fetch_json',lambda _:{'jobs':[
        dict(jobUrl='https://jobs.ashbyhq.com/acme/1',title='Engineer',location='NYC',address={'postalAddress':{'addressCountry':'US'}},
             secondaryLocations=[{'location':'London','address':{'postalAddress':{'addressCountry':'GB'}}}]) ]})
    result=import_board('Ashby','acme')[0]
    assert result['location']=='NYC | United States; London | United Kingdom'
    assert geography_matches(result,{'countries':'UK','cities':'London'})


def test_refresh_pending_location_without_reopening_submitted(tmp_path,monkeypatch):
    from applypilot import discovery
    store=Store(tmp_path)
    old=store.add(dict(job(),location='Bengaluru'))
    sent=store.add(dict(job(),url='https://example.com/submitted',location='Old location'))
    store.state(sent,'submitted')
    monkeypatch.setattr(discovery,'CATALOG',{'Lever':('acme',)})
    monkeypatch.setattr(discovery,'import_board',lambda *a:[job(),dict(job(),url='https://example.com/submitted')])
    report=discover(store,PREF)
    assert report['added']==0 and store.job(old)['location']=='Bengaluru | India'
    assert store.job(sent)['status']=='submitted' and store.job(sent)['location']=='Old location'
    assert plan_queue(store,{},PREF,report['job_ids'])==[old]
