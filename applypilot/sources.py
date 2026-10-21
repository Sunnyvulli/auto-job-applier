"""Public job feeds with explicit pagination and board URL normalization."""
import re
from urllib.parse import urlsplit, quote
from .core import fetch_json, plain

PROVIDERS=['Greenhouse','Lever','Ashby','SmartRecruiters']

def board_identifier(provider,value):
    value=value.strip()
    if '://' in value:
        p=urlsplit(value);host=p.hostname or '';parts=[x for x in p.path.split('/') if x]
        hosts={'Greenhouse':{'boards.greenhouse.io','job-boards.greenhouse.io'},'Lever':{'jobs.lever.co','jobs.eu.lever.co'},'Ashby':{'jobs.ashbyhq.com'},'SmartRecruiters':{'careers.smartrecruiters.com','jobs.smartrecruiters.com'}}
        if p.scheme!='https' or host not in hosts.get(provider,set()) or not parts or p.username:
            raise ValueError('Use a board URL belonging to the selected provider.')
        value=parts[0]
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,100}',value):raise ValueError('Enter a valid company identifier or supported board URL.')
    return value

def extended_board(provider,company):
    if provider=='Ashby':
        data=fetch_json(f'https://api.ashbyhq.com/posting-api/job-board/{company}')
        return [dict(url=j.get('applyUrl') or j['jobUrl'],company=company,title=j['title'],location=j.get('location',''),description=plain(j.get('descriptionPlain') or j.get('descriptionHtml',''))) for j in data['jobs'] if j.get('isListed',True)]
    if provider=='SmartRecruiters':
        result=[];seen=set();offset=0
        for _ in range(100):
            data=fetch_json(f'https://api.smartrecruiters.com/v1/companies/{company}/postings?limit=100&offset={offset}')
            items=data.get('content',[])
            if not items:break
            fresh=[j for j in items if j['id'] not in seen]
            if not fresh:raise ValueError('Job feed repeated a page; import stopped rather than returning incomplete results.')
            for j in fresh:
                seen.add(j['id']);location=j.get('location',{})
                # Public hosted URL accepts the canonical posting ID; never navigate a feed-supplied API ref.
                url='https://jobs.smartrecruiters.com/'+company+'/'+quote(str(j['id']),safe='')
                result.append(dict(url=url,company=j.get('company',{}).get('name',company),title=j['name'],location=', '.join(filter(None,[location.get('city'),location.get('country')])),description=plain(j.get('jobAd',{}).get('sections',{}).get('jobDescription',{}).get('text',''))))
            offset+=len(items)
            if offset>=data.get('totalFound',offset):break
        else:raise ValueError('Board exceeds 10,000 listings. Use selected job links instead.')
        return result
    raise ValueError('Unsupported provider')

def hydrate_job(store,job):
    """Fetch public SmartRecruiters details only for a selected job's documents."""
    p=urlsplit(job['url']);parts=[x for x in p.path.split('/') if x]
    if p.hostname!='jobs.smartrecruiters.com' or len(parts)<2 or job.get('description'):return job
    company=board_identifier('SmartRecruiters',parts[0]);posting=parts[1].split('-')[0]
    if not re.fullmatch(r'[A-Za-z0-9_]+',posting):raise ValueError('Unsupported SmartRecruiters posting ID.')
    record=fetch_json(f'https://api.smartrecruiters.com/v1/companies/{company}/postings/{posting}')
    sections=record.get('jobAd',{}).get('sections',{})
    description='\n\n'.join(plain(sections.get(k,{}).get('text','')) for k in ('companyDescription','jobDescription','qualifications','additionalInformation'))
    job=dict(job,description=description.strip())
    with store.connect() as c:c.execute('UPDATE jobs SET description=? WHERE id=?',(job['description'],job['id']))
    return job
