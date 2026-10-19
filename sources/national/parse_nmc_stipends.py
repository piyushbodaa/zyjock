"""Extract disclosed college PG stipends, preserving dates, source columns and raw evidence."""
from pathlib import Path
import json,re,hashlib,collections
import pymupdf as fitz
B=Path(__file__).parent
RAW=B/'nmc-stipend-rows.json'
if not RAW.exists():
 rows=[]
 for pn,p in enumerate(fitz.open(B/'nmc-stipend.pdf'),1):
  for t in p.find_tables().tables:
   for r in t.extract():
    r=[' '.join((x or '').split()) for x in r]
    if r and re.fullmatch(r'\d+',r[0]):rows.append({'page':pn,'cells':r})
 RAW.write_text(json.dumps(rows,indent=2))
rows=json.loads(RAW.read_text())
print('rows',len(rows),'PG explicit college rows',len([x for x in rows if len(x['cells'])>=7 and re.search(r'\bPG',x['cells'][6],re.I)]))
URL='https://oldnmc.nmc.org.in/wp-content/themes/twentyfourteen/pdf/Stipend%20Detail%20List.pdf'
STATE={'Orissa':'Odisha','odisha':'Odisha','Pondicherry':'Puducherry','Gujrat':'Gujarat','Chattisgarh':'Chhattisgarh','Uttar pradesh':'Uttar Pradesh','andhra Pradesh':'Andhra Pradesh','west Bengal':'West Bengal','Telagana':'Telangana','Uttrakhand':'Uttarakhand','new delhi':'Delhi'}
# Irregular wording reviewed against the college column; never inferred from its neighbour.
OVERRIDES={
 '351':[48000,49000,50000], '442':[30000,30000,30000], '487':[53000,54000,55000],
 '513':[None,41000,42000], '569':[56010,None,None], '628':[84000,85400,87500],
 '633':[56100,57800,59500], '694':[78213,78981,79749], '768':[45000,46000,47000],
 '785':[95594,98491,101388], '622':[84000,85400,None],
}
NON_NUMERIC={'354':'The college cell says total amount given, so ₹21,163 is not normalized to an individual monthly stipend.',
'370':'₹56,100 is base pay plus unspecified allowances, not the total monthly payment.',
'576':'₹15,600 is a base plus unspecified grade pay, not the total monthly payment.'}

def extract(cell,sn):
 if sn in OVERRIDES:return OVERRIDES[sn],sn!='569'
 if sn in NON_NUMERIC:return [None,None,None],False
 # All explicit PG claims after the first PG label, cut before UG/SS/SR clauses.
 pg=re.search(r'\bPG\b',cell,re.I)
 if not pg:return [None,None,None],False
 tail=cell[pg.start():];tail=re.split(r'\b(?:UG|SS|Sr\.?\s*R)\b',tail,flags=re.I)[0]
 if re.search(r'PG\s*-?\s*not\s+paid',tail,re.I):return [0,None,None],False
 vals=[]
 # Monetary amounts have four or more digits; year ordinals cannot match.
 money=re.search(r'\bPG\s*[-. ]*(?:1st\s*[-. ]*)?(?:Rs\.?\s*[-. ]*)?([\d,]{4,})',tail,re.I)
 vals.append(int(money[1].replace(',','')) if money else None)
 for yr in [2,3]:
  ordinal='nd' if yr==2 else 'rd'
  m=re.search(r'\b'+str(yr)+r'(?:'+ordinal+r'|yr)\s*[-. ]*(?:Rs\.?\s*[-. ]*)?([\d,]{4,})',tail,re.I)
  vals.append(int(m[1].replace(',','')) if m else None)
 explicit_years=bool(re.search(r'1st|2nd|3rd|2yr|3yr',tail,re.I))
 return vals,explicit_years
financials=[];excluded=[]
for row in rows:
 c=row['cells'];sn,name,state,date,ug,benchmark,college,university,management=c
 if not re.search(r'\bPG',college,re.I):continue
 vals,years=extract(college,sn)
 # Report receipt is not the academic year and never reset to the 2026 compilation year.
 y=re.search(r'20(?:24|25|26)',date)
 if y:year=int(y[0])
 elif re.search(r'\d{1,2}\.\d{1,2}\.24',date):year=2024
 else:year=None
 notes='NMC compilation published in 2026; the amount is from the college-paid column. Report receipt '+date+'. Receipt year is not a confirmed academic-year coverage. Historical disclosure; not live payroll. '
 if sn in NON_NUMERIC:notes+=NON_NUMERIC[sn]+' '
 if years:notes+='Year-specific PG amounts preserved; missing years stay unknown. '
 else:notes+='The source does not specify a PG study year for this amount. '
 if all(v is None for v in vals):notes+='No unambiguous numeric PG payment is available in this college cell; state benchmark is not substituted. '
 if sn=='513':notes+='First-year PG amount is blank/garbled in the source and remains unknown. '
 if vals[0]==0:notes+='The college cell explicitly reports PG not paid; this is a historical report, not a current allegation. '
 title='NMC PG stipend disclosure'
 if year:title+=' — report '+str(year)
 else:title+=' — receipt date not stated'
 if sn in NON_NUMERIC:title+=' (amount not comparable)'
 f={'id':'nmc-pg-stipend-'+sn,'state':STATE.get(state,state),'instituteName':name,'scope':'Institution-reported postgraduate stipend','title':title,'year':year,'publicationYear':2026,'course':'PG (branch not specified)','annualFee':None,'monthlyStipend':vals[0],'bondYears':None,'bondPenalty':None,'discontinuationPenalty':None,'sourceUrl':URL,'sourcePage':row['page'],'sourceLabel':'NMC stipend disclosure compilation, record '+sn,'dataStatus':'verified','notes':notes.strip(),'rawCollegeStipend':college,'rawStateBenchmark':benchmark,'reportReceived':date,'dateBasis':'Report receipt; not academic year','sourceRecordNumber':int(sn),'institutionManagement':management,'university':university,'amountScope':'PG college column only'}
 if years:f['stipendByYear']=vals
 if sn in ['370','576']:f['basePayExcludingAllowances']=56100 if sn=='370' else 15600
 financials.append(f)
source={'id':'nmc-stipend-compilation-2026','title':'NMC national stipend disclosure compilation 2026 (dated historical institution reports)','url':URL,'year':2026,'scope':'India; college-paid PG column only'}
summary={'sourceRows':len(rows),'sourceRecordNumbers':len(set(r['cells'][0] for r in rows)),'collegePgDisclosures':len(financials),'numericPgDisclosures':sum(any(x is not None for x in f.get('stipendByYear',[f['monthlyStipend']])) for f in financials),'unknownPgAmountDisclosures':sum(not any(x is not None for x in f.get('stipendByYear',[f['monthlyStipend']])) for f in financials),'institutionsWithUnknownReceiptYear':sum(f['year'] is None for f in financials),'stateCount':len(set(f['state'] for f in financials)),'yearCounts':dict(collections.Counter(str(f['year']) for f in financials)),'stateCounts':dict(collections.Counter(f['state'] for f in financials)),'basis':'Only explicit PG wording in Stipend of College column; no UG/SS substitution and no state benchmark substitution. Unknown receipt year remains null. Multiple dated disclosures may reference the same college.'}
(B/'financials.json').write_text(json.dumps({'checkedAt':'2026-10-19','financials':financials,'sources':[source],'summary':summary},ensure_ascii=False,indent=2))
(B/'nmc-stipend-summary.json').write_text(json.dumps(summary,indent=2))
print(json.dumps(summary,indent=2))
