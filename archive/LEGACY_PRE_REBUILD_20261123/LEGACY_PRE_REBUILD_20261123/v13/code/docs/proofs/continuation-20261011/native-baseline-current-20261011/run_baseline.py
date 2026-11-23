import sys,json,time,threading,subprocess,platform,traceback,os,shutil
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
ROOT=Path('/workspace/scratch/7d5ad9273a5e/native_baseline_current_oct11');sys.path.insert(0,str(ROOT/'frozen'))
from v13.config import initialize
from v13.models import ModelManager,catalog,platform_tag,download_file
from v13.bootstrap import extract
from v13.common import file_hash,atomic_write,dumps
from v13.runners import LlamaRunner
from v13.resources import device,process_memory
HOME=Path('/workspace/scratch/7d5ad9273a5e/native_baseline_oct11/home'); OUT=Path('/workspace/scratch/7d5ad9273a5e/native-baseline-current-20261011');OUT.mkdir(exist_ok=True)
rep={'proof_kind':'PINNED_C3_LINUX_BASELINE','created_wall_time':time.time(),'platform':device(),'phone_measured':False,'memory':'NONE_FRESH_HOME','sparse_memory':False,'native_weight_learning':False,'repeat_reason':'Current runner lifecycle materially changed after first baseline; repeat same four fixtures on frozen finalized source.', 'status':'SETUP_RUNNING','rows':[],'failures':[],'claim_limits':['Linux software proof only, not Redmi.','Tiny lexical fixtures are not validated general model quality.','No sparse, native weight learning, B1/B2 or C2 exercised.']}
def save():atomic_write(OUT/'report.json',dumps(rep))
def progress(x):print(x,flush=True)
save()
try:
 cfg=initialize(HOME); mm=ModelManager(HOME);spec=catalog();rep['pinned_model']=spec['models']['language'];rep['runner_spec']=spec['runner'];save()
 def runner_setup():
  archive=download_file(spec['runner']['linux_binaries'][platform_tag()],HOME/'tmp/llama-bin.tar.gz',progress)
  extract(archive,HOME/'bin'/spec['runner']['tag']);found=list((HOME/'bin'/spec['runner']['tag']).rglob('llama-server'))
  if len(found)!=1:raise RuntimeError('Native llama-server not unique')
  target=found[0];target.chmod(0o700);link=HOME/'bin/llama-server';link.unlink(missing_ok=True);link.symlink_to(target)
  version=subprocess.run([str(link),'--version'],capture_output=True,text=True,timeout=15)
  if version.returncode:raise RuntimeError('Runner failed version: '+version.stderr)
  result={'tag':spec['runner']['tag'],'archive_sha256':file_hash(archive),'binary_sha256':file_hash(link),'version':version.stdout+version.stderr,'platform':platform_tag(),'phone_runner_proof':None}
  atomic_write(HOME/'config/runner.json',dumps(result));return result
 rep['installed_runner']=json.loads((HOME/'config/runner.json').read_text());assert file_hash(HOME/'bin/llama-server')==rep['installed_runner']['binary_sha256']
 model=mm.path_for('C3_LANGUAGE');rep['model_sha256']=file_hash(model);rep['model_revision']=mm.revision('C3_LANGUAGE');rep['deep_model_verify']=mm.verify(deep=True)
 cfg=dict(cfg,context_tokens=2048,answer_tokens=64,history_turns=0,threads=2,deadline_seconds=90)
 rep['config']=cfg;rep['status']='INFERENCE_RUNNING';save()
 fixtures=[{'id':'en_greeting','system':'Answer briefly and naturally in English.','user':'Say hello briefly. What could I ask you first?','required_any':['hello','hi']},
 {'id':'de_greeting','system':'Antworte kurz und natürlich auf Deutsch.','user':'Sag kurz Hallo auf Deutsch. Was kann ich dich als Erstes fragen?','required_any':['hallo','hi']},
 {'id':'en_grounded_recall','system':'Answer only from the provided sentence. Give only the budget amount.','user':'Source: Project Aurora has a budget of 120 euros. Question: How large is the budget?','required_all':['120']},
 {'id':'de_grounded_recall','system':'Antworte ausschließlich aus dem gegebenen Satz. Gib nur den Budgetbetrag aus.','user':'Quelle: Projekt Aurora hat ein Budget von 120 Euro. Frage: Wie hoch ist das Budget?','required_all':['120']}]
 rep['fixtures']=fixtures;save()
 for fixture in fixtures:
  # Fresh child for every independent row: no chat history, prompt cache or approved memories.
  r=LlamaRunner(HOME,'C3_LANGUAGE',model,cfg);row={'fixture_id':fixture['id'],'output':'','status':'RUNNING','started_wall_time':time.time()};rep['rows'].append(row);save();started=time.monotonic()
  try:
   for token in r.generate([{'role':'system','content':fixture['system']},{'role':'user','content':fixture['user']}],threading.Event(),time.monotonic()+90,max_tokens=64,seed=13):row['output']+=token
   row['status']='FINAL';low=row['output'].casefold();checks={}
   if fixture.get('required_any'):checks['required_any']=any(x in low for x in fixture['required_any'])
   if fixture.get('required_all'):checks['required_all']=all(x in low for x in fixture['required_all'])
   row['checks']=checks;row['checks_pass']=all(checks.values()) and bool(row['output'].strip())
  except BaseException as exc:
   row['status']='ERROR';row['error']=repr(exc);row['traceback']=traceback.format_exc()
  finally:
   row['elapsed_s']=time.monotonic()-started;row['metrics']=r.last_metrics;row['unload']=r.unload();row['memory_binding']=r.memory_delivery_binding;save();print(json.dumps(row,ensure_ascii=False),flush=True)
 rep['status']='NATIVE_SMOKE_PASS' if all(x['status']=='FINAL' and x['checks_pass'] for x in rep['rows']) else 'NATIVE_SMOKE_FAIL';save()
except BaseException as exc:
 rep['status']='SETUP_OR_RUN_FAILED';rep['failures'].append({'error':repr(exc),'traceback':traceback.format_exc()});save();traceback.print_exc()
finally:
 if (HOME/'logs/C3_LANGUAGE.log').exists():shutil.copyfile(HOME/'logs/C3_LANGUAGE.log',OUT/'llama-server.log')
 shutil.copyfile(Path(__file__),OUT/'run_baseline.py')
 print('REPORT_STATUS='+rep['status'],flush=True)
