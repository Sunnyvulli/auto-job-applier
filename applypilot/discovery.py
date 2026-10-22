"""Automatic, bounded discovery from public employer ATS feeds (no API key)."""
import re
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from .core import import_board, canonical_url, now

# Explicit, inspectable coverage. Failed/retired boards are reported, never hidden.
CATALOG = {
    'Greenhouse': ('databricks','stripe','cloudflare','coinbase','mongodb','datadog',
                   'figma','discord','reddit','pinterest','duolingo','airbnb','twilio',
                   'okta','gitlab','elastic','affirm','robinhood','rubrik','anthropic'),
    'Lever': ('palantir','spotify','zoox','weride'),
    'Ashby': ('ramp','plaid','openai','notion','linear','vanta','deel','cursor'),
    'SmartRecruiters': ('BoschGroup','Visa','ServiceNow','WesternDigital','SopraSteria1'),
}
ALIASES = {
    'united states': ('us','usa','u.s.','u.s.a.','united states of america'),
    'united kingdom': ('gb','uk','great britain'), 'india': ('in',),
    'canada': ('ca',), 'australia': ('au',), 'germany': ('de','deutschland'),
    'france': ('fr',), 'ireland': ('ie',), 'netherlands': ('nl',),
    'singapore': ('sg',), 'united arab emirates': ('ae','uae'),
    'new zealand': ('nz',), 'japan': ('jp',), 'south korea': ('kr',),
    'china': ('cn',), 'brazil': ('br',), 'mexico': ('mx',),
    'spain': ('es',), 'italy': ('it',), 'poland': ('pl',), 'portugal': ('pt',),
    'sweden': ('se',), 'switzerland': ('ch',), 'austria': ('at',),
    'belgium': ('be',), 'denmark': ('dk',), 'norway': ('no',),
    'finland': ('fi',), 'israel': ('il',), 'south africa': ('za',),
    'philippines': ('ph',), 'malaysia': ('my',), 'indonesia': ('id',),
    'vietnam': ('vn',), 'thailand': ('th',), 'taiwan': ('tw',),
    'czechia': ('cz','czech republic'), 'romania': ('ro',), 'hungary': ('hu',),
    'saudi arabia': ('sa',), 'pakistan': ('pk',), 'bangladesh': ('bd',),
}


def normalized(value):
    return ' '.join(re.findall(r'\w+', value.casefold()))


def parts(value):
    return [x.strip() for x in value.split(',') if x.strip()]


def country_name(value):
    value=value.strip().casefold()
    for name, aliases in ALIASES.items():
        if value==name or value in aliases:return name
    if len(value)<3:raise ValueError('Use a full country name, or a supported country code such as US, IN, GB or CA.')
    return value


def contains(text, phrase):
    return ' '+normalized(phrase)+' ' in ' '+normalized(text)+' '


def country_matches(location,country):
    """Only explicit country names or separated ISO tokens; no city guesses."""
    if contains(location,country):return True
    if country in {'united states','united kingdom'} and any(contains(location,a) for a in ALIASES[country]):return True
    for alias in ALIASES.get(country,()):
        if len(normalized(alias).replace(' ',''))>3:
            if contains(location,alias):return True
        else:
            # CA is Canada only when a whole location segment, not San Jose, CA.
            # Ambiguous short codes in free-text locations are intentionally rejected.
            segments=[x.strip().casefold() for x in re.split(r'[|/()]',location)]
            if alias in segments:return True
    return False


def geography_matches(job,preferences):
    countries=[country_name(x) for x in parts(preferences.get('countries',''))]
    cities=parts(preferences.get('cities',''))
    if not countries and not cities:return True
    # Each semicolon-separated location is a separate option, never mix countries/cities.
    return any((not countries or any(country_matches(loc,c) for c in countries))
               and (not cities or any(contains(loc,city) for city in cities))
               for loc in job.get('location','').split(';'))


def discovery_matches(job,preferences):
    roles=parts(preferences.get('titles',''))
    if not roles or not any(contains(job['title'],role) for role in roles):return False
    if any(contains(job['company'],x) for x in parts(preferences.get('exclude',''))):return False
    if preferences.get('exclude_senior',False) and re.search(r'\b(senior|staff|principal|director|head|sr|lead|manager)\b',job['title'],re.I):return False
    return geography_matches(job,preferences)


def validate_search(preferences):
    if not parts(preferences.get('titles','')):raise ValueError('Save at least one target role in Preferences.')
    if not parts(preferences.get('countries','')):raise ValueError('Save at least one target country in Preferences. Cities are optional.')
    for country in parts(preferences['countries']):country_name(country)


def search_boards(store,preferences):
    boards=[dict(provider=p,company=c,region='global') for p,companies in CATALOG.items() for c in companies]
    boards+=store.setting('boards',[])
    unique={}
    for b in boards:
        key=(b['provider'],b['company'].casefold(),b.get('region','global'))
        unique[key]=dict(provider=b['provider'],company=b['company'],region=b.get('region','global'))
    return list(unique.values())[:1000]


def discover(store,preferences,notify=lambda _:None):
    validate_search(preferences)
    boards=search_boards(store,preferences)
    report=dict(started=now(),finished='',roles=preferences['titles'],countries=preferences['countries'],
                cities=preferences.get('cities',''),sources=[],scanned=0,matched=0,added=0,invalid=0,
                job_ids=[],coverage='Built-in employer catalog plus saved sources; not every company or portal.')
    workers=1 if preferences.get('low_resource',False) else 3
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures={pool.submit(import_board,b['provider'],b['company'],b['region']):b for b in boards}
        for future in as_completed(futures):
            board=futures[future];result=dict(board,found=0,matched=0,added=0,error='')
            try:
                jobs=future.result();result['found']=len(jobs);report['scanned']+=len(jobs)
                matches=[]
                for job in jobs:
                    try:
                        canonical_url(job['url'])
                        if discovery_matches(job,preferences):matches.append(job)
                    except (ValueError,KeyError,TypeError):report['invalid']+=1
                result['matched']=len(matches);result['added']=store.add_many(matches)
                # Refresh only unprocessed listings, preserving status/history and URL identity.
                with store.connect() as c:
                    for j in matches:
                        values=(j['company'],j['title'],j.get('location',''),j.get('description',''))
                        c.execute("UPDATE jobs SET company=?,title=?,location=?,description=? WHERE url=? AND status IN ('saved','prepared') AND (company<>? OR title<>? OR location<>? OR description<>?)",(*values,canonical_url(j['url']),*values))
                report['matched']+=len(matches);report['added']+=result['added']
                report['job_ids'].extend(hashlib.sha256(canonical_url(j['url']).encode()).hexdigest()[:20] for j in matches)
            except Exception as e:result['error']=str(e)[:250]
            report['sources'].append(result)
            notify(f"Job search {len(report['sources'])}/{len(boards)} sources: {report['matched']} matching, {report['added']} new")
    report['job_ids']=list(dict.fromkeys(report['job_ids']))
    report['finished']=now();store.save_setting('discovery_report',report)
    return report


def report_text(report):
    if not report:return 'No discovery search has run yet.'
    lines=[f"Search finished: {report['finished']}",f"Roles: {report['roles']}",f"Countries: {report['countries']} | Cities: {report['cities'] or 'Any'}",
           f"Scanned {report['scanned']:,}; matching {report['matched']:,}; newly imported {report['added']:,}; invalid listings {report['invalid']}",
           report['coverage'],'Country matching requires explicit location evidence; unknown-country and worldwide-only listings are excluded.','']
    for source in report['sources']:
        lines.append(f"{source['provider']} / {source['company']}: "+('FAILED: '+source['error'] if source['error'] else f"{source['found']} scanned, {source['matched']} matching, {source['added']} new"))
    return '\n'.join(lines)
