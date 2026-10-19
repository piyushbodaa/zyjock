"""Read published columns geometrically; never store candidate names/form identifiers."""
from pathlib import Path
import pymupdf as fitz,json,re,collections
B=Path(__file__).parent/'raw';doc=fitz.open(B/'mh-allotment-r1.pdf');out=[];seen=[]
for pn,p in enumerate(doc,1):
 words=p.get_text('words');groups=collections.defaultdict(list)
 for w in words:
  if 190<w[1]<790:groups[round(w[1],1)].append(w)
 for y,row in groups.items():
  texts=lambda low,high:' '.join(w[4] for w in sorted(row,key=lambda w:w[0]) if low<=w[0]<high)
  sn=texts(0,45);sml=texts(45,80);flag=None
  service=re.fullmatch(r'(\d+)(IB|I)\s*-\s*(\d+(?:\.\d+)?)',texts(0,80))
  if service:sn,flag,sml=service.groups()
  if not re.fullmatch(r'\d+',sn) or not re.fullmatch(r'\d+(?:\.\d+)?',sml):continue
  seen.append(int(sn));codes=[w[4] for w in row if 275<=w[0]<300 and re.fullmatch(r'\d{4}[A-Z]',w[4])]
  if not codes:continue
  out.append({'page':pn,'serial':int(sn),'rank':float(sml),'code':codes[0],'course':texts(308,390),'institute':texts(390,477),'category':texts(477,595),'inServiceFlag':flag})
(B/'mh-allotment-r1-safe-rows.json').write_text(json.dumps({'rows':out,'sourceRows':len(seen),'uniqueSerials':len(set(seen)),'lastSerial':max(seen)},indent=2));print({'allocatedRows':len(out),'sourceRows':len(seen),'uniqueSerials':len(set(seen)),'lastSerial':max(seen)})
