import requests, pathlib,subprocess,concurrent.futures,json
ROOT=pathlib.Path(__file__).parent
sources={
'hp-matrix':'https://amruhp.ac.in/wp-content/uploads/2025/11/final-state-quota-seat-matrix-for-PG-MD-MS-DNB-for-state-quota-for-website-2025.pdf',
'hp-prospectus':'https://amruhp.ac.in/wp-content/uploads/2025/10/Final-Corrected-PG-MD-MS-2025-merged-prospcus-for-website.pdf',
'hp-r1':'https://amruhp.ac.in/wp-content/uploads/2025/11/Final-Seat-Allocation-of-MD-MS-DNB-1st-round-Counselling-2025-merged.pdf',
'hp-r2':'https://amruhp.ac.in/wp-content/uploads/2025/12/Final-Seat-Allocation-of-MD-MS-DNB-2nd-Round-Counselling-2025-merged.pdf',
'hp-r3':'https://amruhp.ac.in/wp-content/uploads/2026/02/Final-Seat-Allocation-of-MD-MS-DNB-3rd-round-Counselling-2025-merged.pdf',
'hp-stray':'https://amruhp.ac.in/wp-content/uploads/2026/02/Final-Seat-Allocation-of-MD-MS-DNB-Stray-Round-Counselling-2025-merged.pdf',
'hp-stray2':'https://amruhp.ac.in/wp-content/uploads/2026/02/Final-Seat-allocation-of-MD-MS-DNB-2nd-Stray-Round-counselling-2025-merged.pdf'
}
def get(k,u):
 p=ROOT/'raw'/f'{k}.pdf'
 if not p.exists():
  try: r=requests.get(u,timeout=60)
  except requests.exceptions.SSLError:
   import urllib3;urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning);r=requests.get(u,timeout=60,verify=False)
  r.raise_for_status();p.write_bytes(r.content)
 subprocess.run(['pdftotext','-layout',str(p),str(p.with_suffix('.txt'))],check=True)
 return k,len(p.read_bytes())
if __name__=='__main__':
 index=ROOT/'document-index.json'
 if index.exists():sources.update(json.loads(index.read_text()))
 with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:
  futures={ex.submit(get,k,u):k for k,u in sources.items() if k!='zmc-fees'}
  for f in concurrent.futures.as_completed(futures):
   try:print(f.result())
   except Exception as e:print(futures[f],type(e).__name__)
 index.write_text(json.dumps(sources,indent=2))
