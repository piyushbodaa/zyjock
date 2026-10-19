"""Publish independent state snapshots and financial reports with explicit coverage."""
import json,hashlib,re
from collections import Counter,defaultdict
from pathlib import Path

def compile_expansion(root,dist,program,specialty):
    manifest=json.loads((dist/'data.json').read_text())
    inputs=[]
    for p in sorted((root/'sources'/'regions').glob('*.json')):
        inputs.append(json.loads(p.read_text()))
    national=root/'sources'/'national'/'financials.json'
    if national.exists():inputs.append(json.loads(national.read_text()))
    state_docs={};institutes={i['id']:i for i in manifest['institutes']};records=[];finance=[];sources=[]
    for batch in inputs:
        for s in batch.get('states',[]):
            state_docs[s['name']]=dict(s)
        for i in batch.get('institutes',[]):
            if i['id'] in institutes and institutes[i['id']]['name']!=i['name']:raise ValueError('Conflicting institution identity: '+i['id'])
            institutes[i['id']]=i
        records.extend(batch.get('records',[]));finance.extend(batch.get('financials',[]));sources.extend(batch.get('sources',[]))
    old_finance=manifest.get('financials',[])
    for n,f in enumerate(old_finance):
        f=dict(f);f.setdefault('id','initial-finance-'+str(n));f.setdefault('title',f.get('instituteName','Institution financial source'))
        f.setdefault('state','Chandigarh' if str(f.get('instituteCode'))=='700468' else 'Karnataka' if 'John' in f.get('instituteName','') else 'Not specified')
        f.setdefault('scope',f.get('feeScope','Institution publication'));finance.append(f)
    existing_sources={s.get('url') for s in manifest['sources']}
    for s in sources:
        if s.get('url') and s['url'] not in existing_sources:manifest['sources'].append(s);existing_sources.add(s['url'])
    by_state=defaultdict(list);ids=set();unpublished=[]
    for r in records:
        r=dict(r)
        if r['id'] in ids:raise ValueError('Duplicate state record: '+r['id'])
        ids.add(r['id'])
        if r['instituteId'] not in institutes:raise ValueError('Missing institution: '+r['instituteId'])
        state=r.get('jurisdiction') or institutes[r['instituteId']]['state']
        # Tripura's published nominations include an institution located in Assam.
        if r.get('counselling','').startswith('Tripura'):state='Tripura'
        if state not in state_docs:
            # Acquisition batches without a curated jurisdiction registry entry
            # (authority, coverage note, source desk) stay unpublished.
            unpublished.append(state);continue
        r['jurisdiction']=state
        r.update(exam='NEET PG',dataStatus='verified',dataset='state:'+state)
        r.setdefault('program',program(r['course']));r.setdefault('specialty',specialty(r['course']))
        r.setdefault('rankType','Not specified')
        if r['recordKind']=='cutoff' and r['rankType'] not in ['NEET PG AIR','State merit rank']:raise ValueError('Unspecified cutoff rank scale: '+r['id'])
        for k in ['openingRank','closingRank','seats','annualFee','monthlyStipend','bondYears','bondPenalty','previousSeats']:
            r.setdefault(k,None)
        if not r.get('sourceUrl','').startswith(('https://','http://')):raise ValueError('Missing official source: '+r['id'])
        by_state[state].append(r)
    for old in list(dist.glob('state-records-*.json'))+list(dist.glob('financial-records-*.json')):old.unlink()
    catalogue=[]
    for name,s in sorted(state_docs.items()):
        rows=by_state[name];key=re.sub('[^a-z0-9]+','-',name.lower()).strip('-');files=[]
        for n,offset in enumerate(range(0,len(rows),2500)):
            fn=f'state-records-{key}-{n}.json';(dist/fn).write_text(json.dumps(rows[offset:offset+2500],ensure_ascii=False,separators=(',',':')));files.append(fn)
        snapshots=defaultdict(int)
        for r in rows:
            if r['recordKind']=='seat-matrix' and r.get('seats') is not None:snapshots[(r['year'],r['round'],r['counselling'])]+=r['seats']
        financial=[f for f in finance if f.get('state')==name]
        catalogue.append({**s,'id':'state:'+name,'recordFiles':files,'recordCount':len(rows),'seatRecords':sum(r['recordKind']=='seat-matrix' for r in rows),'cutoffRecords':sum(r['recordKind']=='cutoff' for r in rows),'years':sorted({r['year'] for r in rows},reverse=True),'rankTypes':sorted({r['rankType'] for r in rows if r['recordKind']=='cutoff'}),'financialRecords':len(financial),'seatSnapshots':[{'year':k[0],'round':k[1],'counselling':k[2],'seats':v} for k,v in snapshots.items()],'checkedAt':s.get('checkedAt','2026-10-19')})
    financial_ids=set();unique_finance=[]
    for n,f in enumerate(finance):
        f=dict(f);f.setdefault('id','financial-'+hashlib.sha1(json.dumps(f,sort_keys=True).encode()).hexdigest()[:14])
        if f['id'] in financial_ids:continue
        financial_ids.add(f['id']);f.setdefault('checkedAt','2026-10-19')
        for k in ['annualFee','monthlyStipend','bondYears','bondPenalty','discontinuationPenalty']:f.setdefault(k,None)
        if not f.get('sourceUrl'):raise ValueError('Financial report missing source')
        unique_finance.append(f)
    financial_files=[]
    for n,offset in enumerate(range(0,len(unique_finance),250)):
        fn=f'financial-records-{n}.json';(dist/fn).write_text(json.dumps(unique_finance[offset:offset+250],ensure_ascii=False,separators=(',',':')));financial_files.append(fn)
    summary={'jurisdictions':len(catalogue),'jurisdictionsWithRecords':sum(s['recordCount']>0 for s in catalogue),'stateRecords':sum(s['recordCount'] for s in catalogue),'stateCutoffRecords':sum(s['cutoffRecords'] for s in catalogue),'stateSeatRecords':sum(s['seatRecords'] for s in catalogue),'financialReports':len(unique_finance),'financialStates':len({f['state'] for f in unique_finance if f.get('state') and f['state'] not in ['All India','Not specified']}),'financialInstitutions':len({str(f.get('instituteCode') or f.get('instituteName')) for f in unique_finance if f.get('instituteCode') or f.get('instituteName')}),'fields':{k:sum(f.get(k) is not None for f in unique_finance) for k in ['annualFee','monthlyStipend','bondYears','bondPenalty']},'checkedAt':'2026-10-19','complete':False,'unpublishedRecords':len(unpublished),'unpublishedJurisdictions':sorted(set(unpublished))}
    manifest.update(institutes=list(institutes.values()),stateCatalog=catalogue,expansion=summary,financialRecordFiles=financial_files,financials=[])
    manifest['recordDefaults'].update(rankType='NEET PG AIR',dataset='mcc')
    manifest['coverage']['limitations'][0]='The overview totals describe MCC only. State snapshots are separate datasets with their own authorities, source years and rank scales. See State counselling for jurisdiction-by-jurisdiction coverage.'
    manifest['coverage']['limitations'][4]='Financial reports preserve their source year, scope and fee period. Many institution reports contain free-text conditions. Unknown values remain blank. Published reports are not proof of actual stipend payment.'
    manifest['coverage']['summary']+=' State datasets and financial reports are separately indexed; national completeness is not claimed.'
    (dist/'data.json').write_text(json.dumps(manifest,ensure_ascii=False,separators=(',',':')))
    (root/'sources'/'expansion-summary.json').write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary,indent=2))
