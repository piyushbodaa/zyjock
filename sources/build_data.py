from pathlib import Path
import json,re,collections,hashlib
BASE=Path(__file__).resolve().parent
OUT=BASE.parent/'dist'/'data.json'
MATRIX='https://cdnbbsr.s3waas.gov.in/s3e0f7a4d0ef9b84b83b693bbf3feb8e6e/uploads/2025/07/2025072296.pdf'
RESULT='https://cdnbbsr.s3waas.gov.in/s3e0f7a4d0ef9b84b83b693bbf3feb8e6e/uploads/2025/08/20250813289226788.pdf'
REMOVAL='https://cdnbbsr.s3waas.gov.in/s3e0f7a4d0ef9b84b83b693bbf3feb8e6e/uploads/2025/08/20250813868365001.pdf'
# Explicitly bounded to all 20 institutes in this one-page MCC matrix.
rows=[
('200511','AIIMS Bathinda','Bathinda','Punjab',r'^AIIMS Bathinda'),
('200530','AIIMS Bilaspur','Bilaspur','Himachal Pradesh',r'^AIIMS Bilaspur'),
('200518','AIIMS Jammu','Vijaypur','Jammu and Kashmir',r'^AIIMS Jammu'),
('200510','AIIMS Mangalagiri','Mangalagiri','Andhra Pradesh',r'^AIIMS Mangalagiri'),
('200520','AIIMS Rajkot','Rajkot','Gujarat',r'^AIIMS Rajkot'),
('200517','AIIMS Bibinagar','Bibinagar','Telangana',r'^AIIMS, Bibi Nagar'),
('200512','AIIMS Deoghar','Deoghar','Jharkhand',r'^AIIMS, Deogarh'),
('200505','AIIMS Jodhpur','Jodhpur','Rajasthan',r'^AIIMS, Jodhpur'),
('200514','AIIMS Kalyani','Kalyani','West Bengal',r'^AIIMS, Kalyani'),
('200580','AIIMS Madurai','Madurai','Tamil Nadu',r'^AIIMS, Madurai'),
('200509','AIIMS Nagpur','Nagpur','Maharashtra',r'^AIIMS, Nagpur'),
('200502','AIIMS New Delhi','New Delhi','Delhi',r'^AIIMS, New Delhi'),
('200508','AIIMS Patna','Patna','Bihar',r'^AIIMS, Patna'),
('200516','AIIMS Rae Bareli','Rae Bareli','Uttar Pradesh',r'^AIIMS, Rai Bareli'),
('200506','AIIMS Raipur','Raipur','Chhattisgarh',r'^AIIMS, Raipur'),
('200507','AIIMS Rishikesh','Rishikesh','Uttarakhand',r'^AIIMS, Rishikesh'),
('200503','AIIMS Bhopal','Bhopal','Madhya Pradesh',r'^AIIMS-Bhopal'),
('200405','Institute of Medical Sciences, BHU','Varanasi','Uttar Pradesh',r'^INST.OF MED.SCIENCES, BHU,VARANASI'),
('200522','JIPMER Karaikal','Karaikal','Puducherry',r'^JIPMER KARAIKAL'),
('200521','JIPMER Puducherry','Puducherry','Puducherry',r'^JIPMER PUDUCHERRY'),
]
categories=['Open','Open PwD','EWS','EWS PwD','OBC','OBC PwD','SC','SC PwD','ST','ST PwD']
matrix_text=(BASE/'mcc-2025-ug-r1-inis-seat-matrix.txt').read_text()
matrix={}
for line in matrix_text.splitlines():
 m=re.search(r'\((\d{6})\).*?MBBS\s+Open Seat Quota\s+([\d\s]+)$',line)
 if m:
  numbers=list(map(int,m[2].split()))
  assert len(numbers)==11 and sum(numbers[:10])==numbers[10]
  matrix[m[1]]=dict(zip(categories,numbers[:10]))
assert len(matrix)==20
result_text=(BASE/'mcc-2025-ug-r1-result.txt').read_text().replace('\f','\n')
# Preserve table column positions when the allotted category wraps 'PwD' to the next line.
# Do not confuse the separate candidate category with the allotted seat category.
aggregates=collections.defaultdict(list)
matched_counts=collections.Counter()
for block in re.split(r'(?m)(?=^\s*\d+\s+\d+\s)',result_text):
 lines=block.splitlines(); line=next((x for x in lines if x.strip()),'')
 m=re.match(r'^\s*(\d+)\s+(\d+)\s+Open Seat Quota\s+(.+?)\s+MBBS\s+(Open|OBC|EWS|SC|ST)(\s+PwD)?\s{2,}(.+?)\s{2,}Allotted\s*$',line)
 if not m: continue
 target=next((r for r in rows if re.search(r[4],m[3])),None)
 if not target: continue
 cat=m[4]+(' PwD' if m[5] else '')
 if not m[5] and any('PwD' in x[m.start(4):m.start(6)] for x in lines[1:]): cat+=' PwD'
 aggregates[(target[0],cat)].append(int(m[2]))
 matched_counts[target[0]]+=1
institutes=[]; records=[]; discrepancies=[]
for code,name,city,state,pattern in rows:
 iid='mcc-'+code
 institutes.append(dict(id=iid,name=name,city=city,state=state,type='Government',university=None,officialUrl=None,sourceUrl=MATRIX,verified=True,dataStatus='verified',mccCode=code))
 for cat in categories:
  ranks=aggregates[(code,cat)]
  seats=matrix[code][cat]
  notes=[]
  if code=='200502' and cat=='SC PwD':
   seats=0
   notes.append('One SC PwD seat removed by MCC notice dated 13 August 2025. Original July matrix value was 1.')
  if len(ranks)!=seats:
   discrepancies.append(dict(institute=name,category=cat,matrixSeats=seats,allotments=len(ranks)))
   notes.append('The published July seat matrix and August allotment count differ. Seats reflect the matrix snapshot; ranks reflect final allotments. Later changes may apply.')
  originalCat=cat.replace('EWS','General-EWS')
  records.append(dict(id=f'official-{code}-{cat.lower().replace(" ","-")}-2025-r1',instituteId=iid,exam='NEET UG',course='MBBS',counselling='MCC',quota='Open Seat Quota',category=cat,originalCategory=originalCat,year=2025,round='Round 1',openingRank=min(ranks) if ranks else None,closingRank=max(ranks) if ranks else None,seats=seats,annualFee=None,monthlyStipend=None,bondYears=None,bondPenalty=None,previousSeats=None,dataStatus='verified',sourceUrl=RESULT if ranks else MATRIX,sourceLabel='MCC UG 2025 · Round 1 · derived aggregate',seatSourceUrl=REMOVAL if code=='200502' and cat=='SC PwD' else MATRIX,rankSourceUrl=RESULT,seatSnapshotDate='2025-07-22',allotmentCount=len(ranks),notes=' '.join(notes) or 'Historical allotments, not current vacancies or admission guarantees. Fees, stipend and bond have not been verified.'))
exams=['NEET UG','NEET PG','NEET MDS','INICET','NEET SS','DNB PDCET']
# Entirely fictional institutions and generated figures, deliberately separate from official records.
demoInstitutes=[
('aurora','Demo · Aurora Medical Institute','Sample City A','Maharashtra','Government'),
('cedar','Demo · Cedar Teaching Hospital','Sample City B','Karnataka','Private'),
('harbour','Demo · Harbour Medical College','Sample City C','Tamil Nadu','Government'),
('meadow','Demo · Meadow Health Sciences','Sample City D','Delhi','Private'),
('summit','Demo · Summit Medical Academy','Sample City E','Rajasthan','Government'),
('riverbend','Demo · Riverbend Hospital','Sample City F','Uttar Pradesh','Private'),
('orchard','Demo · Orchard Health Institute','Sample City G','Gujarat','Government'),
('horizon','Demo · Horizon Medical College','Sample City H','Telangana','Private'),
]
courseMap={'NEET UG':['MBBS','BDS'],'NEET PG':['MD General Medicine','MS General Surgery','MD Paediatrics','MD Anaesthesiology'],'NEET MDS':['MDS Orthodontics','MDS Oral Surgery','MDS Prosthodontics'],'INICET':['MD General Medicine','MS General Surgery','MD Radiodiagnosis'],'NEET SS':['DM Cardiology','MCh Neurosurgery','DM Neurology'],'DNB PDCET':['DNB Anaesthesiology','DNB Paediatrics','DNB Obstetrics & Gynaecology']}
for i,(slug,name,city,state,typ) in enumerate(demoInstitutes):
 iid='demo-'+slug
 institutes.append(dict(id=iid,name=name,city=city,state=state,type=typ,university='Fictional demonstration institute',officialUrl=None,sourceUrl=None,verified=False,dataStatus='demo'))
 for ei,exam in enumerate(exams):
  course=courseMap[exam][i%len(courseMap[exam])]
  for year in [2024,2025]:
   for ri,roundName in enumerate(['Round 1','Round 2','Round 3']):
    for ci,cat in enumerate(['Open','EWS','OBC','SC','ST']):
     scale={'NEET UG':1100,'NEET PG':300,'NEET MDS':90,'INICET':45,'NEET SS':50,'DNB PDCET':20}[exam]
     closing=int(scale*(i+1)*(1+ci*0.42)*(1+ri*0.12)*(1.04 if year==2025 else 1))
     seats=10+i*2+ci if exam=='NEET UG' else 1+(i+ci)%6
     fee=(18000+i*11000) if typ=='Government' else (320000+i*130000)
     records.append(dict(id=f'demo-{slug}-{ei}-{year}-{ri}-{cat.lower()}',instituteId=iid,exam=exam,course=course,counselling='Demo counselling',quota='Demo All India',category=cat,year=year,round=roundName,openingRank=max(1,int(closing*.55)),closingRank=closing,seats=seats,annualFee=fee,monthlyStipend=(45000+i*5500 if exam not in ['NEET UG','NEET MDS'] else 14000+i*2000),bondYears=[0,1,2,1,0,3,1,2][i],bondPenalty=[0,500000,1000000,700000,0,1500000,500000,1200000][i],previousSeats=seats-(1 if i%3==0 else 0),dataStatus='demo',sourceUrl=None,sourceLabel='Fictional demonstration data',notes='Fictional institute and generated figures. For learning the tool only; never use for admission decisions.'))
resources=[
 dict(id='mcc-ug',title='MCC undergraduate counselling',description='Official notices, schedules, registration links and seat matrices for UG counselling.',exam='NEET UG',url='https://mcc.nic.in/ug-medical-counselling/',type='Official portal'),
 dict(id='mcc-pg',title='MCC postgraduate counselling',description='Official PG counselling notices, schedules and seat information.',exam='NEET PG',url='https://mcc.nic.in/pg-medical-counselling/',type='Official portal'),
 dict(id='mcc-mds',title='MCC dental counselling',description='Official postgraduate dental counselling portal.',exam='NEET MDS',url='https://mcc.nic.in/mds-counselling/',type='Official portal'),
 dict(id='aiims',title='AIIMS examinations',description='Official INI-CET notices, key dates and course information.',exam='INICET',url='https://www.aiimsexams.ac.in/',type='Official portal'),
 dict(id='mcc-ss',title='MCC super speciality counselling',description='Official super speciality counselling information and notices.',exam='NEET SS',url='https://mcc.nic.in/super-speciality-counselling/',type='Official portal'),
 dict(id='nbems-pdcet',title='NBEMS DNB-PDCET',description='Official examination information, bulletins and notices for DNB-PDCET.',exam='DNB PDCET',url='https://www.natboard.edu.in/viewnbeexam?exam=pdcet',type='Official portal'),
 dict(id='pdcet-counselling',title='DNB-PDCET counselling',description='NBEMS counselling portal. Check the session and current handbook before proceeding.',exam='DNB PDCET',url='https://counseling.nbe.edu.in/pdcet/login',type='Official portal'),
 dict(id='nmc-colleges',title='NMC college register',description='Cross-check recognised MBBS institutions and course information with the regulator.',exam='NEET UG',url='https://www.nmc.org.in/information-desk/for-students-to-study-in-india/list-of-college-teaching-mbbs/1000/',type='College register'),
 dict(id='mcc-source-result',title='2025 Round 1 allotment source',description='Source used to derive the historical rank ranges shown for 20 institutions. No candidate identifiers are stored in Zyjock.',exam='NEET UG',url=RESULT,type='Source PDF'),
 dict(id='mcc-source-matrix',title='2025 AIIMS / BHU / JIPMER seat source',description='Published category-level seat matrix for the bounded 20-institution dataset. Includes historical values, not live vacancy counts.',exam='NEET UG',url=MATRIX,type='Source PDF'),
 dict(id='mcc-archive',title='MCC UG archive',description='Historical official bulletins, schedules, seat matrices, and results. Check year and round carefully.',exam='NEET UG',url='https://mcc.nic.in/archive-ug/',type='Archive'),
 dict(id='mcc-bulletin-2025',title='MCC UG information bulletin 2025',description='Historical 2025 counselling bulletin. Current admission rules must be checked in the relevant session bulletin.',exam='NEET UG',url='https://cdnbbsr.s3waas.gov.in/s3e0f7a4d0ef9b84b83b693bbf3feb8e6e/uploads/2025/07/202509181307981517.pdf',type='Guide'),
]
notices=[
 dict(id='notice-ug',title='Check current UG notices and schedules',exam='NEET UG',authority='MCC',date=None,url='https://mcc.nic.in/ug-medical-counselling/',kind='Official notice board',description='Opens the official board; Zyjock does not claim an automated live notice feed.'),
 dict(id='notice-pg',title='Check current PG notices and schedules',exam='NEET PG',authority='MCC',date=None,url='https://mcc.nic.in/pg-medical-counselling/',kind='Official notice board'),
 dict(id='notice-mds',title='Check current MDS notices and schedules',exam='NEET MDS',authority='MCC',date=None,url='https://mcc.nic.in/mds-counselling/',kind='Official notice board'),
 dict(id='notice-ini',title='Check INI-CET notices and key dates',exam='INICET',authority='AIIMS',date=None,url='https://www.aiimsexams.ac.in/',kind='Official notice board'),
 dict(id='notice-ss',title='Check current super speciality notices',exam='NEET SS',authority='MCC',date=None,url='https://mcc.nic.in/super-speciality-counselling/',kind='Official notice board'),
 dict(id='notice-pdcet',title='Check DNB-PDCET notices',exam='DNB PDCET',authority='NBEMS',date=None,url='https://www.natboard.edu.in/viewnbeexam?exam=pdcet',kind='Official notice board'),
 dict(id='notice-correction',title='Historical correction: AIIMS Delhi SC PwD seat',exam='NEET UG',authority='MCC',date='2025-08-13',url=REMOVAL,kind='Dataset correction',description='MCC removed one SC PwD seat from the 2025 Round 1 matrix. Zyjock applies this correction.'),
]
guides=[
 dict(id='shortlist',title='Build your list in three passes',body='Start with courses and locations you would actually join. Check eligibility, the counselling authority, fees and any service bond from the relevant official documents. Then order your saved choices by your genuine preference. This workspace does not submit or lock choices on any counselling portal.',sourceUrl='https://mcc.nic.in/ug-medical-counselling/'),
 dict(id='ranks',title='Read a closing rank carefully',body='A historical closing rank is the highest rank found among published allotments for one course, institution, quota, allotted category, year and round. It is not a guarantee, a current vacancy, a candidate-category cutoff or proof that the student joined. Compare the same pool and check this year’s eligibility and seat matrix.',sourceUrl=RESULT),
 dict(id='documents',title='Prepare your documents',body='Use the current official bulletin and the allotted institute’s reporting notice as your checklist. Verify identity, exam records, qualifying certificates and any applicable category, disability or domicile documents. Requirements and validity dates depend on the counselling authority and session.',sourceUrl='https://mcc.nic.in/ug-medical-counselling/'),
 dict(id='financial',title='Compare the whole financial commitment',body='Tuition alone is not the full cost. Record hostel and other charges, deposits, the duration of the course, stipend terms, and any service-bond conditions from the institute’s current documents. Unknown fields here are deliberately blank. Demo figures are fictional.',sourceUrl='https://mcc.nic.in/pg-medical-counselling/'),
 dict(id='data',title='Know what is covered',body='The verified dataset contains 20 AIIMS, BHU and JIPMER institutions from MCC’s 2025 Round 1 open-seat matrix and aggregate historical ranks. Other examinations and the fee, stipend, bond, rank-conversion and seat-change examples use clearly marked fictional demo data until you import your own verified records.',sourceUrl='https://mcc.nic.in/archive-ug/'),
]
rankCurves=[]
for ei,exam in enumerate(exams):
 maxScore=720 if exam=='NEET UG' else 800 if exam=='NEET PG' else 960 if exam=='NEET MDS' else 200 if exam=='INICET' else 600 if exam=='NEET SS' else 480
 scale=200000 if exam=='NEET UG' else 100000 if exam=='NEET PG' else 12000 if exam=='NEET MDS' else 40000 if exam=='INICET' else 10000 if exam=='NEET SS' else 5000
 rankCurves.append(dict(exam=exam,year=2025,dataStatus='demo',label='Illustrative score-rank curve, not an official estimate',sourceUrl=None,points=[dict(score=round(maxScore*f),rank=round(1+scale*(1-f)**2)) for f in [0.25,.4,.55,.65,.75,.85,.9,.95,1]]))
coverage=dict(label='20 institutions · MCC UG 2025 Round 1',summary='A bounded historical dataset of 20 institutions. Official seat matrix and aggregate opening/closing ranks; not an exhaustive national database.',verifiedInstitutes=20,verifiedRecords=200,verifiedExam='NEET UG',verifiedYear=2025,verifiedRound='Round 1',verifiedQuota='Open Seat Quota',demoInstitutes=8,rankRecords=sum(r['openingRank'] is not None for r in records if r['dataStatus']=='verified'),lastChecked='2026-10-19',limitations=['Only the 20 institutions in the cited one-page AIIMS/BHU/JIPMER seat matrix are included.','Historical ranks describe allotted seats, not admitted or joined candidates.','No verified fee, stipend, bond, score-to-rank curve, previous-year seat or current-vacancy data is bundled.','Other exams have fictional demo records until official records are imported.','Official links are curated; notices and deadlines are not automatically synchronized.'],seatMatrixReconciliation=discrepancies)
data=dict(version='1.0.0',updatedAt='2026-10-19',coverage=coverage,exams=exams,institutes=institutes,records=records,resources=resources,notices=notices,guides=guides,rankCurves=rankCurves)
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n')
summary=dict(institutes=len(institutes),records=len(records),verifiedRecords=200,verifiedRankRecords=coverage['rankRecords'],matchedAllotments=sum(matched_counts.values()),matrixSeats=sum(r['seats'] for r in records if r['dataStatus']=='verified'),discrepancies=discrepancies,files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in BASE.glob('*.pdf')})
(BASE/'acquisition-summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))
