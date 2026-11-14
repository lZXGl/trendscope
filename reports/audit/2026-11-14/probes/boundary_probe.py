import sys,json,tempfile,copy,threading,urllib.request,urllib.error
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from http.server import ThreadingHTTPServer
sys.path.insert(0,str(Path(sys.argv[1]).resolve()))
from src.pipeline.aoi_request import AoiRequest
from src.pipeline.aoi_job import create_or_reuse_job,run_job
from src.pipeline.job_store import LocalJobStore
import pandas as pd
out={}
snapshot=Path(sys.argv[1]).resolve()
with tempfile.TemporaryDirectory() as tmp:
 p=Path(tmp);store=LocalJobStore(p/'jobs');req=AoiRequest((30,30,30.5,30.5));j=create_or_reuse_job(store,req);count=[]
 def submit(*a,**kw):count.append(1);return 'offline-task'
 def wrong_fetch(token,aoi,**kw):
  proc=kw['processed_dir'];proc.mkdir(parents=True,exist_ok=True)
  data=pd.read_csv(snapshot/'data/processed/nile_delta_ndvi.csv');data['region']=aoi['region_id'];data.to_csv(proc/f"{aoi['region_id']}_ndvi.csv",index=False)
  meta=proc/'mismatched_meta.json';meta.write_text(json.dumps({'status':'ok','dataset_id':'WRONG-DATASET','aoi':{'bbox':[100,40,100.5,40.5]},'nasa_task_id':'OTHER-TASK','processing_rules':{'min_pixel_presence':0.1,'allow_marginal':True}}));return meta
 a=run_job(store,j['job_id'],'offline',p/'work',land_check=lambda _:None,submit=submit,fetch=wrong_fetch)
 out['mismatched_fetch_manifest']={'state':a['status'],'error':a['error'],'result_region':(store.get_result(j['job_id']) or {}).get('metadata',{}).get('region')}
 other=AoiRequest((31,30,31.5,30.5));k=create_or_reuse_job(store,other)
 def expired(*a,**kw):
  pp=kw['processed_dir'];pp.mkdir(parents=True,exist_ok=True);f=pp/'expired.json';f.write_text(json.dumps({'status':'failed','error':'AppEEARS task offline-task failed with status: expired'}));return f
 attempts=[]
 for i in range(2):
  s=run_job(store,k['job_id'],'offline',p/'expire',land_check=lambda _:None,submit=submit,fetch=expired);attempts.append({k:s[k] for k in ['status','retryable','nasa_task_id']});create_or_reuse_job(store,other)
 out['expired_retry']={'attempts':attempts,'fake_submit_total_including_first_probe':len(count)}
 if (snapshot/'src/pipeline/job_api.py').exists():
  from src.pipeline.job_api import make_handler,job_result,submit as api_submit
  orphan=LocalJobStore(p/'orphan');orphan.put_result(k['job_id'],{'synthetic_test_only':True})
  out['api_orphan_result']=job_result(k['job_id'],orphan)
  server=ThreadingHTTPServer(('127.0.0.1',0),make_handler(LocalJobStore(p/'http'),lambda *a:None));t=threading.Thread(target=server.serve_forever,daemon=True);t.start()
  address=f'http://127.0.0.1:{server.server_port}/api/jobs'
  for method in ['OPTIONS','POST']:
   body=json.dumps(req.to_dict() | {}).encode() if method=='POST' else None
   if method=='POST':body=json.dumps({'bbox':list(req.bbox)}).encode()
   request=urllib.request.Request(address,data=body,method=method,headers={'Content-Type':'application/json','Origin':'https://example.invalid','Access-Control-Request-Method':'POST'})
   try:response=urllib.request.urlopen(request)
   except urllib.error.HTTPError as e:response=e
   out['http_'+method]={'status':response.status,'allow_origin':response.headers.get('Access-Control-Allow-Origin')}
  server.shutdown();server.server_close()
print(json.dumps(out,indent=2))
