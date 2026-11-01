import datetime,hashlib,importlib.metadata,json,os,pathlib,re,subprocess,time,zipfile
import psutil
ROOT=pathlib.Path('/workspace/scratch/5a9214d3f329/night-phone-qa/V13-Phone')
OUT=pathlib.Path(__file__).resolve().parent
ZIP=pathlib.Path('/workspace/scratch/5a9214d3f329/deliverables/V13-Redmi-Install-20261011-Webchat.zip')
EXPECTED='477593e79a6069210258d91500ca9a42b0dfeaadf696d9788b09c3a63679a88a'
PYTHON='/workspace/scratch/5a9214d3f329/training-resources/venv/bin/python'
def stamp():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def verify():
 manifest=json.loads((ROOT/'WORKSPACE_FILES.json').read_text()); bad=[]
 for name,h in manifest['files'].items():
  p=ROOT/name
  if not p.is_file() or sha(p)!=h:bad.append(name)
 return {'manifest_sha256':sha(ROOT/'WORKSPACE_FILES.json'),'files':len(manifest['files']),'mismatches':bad}
def events():
 p=pathlib.Path('/sys/fs/cgroup/memory.events')
 return {k:int(v)for k,v in (l.split()for l in p.read_text().splitlines())} if p.is_file()else None
assert sha(ZIP)==EXPECTED
with zipfile.ZipFile(ZIP) as z:assert z.testzip()is None; zip_entries=len(z.namelist())
before=verify();assert before['files']==495 and not before['mismatches']
start={'schema':'V13_IMMUTABLE_PHONE_QA_START_V1','started_at':stamp(),'local_source_head':'f0cc27f','source_tree_prefix':'0bd3b','zip_sha256':EXPECTED,'zip_bytes':ZIP.stat().st_size,'zip_entries':zip_entries,'extracted_root':str(ROOT),'manifest_before':before,'packages':{p:importlib.metadata.version(p)for p in ('torch','transformers','peft','safetensors','Pillow')},'command':[PYTHON,'-u','-m','unittest','discover','-s','tests','-v'],'environment':{'OMP_NUM_THREADS':'1','MKL_NUM_THREADS':'1'},'cgroup_events_before':events(),'phone_hardware_measured':False,'native_quality_claim':False}
(OUT/'start.json').write_text(json.dumps(start,indent=2)+'\n')
t=time.monotonic();peak=0;samples=0
with (OUT/'unittest.log').open('w') as log:
 p=subprocess.Popen(start['command'],cwd=ROOT,env=dict(os.environ,**start['environment']),stdout=log,stderr=subprocess.STDOUT)
 while p.poll()is None:
  try:peak=max(peak,psutil.Process(p.pid).memory_info().rss);samples+=1
  except psutil.Error:pass
  time.sleep(.5)
code=p.returncode;after=verify();text=(OUT/'unittest.log').read_text();footer=re.findall(r'Ran (\d+) tests in ([0-9.]+)s\n\n(OK(?: \([^\n]+\))?|FAILED[^\n]*)',text)
result={'schema':'V13_IMMUTABLE_PHONE_QA_RESULT_V1','finished_at':stamp(),'exit_code':code,'elapsed_seconds':round(time.monotonic()-t,3),'footer':footer[-1]if footer else None,'manifest_after':after,'manifest_unchanged':before==after,'peak_owned_python_rss_bytes':peak,'rss_samples':samples,'cgroup_events_after':events(),'log_sha256':sha(OUT/'unittest.log'),'all_checks_passed':code==0 and bool(footer)and footer[-1][2].startswith('OK')and before==after,'phone_hardware_measured':False,'native_quality_claim':False}
(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2),flush=True)
raise SystemExit(0 if result['all_checks_passed']else 1)
