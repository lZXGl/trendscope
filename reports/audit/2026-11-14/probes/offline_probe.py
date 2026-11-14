"""Independent, offline audit; all generated observations are synthetic fixtures."""
import sys, json, tempfile, math, copy, statistics, threading, warnings
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

snapshot = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(snapshot))
import numpy as np
import pandas as pd
import rasterio
from rasterio.transform import from_origin
from src.stats.stats import analyze_trend
from src.pipeline.aoi_request import AoiRequest
from src.pipeline.aoi_job import create_or_reuse_job, run_job
from src.pipeline.job_store import LocalJobStore
from src.pipeline.build import load_job_results
from src.data.fetch import process_modis_rasters, download_appeears_rasters

out = {"snapshot": str(snapshot)}
df = pd.read_csv(snapshot / 'data/processed/nile_delta_ndvi.csv')
r = analyze_trend(df, lat=30.95, lon=31)
raw = df.raw_value.to_numpy(float)
months = df.date.str[5:].tolist()
means = {m: statistics.fmean(v for v, mm in zip(raw, months) if mm == m) for m in set(months)}
y = np.array([v-means[m] for v,m in zip(raw,months)])
n = len(y)
S = sum(int(v>u)-int(v<u) for i,u in enumerate(y) for v in y[i+1:])
_,counts = np.unique(y, return_counts=True)
variance = (n*(n-1)*(2*n+5)-sum(int(t)*(int(t)-1)*(2*int(t)+5) for t in counts))/18
z = (S-1)/math.sqrt(variance) if S>0 else (S+1)/math.sqrt(variance) if S<0 else 0
dates = pd.to_datetime(df.date,format='%Y-%m')
x = np.array([d.year+(d.dayofyear-1)/(366 if d.is_leap_year else 365) for d in dates])
slope = statistics.median((y[j]-y[i])/(x[j]-x[i])*10 for i in range(n) for j in range(i+1,n))
out['baseline'] = {'n':n,'S':S,'variance':variance,'tau_a':S/(n*(n-1)/2),'p':math.erfc(abs(z)/math.sqrt(2)), 'slope':slope,'engine':r['trend'], 'max_anomaly_error':float(max(abs(y-np.array([s['anomaly'] for s in r['series']])))), 'coverage_min':float(df.valid_fraction.min()),'coverage_median':float(df.valid_fraction.median()),'below_80':int((df.valid_fraction<.8).sum())}
out['input_cases']={}
cases={'zero':df.iloc[:0], 'one':df.iloc[:1], 'single_year':df.iloc[:12], 'two_januaries':df.iloc[[0,12]],'duplicate_dates':pd.concat([df,df.iloc[:1]]),'wrong_units':df.assign(unit='degC'),'out_of_range':df.assign(raw_value=5000.),'constant':df.assign(raw_value=.5),'gapped':df.drop(index=[2,3,4,30]),'all_missing':df.assign(raw_value=np.nan)}
for name,data in cases.items():
 try:
  a=analyze_trend(data,lat=30.95,lon=31);out['input_cases'][name]={'accepted':True,'n':len(a['series']),'trend':a['trend']}
 except Exception as e:out['input_cases'][name]={'accepted':False,'error':f'{type(e).__name__}: {e}'}
out['requests']={}
for name,box in {'reversed':[31,31,30,30],'nan':[float('nan'),30,31,31],'antimeridian':[179.8,30,-179.7,30.5],'too_large':[30,30,33,33],'high_lat':[20,85,20.5,85.5],'numeric_strings':['30','30','30.5','30.5'],'distinct_a':[30,30,30.5,30.5],'distinct_b':[31,30,31.5,30.5]}.items():
 try:out['requests'][name]={'id':AoiRequest(bbox=box).job_id()}
 except Exception as e:out['requests'][name]={'error':str(e)}

with tempfile.TemporaryDirectory() as tmp:
 p=Path(tmp);store=LocalJobStore(p/'store');req=AoiRequest((30,30,30.5,30.5));j=create_or_reuse_job(store,req)
 j.update(status='completed',result_file=f"results/{j['job_id']}.json");store.put_job(j);store.put_result(j['job_id'],r)
 try:out['wrong_aoi_cache']={'returned_status':create_or_reuse_job(store,req)['status']}
 except Exception as e:out['wrong_aoi_cache']={'error':str(e)}
 orphan=LocalJobStore(p/'orphan');orphan.put_result(j['job_id'],r)
 try:out['orphan_publication']={'accepted':len(load_job_results(p/'orphan'))}
 except Exception as e:out['orphan_publication']={'error':str(e)}
 # Invalid JSON is not handled as a durable failed job.
 store.put_job(j)
 (p/'store/results'/f"{j['job_id']}.json").write_text('{')
 try:out['corrupt_cache']={'returned':create_or_reuse_job(store,req)['status']}
 except Exception as e:out['corrupt_cache']={'error':f'{type(e).__name__}: {e}','persisted_status':store.get_job(j['job_id'])['status']}

 # Two workers both read queued before either claims. No real NASA calls.
 class MemoryStore:
  def __init__(self):self.job=copy.deepcopy({**j,'status':'queued','nasa_task_id':None,'result_file':None});self.barrier=threading.Barrier(2);self.lock=threading.Lock()
  def get_job(self,_):
   a=copy.deepcopy(self.job);self.barrier.wait(timeout=5);return a
  def put_job(self,j):
   with self.lock:self.job=copy.deepcopy(j)
  def get_result(self,_):return None
  def put_result(self,*args):raise AssertionError('not expected')
 ms=MemoryStore();calls=[];barrier=threading.Barrier(2)
 def submit(*a,**kw):
  with ms.lock:calls.append(kw['task_name'])
  barrier.wait(timeout=5);return f'fake-{threading.get_ident()}'
 def fail_fetch(*a,**kw):raise TimeoutError('offline synthetic interruption')
 def runner(i):return run_job(ms,j['job_id'],'offline',p/str(i),land_check=lambda _:None,submit=submit,fetch=fail_fetch)['status']
 with ThreadPoolExecutor(2) as pool:results=list(pool.map(runner,range(2)))
 out['duplicate_workers']={'fake_nasa_submit_count':len(calls),'final_states':results}

 # Deterministically overlap the two writes immediately before rename.
 ls=LocalJobStore(p/'write-race');barrier=threading.Barrier(2);orig=Path.replace
 def replace(path,target):
  if path.suffix=='.tmp':barrier.wait(timeout=5)
  return orig(path,target)
 def writer(i):
  try:ls.put_job({**j,'error':str(i)});return 'ok'
  except Exception as e:return type(e).__name__
 with patch.object(Path,'replace',replace):
  with ThreadPoolExecutor(2) as pool:out['atomic_write_race']=list(pool.map(writer,range(2)))

 # Synthetic tiny rasters: one valid acquisition in a requested 24-month window.
 raster=p/'rasters';raster.mkdir()
 def write(name,val):
  with rasterio.open(raster/name,'w',driver='GTiff',height=1,width=1,count=1,dtype='int16',crs='EPSG:4326',transform=from_origin(30,31,.01,.01)) as ds:ds.write(np.array([[val]],dtype='int16'),1)
 write('MOD13A3.061_1_km_monthly_NDVI_doy2001001_aid0001.tif',5000)
 write('MOD13A3.061_1_km_monthly_pixel_reliability_doy2001001_aid0001.tif',0)
 a=process_modis_rasters(raster,p/'one.csv',start_ym='2001-01',end_ym='2002-12')
 out['eligibility_missing_calendar']={'requested_months':len(a),'finite_months':int(a.raw_value.notna().sum()),'eligible_pixels_implicitly_at_80pct':int(a.valid_pixel_count.max())}
 # A partial .tif.tmp matching the processor glob is read as a real layer.
 (raster/'MOD13A3.061_1_km_monthly_NDVI_doy2001032_aid0001.tif.tmp').write_bytes(b'partial')
 try:process_modis_rasters(raster,p/'partial.csv');out['partial_glob']='accepted'
 except Exception as e:out['partial_glob']=f'{type(e).__name__}: {e}'

 # Existing corrupt download is treated as an intact cache entry (no download).
 cache=p/'dl';cache.mkdir();(cache/'bad.tif').write_bytes(b'corrupt')
 class Response:
  def __init__(self,d):self.d=d
  def raise_for_status(self):pass
  def json(self):return self.d
 hits=[]
 def get(url,**kw):
  hits.append(url)
  return Response({'status':'done'} if '/task/' in url else {'files':[{'file_name':'bad.tif','file_id':'x'}]})
 with patch('src.data.fetch.requests.get',get):saved=download_appeears_rasters('offline','fake',cache)
 out['corrupt_raster_cache']={'network_calls_to_fakes':len(hits),'files':len(saved),'retained_bytes':(cache/'bad.tif').read_text()}

print(json.dumps(out,indent=2,allow_nan=False))
