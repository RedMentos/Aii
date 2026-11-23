"""Zero-native replay of the native46 row-9+ SQLite write/close boundaries on a copy of checkpoint65-first8."""
import json,shutil,sys,time
from pathlib import Path
APP=Path(sys.argv[1]);WORK=Path(sys.argv[2]);ROWS=int(sys.argv[3]);sys.path.insert(0,str(APP))
from v13.runtime import Runtime
from v13.store import Store,audit_closed
from scripts.export_live_output_dataset import select_label,persist_export_decision
P=APP/'docs/proofs/causal-output-lifecycle-20261009';ACT=P/'native46-actual'
home=WORK/'home';shutil.rmtree(WORK,ignore_errors=True);(home/'data/db').mkdir(parents=True)
shutil.copytree(ACT/'isolated-home/config',home/'config')
shutil.copyfile(APP/'docs/proofs/sqlite-native46-diagnosis-20261009/checkpoint65-first8.sqlite3',home/'data/db/brain.sqlite3')
manifest=json.loads((ACT/'manifest.json').read_text());failed=json.loads((P/'native46-failed-report.json').read_text())
ans=failed['rows'][8]['answer'];meta=ans['metadata'];row8=ACT/'export-row-8';abi=json.loads((row8/'binding.json').read_text())['feature_abi']
log=[]
def audit(i,b):
    a=audit_closed(home);a.update(row=i,boundary=b);log.append(a)
    if not a['ok']:raise SystemExit(json.dumps({'status':'FAILED','at':a},indent=1))
audit(8,'start-first8')
for i in range(8,8+ROWS):
    fx=manifest['rows'][i%len(manifest['rows'])]
    r=Runtime(home)
    try:
        e=r.store.event(r.session,fx['input']);r._causal_output_context(e,[{'role':'user','content':fx['input']}],[])
        mid=r.store.message(r.session,e['event_id'],'assistant','',status='STREAMING')
        for chunk in ans['text'].split(' '):r.store.append_message(mid,chunk+' ')
        r.store.finish_message(mid,'FINAL',meta)
        for k in range(12):r.store.log('turn_stage',e['event_id'],{'status':'ok','duration_s':k*.1})
        r.learner.output_feedback(e['event_id'],fx['human_reference'],'learn')
        rev=r.models.revision('C3_LANGUAGE');d=json.loads(r.store.one("SELECT payload FROM packets WHERE kind='HumanDecision' AND event_id=? ORDER BY created DESC LIMIT 1",(e['event_id'],))['payload'])
    finally:r.close()
    audit(i,'runtime-close')
    s=Store(home)
    try:persist_export_decision(s,select_label(s,d['packet_id'],d['source_ref']['source_id'],rev,True),row8/'observed.json',abi,True)
    finally:s.close()
    audit(i,'export-close')
    s=Store(home);s.close();audit(i,'verify-close')
print(json.dumps({'status':'ALL_BOUNDARIES_OK','rows_replayed':ROWS,'boundaries':len(log),'final':log[-1]},indent=1))
(WORK/'replay-log.json').write_text(json.dumps(log,indent=1))
