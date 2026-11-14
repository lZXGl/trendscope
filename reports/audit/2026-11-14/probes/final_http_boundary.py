import sys,tempfile,json,io
from pathlib import Path
sys.path.insert(0,str(Path(sys.argv[1]).resolve()))
from src.pipeline.job_runtime import Application
from src.pipeline.job_store import LocalJobStore
class Worker:
 def dispatch(self,*a):pass
with tempfile.TemporaryDirectory() as d:
 store=LocalJobStore(Path(d));app=Application(store,Worker(),token='audit-only-token-0000000000000000000000');out={}
 def call(body,auth=True):
  raw=json.dumps(body).encode();status=[]
  e={'REQUEST_METHOD':'POST','PATH_INFO':'/api/jobs','CONTENT_TYPE':'application/json','CONTENT_LENGTH':str(len(raw)),'wsgi.input':io.BytesIO(raw)}
  if auth:e['HTTP_AUTHORIZATION']='Bearer audit-only-token-0000000000000000000000'
  data=b''.join(app(e,lambda s,h:status.append(s)));return [status[0],json.loads(data)]
 out['frontend_without_authorization']=call({'bbox':[30,30,30.5,30.5]},False)
 out['authorized_valid_request']=call({'bbox':[30,30,30.5,30.5]})
 p=Path(d)/'jobs/aoi_0000000000000000.json';p.write_text('{broken')
 out['new_unrelated_request_after_corrupt_job']=call({'bbox':[31,30,31.5,30.5]})
 print(json.dumps(out,indent=2))
