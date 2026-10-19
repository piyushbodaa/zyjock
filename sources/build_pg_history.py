#!/usr/bin/env python3
"""Build only aggregate public PG counselling history from official MCC PDFs.
Run: uv run --with pymupdf python sources/build_pg_history.py [--download]
No candidate-level extraction is written to disk. Source PDFs remain local.
"""
from pathlib import Path
import re,json,hashlib,bisect,sys,collections,concurrent.futures,urllib.request
import pymupdf as fitz
BASE=Path(__file__).resolve().parent
ROOT=BASE.parent
CDN='https://cdnbbsr.s3waas.gov.in/s3e0f7a4d0ef9b84b83b693bbf3feb8e6e/uploads/'
SOURCES=[
 dict(id='pg2025-r1',key='r1',round='Round 1',title='Final Result of Round 1 for PG Counselling 2025',url=CDN+'2025/11/202511221303622410.pdf',firstPage=1,columns=[0,44.91,89.82,179.63,538.88,651.15,696.06,752.19,842],fields={'serial':0,'rank':1,'quota':2,'institute':3,'course':4,'category':5,'remarks':7}),
 dict(id='pg2025-r2',key='r2',round='Round 2',title='Final Result for Round 2 of PG counselling 2025',url=CDN+'2025/12/202512172132273940.pdf',firstPage=1,columns=[0,46.41,99.45,212.16,298.35,358.02,417.69,550.29,636.47,689.51,735.92,782.33,842],fields={'rank':0,'quota':5,'institute':6,'course':7,'category':8,'remarks':11}),
 dict(id='pg2025-r3',key='r3',round='Round 3',title='Final Result for Round-III of NEET PG Counselling 2025',url=CDN+'2026/02/20260206892439077.pdf',firstPage=3,columns=[0,44.39,73.98,199.74,236.72,303.3,355.08,480.84,517.83,577.01,621.4,865.51,991.27,1035.66,1080.04,1124.43,1191],fields={'rank':0,'quota':9,'institute':10,'course':11,'category':12,'remarks':15}),
 dict(id='pg2025-stray',key='stray',round='Stray Vacancy',title='Final Result for Stray Round of PG counselling 2025',url=CDN+'2026/02/20260223177387794.pdf',firstPage=1,columns=[0,44.91,89.82,179.63,538.88,651.15,696.06,752.19,842],fields={'serial':0,'rank':1,'quota':2,'institute':3,'course':4,'category':5,'remarks':7}),
]
CATEGORIES={'Open','Open PwD','OBC','OBC PwD','EWS','EWS PwD','SC','SC PwD','ST','ST PwD'}
def clean(s):return re.sub(r'\s+',' ',s.replace('\xad','').replace('\u0002','-')).strip()
def norm(s):return re.sub(r'[^a-z0-9]','',clean(s).lower())
def normwords(s):return re.sub(r'[^a-z0-9]+',' ',clean(s).lower()).strip()
def digest(s):return hashlib.sha1(s.encode()).hexdigest()[:14]
def download(s):
 p=BASE/f'mcc-pg-2025-{s["key"]}-result.pdf'
 if not p.exists():p.write_bytes(urllib.request.urlopen(s['url']).read())
 return p

def page_rows(page, columns):
 """Use PDF table cell rectangles, not character-column guessing.
 Rotation is applied to text and drawing rectangles, preserving wrapped cells.
 """
 ranges=set()
 for drawing in page.get_drawings():
  r=drawing['rect']*page.rotation_matrix
  if abs(r.x0)<.1 and abs(r.x1-columns[1])<.15 and r.height>8:
   ranges.add((round(r.y0,2),round(r.y1,2)))
 ranges=sorted(ranges)
 if not ranges:return []
 starts=[r[0] for r in ranges]; cells=[[[] for _ in range(len(columns)-1)] for r in ranges]
 for word in page.get_text('words'):
  rect=fitz.Rect(word[:4])*page.rotation_matrix
  x=(rect.x0+rect.x1)/2;y=(rect.y0+rect.y1)/2
  ri=bisect.bisect_right(starts,y)-1
  if ri<0 or y>ranges[ri][1]+.1:continue
  ci=bisect.bisect_right(columns,x)-1
  if 0<=ci<len(columns)-1:cells[ri][ci].append((rect.y0,rect.x0,word[4]))
 output=[]
 for row in cells:
  fields=[]
  for cell in row:
   # Baselines in one line differ slightly by font; rounded Y keeps word order.
   fields.append(clean(' '.join(w[2] for w in sorted(cell,key=lambda w:(round(w[0]/2),w[1])))))
  output.append(fields)
 return output

def parse_source(source):
 p=download(source);doc=fitz.open(p)
 stats=dict(id=source['id'],round=source['round'],sourceUrl=source['url'],pages=len(doc),candidateRows=0,allotments=0,pools=0,omittedRows=0,omissionReasons={},nonAllocationRows=0,nonAllocationReasons={},sha256=hashlib.sha256(p.read_bytes()).hexdigest())
 omissions=collections.Counter(); non=collections.Counter(); allocation_types=collections.Counter(); agg={}; inst={}; originals={}; serials=[]; seenRanks=set(); duplicateRanks=0
 f=source['fields']
 for pn in range(source['firstPage'],len(doc)):
  for cells in page_rows(doc[pn],source['columns']):
   rankText=cells[f['rank']]
   if not re.fullmatch(r'\d+',rankText):continue
   rank=int(rankText);stats['candidateRows']+=1
   if rank in seenRanks: duplicateRanks+=1
   seenRanks.add(rank)
   if 'serial'in f:serials.append(int(cells[f['serial']]))
   vals={k:cells[i] for k,i in f.items()};q=vals['quota'];original=vals['institute'];course=vals['course'];cat=vals['category'];remark=vals['remarks']
   if not original or original=='-':
    non[remark or 'No current-round allocation']+=1;continue
   if not course or course=='-' or not q or q=='-' or cat not in CATEGORIES:
    omissions['Invalid or missing quota/course/allotted category']+=1;continue
   if not re.search(r'Allott|Upgrad',remark,re.I):
    omissions['Populated allocation with unrecognized remarks']+=1;continue
   # Plain source strings differ only by nonsemantic PDF wrapping/punctuation.
   ikey=norm(original);ckey=norm(course)
   inst.setdefault(ikey,original)
   quota='Self-Financed Merit Seat' if norm(q)==norm('Self-Financed Merit Seat/(Paid Seat Quota)') else q
   key=(ikey,ckey,quota,cat)
   if key not in agg:agg[key]=dict(institutionKey=ikey,originalInstitution=original,originalCourse=course,originalQuota=q,quota=quota,category=cat,openingRank=rank,closingRank=rank,allotmentCount=0,sourcePageFirst=pn+1,sourcePageLast=pn+1)
   allocation_types[re.sub(r'AFMS Rank\s*:\s*\d+', 'AFMS ranking', remark)]+=1
   rec=agg[key];rec['openingRank']=min(rank,rec['openingRank']);rec['closingRank']=max(rank,rec['closingRank']);rec['allotmentCount']+=1;rec['sourcePageLast']=pn+1;stats['allotments']+=1
  if pn and pn%400==0:print(source['key'],pn,'pages processed',flush=True)
 stats['allocationRemarks']=dict(allocation_types)
 stats['pools']=len(agg);stats['omissionReasons']=dict(omissions);stats['omittedRows']=sum(omissions.values());stats['nonAllocationReasons']=dict(non);stats['nonAllocationRows']=sum(non.values());stats['duplicateRankRows']=duplicateRanks
 if serials:stats['serialReconciliation']=dict(min=min(serials),max=max(serials),count=len(serials),contiguous=len(set(serials))==max(serials) and min(serials)==1)
 assert stats['candidateRows']==stats['allotments']+stats['omittedRows']+stats['nonAllocationRows']
 print(json.dumps(stats),flush=True)
 return source,list(agg.values()),stats

STATES=['Andaman and Nicobar Islands','Andhra Pradesh','Arunachal Pradesh','Assam','Bihar','Chandigarh','Chhattisgarh','Dadra and Nagar Haveli','Daman and Diu','Delhi (NCT)','Delhi','Goa','Gujarat','Haryana','Himachal Pradesh','Jammu and Kashmir','Jharkhand','Karnataka','Kerala','Ladakh','Lakshadweep','Madhya Pradesh','Maharashtra','Manipur','Meghalaya','Mizoram','Nagaland','Odisha','Orissa','Puducherry','Punjab','Rajasthan','Sikkim','Tamil Nadu','Telangana','Tripura','Uttar Pradesh','Uttarakhand','West Bengal']
def state_for(original):
 # Use the last explicit state occurrence in the original institution/address cell.
 matches=[]
 for st in STATES:
  for m in re.finditer(r'(?<![a-z])'+re.escape(st)+r'(?![a-z])',original,re.I):matches.append((m.start(),len(st),st))
 if not matches:return 'Not reported'
 st=max(matches)[2]
 return {'Delhi (NCT)':'Delhi','Orissa':'Odisha'}.get(st,st)
def name_for(original):
 # Repeated institution name marks name/address boundary in many MCC cells.
 parts=[clean(x) for x in original.split(',')]
 for i in range(1,len(parts)):
  if norm(parts[i]) and len(norm(parts[i]))>12 and norm(parts[i])==norm(parts[0]):return ', '.join(parts[:i]).strip(' ,')
 # Do not falsely truncate institutions such as Govt Medical College, city.
 # Full source label remains available; display first 2 comma fragments when safe.
 if len(parts)>2 and len(parts[0])>35:return parts[0]
 return ', '.join(parts[:2]).strip(' ,') if len(parts)>2 else original

def course_glossary():
 doc=fitz.open(BASE/'mcc-pg-2025-r3-result.pdf')
 text='\n'.join(doc[i].get_text() for i in range(3))
 section=text.split('Program Abbrevations',1)[1].split('Note*',1)[0]
 entries={};code=None
 for line in section.splitlines():
  line=clean(line)
  if not line or line in ['Abbrevation','Description'] or line.startswith('Page No.') or re.match(r'^\d{2}-\d{2}-\d{4}',line):continue
  if re.fullmatch(r'[A-Z][A-Z0-9-]{1,5}',line):code=line;entries[code]=[]
  elif code:entries[code].append(line)
 glossary=[dict(code=code,label=clean(' '.join(parts)),sourceUrl=SOURCES[2]['url'],sourcePages='1-3') for code,parts in entries.items()]
 (BASE/'pg-course-glossary.json').write_text(json.dumps(glossary,indent=2,ensure_ascii=False)+'\n')
 return {norm(g['label']):g for g in glossary}

def main():
 with concurrent.futures.ProcessPoolExecutor(max_workers=4) as pool:results=list(pool.map(parse_source,SOURCES))
 institutes={};records=[];summaries=[];glossary=course_glossary()
 # Join to current-year matrix only by exact complete normalized source cell.
 lookup={}
 matrixPath=ROOT/'dist'/'pg-seats.json'
 if matrixPath.exists():
  matrix=json.loads(matrixPath.read_text())
  for i in matrix.get('institutes',[]):
   for candidate in [i.get('originalInstitution',''),i.get('normalizedInstitution','')]:
    if candidate:lookup[norm(re.sub(r'\(\d{6}\)\s*$','',candidate))]=i
 for source,aggs,summary in results:
  summaries.append(summary)
  for item in aggs:
   original=item.pop('originalInstitution');ikey=item.pop('institutionKey')
   matched=lookup.get(ikey)
   iid=matched['id'] if matched else 'pg-history-'+digest(ikey)
   if iid not in institutes:
    institutes[iid]=dict(id=iid,name=matched.get('name') if matched else name_for(original),city=matched.get('city') if matched else None,state=matched.get('state') if matched else state_for(original),type=matched.get('type') if matched else 'Not reported',university=None,officialUrl=None,sourceUrl=source['url'],verified=True,dataStatus='verified',instituteCode=matched.get('instituteCode') if matched else None,originalInstitution=original,normalizedInstitution=normwords(original))
   course=item['originalCourse'];entry=glossary.get(norm(course));code=entry['code'] if entry else None
   if entry:course=entry['label']
   rid='pg-cutoff-'+digest('|'.join([iid,norm(course),item['quota'],item['category'],'2025',source['round']]))
   records.append(dict(id=rid,instituteId=iid,exam='NEET PG',course=course,courseCode=code,instituteCode=institutes[iid]['instituteCode'],counselling='MCC',year=2025,round=source['round'],recordKind='cutoff',seats=None,annualFee=None,monthlyStipend=None,bondYears=None,bondPenalty=None,previousSeats=None,dataStatus='verified',sourceUrl=source['url'],sourceId=source['id'],sourceLabel='MCC PG 2025 · '+source['round'],originalCategory=item['category'],**item))
 total=sum(x['allotments'] for x in summaries)
 coverage=dict(exam='NEET PG',year=2025,rounds=[s['round'] for s in summaries],institutes=len(institutes),records=len(records),allotments=total,scope='MCC NEET PG 2025 final Round 1, Round 2, Round 3 and Stray Vacancy result documents; current-round allotment columns only.',method='Opening and closing rank are the minimum and maximum AIR by institution, course, quota and allotted seat category. Earlier-round held seats with no new allocation are excluded from later-round aggregates.',limitations=['Historical allotments are not joined admissions, current vacancies or admission guarantees.','State counselling outside these MCC result documents is not covered.','Allotment counts are not seat-matrix capacity; seats remains null.','Historical fees, stipend and service-bond data are not present in these result PDFs.','Institutions are matched across years only by exact normalized source institution/address cell; unmatched identities remain separate.','No candidate-level identifiers or records are published.'],omittedRows=sum(x['omittedRows'] for x in summaries),sources=summaries,courseCodeMatchedRecords=sum(r['courseCode'] is not None for r in records),institutionCodeMatchedIdentities=sum(i['instituteCode'] is not None for i in institutes.values()))
 publicSources=[{k:v for k,v in s.items() if k in ['id','round','title','url']} for s in SOURCES]
 output=dict(institutes=list(institutes.values()),records=records,coverage=coverage,sources=publicSources)
 (ROOT/'dist'/'pg-history.json').write_text(json.dumps(output,ensure_ascii=False,separators=(',',':'))+'\n')
 (BASE/'pg-history-summary.json').write_text(json.dumps(coverage,ensure_ascii=False,indent=2)+'\n')
 print('FINAL',len(institutes),'institutions',len(records),'pools',total,'allotments',flush=True)
def enrich_existing():
 path=ROOT/'dist'/'pg-history.json'
 data=json.loads(path.read_text());glossary=course_glossary()
 matrix_path=ROOT/'dist'/'pg-seats.json';lookup=collections.defaultdict(dict)
 if matrix_path.exists():
  matrix=json.loads(matrix_path.read_text())
  for i in matrix.get('institutes',[]):
   for candidate in [i.get('originalInstitution',''),i.get('normalizedInstitution','')]:
    if candidate:lookup[norm(re.sub(r'\(\d{6}\)\s*$','',candidate))][i['id']]=i
 mapping={};updated={}
 for i in data['institutes']:
  candidates=lookup.get(norm(i['originalInstitution']),{})
  matched=next(iter(candidates.values())) if len(candidates)==1 else None
  old_id=i['id'];new_id=matched['id'] if matched else old_id
  mapping[old_id]=new_id
  if matched:
   i={**i,'id':new_id,'name':matched['name'],'state':matched.get('state'),'city':matched.get('city'),'type':matched.get('type'),'instituteCode':matched.get('instituteCode'),'identityMatchMethod':'Exact normalized full institution/address cell'}
  updated[new_id]=i
 for r in data['records']:
  r['instituteId']=mapping[r['instituteId']];r['instituteCode']=updated[r['instituteId']].get('instituteCode')
  entry=glossary.get(norm(r['originalCourse']))
  if entry:r['courseCode']=entry['code'];r['course']=entry['label']
  r['id']='pg-cutoff-'+digest('|'.join([r['instituteId'],norm(r['course']),r['quota'],r['category'],'2025',r['round']]))
 # Some official remarks contain a separate individual's AFMS merit rank.
 # Publish only the grouped allocation reason, never that candidate-level value.
 for summary in data['coverage']['sources']:
  cleaned=collections.Counter()
  for reason,count in summary.get('allocationRemarks',{}).items():cleaned[re.sub(r'AFMS Rank\s*:\s*\d+', 'AFMS ranking', reason)]+=count
  if cleaned:summary['allocationRemarks']=dict(cleaned)
 data['institutes']=list(updated.values())
 coverage=data['coverage'];coverage['institutes']=len(updated)
 coverage['institutionCodeMatchedIdentities']=sum(i.get('instituteCode') is not None for i in updated.values())
 coverage['courseCodeMatchedRecords']=sum(r.get('courseCode') is not None for r in data['records'])
 coverage['courseCodesDerivedFrom']={'url':SOURCES[2]['url'],'pages':'1–3','method':'Exact normalized course-title match to MCC program glossary; originalCourse retained.'}
 coverage['rankColumn']='Rank column in MCC result. Separate internal AFMS merit ranks appearing in remarks are not collected.'
 path.write_text(json.dumps(data,ensure_ascii=False,separators=(',',':'))+'\n')
 (BASE/'pg-history-summary.json').write_text(json.dumps(coverage,ensure_ascii=False,indent=2)+'\n')
 print('ENRICHED',coverage['institutes'],'identities,',coverage['institutionCodeMatchedIdentities'],'exact code matches,',coverage['courseCodeMatchedRecords'],'coded records',flush=True)

if __name__=='__main__':
 if '--enrich-only' not in sys.argv:main()
 enrich_existing()

