"""Rebuild northern official PG dataset. No candidate-level fields are serialized."""
from pathlib import Path
import json,re,hashlib,collections
import pymupdf
ROOT=Path(__file__).parent
URLS=json.loads((ROOT/'document-index.json').read_text())
OUT={'region':'North and Northeast','checkedAt':'2026-10-19','states':[],'institutes':[],'records':[],'financials':[],'sources':[],'summary':{}}
inst={}
def clean(x):return ' '.join((x or '').split())
def ident(*parts):return hashlib.sha256('|'.join(map(str,parts)).encode()).hexdigest()[:16]
def institution(name,state,url,typ='Government',city=None):
 key=(name,state)
 if key not in inst:
  inst[key]='state-north-'+ident(*key);OUT['institutes'].append({'id':inst[key],'name':name,'state':state,'city':city,'type':typ,'officialUrl':url})
 return inst[key]
def record(i,course,quota,category,year,round,source,page,seats=None,ranks=None,rankType='NEET PG AIR',counselling=None):
 r={'id':'pg-north-'+ident(i,course,quota,category,year,round,source),'instituteId':i,'exam':'NEET PG','recordKind':'cutoff' if ranks else 'seat-matrix','counselling':counselling,'course':clean(course),'program': ('NBEMS Diploma' if 'NBEMS' in course else ('PG Diploma' if course.startswith('DIPLOMA') else ('DNB' if course.startswith('DNB') else ('MS' if course.startswith('MS') or '(MS)' in course else 'MD')))),'quota':clean(quota),'category':clean(category),'year':year,'round':round,'seats':seats,'openingRank':min(ranks) if ranks else None,'closingRank':max(ranks) if ranks else None,'rankType':rankType,'sourceUrl':URLS[source],'sourceLabel':source,'sourcePage':page,'dataStatus':'verified'}
 if ranks:r['allotmentCount']=len(ranks)
 OUT['records'].append(r)
def finance(state,title,source,page,scope,year=2025,**kw):
 f={'id':'pg-fin-north-'+ident(state,title,kw.get('course'),kw.get('quota')),'state':state,'scope':scope,'title':title,'year':year,'annualFee':None,'monthlyStipend':None,'bondYears':None,'bondPenalty':None,'discontinuationPenalty':None,'sourceUrl':URLS.get(source,source),'sourcePage':page,'notes':'','dataStatus':'verified'};f.update(kw);OUT['financials'].append(f)
# HP source tables explicitly label Merit No.; these are NOT All India Ranks.
hpCounts={}
for key,round in [('hp-r1','Round 1'),('hp-r2','Round 2'),('hp-r3','Round 3'),('hp-stray','Stray'),('hp-stray2','Second stray')]:
 groups=collections.defaultdict(list);pages=collections.defaultdict(set);serials=[]
 doc=pymupdf.open(ROOT/'raw'/f'{key}.pdf')
 for pi,p in enumerate(doc):
  for tab in p.find_tables().tables:
   for row in tab.extract():
    if len(row)!=8 or not re.fullmatch(r'\d+',clean(row[0])):continue
    serials.append(int(row[0]));assert clean(row[1]).isdigit(),(key,row[0],'missing merit')
    name,course,quota,cat=map(clean,row[4:8]);assert name and course and quota and cat
    iid=institution(name,'Himachal Pradesh','https://amruhp.ac.in/counselling-notifications/', 'Private' if 'Maharishi' in name else 'Government')
    g=(iid,course,quota,cat);groups[g].append(int(row[1]));pages[g].add(pi+1)
 for g,ranks in groups.items():record(*g,2025,round,key,','.join(map(str,sorted(pages[g]))),ranks=ranks,rankType='State merit rank',counselling='Himachal Pradesh — AMRU')
 assert serials==list(range(1,len(serials)+1)),(key,'non-contiguous serial sequence')
 hpCounts[key]={'sourceRows':len(serials),'aggregatePools':len(groups),'rankType':'State merit rank'}
OUT['summary']['himachalAllotments']=hpCounts
# Current 2026 institutional Northeast pool; AIQ deliberately omitted (already in MCC).
name='North Eastern Indira Gandhi Regional Institute of Health and Medical Sciences (NEIGRIHMS)'
iid=institution(name,'Meghalaya','https://www.neigrihms.gov.in/examsnotification.html',city='Shillong')
doc=pymupdf.open(ROOT/'raw/neigrihms-prospectus.pdf');total=0
for row in doc[3].find_tables().tables[0].extract():
 if not row[0] or not row[0].isdigit() or not (row[3] or '').isdigit():continue
 course=clean(row[1]);program='MS' if course in ['Obst and Gynaecology','Otorhinolaryngology','Ophthalmology','Orthopaedics'] else 'MD'
 for col,quota in [(5,'Open Northeast'),(6,'NEIGRIHMS institutional roster')]:
  seats=int(row[col]);total+=seats
  if seats:record(iid,program+' '+course,quota,'As per institutional roster',2026,'Published matrix','neigrihms-prospectus',4,seats=seats,counselling='NEIGRIHMS institutional counselling')
assert total==17
OUT['summary']['neigrihms2026InstitutionalSeats']=total
finance('Meghalaya','NEIGRIHMS MD/MS annual tuition and discontinuation terms','neigrihms-prospectus','9–10','Institutional MD/MS courses',2026,instituteName=name,program='MD/MS',annualFee=8000,discontinuationPenalty=1000000,notes='Annual tuition ₹8,000; annual charges including hostel total ₹28,300. One-time admission/enrolment ₹20,700 and refundable security ₹20,000 separately. Course departure: ₹10 lakh in year 1, ₹15 lakh in year 2, ₹20 lakh in year 3; original-certificate clause additionally specifies ₹50,000. These are course-discontinuation obligations, not a post-course service bond. Monthly JR emoluments are referenced without a numeric amount.')
# Tripura prospectus Annexure C, positive pools only; blank/dashes are not emitted.
trip={'agmc':institution('Agartala Government Medical College','Tripura','https://trmcc.admissions.nic.in/pg-counselling/',city='Agartala'),'tmc':institution('Tripura Medical College','Tripura','https://trmcc.admissions.nic.in/pg-counselling/','Society',city='Agartala'),'lgb':institution('Lokopriya Gopinath Bordoloi Regional Institute of Mental Health','Assam','https://trmcc.admissions.nic.in/pg-counselling/',city='Tezpur'),'igm':institution('IGM Hospital','Tripura','https://trmcc.admissions.nic.in/pg-counselling/',city='Agartala')}
doc=pymupdf.open(ROOT/'raw/tripura-prospectus.pdf');seatTotals=collections.Counter()
for pi in [16,17]:
 for row in doc[pi].find_tables().tables[0].extract():
  if not row[0] or not re.fullmatch(r'\d+\.',row[0]):continue
  course=clean(row[1])
  for col,cat in [(2,'UR'),(3,'EWS'),(4,'ST'),(5,'SC')]:
   v=clean(row[col]);m=re.match(r'^(\d+)(?:-(\w+))?',v)
   if m:
    n=int(m[1]);seatTotals['AGMC']+=n;record(trip['agmc'],course,'Tripura State quota',cat+((' — '+m[2]) if m[2] else ''),2025,'Published matrix','tripura-prospectus',pi+1,seats=n,counselling='Tripura — TRMCC')
  for col,quota,ik in [(7,'Tripura State quota','tmc'),(8,'TMC Open quota (eligible AGMC/TMC graduates)','tmc'),(10,'Tripura State quota nomination','lgb')]:
   m=re.match(r'^(\d+)-(\w+)',clean(row[col]))
   if m:
    n=int(m[1]);seatTotals['TMC' if ik=='tmc' else 'LGBRIMH']+=n;record(trip[ik],course,quota,m[2],2025,'Published matrix','tripura-prospectus',pi+1,seats=n,counselling='Tripura — TRMCC')
for row in doc[18].find_tables().tables[0].extract():
 if not row[0] or not row[0].isdigit():continue
 course=clean(row[1]);subtotal=0
 for n,cat in re.findall(r'(\d+)-([^,]+)',row[3]):
  n=int(n);subtotal+=n;seatTotals['IGM Diploma']+=n;record(trip['igm'],course,'Tripura State quota — in-service',clean(cat),2025,'Published matrix','tripura-prospectus',19,seats=n,counselling='Tripura — TRMCC')
 assert subtotal==int(row[2])
assert dict(seatTotals)=={'AGMC':46,'TMC':8,'LGBRIMH':1,'IGM Diploma':10},seatTotals
OUT['summary']['tripura2025Seats']=dict(seatTotals)
# Precisely scoped official finance observations.
finance('Himachal Pradesh','Government medical colleges — annual MD/MS tuition','hp-prospectus',22,'Government medical colleges of Himachal Pradesh',annualFee=24000,program='MD/MS',notes='Chapter 8.2: tuition ₹24,000/year; total annual college charges ₹31,500. Hostel charges ₹21,000/year and refundable securities ₹12,500 separately. More than 40% disability fee exemption in clause 8.1. Stipend and bond are college-specific, not quoted by this prospectus.')
finance('Manipur','JNIMS direct and institutional preference MD/MS fees and stipend','jnims-prospectus','5–6','Direct and institutional preference candidates',instituteName='Jawaharlal Nehru Institute of Medical Sciences (JNIMS), Imphal',program='MD/MS',annualFee=50000,monthlyStipend=50000,stipendByYear=[50000,55000,60000],discontinuationPenalty=300000,notes='First-year admission fee ₹50,000; second and third years ₹25,000 each. Direct/institutional preference stipend ₹50,000/55,000/60,000 by year. Leaving before one year: ₹3 lakh; after one year: ₹7 lakh; additionally return cumulative stipend received. Not a post-course service bond.')
finance('Manipur','JNIMS in-service MD/MS candidates — stipend exclusion','jnims-prospectus','5–6','In-service candidates',instituteName='Jawaharlal Nehru Institute of Medical Sciences (JNIMS), Imphal',program='MD/MS',annualFee=50000,monthlyStipend=0,stipendByYear=[0,0,0],discontinuationPenalty=300000,notes='Source explicitly says no stipend for in-service candidates. Annual admission charges ₹50,000 first year and ₹25,000 each in years 2/3. Course leaving ₹3 lakh before one year or ₹7 lakh thereafter. Salary continuation is not described here.')
finance('Delhi','University of Delhi MD/MS annual university fee','du-prospectus','17–18','MD/MS students registered with Faculty of Medical Sciences, University of Delhi',2026,program='MD/MS',annualFee=13000,notes='Tuition ₹13,000/year within total annual university fee ₹19,500 in 2026 bulletin. Registration and college/hostel charges are separate. This university amount is not a full college-cost quote. Fee concessions and revisions apply; consult prospectus.')
finance('Delhi','VMMC and Safdarjung MD/MS tuition and withdrawal fee','vmmc-fee',1,'VMMC and Safdarjung Hospital MD/MS courses from academic session 2024–25 onwards',instituteName='Vardhman Mahavir Medical College and Safdarjung Hospital',program='MD/MS',annualFee=15000,discontinuationPenalty=300000,notes='College tuition ₹15,000/year. Total dues ₹54,500 year 1 including ₹10,000 refundable security; ₹44,500 year 2; ₹16,000 year 3. No hostel fee; HRA deducted on hostel allotment. ₹3 lakh MD/MS withdrawal penalty is not a post-PG service bond. University share subject to revision.')
exec((ROOT/'extensions.py').read_text())
# Additional states/finance prepared from source review, and optional extension parsers.
extra=ROOT/'curated.json'
if extra.exists():
 d=json.loads(extra.read_text())
 for k in ['states','financials','sources','records','institutes']:OUT[k].extend(d.get(k,[]))
for k,u in URLS.items():
 if k not in ['zmc-fees'] and (ROOT/'raw'/f'{k}.pdf').exists():OUT['sources'].append({'id':'north-'+k,'title':k.replace('-',' ').title(),'url':u,'year':2026 if k.startswith('du-') or k=='neigrihms-prospectus' or k=='arunachal-matrix' else 2025,'scope':'Northern region official PG documents'})

for f in OUT['financials']:
 if 'JNIMS' in f['title']:
  f['feeScope']='First-year admission charges';f['yearOfStudy']=1;f['tuitionByYear']=[50000,25000,25000]
 elif 'SMIMS' in f['title']:f['feeScope']='Annual course fee, single instalment'
 elif f.get('annualFee') is not None:f['feeScope']='Annual tuition only'

OUT['summary'].update({'institutions':len(OUT['institutes']),'records':len(OUT['records']),'financialPolicies':len(OUT['financials']),'jurisdictions':len(OUT['states']),'allotmentObservations':sum(r.get('allotmentCount',0) for r in OUT['records']),'seatCount':sum(r.get('seats') or 0 for r in OUT['records']),'sourceIntegrity':'Candidate identifiers and names excluded. Himachal serial rows reconcile exactly within each published final list. State merit ranks are not NEET AIR. Historical and current matrices remain separate.'})
(ROOT.parent/'north.json').write_text(json.dumps(OUT,ensure_ascii=False,separators=(',',':')))
(ROOT/'summary.json').write_text(json.dumps(OUT['summary'],indent=2))
print(json.dumps(OUT['summary'],indent=2))
