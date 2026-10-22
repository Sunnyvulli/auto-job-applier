"""Bounded local matching, document import and resumable queue planning."""
import heapq
import re
from pathlib import Path
from .core import match

HEADINGS={'summary':'summary','professional summary':'summary','profile':'summary','experience':'experience','work experience':'experience','professional experience':'experience','employment history':'experience','projects':'projects','selected projects':'projects','education':'education','academic background':'education','skills':'skills','technical skills':'skills','core competencies':'skills'}

def resume_text(path):
    path=Path(path)
    if path.stat().st_size>20*1024*1024:raise ValueError('Choose a resume under 20 MB.')
    if path.suffix.lower()=='.pdf':
        from pypdf import PdfReader
        reader=PdfReader(path)
        if reader.is_encrypted:raise ValueError('Unlock the resume PDF before importing it.')
        if len(reader.pages)>20:raise ValueError('Choose a resume with 20 pages or fewer.')
        text='\n'.join(page.extract_text() or '' for page in reader.pages)
    elif path.suffix.lower() in {'.txt','.md'}:text=path.read_text(encoding='utf-8-sig')
    elif path.suffix.lower()=='.docx':
        import zipfile,xml.etree.ElementTree as ET
        with zipfile.ZipFile(path) as archive:
            item=archive.getinfo('word/document.xml')
            if item.file_size>10*1024*1024:raise ValueError('Resume document is too large to extract.')
            root=ET.fromstring(archive.read(item))
        ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
        text='\n'.join(''.join(p.itertext()) for p in root.findall('.//w:p',ns))
    else:raise ValueError('Choose a PDF, DOCX or UTF-8 text resume.')
    if len(text.strip())<30:raise ValueError('No usable text found. Scanned resumes need OCR before importing.')
    return text[:100000]

def extract_profile(text):
    """Only explicit headings/contact patterns. Always review before saving."""
    lines=[line.strip() for line in text.splitlines() if line.strip()]
    result={};section=None;sections={}
    email=re.search(r'[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}',text,re.I)
    if email:result['email']=email.group()
    for key,pattern in [('linkedin',r'(?:https?://)?(?:www\.)?linkedin\.com/in/[\w-]+/?'),('website',r'https://github\.com/[\w-]+/?')]:
        found=re.search(pattern,text,re.I)
        if found:result[key]=found.group() if found.group().startswith('http') else 'https://'+found.group()
    if lines and 1<len(lines[0].split())<=6 and len(lines[0])<75 and not re.search(r'[@\d|:/]',lines[0]) and lines[0].lower() not in HEADINGS:
        result['name']=lines[0]
    for line in lines:
        heading=re.sub(r'[:\s]+$','',line).lower()
        if heading in HEADINGS:section=HEADINGS[heading];sections.setdefault(section,[])
        elif section:sections[section].append(line)
    for key,values in sections.items():result[key]='\n'.join(values)
    if result.get('skills'):result['skills']=re.sub(r'[\n;|•]+',', ',result['skills'])
    return result

def terms(value):return [t.strip().lower() for t in value.split(',') if t.strip()]

def assess(profile,job,preferences):
    title=job['title'].lower();location=job.get('location','').lower();company=job['company'].lower()
    found=match(profile,job)['skills'];reasons=[]
    wanted=terms(preferences.get('titles',''));places=terms(preferences.get('locations',''))
    excluded=terms(preferences.get('exclude',''))
    if wanted and not any(x in title for x in wanted):reasons.append('Title outside preferences')
    if places and not any(x in location for x in places):reasons.append('Location outside preferences')
    from .discovery import geography_matches
    if not geography_matches(job,preferences):reasons.append('Country or city outside preferences (or unknown)')
    if any(x in company for x in excluded):reasons.append('Excluded company')
    if preferences.get('exclude_senior',False) and re.search(r'\b(senior|staff|principal|director|head|sr\.?|lead|manager)\b',title):reasons.append('Seniority excluded')
    minimum=int(preferences.get('min_skills',0))
    if len(found)<minimum:reasons.append('Insufficient skill overlap')
    return dict(eligible=not reasons,skills=found,score=len(found),reasons=reasons,note='Preference/keyword match; verify qualifications and work authorization.')

def plan_queue(store,profile,preferences,candidate_ids=None):
    cap=max(1,min(50,int(preferences.get('queue_limit',10))))
    allowed=set(candidate_ids) if candidate_ids is not None else None
    ranked=[]
    for job in store.candidates():
        if allowed is not None and job['id'] not in allowed:continue
        assessment=assess(profile,job,preferences)
        if assessment['eligible']:
            heapq.heappush(ranked,(assessment['score'],job['updated'],job['id']))
            if len(ranked)>cap:heapq.heappop(ranked)
    ranked.sort(reverse=True)
    return [item[2] for item in ranked[:cap]]


def queue_preflight(store,ids,profile,preferences):
    """Recheck current saved preferences and claimable status before starting."""
    accepted=[];skipped=[];seen=set()
    for jid in ids[:50]:
        if jid in seen:continue
        seen.add(jid)
        try:job=store.job(jid)
        except ValueError:skipped.append((jid,'Job no longer exists'));continue
        reasons=[]
        if job['status'] not in {'saved','prepared'}:reasons.append('Already processed or needs manual review')
        reasons.extend(assess(profile,job,preferences)['reasons'])
        if reasons:skipped.append((jid,'; '.join(reasons)))
        else:accepted.append(jid)
    return accepted,skipped
