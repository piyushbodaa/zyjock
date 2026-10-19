"""Compile official PG evidence into a compact static-site dataset.
Run acquisition builders first. Only conservative exact source identities are joined.
"""
import json,re,unicodedata,hashlib
from pathlib import Path
from collections import defaultdict
ROOT=Path(__file__).resolve().parents[1]
DIST=ROOT/'dist'
DERIVED=ROOT/'sources'/'derived'
DERIVED.mkdir(exist_ok=True)
def read(name):
    p=DIST/name
    if not p.exists():p=(ROOT/'sources'/name) if name=='pg-content.json' else DERIVED/name
    return json.loads(p.read_text())
def norm(s):return re.sub(r'[^a-z0-9]','',unicodedata.normalize('NFKD',str(s or '')).lower())
def instkey(i):
    s=i.get('normalizedInstitution') or i.get('originalInstitution') or i['name']
    s=re.sub(r'\(?\b[67]\d{5}\b\)?\s*$','',s)
    return norm(s)
def coursekey(r):return norm(r.get('courseCode') or r.get('originalCourse') or r['course'])
def quota(s):
    n=norm(s)
    return {'allindia':'All India','allindiaquota':'All India','dnbquota':'DNB Quota','dnb':'DNB Quota','nonresidentindian':'Non-Resident Indian','selffinancedmeritseat':'Self-Financed Merit Seat'}.get(n,s)
def program(course):
    c=course.upper().strip()
    if 'NBEMS-DIPLOMA' in c:return 'NBEMS Diploma'
    if 'DIRECT 6 YEARS' in c:return 'Direct 6-year NBEMS'
    if 'NBEMS' in c:return 'DNB'
    if c.startswith('DIP') or 'PG DIPLOMA' in c:return 'PG Diploma'
    if c.startswith('MD/MS') or ('OBST.' in c and '/MS' in c):return 'MD / MS'
    if c.startswith('M.D.'):return 'MD'
    if c.startswith('M.S.'):return 'MS'
    if c.startswith('M.CH.'):return 'MCh (PG entry)'
    if c.startswith('M.P.H.'):return 'MPH'
    return 'Other PG programme'
def specialty(course):
    c=norm(course)
    if c in {'nbemsdiplomaent','nbemsent','msent'}:return 'Otorhinolaryngology (ENT)'
    terms=[('aerospace','Aerospace Medicine'),('anaesthes','Anaesthesiology'),('anatomy','Anatomy'),('biochemistry','Biochemistry'),('cardiovascular','Cardiovascular & Thoracic Surgery'),('communityhealth','Community Health & Administration'),('communitymedicine','Community Medicine'),('preventiveandsocial','Community Medicine'),('derm','Dermatology'),('diabetology','Diabetology'),('emergency','Emergency Medicine'),('epidemiology','Epidemiology'),('familymedicine','Family Medicine'),('forensic','Forensic Medicine'),('generalmedicine','General Medicine'),('generalsurgery','General Surgery'),('geriatric','Geriatric Medicine'),('healthadministration','Health Administration'),('hospitaladministration','Hospital Administration'),('transfusion','Transfusion Medicine'),('immunohaematology','Transfusion Medicine'),('laboratory','Laboratory Medicine'),('microbiology','Microbiology'),('bacteriology','Bacteriology'),('neurosurgery','Neurosurgery'),('nuclearmedicine','Nuclear Medicine'),('gynae','Obstetrics & Gynaecology'),('obstetrics','Obstetrics & Gynaecology'),('ophthalm','Ophthalmology'),('orthopaed','Orthopaedics'),('otorhino','Otorhinolaryngology (ENT)'),('msent','Otorhinolaryngology (ENT)'),('paediatricsurgery','Paediatric Surgery'),('paediatrics','Paediatrics'),('childhealth','Paediatrics'),('palliative','Palliative Medicine'),('clinicalpathology','Clinical Pathology'),('pathology','Pathology'),('pharmacology','Pharmacology'),('physicalmed','Physical Medicine & Rehabilitation'),('phymedicine','Physical Medicine & Rehabilitation'),('physiology','Physiology'),('plastic','Plastic & Reconstructive Surgery'),('psych','Psychiatry'),('publichealth','Public Health'),('radiodiagnosis','Radio-diagnosis'),('radiationmedicine','Radiation Medicine'),('radiotherapy','Radiation Oncology'),('radiationoncology','Radiation Oncology'),('respiratory','Respiratory Medicine'),('tuberculosis','Respiratory Medicine'),('tb','Respiratory Medicine'),('sport','Sports Medicine'),('traumatology','Traumatology & Surgery'),('tropical','Tropical Medicine')]
    for needle,label in terms:
        if needle in c:return label
    return re.sub(r'^\(?NBEMS(?:-DIPLOMA)?\)?\s*|^M\.[DS]\.\s*','',course,flags=re.I).strip(' ()').title()
seats=read('pg-seats.json');history=read('pg-history.json');content=read('pg-content.json')
(ROOT/'sources'/'pg-content.json').write_text(json.dumps(content,ensure_ascii=False,indent=2))
insts={i['id']:dict(i) for i in seats['institutes']}
match_artifact=json.loads((ROOT/'sources'/'pg-institution-matches.json').read_text())
approved={m['historicalId']:m for m in match_artifact['matches']}
if len(approved)!=len(match_artifact['matches']) or len({m['currentId'] for m in approved.values()})!=len(approved):
    raise ValueError('Institution matches must be one-to-one.')
remap={};ambiguous=match_artifact['unmatchedReasonCounts'].get('name_state_not_unique',0)
for i in history['institutes']:
    match=approved.get(i['id'])
    if match:
        if match['currentId'] not in insts:raise ValueError('Matched institution is missing from current matrices.')
        remap[i['id']]=match['currentId']
    else:
        remap[i['id']]=i['id'];insts[i['id']]=dict(i)
# Historical duplicates differing only in PDF line wraps are combined by source pool.
round_order={'Round 1':1,'Round 2':2,'Round 3':3,'Stray Vacancy':4}
combined={}
for row in history['records']:
    r=dict(row);match=approved.get(r['instituteId'])
    if match:r['institutionMatchMethod']=match['method']
    r['instituteId']=remap.get(r['instituteId'],r['instituteId']);r['quota']=quota(r['quota'])
    key=(r['instituteId'],coursekey(r),norm(r['quota']),norm(r['category']),r['year'],r['round'])
    if key in combined:
        old=combined[key];old['openingRank']=min(old['openingRank'],r['openingRank']);old['closingRank']=max(old['closingRank'],r['closingRank']);old['allotmentCount']+=r['allotmentCount']
    else:combined[key]=r
historic=list(combined.values());by_pool=defaultdict(list)
def pool(r):return(r['instituteId'],coursekey(r),norm(r['quota']),norm(r['category']))
for r in historic:by_pool[pool(r)].append(r)
for rows in by_pool.values():rows.sort(key=lambda r:(r['year'],round_order.get(r['round'],0)))
current=[];matched=0
for row in seats['records']:
    r=dict(row);r['quota']=quota(r['quota']);past=by_pool.get(pool(r),[])
    if past:
        h=past[-1];r.update(historicalOpeningRank=h['openingRank'],historicalClosingRank=h['closingRank'],historicalYear=h['year'],historicalRound=h['round'],historicalSourceUrl=h['sourceUrl'],historicalMatchMethod=h.get('institutionMatchMethod'),historyIds=[x['id'] for x in past]);matched+=1
    current.append(r)
all_rows=current+historic
# Financial enrichment is separately dated and only linked to exact institution codes/names.
financials=content.get('financials',[]);financial_matches=0
for r in all_rows:
    r['program']=program(r['course']);
    if r.get('programType') and 'Direct 6' not in r['program']:r['program']={'Diploma':'PG Diploma','MCh':'MCh (PG entry)'}.get(r['programType'],r['programType'])
    r['specialty']=specialty(r['course']);i=insts[r['instituteId']]
    for f in financials:
        same=(f.get('instituteCode') and str(f['instituteCode'])==str(i.get('instituteCode'))) or (f.get('instituteName') and norm(f['instituteName'])==norm(i['name']))
        if not same:continue
        if f.get('course') and norm(f['course'])!=norm(r['course']) and not ('all specialties' in f['course'].lower() and r['program'] in ['MD','MS','MD / MS']):continue
        if f.get('program') and f['program']!=r['program']:continue
        if f.get('quota') and norm(quota(f['quota']))!=norm(r['quota']):continue
        for k in ['annualFee','monthlyStipend','bondYears','bondPenalty']:
            if f.get(k) is not None:r[k]=f[k]
        r.update(financialYear=f.get('year'),financialSourceUrl=f.get('sourceUrl'),financialSourceLabel=f.get('sourceLabel'),financialNotes=' '.join(filter(None,[f.get('feeScope'),f.get('notes')])));financial_matches+=1;break
# Strip extraction-only text from deployment, keeping exact originals in acquisition artifacts.
source_index={};source_by_url={}
all_sources=[]
for x in seats['sources']+history['sources']+content.get('sources',[]):
    u=x.get('url') or x.get('sourceUrl')
    if not u or u in source_by_url:continue
    sid=x.get('id') or 's-'+hashlib.sha1(u.encode()).hexdigest()[:10]
    if sid in source_index:sid='s-'+hashlib.sha1(u.encode()).hexdigest()[:10]
    source_by_url[u]=sid;source_index[sid]={'url':u,'title':x.get('title') or x.get('label') or 'Official publication'}
    all_sources.append({**x,'id':sid,'url':u})
def source_id(url,title=None):
    if not url:return None
    if url not in source_by_url:
        sid='s-'+hashlib.sha1(url.encode()).hexdigest()[:10];source_by_url[url]=sid;source_index[sid]={'url':url,'title':title or 'Official publication'}
    return source_by_url[url]
keep=['institutionMatchMethod','historicalMatchMethod','id','instituteId','instituteCode','courseCode','course','program','specialty','quota','category','year','round','recordKind','seats','openingRank','closingRank','allotmentCount','historyIds','historicalOpeningRank','historicalClosingRank','historicalYear','historicalRound','annualFee','monthlyStipend','bondYears','bondPenalty','previousSeats','financialYear','financialSourceLabel','financialNotes','sourcePage','sourcePageFirst','sourcePageLast']
packed=[]
for r in all_rows:
    out={k:r[k] for k in keep if r.get(k) is not None}
    out['sourceId']=source_id(r.get('sourceUrl'),r.get('sourceLabel'))
    if r.get('historicalSourceUrl'):out['historicalSourceId']=source_id(r['historicalSourceUrl'])
    if r.get('financialSourceUrl'):out['financialSourceId']=source_id(r['financialSourceUrl'])
    packed.append(out)
files=[];zero_files=[]
for old in list(DIST.glob('pg-records-*.json'))+list(DIST.glob('pg-zero-*.json')):old.unlink()
active=[r for r in packed if r.get('seats')!=0]
zero=[r for r in packed if r.get('seats')==0]
for label,rows,dest in [('pg-records',active,files),('pg-zero',zero,zero_files)]:
    for n,start in enumerate(range(0,len(rows),6000)):
        fn=f'{label}-{n}.json';(DIST/fn).write_text(json.dumps(rows[start:start+6000],ensure_ascii=False,separators=(',',':')));dest.append(fn)
# Keep source identity unique; historical-only entities remain visible in the historical explorer.
public_insts=[]
for i in insts.values():
    public={k:i.get(k) for k in ['id','instituteCode','name','city','state','type','officialUrl']}
    original=i['name'];parts=original.split(',');short=parts[0].strip()
    if len(short)<65 and len(parts)>1 and len(short+', '+parts[1].strip())<105:short+=', '+parts[1].strip()
    public['name']=short;public['address']=original if original!=short else None
    if public.get('state'):public['state']=public['state'].title()
    public_insts.append(public)
published=sum(r.get('seats') or 0 for r in current)
coverage={'label':'NEET PG official data','publishedSeats':published,'currentInstitutes':len(seats['institutes']),'currentRecords':len(current),'historicalRecords':len(historic),'historicalAllotments':sum(r['allotmentCount'] for r in historic),'historicalScope':'2025 · Rounds 1, 2, 3 and Stray Vacancy','matchedCurrentPools':matched,'financialPools':financial_matches,'summary':f'MCC 2026 Round 1 published matrices contain {published:,} seats. The historical explorer contains {len(historic):,} cutoff observations derived from MCC 2025 final allotment results. {matched:,} current seat pools have an exact historical match.','limitations':['MCC counselling only. State counselling outside these MCC sources is not included in the seat and cutoff dataset.','The 2026 matrices are a dated publication snapshot and can be revised; they are not a live vacancy feed.','Historical cutoffs aggregate current-round allotments by allotted seat category. Held seats without a new allocation are excluded from later-round observations.','Cross-year institution matching uses exact full addresses or unique exact names within the same explicit state. Generic names, ambiguous identities and conflicting postcodes are excluded from name matching. Course code, quota and allotted category must also match. Unmatched rows are not labelled new seats.','Financial source coverage is limited and separately dated. Missing fees, stipends or bond terms remain unknown.','No fictional colleges, demo ranks or other exams are included. Personal candidate identifiers are excluded.']}
defaults={k:None for k in ['openingRank','closingRank','seats','annualFee','monthlyStipend','bondYears','bondPenalty','previousSeats','historicalOpeningRank','historicalClosingRank','historicalYear','historicalRound','financialYear']};defaults.update(exam='NEET PG',dataStatus='verified',counselling='MCC')
output={'version':2,'updatedAt':'2026-10-19','exams':['NEET PG'],'coverage':coverage,'institutes':public_insts,'records':[],'recordFiles':files,'zeroRecordFiles':zero_files,'recordDefaults':defaults,'sourceIndex':source_index,'sources':all_sources,'resources':content.get('resources',[]),'guides':content.get('guides',[]),'notices':content.get('notices',[]),'timeline':content.get('timeline',[]),'financials':financials,'dnbAnnualFeeReference':content.get('dnbAnnualFeeReference')}
(DIST/'data.json').write_text(json.dumps(output,ensure_ascii=False,separators=(',',':')))
summary={**coverage,'institutionMatches':len([k for k,v in remap.items() if k!=v]),'ambiguousInstitutionKeys':ambiguous,'compiledPools':len(all_rows),'files':[{ 'name':f,'bytes':(DIST/f).stat().st_size} for f in ['data.json']+files+zero_files],'matchingMethod':'Exact full institution/address or unique exact institution name and explicit state, with generic names, ambiguity and postcode conflicts excluded; exact course code, quota and allotted category. See pg-institution-matches.json. No fuzzy matching.'}
(ROOT/'sources'/'pg-site-summary.json').write_text(json.dumps(summary,indent=2))
for name in ['pg-history.json','pg-seats.json','pg-content.json']:
    p=DIST/name
    if p.exists():p.replace(DERIVED/name)
print(json.dumps(summary,indent=2))
