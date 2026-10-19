import urllib.request,urllib.parse,ssl,json,re,concurrent.futures
from pathlib import Path
BASE=Path(__file__).parent
RAW=BASE/'raw'; RAW.mkdir(exist_ok=True)
def fetch(name,url):
 p=RAW/(name+'.pdf' if '.pdf' in url.lower() else name+'.html')
 if p.exists():return p
 req=urllib.request.Request(urllib.parse.quote(url,safe=':/?=&%'),headers={'User-Agent':'Mozilla/5.0'})
 try:
  content=urllib.request.urlopen(req,timeout=60).read()
  p.write_bytes(content);print(name,len(content)); return p
 except Exception as e: print('ERROR',name,str(e));return None
if __name__=='__main__':
 jobs={
 'gj-seats':'https://medadmgujarat.ncode.in/web/PG2025/MDMS/PG MD MS SEATS 2025-26.pdf',
 'gj-fees':'https://medadmgujarat.ncode.in/web/PG2025/MDMS/PG MD MS FEES 2025-26.pdf',
 'gj-closure':'https://medadmgujarat.ncode.in/WEB/PG2025/MDMS/Compiled_Closure_PG_2025-26_PGMDMS.pdf',
 'gj-bjmc':'https://www.bjmcabd.edu.in/UploadedDocs/News/Joining process for MD -MS Admissions 2025.pdf',
 'mp-cutoffs-r2':'https://dme.mponline.gov.in/ql_dme/DMECounselling_Public/DMEPG/2025/DISPLAY OPENING_CLOSING_PG_MDMS_REPORT_SR_91.pdf',
 'bihar-cutoffs-r1':'https://bceceboard.bihar.gov.in/pdf_Web/REV_PGMAC25_FOCRANK.pdf',
 'rajasthan':'https://rajpgneet2025.in/',
 'wb1':'https://wbmcc.nic.in/pg-medical-counselling/pgmedical-archive-2025/',
 'wb2':'https://wbmcc.nic.in/pg-medical-counselling/pgmedical-archive-2025/page/2/',
 'odisha-guide':'https://dmetodisha.gov.in/files/Guidelines_PG_Medical_2025%20FINAL.pdf',
 'odisha':'http://dmetodisha.gov.in/PG%202025.html'}
 with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:list(pool.map(lambda kv:fetch(*kv),jobs.items()))
 (BASE/'downloads.json').write_text(json.dumps(jobs,indent=2))
