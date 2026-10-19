"""Compile aggregate NEET PG southern data. Run: uv run --with pymupdf python sources/regions/south/build.py.
No candidate identifiers leave raw source files. Null means unreported, never zero.
"""
from pathlib import Path
import json,re,hashlib,collections
import pymupdf as fitz
ROOT=Path(__file__).parent
RAW=ROOT/'raw'
URLS=json.loads((RAW/'downloads.json').read_text())
OUT={'region':'South','checkedAt':'2026-10-19','states':[],'institutes':[],'records':[],'financials':[],'sources':[],'summary':{}}
inst={}; audit={}
def clean(x):return ' '.join((x or '').split())
def ident(*x):return hashlib.sha256('|'.join(map(str,x)).encode()).hexdigest()[:16]
def institution(code,name,state,typ=None):
 id='state-'+state.lower().replace(' ','-')+'-'+code.lower()
 if id not in inst:inst[id]={'id':id,'name':clean(name),'state':state,'city':None,'type':typ,'officialUrl':None}
 return id

def source(key,title,state,kind='policy',year=2025):
 s={'id':'south-'+key,'title':title,'url':URLS[key],'year':year,'scope':state,'kind':kind};OUT['sources'].append(s);return s

def rec(i,course,quota,cat,source,page,kind='seat-matrix',seats=None,opening=None,closing=None,round='Published matrix',count=None,rankType='NEET PG AIR',**extra):
 r={'id':'south-'+ident(i,course,quota,cat,source['id'],round),'instituteId':i,'exam':'NEET PG','recordKind':kind,'counselling':{'Kerala':'Kerala CEE','Karnataka':'Karnataka KEA','Andhra Pradesh':'Andhra Pradesh Dr NTRUHS','Andaman and Nicobar Islands':'ANIIMS UT counselling'}.get(inst[i]['state'],inst[i]['state']+' state counselling'),'course':clean(course),'quota':quota,'category':cat,'year':source['year'],'round':round,'seats':seats,'openingRank':opening,'closingRank':closing,'rankType':rankType,'sourceUrl':source['url'],'sourceLabel':source['title'],'sourcePage':page,'dataStatus':'verified',**extra}
 if count is not None:r['allotmentCount']=count
 OUT['records'].append(r)

def fin(state,title,scope,src,page,**kw):
 f={'id':'south-fin-'+ident(title,scope,kw.get('instituteName'),kw.get('course'),kw.get('quota')),'state':state,'scope':scope,'title':title,'year':src['year'],'annualFee':None,'monthlyStipend':None,'bondYears':None,'bondPenalty':None,'discontinuationPenalty':None,'sourceUrl':src['url'],'sourcePage':page,'notes':'',**kw};OUT['financials'].append(f)

def tables(key):
 for p in fitz.open(RAW/(key+'.pdf')):
  for t in p.find_tables().tables:
   yield p.number+1,t.extract()

# Kerala base category matrix: numeric cells only; dash means not offered and is omitted.
s=source('kerala-seats','Kerala CEE 2025 category-wise seat distribution, excluding in-service/minority/NRI','Kerala','seat-matrix')
current=None;headers=[];source_rows=0;seat_total=0
for pg,rows in tables('kerala-seats'):
 for r in rows:
  r=[clean(x) for x in r]
  if re.match(r'^[A-Z]{3}:',r[0]):
   code,name=r[0].split(':',1);current=institution(code,name,'Kerala','Government' if 'Govt.' in name else None)
  elif r[0]=='Course':headers=r
  elif '[' in r[0] and current:
   source_rows+=1;values=[int(x) if x.isdigit() else 0 for x in r[2:]]
   if int(r[1])!=sum(values):raise ValueError(('Kerala row reconciliation',pg,r))
   seat_total+=int(r[1])
   for cat,value in zip(headers[2:],r[2:]):
    if value.isdigit():rec(current,re.sub(r'\[[^]]+\]','',r[0]),'State quota (non-service)',cat,s,pg,seats=int(value))
audit['keralaSeatMatrix']={'sourceCourseRows':source_rows,'seats':seat_total,'categoryRows':len(OUT['records'])}

# Karnataka official yearly fee schedule. N/A is omitted and never interpreted as zero fee.
s=source('karnataka-fees','KEA provisional college/course/seat-quota annual fees 2025-26','Karnataka','fee')
current=None;fee_course_rows=0;fee_cells=0
qnames=['Government (G)','Private (P)','Other (Q)','NRI (N)']
for pg,rows in tables('karnataka-fees'):
 for row in rows:
  r=[clean(x) for x in row]
  m=re.match(r'^(M\d+)\s*-\s*(.*)',r[0])
  if m:
   name=re.sub(r'\(.*?College\)\s*$','',m[2]).strip();current=institution(m[1],name,'Karnataka','Government' if 'Government' in m[2] else 'Private')
  elif re.match(r'^[A-Z][A-Z0-9]-',r[0]) and len(r)==5:
   fee_course_rows+=1;course=r[0].split('-',1)[1].strip()
   for q,v in zip(qnames,r[1:]):
    if v.isdigit():
     fee_cells+=1;fin('Karnataka','KEA published annual course fee',f'{q} seat, institution and course shown',s,pg,instituteName=inst[current]['name'],instituteId=current,course=course,quota=q,annualFee=int(v),notes='Provisional 2025-26 schedule. Amount is per one year and includes RGUHS/other university registration fees; it is not a pure tuition-only quote. N/A cells were omitted. Hostel and other unpublished costs are not included.')
audit['karnatakaFees']={'courseRows':fee_course_rows,'numericFeeCells':fee_cells}

# Karnataka round 3 only fresh Allotted/Upgraded events; carried-forward rows are explicitly excluded.
s=source('karnataka-allotment','KEA NEET PG 2025 non-service round 3 FINAL allotment, 26 February 2026','Karnataka','cutoff')
groups={};status=collections.Counter();serials=set()
for pg,rows in tables('karnataka-allotment'):
 for row in rows:
  r=[clean(x) for x in row]
  if not r[0].isdigit():continue
  serials.add(int(r[0]));status[r[-1]]+=1
  if r[-1] not in ['Allotted','Upgraded']:continue
  code=r[2];m=re.match(r'^(M\d+)([GPQN])(.+)$',code)
  if not m or not r[1].isdigit():raise ValueError(('KEA invalid allotment',pg,r))
  i=institution(m[1],r[3],'Karnataka');quota=dict(zip('GPQN',qnames))[m[2]];key=(i,r[4],quota,r[5]);g=groups.setdefault(key,{'ranks':[],'pages':[]});g['ranks'].append(int(r[1]));g['pages'].append(pg)
for (i,c,q,cat),g in groups.items():rec(i,c,q,cat,s,f"{min(g['pages'])}-{max(g['pages'])}",kind='cutoff',opening=min(g['ranks']),closing=max(g['ranks']),round='Round 3',count=len(g['ranks']),notes='Only fresh Allotted and Upgraded rows included. Not Upgraded rows were excluded.')
if serials!=set(range(1,max(serials)+1)):raise ValueError('KEA missing serials')
audit['karnatakaRound3']={'sourceRows':len(serials),'sourceStatusCounts':dict(status),'freshAllotments':sum(len(g['ranks']) for g in groups.values()),'cutoffPools':len(groups)}

# AP phase 1 management allotments. Group on allotted subquota, NOT candidate caste category.
s=source('ap-mq-r1','Dr NTRUHS AP 2025 management quota Phase I final allotments, 10 December 2025','Andhra Pradesh','cutoff')
groups={};name=None;n=0
for pg,rows in tables('ap-mq-r1'):
 for row in rows:
  r=[clean(x) for x in row]
  if r[0] and sum(bool(x) for x in r)==1 and not r[0].isdigit():name=r[0]
  if not r[0].isdigit():continue
  if len(r)<12 or not r[1].isdigit():raise ValueError(('AP invalid row',pg,r))
  m=re.match(r'^([A-Z]+)\s*-\s*(.*?)\s*-\s*(S1A|S1B|S2|S3)',r[9])
  if not m:raise ValueError(('AP quota parse',pg,r[9]))
  i=institution(m[1],name,'Andhra Pradesh');q={'S1A':'Management S1A','S1B':'Management S1B','S2':'NRI S2','S3':'Institutional S3'}[m[3]];key=(i,r[10],q);g=groups.setdefault(key,{'ranks':[],'pages':[]});g['ranks'].append(int(r[1]));g['pages'].append(pg);n+=1
for (i,c,q),g in groups.items():rec(i,c,q,'Management quota - no caste reservation',s,f"{min(g['pages'])}-{max(g['pages'])}",kind='cutoff',opening=min(g['ranks']),closing=max(g['ranks']),round='Round 1',count=len(g['ranks']))
audit['apManagementRound1']={'allotmentRows':n,'cutoffPools':len(groups)}

# ANIIMS UT-specific matrix. AIQ columns omitted here to avoid duplication with MCC.
s=source('aniims-prospectus','ANIIMS PG prospectus 2025-26','Andaman and Nicobar Islands','prospectus')
i=institution('aniims','Andaman and Nicobar Islands Institute of Medical Sciences (ANIIMS)','Andaman and Nicobar Islands','Government')
for course in ['MD Anatomy','MD Biochemistry','MD Microbiology','MD Anaesthesiology','MS General Surgery','MS Ophthalmology']:
 rec(i,course,'UT state quota','Combined local merit (categories I, IIIA, IIIB, IV)',s,3,seats=1)
for course in ['DNB General Medicine','DNB Obstetrics & Gynaecology','DNB Paediatrics']:rec(i,course,'In-service','Eligible A&N Administration service doctors',s,3,seats=1)
fin('Andaman and Nicobar Islands','ANIIMS MD/MS annual charges, stipend and service bond','ANIIMS MD/MS; state and AIQ admissions',s,'3,6',instituteName=inst[i]['name'],instituteId=i,program='MD/MS',annualFee=110000,monthlyStipend=87000,stipendByYear=[87000,88000,89000],bondYears=1,bondPenalty=1000000,notes='Annual academic fee 33,000 + learning resource fee 44,000 + establishment charges 33,000. First admission additionally 50,000 admission fee and 25,000 refundable college deposit. Hostel 4,000/month deducted from stipend, plus refundable 10,000 deposit. Service-default penalty additionally recovers stipend drawn, per page 6.')
fin('Andaman and Nicobar Islands','ANIIMS DNB fees and stipend','ANIIMS post-MBBS DNB in-service seats',s,'3-4',instituteName=inst[i]['name'],instituteId=i,program='DNB',annualFee=125000,monthlyStipend=87000,stipendByYear=[87000,88000,89000],bondYears=10,notes='DNB in-service candidates must serve A&N Administration for at least 10 years after completion (page 4). Additional 20,000/month is payable during postings at Apollo Hospital Chennai. MD/MS 1-year bond must not be substituted for this service condition; DNB default amount unreported here.')
audit['aniimsUTSeats']={'mdms':6,'dnbInService':3,'aiqExcluded':True}

# Narrow current AP institute policies; do not apply SVIMS figures to all AP colleges.
s=source('ap-cq-2026','Dr NTRUHS competent authority quota prospectus 2026-27','Andhra Pradesh','prospectus',2026)
fin('Andhra Pradesh','SVIMS MD/MS fees, stipend and service bond','SVIMS MD/MS except separately specified MS Orthopaedics/BIRRD',s,'50,52,55',instituteName='Sri Venkateswara Institute of Medical Sciences (SVIMS), Tirupati',program='MD/MS',annualFee=175000,monthlyStipend=96951,stipendByYear=[96951,99722,102493],bondYears=1,bondPenalty=4000000,discontinuationPenalty=500000,notes='Tuition 175,000/year; annual library fee 5,000 additional. University fee 25,600 and other admission charges separate. Discontinuation additionally repays stipend. In-service candidates drawing leave salary do not receive stipend. Figures for MS Orthopaedics are separately specified.')
fin('Andhra Pradesh','SVIMS/BIRRD MS Orthopaedics fees and stipend','MS Orthopaedics at BIRRD academically attached to SVIMS',s,56,instituteName='SVIMS / BIRRD Hospital, Tirupati',course='MS Orthopaedics',annualFee=30000,monthlyStipend=60823,stipendByYear=[60823,61528,64767],bondYears=1,bondPenalty=4000000,discontinuationPenalty=500000,notes='Tuition 30,000/year and one-time University fee 25,600. Prospectus states all other training regulations same as other PGs; SVIMS service/discontinuation conditions apply, including stipend recovery on discontinuation.')

# Telangana management allotments: parse only course/college headers and anonymous rank/quota fields.
s=source('telangana-r1','KNRUHS 2025 management quota first phase college-wise allotments, 19 January 2026','Telangana','cutoff')
groups={};colleges={};courses={};i=None;course=None;row_count=0
for pg,body in enumerate((RAW/'telangana-r1.txt').read_text().split('\f'),1):
 for line in body.splitlines():
  m=re.search(r'COLL ::\s*(\w+)\(\d+\)\s*-\s*(.*)',line)
  if m:colleges[m[1]]=clean(m[2]);i=institution(m[1],m[2],'Telangana','Private');continue
  m=re.search(r'CRS ::\s*(\w+)\s*\(\d+\)\s*-\s*(.*)',line)
  if m:course=clean(m[2].replace('_',' '));courses[m[1]]=course;continue
  m=re.match(r'^\s*(\d+)\s+\d{11}\s+\d+.*\s(MQ[123])-(\S+)-P1\s*$',line)
  if m:
   row_count+=1;key=(i,course,m[2],m[3]);g=groups.setdefault(key,{'ranks':[],'pages':[]});g['ranks'].append(int(m[1]));g['pages'].append(pg)
for (i,c,q,cat),g in groups.items():rec(i,c,q,cat,s,f"{min(g['pages'])}-{max(g['pages'])}",kind='cutoff',opening=min(g['ranks']),closing=max(g['ranks']),round='Round 1',count=len(g['ranks']),notes='Ranks from first-phase KNRUHS management allotments; allotted subquota/local status retained. Candidate caste was not used as the allotment category.')
expected=sum(1 for l in (RAW/'telangana-r1.txt').read_text().splitlines() if re.match(r'^\s*\d+\s+\d{11}\s+',l))
if expected!=row_count:raise ValueError(('Telangana rank parsing incomplete',expected,row_count))
audit['telanganaManagementRound1']={'allotmentRows':row_count,'cutoffPools':len(groups)}
# Explicit institution codes join matrices to names in the same authority's allotments.
colleges['NEELIMA']='Neelima Institute of Medical Sciences'
for key,title in [('telangana-mq-seats','non-minority colleges'),('telangana-mq-minority','minority colleges'),('telangana-mq-neelima','Neelima Institute of Medical Sciences')]:
 s=source(key,'KNRUHS 2025 management quota seat matrix: '+title,'Telangana','seat-matrix');total=0;cells=0;zeros=0
 for pg,rows in tables(key):
  codes=[];quotas=[]
  for row in rows:
   r=[clean(x) for x in row]
   if r[0]=='Course':
    code=None;codes=[]
    for h in r[1:]:
     if h:code=h.split()[0]
     codes.append(code)
   elif not r[0] and len(r)>1 and r[1].startswith('MQ'):quotas=r[1:]
   elif r[0] in courses or (codes and re.fullmatch(r'[A-Z]+',r[0]) and r[0]!='TOTAL'):
    for code,q,v in zip(codes,quotas,r[1:]):
     if v=='0':zeros+=1
     if v.isdigit() and int(v)>0:
      i=institution(code,colleges.get(code,'KNRUHS college code '+code),'Telangana','Private');rec(i,courses.get(r[0],r[0]),q,'Management '+('minority' if key=='telangana-mq-minority' else 'non-minority'),s,pg,seats=int(v),notes='Positive published seat cells only; explicit zero cells omitted. Matrix is a snapshot, not current vacancies.');total+=int(v);cells+=1
 audit[key]={'positiveSeatCells':cells,'seats':total,'explicitZeroCellsOmitted':zeros}
# Competent-authority course matrices: first page is the net aggregate and is excluded from output.
# Reconciliation is per course against that net page. Diploma course pages (DO, DTCD, DPH)
# are published in the same PDFs but are not part of the net-group page, so they are
# tallied separately. Some college rows merge the serial number into the name cell
# (e.g. 'TRR INSTITUTE OF MEDICAL 29 SCIENCES'); those rows are recovered, not skipped.
def cqkey(name):return re.sub(r'^(MD|MS|ME)\s+','',clean(name).upper()).replace(' ','')
for key,title in [('telangana-cq-clinical','clinical'),('telangana-cq-nonclinical','non-clinical')]:
 s=source(key,'KNRUHS 2025 non-minority non-service '+title+' competent authority quota seats','Telangana','seat-matrix');total=0;cells=0;net={};detail={};diploma={}
 for pg,rows in tables(key):
  rows=[[clean(x) for x in row] for row in rows]
  if pg==1:
   for r in rows[6:]:
    if r[0].isdigit():net[cqkey(r[1])]=sum(int(v) for v in r[2:] if v.isdigit())
   continue
  course=clean(rows[4][0]).replace(' (NON-SERVICE)','');headers=rows[5]
  bucket=detail if cqkey(course) in net else diploma
  for r in rows[6:]:
   if r[0].isdigit():name=r[1]
   elif r[0] and not r[1] and any(v.isdigit() for v in r[2:]):name=clean(re.sub(r'\s\d{1,3}(?=\s|$)',' ',r[0],count=1))
   else:continue
   i=institution('cq-'+ident(name),name,'Telangana')
   for cat,v in zip(headers[2:],r[2:]):
    if v.isdigit() and int(v)>0:rec(i,course,'Competent authority (non-service)',cat,s,pg,seats=int(v),notes='Source category codes retained: G denotes general allocation, F female reservation, PH disability. Net group summary page excluded.');total+=int(v);cells+=1;bucket[cqkey(course)]=bucket.get(cqkey(course),0)+int(v)
 if detail!=net:raise ValueError(('Telangana matrix reconciliation',key,{c:(net.get(c),detail.get(c)) for c in set(net)|set(detail) if net.get(c)!=detail.get(c)}))
 audit[key]={'seats':total,'netGroupSummarySeats':sum(net.values()),'positiveSeatCells':cells,'diplomaSeatsNotInNetGroup':sum(diploma.values()),'diplomaCourses':sorted(diploma)}
s=source('telangana-prospectus-2026','KNRUHS competent authority quota prospectus 2026-27','Telangana','prospectus',2026)
for program,penalty in [('MD/MS',2000000),('PG Diploma',1000000)]:
 fin('Telangana','KNRUHS '+program+' service and discontinuation conditions','Competent authority quota; non-service candidates',s,'21-22',program=program,quota='Competent authority',bondYears=1,bondPenalty=penalty,discontinuationPenalty=5000000,notes='Government service for one year if required by Telangana. In-service candidates excluded from this service condition. Discontinuation additionally recovers stipend/salary; after free exit, counselling debarment is three years. University admission payment 35,000 is one-time and not annual tuition. Tuition and stipend amounts not specified here.')

# CENTAC first-round ADMITTED snapshot, distinct from a final allotment result.
s=source('puducherry-r1','CENTAC 2025 first-round admitted list, 15 December 2025','Puducherry','cutoff');groups={};total=0;page_counts=[]
for pg,body in enumerate((RAW/'puducherry-r1.txt').read_text().split('\f'),1):
 header=re.search(r'([^\n]+QUOTA[^\n]*?)\s*-\s*\[\s*([^]]+)\]',body)
 if not header:continue
 quota=clean(header[1]);name=clean(header[2]);i=institution('centac-'+ident(name),name,'Puducherry','Government' if 'INDIRA GANDHI' in name else 'Private');serials=[]
 for line in body.splitlines():
  m=re.match(r'^\s*(\d+)\s+\d{8}\s+.+?\s+\d{11}\s+\d+\s+(\d+)\s+(\S+)\s+(\S+)\s+(.+?)\s+FIRST\s*$',line)
  if not m:continue
  serials.append(int(m[1]));rank=int(m[2]);cat=m[4];course=clean(m[5]);total+=1
  if course.startswith('TB/RESPIRATORY'):course='Respiratory Medicine'
  key=(i,course,quota,cat);g=groups.setdefault(key,{'ranks':[],'pages':[]});g['ranks'].append(rank);g['pages'].append(pg)
 expected=sum(1 for l in body.splitlines() if re.match(r'^\s*\d+\s+\d{8}\s+',l))
 if len(serials)!=expected:raise ValueError(('CENTAC incomplete lines',pg,len(serials),expected))
 page_counts.append({'page':pg,'admittedRows':len(serials)})
for (i,c,q,cat),g in groups.items():rec(i,c,q,cat,s,f"{min(g['pages'])}-{max(g['pages'])}",kind='cutoff',opening=min(g['ranks']),closing=max(g['ranks']),round='Round 1 admitted snapshot',count=len(g['ranks']),notes='AIR range among candidates recorded as admitted in first round. This is not the closing rank of every seat offered in that round; withdrawals/non-joining can change the range.')
audit['puducherryRound1Admitted']={'admittedRows':total,'cutoffPools':len(groups),'pages':page_counts}

# AP 2026 current tuition orders as reproduced in the current university prospectuses.
s=next(x for x in OUT['sources'] if x['id']=='south-ap-cq-2026')
for group,fee in [('Clinical',571320),('Para-clinical',178538),('Pre-clinical',80937)]:
 fin('Andhra Pradesh','AP 2026 private college competent authority tuition','Private unaided medical colleges, Category A competent authority seats',s,17,course=group,quota='Category A (CQ)',annualFee=fee,notes='2026-27 tuition as G.O.Rt.No.786 dated 29 August 2026; subject to W.P.32975,33162,35090 of 2022. Other admission/hostel charges not included.')
for city in ['Eluru','Machilipatnam','Nandyal','Rajahmundry','Vizianagaram']:
 for q,fee in [('AIQ',30000),('Competent authority general',30000),('Competent authority self-financing',900000),('Competent authority NRI',2900000)]:
  fin('Andhra Pradesh','AP newer government medical colleges annual tuition','Only the five government colleges expressly listed in section 9.2',s,17,instituteName='Government Medical College, '+city,program='MD/MS',quota=q,annualFee=fee,notes='2026-27 prospectus reproduces G.O.Ms.No.163 and 164, dated 5 December 2025; subject to pending writ proceedings. Does not establish the fee for every AP government college.')
s=source('ap-mq-2026','Dr NTRUHS management quota prospectus 2026-27','Andhra Pradesh','prospectus',2026)
for quota,values in [('Category B management',[1142640,357075,161874]),('Category C NRI/institutional',[6612500,1983750,1058000])]:
 for group,fee in zip(['Clinical','Para-clinical','Pre-clinical'],values):
  fin('Andhra Pradesh','AP 2026 private management tuition','Private unaided medical colleges; management quota category shown',s,17,course=group,quota=quota,annualFee=fee,notes='2026-27 tuition as notified in the management prospectus. Subject to the writ-petition conditions stated in the prospectus. Amount is not a whole-course or hostel-inclusive quote.')

# Kerala annual tuition and service conditions have deliberately different scopes.
s=source('kerala-prospectus','Kerala CEE PG medical prospectus 2025-26','Kerala','prospectus')
fin('Kerala','Kerala government PG tuition and fees','Government medical colleges, MD/MS',s,5,program='MD/MS',annualFee=57890,notes='Tuition per annum 57,890. Additional annual miscellaneous fee 11,580; refundable caution deposit 11,580 and university charges are separate. Prospectus academic year 2025-26; no unverified statewide stipend amount added.')
fin('Kerala','Kerala government medical college non-service bond','General-merit/non-service PG admission to government medical colleges, including AIQ',s,'34-35,72-74',program='MD/MS',bondYears=1,bondPenalty=5000000,discontinuationPenalty=5000000,notes='One year government service. Bond default and discontinuation are separate obligations; recoverable stipend/government study costs and applicable interest may be additional under the bond. Private college students are not automatically assigned this government-college service rule.')
fin('Kerala','Kerala government medical college in-service bond','Government medical colleges, service quota',s,'34-35,72-74',program='MD/MS',quota='In-service',bondYears=10,bondPenalty=5000000,discontinuationPenalty=5000000,notes='Ten years or until superannuation; two years in difficult/remote areas immediately after completion. Bond additionally provides government study cost/stipend or salary recovery as applicable. Not the one-year non-service rule.')
s=source('kerala-fees-govt','Kerala G.O.(Ms)355/2025 tuition order, 18 October 2025','Kerala','fee')
fee_colleges=[('MES Medical College, Perinthalmanna',1,False),('Malabar Medical College Hospital and Research Centre, Ulliyeri',2,False),('Sree Narayana Institute of Medical Sciences, Chalakka',2,True),('Sree Gokulam Medical College and Research Foundation, Venjaramoodu',2,True),('Mount Zion Medical College, Adoor',2,False),('KMCT Medical College, Manassery',2,False),('Travancore Medical College, Mylapore',2,False),("Dr. Moopen’s Medical College, Meppadi",2,False),('Azeezia Institute of Medical Sciences and Research, Meeyannoor',2,False),('Dr. Somervell Memorial CSI Medical College, Thiruvananthapuram',2,False),('Al Azhar Medical College and Super Specialty Hospital, Thodupuzha',3,False)]
for name,page,reduced in fee_colleges:
 for c,q,f in [('Clinical','85% merit',1836456 if reduced else 1942235),('Non-clinical','85% merit',1114992 if reduced else 1179215),('MD/MS','15% NRI',4081014)]:
  fin('Kerala','Kerala 2025 self-financing PG tuition','Named institution and quota only',s,page,instituteName=name,course=c,quota=q,annualFee=f,notes='Fee fixed for academic year 2025-26 by G.O.(Ms)355/2025. Super-specialty column excluded. Tuition is not hostel-inclusive. Scanned order values were read against page images.')
s=source('kerala-fees-private','Kerala G.O.(Ms)394/2025 KCMC PG tuition order, 9 November 2025','Kerala','fee')
for name in ['Amala Institute of Medical Sciences, Thrissur','Jubilee Mission Medical College and Research Institute, Thrissur','Malankara Orthodox Syrian Church Medical College, Kolenchery','Pushpagiri Institute of Medical Sciences, Thiruvalla']:
 for c,q,f in [('Clinical','85% merit',1942235),('Non-clinical','85% merit',1179215),('MD/MS','15% NRI',4081014)]:
  fin('Kerala','Kerala 2025 KCMC private PG tuition','Named institution and quota only',s,2,instituteName=name,course=c,quota=q,annualFee=f,notes='Academic-year 2025-26 fee order for these four colleges. DM/MCh fees excluded. Hostel, deposits and unreported stipend/bond amounts not included.')

# Karnataka compulsory rural-service and government-seat undertakings are separate conditions.
s=source('karnataka-prospectus-2026','KEA PGNEET 2026 information bulletin','Karnataka','prospectus',2026)
fin('Karnataka','Karnataka one-year compulsory service','PG medical degree/diploma in government, private and deemed colleges; all quotas',s,8,program='MD/MS/PG Diploma',bondYears=1,notes='Exempts candidates who already completed compulsory rural service after MBBS. Bulletin specifies service in government hospital in urban area. Separate government-seat undertaking exists; do not simply add the two periods. Default penalty is not stated on this page.')
for program,penalty in [('MD/MS',5000000),('PG Diploma',2500000)]:
 fin('Karnataka','Karnataka government-seat '+program+' service undertaking','Government seats including AIQ; non-service candidates',s,'8,45',program=program,quota='Government seats including AIQ',bondYears=3,bondPenalty=penalty,notes='Minimum three years after course completion if Government desires. Annexure 2 gives 50 lakh degree / 25 lakh diploma default amount. Separate one-year statutory service provision also appears; applicability must be read together, not summed automatically.')

# Puducherry current fee order and institute-specific fees.
s=source('puducherry-fees','Puducherry approved fee order dated 28 August 2026, AY 2026-27 to 2028-29','Puducherry','fee',2026)
for name in ['Pondicherry Institute of Medical Sciences','Sri Manakula Vinayagar Medical College & Hospital']:
 for c,q,f in [('Clinical','Government quota',850000),('Non-clinical','Government quota',675000),('Clinical','Management quota',2500000),('Non-clinical','Management quota',1325000)]:
  fin('Puducherry','Puducherry 2026 regulated PG academic fee','PIMS and SMVMCH only; named course group and quota',s,'1,4',instituteName=name,course=c,quota=q,annualFee=f,notes='Maximum approved academic-year fee for 2026-27, 2027-28 and 2028-29; institution may charge less. Includes admission, tuition, laboratory, maintenance and recurring academic charges. Excludes books/equipment, hostel, transport and food. Sri Venkateshwaraa is subject to separate court orders and is not assigned these fees. Stipend referenced to GO28 but amount not specified.')
s=source('puducherry-igmcri-fees','IGMC&RI 2025-26 revised PG seat and fee particulars, 31 October 2025','Puducherry','fee')
fin('Puducherry','IGMC&RI annual PG academic charges','Indira Gandhi Medical College and Research Institute, PG MD/MS',s,3,instituteName='Indira Gandhi Medical College & Research Institute',program='MD/MS',annualFee=110000,discontinuationPenalty=1000000,notes='Annual academic fee 33,000 + learning resource 44,000 + establishment charges 33,000. First-year total 185,000 includes 50,000 one-time admission and 25,000 refundable college deposit. Hostel 4,000/month and 10,000 refundable deposit. Discontinuation on/after last counselling date or during subsequent years costs 10 lakh; before that date caution deposit is forfeited. Service bond and stipend amount not stated.')

# Tamil Nadu: independently published institute fees/stipend; no fabricated state-wide matrix.
s=source('tn-bhaarath-finance','Bhaarath Medical College PG admission 2026-27 fees and stipend','Tamil Nadu','fee',2026)
for c,f in [('MD Radiodiagnosis',7500000),('MD Dermatology, Venereology and Leprosy',7500000),('MD General Medicine',6000000),('MD Psychiatry',3600000),('MD Anaesthesiology',4000000),('MD Respiratory Medicine',5500000),('MD Emergency Medicine',4500000),('MS Ophthalmology',4000000),('MS General Surgery',5000000),('MS Orthopaedics',6000000),('MS ENT',4500000),('MD Paediatrics',5000000),('MS Obstetrics and Gynaecology',6500000)]:
 fin('Tamil Nadu','Bhaarath 2026 PG management annual tuition and stipend','Bhaarath Medical College and Hospital; deemed-university management seats through MCC',s,'PG Fees Structure / Stipend sections',instituteName='Bhaarath Medical College and Hospital',course=c,quota='Management (deemed university)',annualFee=f,monthlyStipend=48000,stipendByYear=[48000,49000,50000],notes='2026-27 institute-published per-annum tuition. Hostel 150,000/year and mess 75,000/year additional; one-time admission/registration and refundable deposits separate. NRI USD fee not converted or mixed with INR. Discontinuation requires remaining-course tuition, a variable amount; no fixed service-bond value established. Financial data only, no duplicate MCC seat matrix.')

# Every jurisdiction has an explicit authority and honest imported coverage.
authorities={
 'Andhra Pradesh':('Dr NTR University of Health Sciences','https://drntr.uhsap.in/index/Notifications','partial','2026-27 tuition policies and SVIMS stipend/bond; 2025 management Round 1 AIR aggregates. State competent-authority allotments and statewide stipend/bond coverage remain incomplete.'),
 'Telangana':('Kaloji Narayana Rao University of Health Sciences','https://www.knruhs.telangana.gov.in/','partial','2025 non-minority non-service competent authority clinical/non-clinical matrices plus management matrices and Round 1 AIR aggregates. 2026-27 service/discontinuation policies. Statewide fees/stipends and later rounds remain incomplete.'),
 'Karnataka':('Karnataka Examinations Authority','https://cetonline.karnataka.gov.in/kea/pgetmed2025','partial','2025-26 institution/course/quota annual fee schedule and fresh Round 3 AIR allotment aggregates; 2026 service policies. Retained/not-upgraded rows excluded; no complete stipend table or live vacancy claim.'),
 'Tamil Nadu':('Directorate of Medical Education and Research, Selection Committee','https://tnmedicalselection.net/','partial','2026-27 official state prospectus links located but PDF retrieval repeatedly failed. Bhaarath institute annual tuition and PG stipend imported; this is not statewide Tamil Nadu fee, bond or cutoff coverage.'),
 'Kerala':('Commissioner for Entrance Examinations, Kerala','https://cee.kerala.gov.in/pgm2025/','partial','2025 base category-wise seats excluding in-service/minority/NRI; government and 15 private colleges tuition; government-college service bonds. Stipend amounts and historical last-rank numerical tables not yet imported; official last-rank documents linked.'),
 'Puducherry':('Centralised Admission Committee (CENTAC)','https://centacpuducherry.in/','partial','2025 first-round admitted AIR snapshot; IGMC&RI annual charges and discontinuation penalty; current 2026-29 PIMS/SMVMCH fee order. Full state seat matrix and stipend/service-bond coverage remain incomplete. JIPMER INI-CET excluded.'),
 'Andaman and Nicobar Islands':('Andaman and Nicobar Islands Institute of Medical Sciences','https://aniims.andamannicobar.gov.in/notices.html','partial','2025-26 ANIIMS six UT MD/MS seats and three in-service DNB seats, annual fees/stipends and distinct MD/MS versus in-service DNB service conditions. AIQ seats omitted to avoid MCC duplication; state cutoff history not available here.'),
 'Lakshadweep':('Directorate of Health Services, UT Administration of Lakshadweep','https://lakshadweep.gov.in/health-services/','not-located','Official health authority located. No separate NEET PG counselling seat/allotment dataset or applicable PG fee/stipend/bond order verified in this acquisition. This is a data gap, not an assertion of zero seats or zero fees.')}
for name,(authority,url,status,note) in authorities.items():
 docs=[{'title':x['title'],'url':x['url'],'year':x['year'],'kind':x['kind']} for x in OUT['sources'] if x['scope']==name]
 if name=='Tamil Nadu':docs += [{'title':'2026-27 government quota prospectus (retrieval pending)','url':URLS['tn-gq-2026'],'year':2026,'kind':'prospectus'},{'title':'2026-27 management quota prospectus (retrieval pending)','url':URLS['tn-mq-2026'],'year':2026,'kind':'prospectus'}]
 if name=='Kerala':docs += [{'title':'CEE 2025 '+r+' official last-rank table (not numerically imported)','url':URLS[k],'year':2025,'kind':'cutoff'} for k,r in [('kerala-r1','Round 1'),('kerala-r2','Round 2')]]
 if name=='Puducherry':docs += [{'title':'CENTAC 2025 PG seat matrix (scanned, not numerically imported)','url':URLS['puducherry-seats'],'year':2025,'kind':'seat-matrix'}]
 if not docs:docs=[{'title':'UT Directorate of Health Services','url':url,'year':2026,'kind':'authority'}]
 OUT['states'].append({'name':name,'authority':authority,'authorityUrl':url,'coverageNote':note,'status':status,'documents':docs})

OUT['institutes']=list(inst.values());OUT['summary']={'institutes':len(inst),'records':len(OUT['records']),'financialEntries':len(OUT['financials']),'reconciliation':audit}
(ROOT.parent/'south.json').write_text(json.dumps(OUT,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(OUT['summary'],indent=2))
