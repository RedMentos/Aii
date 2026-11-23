import json,os,sys,datetime,subprocess,shutil,traceback
from pathlib import Path
APP=Path('/workspace/scratch/5a9214d3f329/v13-work/Aii/v13/code')
sys.path.insert(0,str(APP))
from v13.models import ModelManager,download_file
from v13.memory_server import build,runtime_library_hashes
from v13.bootstrap import extract
from v13.common import file_hash,atomic_write,dumps
home=Path('/workspace/scratch/5a9214d3f329/native-audit-cache')
proof=APP/'docs/proofs/continuation-20261011/night-native-recovery-20261011'
old=json.loads((APP/'docs/proofs/continuation-20261011/resource-recovery-20261011/native-resource-recovery.json').read_text())
report={'schema':'v13_native_second_pruning_resource_recovery_v1','started_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'reason':'Second automated workspace maintenance removed native cache; durable original binding preserved on GitHub','original_recovery_report_sha256':file_hash(APP/'docs/proofs/continuation-20261011/resource-recovery-20261011/native-resource-recovery.json'),'heavy_inference_started':False,'canonical_gate_pass':False,'phone_proof':False,'status':'RESTORING','events_before':Path('/sys/fs/cgroup/memory.events').read_text()}
def save():atomic_write(proof/'native-resource-recovery.json',dumps(report))
save()
try:
    models=ModelManager(home)
    for key in ['body','gist','language']:
        if models.specs['models'][key]!=old['models'][key]:raise ValueError('Catalog mismatch '+key)
        models.install(key)
        print('MODEL VERIFIED',key,flush=True)
    report['model_deep_verification']=models.verify(deep=True);save()
    arc=old['source_archive'];dst=home/'tmp/llama-source.tar.gz'
    download_file({'url':arc['source_url'],'sha256':arc['source_sha256'],'size':arc['source_size']},dst)
    extract(dst,home/'source');source=home/'source/llama.cpp-b10964'
    report['source_archive_verified']=file_hash(dst)==arc['source_sha256'];save()
    manifest=build(home,source,jobs=2)
    target=home/'bin/build-mem-b10964/bin/llama-server'
    link=home/'bin/llama-server';tmp=link.with_name('llama-server.new');tmp.unlink(missing_ok=True);tmp.symlink_to(target);os.replace(tmp,link)
    observed={'model_sha256':{r:file_hash(models.path_for(r)) for r in ('B1_DETAIL','B2_GIST','C3_LANGUAGE')},'model_revisions':{r:models.revision(r) for r in ('B1_DETAIL','B2_GIST','C3_LANGUAGE')},'runner_sha256':file_hash(link),'runner_runtime_libraries_sha256':runtime_library_hashes(link)}
    expected=old['previous_installed_binding']
    report['current_installed_binding']=observed;report['binding_comparison']={k:expected[k]==v for k,v in observed.items()};report['same_original_installed_binding']=all(report['binding_comparison'].values())
    report['patched_source_sha256']={p:file_hash(source/p) for p in old['patched_native_source_sha256']};report['patched_sources_exact']=report['patched_source_sha256']==old['patched_native_source_sha256']
    report['memory_server_manifest']=manifest
    version=subprocess.run([str(link),'--version'],capture_output=True,text=True,timeout=20)
    report['version_result']={'returncode':version.returncode,'stdout':version.stdout,'stderr':version.stderr}
    atomic_write(home/'config/runner.json',dumps({'tag':'b10964','platform':'linux-x86_64','binary_sha256':file_hash(link),'version':(version.stdout+version.stderr).strip(),'phone_runner_proof':None}))
    report['events_after']=Path('/sys/fs/cgroup/memory.events').read_text()
    report['cmake_version']=subprocess.run(['cmake','--version'],capture_output=True,text=True).stdout.splitlines()[0]
    report['status']='RESTORED_EXACT_BINDING' if report['same_original_installed_binding'] and report['patched_sources_exact'] and version.returncode==0 else 'BINDING_MISMATCH'
    report['completed_at']=datetime.datetime.now(datetime.timezone.utc).isoformat();save()
    shutil.copyfile(home/'logs/build.log',proof/'native-build.log')
    print(json.dumps({'status':report['status'],'binding_comparison':report['binding_comparison'],'patched_sources_exact':report['patched_sources_exact'],'library_entries':len(observed['runner_runtime_libraries_sha256'])},indent=2),flush=True)
except Exception:
    report['status']='FAILED';report['error']=traceback.format_exc();save();raise
