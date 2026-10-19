# Executed by build.py in its namespace. Official source-specific aggregation.
# Assam R2: columns use revised STATE merit rank. Read cells geometrically to
# avoid the PDF's merged Selection Details cell swallowing adjacent records.
cachePath=ROOT/'assam-aggregate.json'
sourceHash=hashlib.sha256((ROOT/'raw/assam-r2.pdf').read_bytes()).hexdigest()
cache=json.loads(cachePath.read_text()) if cachePath.exists() else {}
if cache.get('sourceSHA256')==sourceHash:
 for i in cache['institutes']:
  if (i['name'],i['state']) not in inst:
   inst[(i['name'],i['state'])]=i['id'];OUT['institutes'].append(i)
 OUT['records'].extend(cache['records']);OUT['summary']['assam2025Round2']=cache['summary']
else:
 key='assam-r2';doc=pymupdf.open(ROOT/'raw'/f'{key}.pdf');groups=collections.defaultdict(list);pgs=collections.defaultdict(set);seen=[];na=0
 for pi,p in enumerate(doc):
  tables=p.find_tables().tables
  for t in tables:
   if t.col_count!=11:continue
   for rowobj in t.rows:
    rect=rowobj.cells[0]
    if rect is None:continue
    sn=clean(p.get_textbox(rect))
    if not sn.isdigit():continue
    seen.append(int(sn));y0,y1=rect[1],rect[3]
    rank=clean(p.get_textbox((273,y0,328,y1)))
    code=clean(p.get_textbox((631,y0,678,y1)))
    if re.search(r'\bNA\b',code):na+=1;continue
    cm=re.search(r'\b(\d{4})\b',code);assert cm,(pi+1,sn,code)
    code=cm[1];assert rank.isdigit(),(pi+1,sn,rank)
    category=clean(p.get_textbox((678,y0,727,y1)))
    course=re.sub(r'^\)\s*','',clean(p.get_textbox((727,y0,851,y1))))
    name=clean(p.get_textbox((851,y0,1001,y1)))
    assert name and course and category,(pi+1,sn,'empty selection')
    iid=institution(name,'Assam','https://dme.assam.gov.in/latest/admission-notice-ugpgothersnew')
    g=(iid,course,'Assam State quota',category);groups[g].append(int(rank));pgs[g].add(pi+1)
 assert seen==list(range(1,len(seen)+1)),('Assam serial discontinuity',len(seen),max(seen))
 for g,ranks in groups.items():
  record(*g,2025,'Round 2 — provisional selection',key,','.join(map(str,sorted(pgs[g]))),ranks=ranks,rankType='State merit rank',counselling='Assam — DME')
  OUT['records'][-1]['notes']='Official provisional select list, conditional on document verification. Revised state merit rank includes applicable incentives; not NEET AIR. NA choices excluded. Selection snapshot counts are not proof of new round-2 allotment events.'
 OUT['summary']['assam2025Round2']={'publishedRows':len(seen),'selected':len(seen)-na,'noChoice':na,'aggregatePools':len(groups),'rankType':'State merit rank','resultStatus':'provisional'}
# Arunachal 2026 source advertisement manually transcribed from scanned table.
iid=institution('Tomo Riba Institute of Health and Medical Sciences (TRIHMS)','Arunachal Pradesh','https://dmetrap.in/',city='Naharlagun')
for course,n,quota,cat in [('DNB Emergency Medicine',1,'Arunachal State quota — in-service','In-service'),('NBEMS Diploma Ophthalmology',1,'Arunachal State quota — in-service','In-service')]+[(c,n,'Arunachal State quota','As per 200-point roster') for c,n in [('MD General Medicine',1),('MD Paediatrics',1),('MS General Surgery',1),('MD Anesthesiology',1),('MD Microbiology',1),('MD Physiology',1),('MD Community Medicine',1),('MD Radio Diagnosis',2),('MD Obstetrics & Gynaecology',1),('MD Pharmacology',1)]]:
 record(iid,course,quota,cat,2026,'Published matrix','arunachal-matrix',1,seats=n,counselling='Arunachal Pradesh — DMETR')
 OUT['records'][-1]['notes']='16 October 2026 advertisement: MD/MS distribution subject to 200-point roster. Source labels Obstetrics and Gynaecology as MD; retained as published. Not live vacancies.'
OUT['summary']['arunachal2026Seats']=13
# SMIMS 2025 initial published matrix and exact single-instalment annual course fees.
iid=institution('Sikkim Manipal Institute of Medical Sciences','Sikkim','https://www.smu.edu.in/notice-board.php','Private',city='Gangtok')
rows=[('MD General Medicine',1,2960000,'General'),('MS Obstetrics & Gynaecology',1,2960000,'General'),('MD Paediatrics',2,2960000,'General'),('MS Orthopaedics',1,2960000,'General'),('MS ENT',2,2700000,'General'),('MD Radio Diagnosis',1,3500000,'General'),('MD Anaesthesiology',3,2500000,'General'),('MD Psychiatry',3,2300000,'General'),('MD Community Medicine',1,500000,'General'),('MD Microbiology',2,500000,'General'),('MD Physiology',2,500000,'General'),('MD Biochemistry',1,500000,'General'),('MD Pharmacology',1,500000,'General'),('MD General Medicine',1,5300000,'Management'),('MS Obstetrics & Gynaecology',1,5300000,'Management'),('MS Orthopaedics',1,5300000,'Management'),('MD Radio Diagnosis',1,6600000,'Management'),('MD Anaesthesiology',1,4400000,'Management')]
for course,seats,fee,quota in rows:
 record(iid,course,'SMIMS '+quota+' category',quota,2025,'Initial published matrix','smims-full',1,seats=seats,counselling='Sikkim — SMIMS')
 finance('Sikkim','SMIMS '+course+' — '+quota+' category annual fee','smims-full',1,'SMIMS '+quota+' category',instituteName='Sikkim Manipal Institute of Medical Sciences',course=course,program=course.split()[0],quota=quota,annualFee=fee,notes='Annual course fee when paid in a single instalment; same course fee in subsequent years. Two-instalment option costs 4% more in total. ₹25,000 refundable caution + ₹10,000 registration separate. Double sharing accommodation ₹65,000/year. This 2025 initial fee matrix is historical; not a 2026 quote.')
OUT['summary']['smims2025InitialSeats']=sum(x[1] for x in rows)
finance('Mizoram','Zoram Medical College MD/MS stipend and post-course service bond','https://zmc.edu.in/pages/remunerationstipend-and-bonds','Official disclosure webpage','Zoram Medical College MD/MS students',2026,instituteName='Zoram Medical College and Hospital',program='MD/MS',monthlyStipend=50000,stipendByYear=[50000,55000,60000],bondYears=1,bondPenalty=2000000,notes='Official undated institutional disclosure checked 19 October 2026: PG stipend ₹50,000/55,000/60,000 by year. One year compulsory service after MD/MS; ₹20 lakh failure-to-serve penalty. Permanent government employees exempt from this bond, excluding any bond separately signed for further-study approval. Website separately lists JR salary ₹80,000; that is not the PG stipend.')
# VMMC disclosure provides basic pay rather than a fixed take-home stipend.
for f in OUT['financials']:
 if f['id']=='pg-fin-north-'+ident('Delhi','VMMC and Safdarjung MD/MS tuition and withdrawal fee',None,None):
  f['sourcePage']='1–2';f['notes']+=' MD/MS Junior Resident basic pay Level 10 ₹56,100–177,500 plus applicable allowances and increments; no fixed take-home stipend is quoted.'
