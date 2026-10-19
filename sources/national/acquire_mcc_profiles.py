"""Fetch public MCC institute reports through their published form, without login."""
import requests,re,html,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
URL='https://mcc.admissions.nic.in/Applicant/Report/ViewInstituteProfileDynamic.aspx?enc=b3y6S6rqn323+Rrps4aJmWq6uDzwcVyR2D994Iqx3miWKIwOHdAUl7I6zs1LI/bNq85fKhJWyvHvAMhgNvbzOg=='
P='ctl00$ContentPlaceHolder1$'
def form(s):
 f={}
 for tag in re.findall(r'<input\b[^>]*>',s):
  a=dict(re.findall(r'([\w:$-]+)="([^"]*)"',tag))
  if a.get('type')=='hidden' and a.get('name'): f[a['name']]=html.unescape(a.get('value',''))
 for name,body in re.findall(r'<select\b[^>]*name="([^"]+)"[^>]*>([\s\S]*?)</select>',s):
  opts=re.findall(r'<option([^>]*)>([\s\S]*?)</option>',body)
  for attrs,text in opts:
   if 'selected=' in attrs:
    f[name]=html.unescape(re.search(r'value="([^"]*)"',attrs)[1]);break
  else:
   if opts:f[name]=html.unescape(re.search(r'value="([^"]*)"',opts[0][0])[1])
 return f
def post(s,page,event,values):
 f=form(page);f.update(values);f.update(__EVENTTARGET=event,__EVENTARGUMENT='')
 r=s.post(URL,data=f,timeout=180);r.raise_for_status();return r
if __name__=='__main__':
 s=requests.Session();r=s.get(URL,timeout=45);r.raise_for_status()
 for step,name in enumerate(['ddlInstType','ddlInstitutes']):
  r=post(s,r.text,P+name,{P+name:'All'});(ROOT/f'mcc-profile-step-{step}.html').write_text(r.text)
  for m in re.finditer(r'<select\b[^>]*name="([^"]+)"[^>]*>([\s\S]*?)</select>',r.text):
   print(m[1], 'options',m[2].count('<option'),m[2][:400] if 'ddlprogram' in m[1] else '',flush=True)
 vals={P+'ddlInstType':'All',P+'ddlInstitutes':'All',P+'ddlprogram':'All',P+'btnsubmit':'Submit'}
 r=post(s,r.text,'',vals)
 (ROOT/'mcc-profile-result.html').write_text(r.text)
 print('RESULT',r.status_code,r.headers.get('content-type'),len(r.content),r.url,flush=True)
 print(re.findall(r'(?:src|href)="([^"]+)"',r.text)[-30:],flush=True)
