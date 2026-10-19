"""Build aggregates from official public NEET PG sources. Raw candidate data never leaves raw/."""
from pathlib import Path
import json,re,hashlib,collections
BASE=Path(__file__).parent; RAW=BASE/'raw'
DOWNLOADS=json.loads((BASE/'downloads.json').read_text())
def clean(v):return ' '.join((v or '').split())
def slug(v):return re.sub('[^a-z0-9]+','-',v.lower()).strip('-')
def key(v):return re.sub('[^a-z0-9]','',v.lower())
def uid(v):return hashlib.sha256(v.encode()).hexdigest()[:12]
def tables(k):
 for pn,p in enumerate(json.loads((RAW/(k+'-tables.json')).read_text()),1):
  for t in p: yield pn,[[clean(x) for x in row] for row in t]
def num(v):return int(v.replace(',','')) if re.fullmatch(r'[\d,]+',v or '') else None
D={'region':'west-east','checkedAt':'2026-10-19','states':[],'institutes':[],'records':[],'financials':[],'sources':[],'summary':{}}
INST={};SOURCES={};AUDIT={}
def institution(state,name,typ=None,official=None):
 k=(state,key(name))
 if k not in INST:
  i='state-'+slug(state)+'-'+uid(name.lower());INST[k]=i
  D['institutes'].append({'id':i,'name':name,'state':state,'city':'','type':typ or 'Not classified','officialUrl':official or ''})
 return INST[k]
def source(k,title,state,year=2025,url=None):
 u=url or DOWNLOADS[k]; SOURCES[k]={'id':'we-'+k,'title':title,'url':u,'year':year,'scope':state};return SOURCES[k]
def record(k,state,name,course,quota,cat,year=2025,round='Round 1',seats=None,op=None,cl=None,count=None,rank='NEET PG AIR',page=1,typ=None,**extra):
 src=SOURCES[k];i=institution(state,name,typ,src['url'])
 row={'id':'we-'+k+'-'+uid('|'.join(map(str,[i,course,quota,cat,page,len(D['records'])]))),'instituteId':i,'exam':'NEET PG','recordKind':'seat-matrix' if seats is not None else 'cutoff','counselling':state+' State Counselling','course':course,'quota':quota,'category':cat,'year':year,'round':round,'seats':seats,'openingRank':op,'closingRank':cl,'rankType':rank,'sourceUrl':src['url'],'sourceLabel':src['title'],'sourcePage':page,'dataStatus':'verified',**extra}
 if count is not None:row['allotmentCount']=count
 D['records'].append(row);return row
# Gujarat: category closing ranks from the authority's compiled closure; AIR column only.
source('gj-closure','Gujarat PG 2025 compiled institute-wise last ranks','Gujarat')
n=0
for pn,t in tables('gj-closure'):
 for r in t:
  if len(r)!=22 or ' - ' not in r[1]:continue
  n+=1;course,label,name=r[:3];quota=label.rsplit(' - ',1)[1]
  for cat,col in [('OPEN',4),('SC',7),('ST',11),('SEBC',15),('EWS',19)]:
   if num(r[col]) and num(r[col])<240000:
    record('gj-closure','Gujarat',name,course,quota,cat,round='Compiled last rank (all rounds)',cl=num(r[col]),page=pn)
AUDIT['gujaratClosure']={'sourceProgramQuotaRows':n,'rankBasis':'NEET AIR columns; general/category state merit columns not substituted','blankRanks':'Omitted; no inferred conversion'}
# Gujarat seat table: state GQ/MQ/NRI only; exclude AIQ duplication.
source('gj-seats','Gujarat PG MD/MS/Diploma seat list 2025-26','Gujarat')
total=0;prow=0
for pn,t in tables('gj-seats'):
 name=t[0][1]
 if name=='Total':continue
 for r in t[2:]:
  if len(r)!=8 or r[0]=='Total':continue
  if not r[0] or num(r[2]) is None:continue
  prow+=1
  for quota,c in [('GQ',4),('MQ',5),('NRI',6)]:
   if num(r[c]):total+=num(r[c]);record('gj-seats','Gujarat',name,r[0],quota,'All categories (aggregate)',seats=num(r[c]),page=pn,round='Published seat list')
AUDIT['gujaratSeats']={'sourceProgramRows':prow,'stateQuotaSeats':total,'excluded':'AIQ columns already represented through MCC; zero pools excluded'}
# Madhya Pradesh published opening/closing AIR, with home-state/institution subpools distinct.
source('mp-cutoffs-r2','MP 2025 Round 2 opening and closing ranks (24 December 2025)','Madhya Pradesh')
mpn=0;mpcount=0
for pn,t in tables('mp-cutoffs-r2'):
 for r in t:
  if len(r)!=15 or num(r[0]) is None:continue
  mpn+=1;mpcount+=num(r[13]) or 0
  record('mp-cutoffs-r2','Madhya Pradesh',r[1],r[3]+' '+r[4],('Institutional preference' if r[12].startswith('INST/') else 'State quota')+'; MBBS from MP: '+r[14],r[12],round='Round 2',op=num(r[6]),cl=num(r[7]),count=num(r[13]),page=pn,typ='Government' if r[2]=='Govt' else r[2],stateOpeningRank=num(r[8]),stateClosingRank=num(r[9]))
AUDIT['mpRound2']={'publishedPools':mpn,'allotments':mpcount,'rankBasis':'Explicit NEET PG All India Rank; state merit stored separately'}
# Bihar revised Round 1 opening/closing NEET ranks.
source('bihar-cutoffs-r1','Bihar PGMAC 2025 revised Round 1 opening and closing ranks','Bihar')
bn=0
for pn,t in tables('bihar-cutoffs-r1'):
 for r in t:
  if len(r)!=11 or num(r[5]) is None or num(r[6]) is None:continue
  bn+=1;course=r[0]+' · '+r[2]
  record('bihar-cutoffs-r1','Bihar',r[1],course,'State quota; '+r[4],r[3],op=num(r[5]),cl=num(r[6]),page=pn,program=r[0])
AUDIT['biharRound1']={'publishedPools':bn,'rankBasis':'NEET opening/closing rank, not UR/category state merit ranks'}
# Maharashtra Round 1 public selection rows, aggregated by published seat pool.
source('mh-allotment-r1','Maharashtra NEET PG 2025 Round 1 provisional selection list','Maharashtra')
pools={};mh=json.loads((RAW/'mh-allotment-r1-safe-rows.json').read_text())
for row in mh['rows']:
 name,course,cat,code=row['institute'],row['course'],row['category'],row['code']
 cat=re.sub(r'\s*\(EM[DR]\)','',cat).strip()
 q='Institutional quota' if code.endswith('I') else 'State quota'
 if row.get('inServiceFlag'):q+='; In-service '+('with incentive marks' if row['inServiceFlag']=='I' else 'without incentive marks')
 pk=(name,course,q,cat,code);g=pools.setdefault(pk,{'ranks':[],'pages':set()});g['ranks'].append(row['rank']);g['pages'].add(row['page'])
for (name,course,q,cat,code),g in pools.items():
 record('mh-allotment-r1','Maharashtra',name,course,q,cat,op=min(g['ranks']),cl=max(g['ranks']),count=len(g['ranks']),rank='State merit rank',page=min(g['pages']),sourceCode=code,notes='SML is Maharashtra state merit rank, not NEET All India Rank. Provisional selections, not admissions.')
AUDIT['maharashtraRound1']={'selectedRows':len(mh['rows']),'notAllocatedRows':mh['sourceRows']-len(mh['rows']),'sourceRows':mh['sourceRows'],'sourceLastSerial':mh['lastSerial'],'uniqueSourceSerials':mh['uniqueSerials'],'aggregatePools':len(pools),'rankBasis':'State merit list (SML); never AIR'}
# Goa 2026 state category distribution; PwD split preserves inclusive counts.
source('goa-2026-seats','Goa PG medical state seat distribution 2026-27','Goa',2026)
nt=0
for pn,t in tables('goa-2026-seats'):
 for r in t:
  if len(r)!=8 or num(r[0]) is None:continue
  for cat,cell in zip(['SC','ST','OBC','EWS','GEN'],r[3:]):
   if not re.search(r'\d',cell):continue
   parts=re.findall(r'(\d+)\s*(\(PwD\))?',cell,re.I)
   for v,pwd in parts:
    nt+=int(v);record('goa-2026-seats','Goa','Goa Medical College, Bambolim',r[1],'State quota',cat+(' PwD' if pwd else ''),year=2026,seats=int(v),page=pn,typ='Government',round='Published seat distribution')
AUDIT['goa2026']={'publishedSeats':72,'extractedSeats':nt,'sourceCourses':22}
# Jharkhand uses CML state ranks; only current allotment columns are read.
for k,rnd,ci,co,ca in [('jh-allotment-r2','Round 2',17,18,19),('jh-allotment-r3','Round 3',17,18,22),('jh-allotment-stray','Stray',14,15,17)]:
 source(k,'Jharkhand PG medical 2025 '+rnd+' provisional allotment','Jharkhand');pools={};nn=0
 for pn,t in tables(k):
  for r in t:
   if len(r)<=ca or num(r[0]) is None or num(r[12]) is None:continue
   if not r[ci] or not r[co]:continue
   pk=(r[ci],r[co],r[ca]);g=pools.setdefault(pk,{'ranks':[],'pages':set()});g['ranks'].append(num(r[12]));g['pages'].add(pn);nn+=1
 for (name,course,cat),g in pools.items():record(k,'Jharkhand',name,course,'State quota',cat,round=rnd,op=min(g['ranks']),cl=max(g['ranks']),count=len(g['ranks']),rank='State merit rank',page=min(g['pages']),notes='CML state rank is specific to this counselling round; cannot be compared with AIR or another round merit list.')
 AUDIT[k]={'allotments':nn,'pools':len(pools),'rankBasis':'Round-specific CML State merit rank'}
# Further official datasets and reviewed financial annotations are assembled below.
# Chhattisgarh revised combined R1+R2 supersedes the earlier cancelled rounds.
source('cg-allotment','Chhattisgarh PG 2025 combined Round 1 and 2 allotment (28 January 2026)','Chhattisgarh',url='https://drive.google.com/file/d/1KaNsNSdAC3DnFPzisjGqU8mgqpU2G9XJ/view')
pools={};sn=[]
for pn,t in tables('cg-allotment'):
 for r in t:
  if len(r)!=15 or num(r[0]) is None or num(r[12]) is None:continue
  sn.append(num(r[0]));pk=(r[5],r[6],r[8],r[9],r[10],r[14]);g=pools.setdefault(pk,{'ranks':[],'pages':set()});g['ranks'].append(num(r[12]));g['pages'].add(pn)
for (name,course,q,cat,gender,eligibility),g in pools.items():record('cg-allotment','Chhattisgarh',name,course,q+'; '+eligibility,cat+'; seat gender '+gender,round='Combined Round 1 and 2 (revised)',op=min(g['ranks']),cl=max(g['ranks']),count=len(g['ranks']),page=min(g['pages']))
AUDIT['cgCombinedRound12']={'allotmentRows':len(sn),'sourceLastSerial':max(sn),'uniqueSerials':len(set(sn)),'aggregatePools':len(pools),'supersedes':'Earlier 2025 Round 1 and Round 2 process cancelled by 22 January 2026 authority notice'}
source('cg-mopup','Chhattisgarh PG 2025 mop-up clear vacancies (7 February 2026)','Chhattisgarh',url='https://drive.google.com/file/d/1rZYwgD_CqoTeHcxSLkduNpQA2ZZ5mRG7/view')
v=0;rows=0
for pn,t in tables('cg-mopup'):
 for r in t:
  if len(r)!=6 or num(r[5]) is None or 'TOTAL' in r[0].upper():continue
  if not r[0] or not r[1]:continue
  v+=num(r[5]);rows+=1;record('cg-mopup','Chhattisgarh',r[0],r[1],r[2],r[3]+(' '+r[4] if r[4]!='NO' else ''),seats=num(r[5]),round='Mop-up clear vacancy snapshot',page=pn,notes='Historical clear vacancy on 7 February 2026 for 2025 counselling; not initial sanctioned capacity or a live vacancy.')
AUDIT['cgMopup']={'publishedPools':rows,'historicalClearVacancies':v}
# Financial entries are exact policy/institute scopes, never silently propagated nationwide.
def finance(k,state,title,scope,year=2025,institute=None,course=None,fee=None,stipend=None,bond=None,penalty=None,discontinuation=None,page=1,notes='',**extra):
 src=SOURCES[k];r={'id':'we-fin-'+uid('|'.join(map(str,[k,title,scope,institute,course,len(D['financials'])]))),'state':state,'instituteName':institute,'scope':scope,'title':title,'year':year,'course':course,'annualFee':fee,'monthlyStipend':stipend,'bondYears':bond,'bondPenalty':penalty,'discontinuationPenalty':discontinuation,'sourceUrl':src['url'],'sourcePage':page,'notes':notes,'dataStatus':'verified',**extra};D['financials'].append(r);return r
source('odisha-guide','Odisha PG medical counselling guidelines 2025','Odisha')
# Printed guideline page 88 is PDF page 12 (located by explicit fee heading).
opages=(RAW/'odisha-guide.txt').read_text().split('\f');opage=next(i for i,s in enumerate(opages,1) if 'Consolidated tuition fees' in s)
finance('odisha-guide','Odisha','Government PG tuition and discontinuation rules','Government medical colleges; PG medical degree/diploma',course='PG medical degree/diploma',fee=35000,discontinuation=1000000,page=opage,notes='Annual tuition only. Additional annual library ₹1,500 and journal ₹2,000; admission ₹3,000 and other one-time charges. Refundable security ₹15,000. Discontinuation also requires stipend/salary repayment; not a service-bond buyout. Private colleges excluded.')
source('goa-2026-rules','Goa PG admission rules 2026 (Gazette 29 May 2026)','Goa',2026)
gp=(RAW/'goa-2026-rules.txt').read_text().split('\f');gpage=next(i for i,s in enumerate(gp,1) if '64,324' in s)
finance('goa-2026-rules','Goa','Goa Medical College service obligation and term fees','Goa Medical College postgraduate degrees',year=2026,institute='Goa Medical College, Bambolim',course='MD/MS',bond=1,page=gpage,notes='Service if called by the government within six months of successful course completion. The 2026 rules quote ₹64,324 per term for 2025-26 with 5% annual escalation; no inferred 2026 annual total is shown. ₹10 lakh higher-study bank guarantee is not a service-bond penalty.',feePerTerm=64324,feeReferenceYear=2025)
source('goa-stipend','Goa Medical College stipend disclosure for FY 2023-24 (23 April 2024)','Goa',2023)
finance('goa-stipend','Goa','Clinical MD/MS stipend (historical disclosure)','Clinical MD/MS residents; FY 2023-24',year=2023,institute='Goa Medical College, Bambolim',course='Clinical MD/MS',stipend=60000,stipendByYear=[60000,62500,65000],notes='Historical paid monthly stipend disclosure for FY 2023-24, published April 2024; not a claim about 2026 pay. PG rows only; excludes UG and superspecialty rates.')
finance('goa-stipend','Goa','Pre/para-clinical PG stipend (historical disclosure)','Pre/para-clinical MD/MS and diploma residents; FY 2023-24',year=2023,institute='Goa Medical College, Bambolim',course='Pre/para-clinical MD/MS and diploma',stipend=60000,stipendByYear=[60000,60000,60000],notes='Historical paid monthly disclosure for FY 2023-24, published April 2024. Third-year figure only for degree courses; diplomas do not acquire a third year from this table.')
source('namo-fees-revised','NAMO Medical Education and Research Institute annual PG tuition 2025-26','Dadra and Nagar Haveli and Daman and Diu')
for course,fee in [('MD Anaesthesiology',1200000),('MD Community Medicine',700000),('MD Dermatology and Venereology',2500000),('MD General Medicine',2000000),('MS General Surgery',2000000),('MD Microbiology',700000),('MS Obstetrics and Gynaecology',2000000),('MS Ophthalmology',1500000),('MS Orthopaedics',2000000),('MD Paediatrics',2000000),('MD Pathology',700000),('MD Radio Diagnosis',2500000)]:
 finance('namo-fees-revised','Dadra and Nagar Haveli and Daman and Diu','NAMO annual PG tuition','Institute course fee schedule',institute='NAMO Medical Education and Research Institute, Silvassa',course=course,fee=fee,notes='Annual tuition only; admission ₹5,000 once, annual library ₹2,000, annual hostel ₹4,000 and refundable security ₹1 lakh separately. University, examination, mess and welfare charges additional.')
source('wb-fees','West Bengal private PG fee fixation order (3 December 2025)','West Bengal')
for name,scope,sq,mq,page in [('Gouridevi Medical College, Durgapur','MD/MS',900000,2700000,1),('Shri Ramkrishna Institute of Medical Sciences and Sanaka Hospital, Durgapur','MD/MS',900000,2700000,1),('IQ City Medical College','Non-clinical MD/MS',216000,640000,1),('IQ City Medical College','Clinical MD/MS',900000,2700000,1),('KPC Medical College, Jadavpur','MD/MS',850000,2700000,1),('ICARE Institute of Medical Science and Research and Dr BC Roy Hospital, Haldia','Clinical MD/MS',900000,2700000,2),('ICARE Institute of Medical Science and Research and Dr BC Roy Hospital, Haldia','Non-clinical MD/MS',390000,1550000,2),('Jagannath Gupta Institute of Medical Sciences and Hospital','MD/MS',900000,2700000,2)]:
 for quota,fee in [('State quota',sq),('Management quota',mq)]:finance('wb-fees','West Bengal',name+' — '+quota,scope+'; '+quota,institute=name,course=scope,fee=fee,page=page,quota=quota,notes='Per-year fee approved by the Permanent Fee Fixation Committee. Clinical/non-clinical and quota scope preserved. This order does not establish stipend or bond amounts.')
source('cg-fees','Chhattisgarh private PG interim annual fee order (23 September 2025)','Chhattisgarh',url='https://drive.google.com/file/d/15tKBNGU0FZAqHkw-Kuj7SZlsng7eUfNP/view')
for name,clinical,other in [('Shri Shankaracharya Institute of Medical Sciences, Bhilai',1054000,848200),('Raipur Institute of Medical Sciences, Raipur',984500,792600),('Shri Balaji Institute of Medical Sciences, Raipur',1054000,848200)]:
 for scope,fee in [('Clinical MD/MS',clinical),('Pre-clinical/para-clinical MD/MS',other)]:finance('cg-fees','Chhattisgarh',name+' — interim annual fee',scope,institute=name,course=scope,fee=fee,notes='Interim per-year per-student fee inclusive of growth/development, weightage and miscellaneous fee, stated for 2024-25, 2025-26 and 2026-27. Subject to the order and underlying fee-regulator conditions.',validAcademicYears=['2024-25','2025-26','2026-27'])
source('mh-nagpur-finance','GMC Nagpur PG admission proforma and fee/bond schedule 2025-26','Maharashtra')
finance('mh-nagpur-finance','Maharashtra','GMC Nagpur MD/MS tuition and service bond','GMC Nagpur non-in-service MD/MS admissions; AIQ and Maharashtra quota',institute='Government Medical College, Nagpur',course='MD/MS',fee=152100,bond=1,penalty=5000000,page=10,notes='2025-26 tuition ₹1,52,100; additional fees and deposits listed on PDF page 10. One-year service and ₹50 lakh default amount on PDF page 8. In-service candidates have a separate fee arrangement. No numeric discontinuation penalty or stipend inferred.')
source('gj-bjmc-correct','BJ Medical College Ahmedabad joining instructions (19 November 2025)','Gujarat')
finance('gj-bjmc-correct','Gujarat','BJMC first-year government fee, stipend and service bond','MD/MS; excluding listed bond-exempt specialties',institute='B. J. Medical college, Ahmedabad',course='MD/MS (bond exemptions in notes)',fee=30000,stipend=100800,bond=1,penalty=4000000,page=1,notes='First-year government fee ₹30,000 plus separately refundable ₹1,00,800 deposit (one month stipend). Additional university fees. Service bond applies AIQ and state; Anatomy, Physiology, Biochemistry, Community Medicine, Forensic Medicine and Pharmacology are exempt. Institution notice currently indexed but direct PDF fetch returned 404 on check; re-confirm before payment.',feeBasis='First-year government fee',sourceAvailability='Indexed official document; direct fetch returned 404')
# Readable source tables with ambiguous annual/deposit basis are linked, not normalized into annual fees.
source('gj-fees','Gujarat PG MD/MS/Diploma official fee details 2025-26','Gujarat')
AUDIT['gujaratFeeCaution']='Authority table headed TUTION FEE includes ₹130800 at BJMC where institute notice separates ₹30000 fee + ₹100800 refundable caution. Not imported as annual tuition without resolving basis.'
REGISTRY=[
 ('Maharashtra','State Common Entrance Test Cell, Maharashtra','https://medicalug2025.mahacet.org/NEET-PGM-2025/login','Historical Round 1 state-merit cutoff aggregates. GMC Nagpur fee/bond disclosure only; full state matrix and financial coverage incomplete.',['mh-allotment-r1','mh-nagpur-finance']),
 ('Gujarat','ACPPGMEC, Government of Gujarat','https://medadmgujarat.org/pg/Home.aspx','2025 state seat list and all-round compiled AIR closure imported. Current portal has 2026 registration information; 2026 state matrix not acquired. Published fee table linked; fee/deposit basis unresolved outside reviewed BJMC notice.',['gj-closure','gj-seats','gj-fees','gj-bjmc-correct']),
 ('Goa','Directorate of Technical Education, Government of Goa','https://dte.goa.gov.in/pg-medical-admissions-0','2026 state seat matrix (72 seats) and 2026 rules imported. Stipend disclosure is explicitly historical FY 2023-24, not current 2026 pay.',['goa-2026-seats','goa-2026-rules','goa-stipend']),
 ('Rajasthan','Office of the Chairman, NEET PG Counselling Board, SMS Medical College Jaipur','https://rajpgneet2025.in/','Official 2025 portal identified but direct source acquisition returned HTTP 503. The indexed static booklet contained 2024 rules and was rejected as 2025 evidence. State datasets and financial figures remain incomplete. Private fee notices flag ongoing court proceedings; do not infer final fees.',[]),
 ('Madhya Pradesh','Directorate of Medical Education, Madhya Pradesh','https://dme.mponline.gov.in/Portal/Services/DMEMP/DMEPG/Profile/ProfileLoginHome.aspx','2025 Round 2 official opening/closing AIR pools imported. Other rounds, initial state seat matrices and full financial data remain incomplete.',['mp-cutoffs-r2']),
 ('Chhattisgarh','Commissionerate of Medical Education, Chhattisgarh','https://cgdme.in/MD-MS-DIPLOMA.php','Revised combined Round 1+2 AIR allotments and historical mop-up clear vacancy matrix imported for 2025. Earlier cancelled rounds excluded. Interim private MD/MS annual fees cover three institutions.',['cg-allotment','cg-mopup','cg-fees']),
 ('Bihar','Bihar Combined Entrance Competitive Examination Board','https://bceceboard.bihar.gov.in/','2025 revised Round 1 opening/closing NEET rank pools imported. Other rounds, initial matrix and financial coverage incomplete.',['bihar-cutoffs-r1']),
 ('Jharkhand','Jharkhand Combined Entrance Competitive Examination Board','https://jceceb.jharkhand.gov.in/Links/download.aspx','2025 Round 2, Round 3 and stray current allotments aggregated by round-specific CML state merit rank. These are not AIR. Financial and initial seat-matrix coverage incomplete.',['jh-allotment-r2','jh-allotment-r3','jh-allotment-stray']),
 ('Odisha','Directorate of Medical Education and Training, Odisha','http://dmetodisha.gov.in/PG%202025.html','2025 government tuition and discontinuation policy imported with original scope. Service-bond document linked. State allotment/matrix and current numeric stipend coverage incomplete.',['odisha-guide']),
 ('West Bengal','West Bengal Medical Counselling Committee','https://wbmcc.nic.in/pg-medical-counselling/pgmedical-archive-2025/','2025 private annual fee order imported: six colleges, quota-specific and clinical/non-clinical rates. Full state allotment and seat-matrix coverage incomplete.',['wb-fees']),
 ('Dadra and Nagar Haveli and Daman and Diu','NAMO Medical Education and Research Institute, UT Administration','https://namomeri.in/fees-stucture.html','2025 NAMO annual PG course tuition imported for twelve specialties. State counselling matrix, cutoffs, numeric stipend and bond coverage incomplete.',['namo-fees-revised'])]
for name,authority,url,note,keys in REGISTRY:
 docs=[{'title':SOURCES[k]['title'],'url':SOURCES[k]['url'],'year':SOURCES[k]['year'],'kind':'financial-policy' if k in ['mh-nagpur-finance','gj-fees','gj-bjmc-correct','goa-stipend','namo-fees-revised','wb-fees','cg-fees'] else 'seat-matrix' if 'seats' in k or 'mopup' in k else 'cutoffs' if any(z in k for z in ['cutoffs','allotment','closure']) else 'prospectus'} for k in keys]
 if name=='Rajasthan':docs=[{'title':'Rajasthan NEET PG 2025 official notification board (acquisition unavailable)','url':url,'year':2025,'kind':'official-notice-board'}]
 if name=='Odisha':docs.append({'title':'Odisha modified PG/SS service bond order (9 December 2021), linked by 2025 authority','url':DOWNLOADS['odisha-bond'],'year':2021,'kind':'bond-policy'})
 if name=='West Bengal':docs.append({'title':'WB PG medical 2025 information bulletin','url':DOWNLOADS['wb-bulletin'],'year':2025,'kind':'prospectus'})
 D['states'].append({'name':name,'authority':authority,'authorityUrl':url,'coverageNote':note,'status':'partial' if keys else 'source-unavailable','documents':docs})
D['sources']=list(SOURCES.values())
D['summary']={'states':len(D['states']),'institutes':len(D['institutes']),'records':len(D['records']),'financialEntries':len(D['financials']),'sourceCount':len(D['sources']),'coverage':'Partial, explicitly dated official-source coverage; not all states or all institutions complete.','stateRecords':dict(collections.Counter(next(i['state'] for i in D['institutes'] if i['id']==r['instituteId']) for r in D['records'])),'acquisitionReconciliation':AUDIT}
(BASE.parent/'west-east.json').write_text(json.dumps(D,ensure_ascii=False,indent=2))
(BASE/'summary.json').write_text(json.dumps(D['summary'],ensure_ascii=False,indent=2))
print(json.dumps(D['summary'],indent=2))
