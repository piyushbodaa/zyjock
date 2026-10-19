from pathlib import Path
import pymupdf as fitz,json
base=Path(__file__).parent/'raw'
for k in ['gj-closure','gj-seats','gj-fees','mp-cutoffs-r2','bihar-cutoffs-r1','goa-2026-seats','jh-allotment-r2','jh-allotment-r3','jh-allotment-stray','cg-mopup','cg-allotment']:
 out=base/(k+'-tables.json')
 if out.exists():continue
 doc=fitz.open(base/(k+'.pdf'));pages=[]
 for page in doc:
  tables=page.find_tables();pages.append([t.extract() for t in tables.tables])
 out.write_text(json.dumps(pages));print(k,len(doc),[sum(len(t) for t in ts) for ts in pages])
