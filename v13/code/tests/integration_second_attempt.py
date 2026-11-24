"""Canon §24.1 real-weight second-attempt family, isolated from the operator's brain.

Every completed case is saved immediately. Lexical output markers are diagnostic;
retrieval lineage, native inference and unchanged weights are independently checked.
"""
import argparse
import json
from pathlib import Path
import re
import shutil
import sys
import tempfile
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from v13.common import APP,atomic_write,file_hash,digest
from v13.config import initialize,save_config
from v13.proofs import archive_previous
from v13.runtime import Runtime
from v13.resources import device

QUESTION='Welches Budget hat Projekt Aurora? Sag nur den Betrag, falls er bekannt ist.'
CORRECTION='Das Budget von Projekt Aurora beträgt 120 Euro. Es gelten weiterhin die Vorgaben: nur lokal, keine Cloud.'
CASES=[
    ('same_task',QUESTION,True,[120]),
    ('paraphrase','Wie viel Budget steht Projekt Aurora zur Verfügung?',True,[120]),
    ('reordered_paraphrase','Projekt Aurora hat welches verfügbare Budget?',True,[120]),
    ('partial_transfer','Für Projekt Aurora: Wie viel bleibt vom Budget nach einer Ausgabe von 30 Euro?',True,[90]),
    ('second_transfer','Wie viel ist die Hälfte des Budgets von Projekt Aurora?',True,[60]),
    ('constraint_retention','Wie hoch ist das Budget von Projekt Aurora? Beachte weiterhin die lokale Vorgabe.',True,[120]),
    ('negative_other_project','Welches Budget hat Projekt Borealis? Sag nur den Betrag, falls er bekannt ist.',False,[]),
    ('negative_other_attribute','Wer leitet Projekt Aurora? Nenne nur den Namen, falls er bekannt ist.',False,[]),
    ('negative_adjacent_topic','Wann ist die Deadline von Projekt Aurora? Nenne nur das Datum, falls es bekannt ist.',False,[]),
]

def run(installed,out):
    installed=Path(installed).resolve();out=Path(out).resolve();out.parent.mkdir(parents=True,exist_ok=True);archive_previous(out)
    report={'proof_kind':'STEP3_SECOND_ATTEMPT_FAMILY','status':'RUNNING','uses_real_weights':True,'phone_measured':device()['android'],'device':device(),'turns':[],
            'canon':'§24.1 / STEP3','source_hashes':{str(p.relative_to(APP)):file_hash(p) for p in list((APP/'v13').glob('*.py'))+[Path(__file__).resolve()]},
            'semantic_advantage_proven':False,'claim_limits':['Small diagnostic family, not a general semantic benchmark.','Expected-number presence cannot validate assignment or reasoning.','Exact source-backed recall is memory adaptation, not JEPA or body-weight learning.','No canned answer, model inference mock or response-cache replacement is used.']}
    def save():atomic_write(out,json.dumps(report,ensure_ascii=False,indent=2))
    save();runtime=None
    with tempfile.TemporaryDirectory(prefix='v13-second-attempt-') as tmp:
        try:
            home=Path(tmp);cfg=initialize(home);cfg.update(observer_mode='off',route_override='detail',history_turns=0,answer_tokens=128,learning_mode='RECORD_ONLY');save_config(home,cfg)
            for name in ['models','bin']:shutil.rmtree(home/name);(home/name).symlink_to(installed/name,target_is_directory=True)
            shutil.copyfile(installed/'config/models.json',home/'config/models.json');runtime=Runtime(home)
            report['model_revisions']=runtime.revisions();report['effective_config']=dict(cfg)
            request=runtime.store.request('RULES',{'base_rule':runtime.store.generation()['rule_version'],'after':['Nur lokal, keine Cloud.']});runtime.store.approve_rule(request,runtime.cfg,runtime.revisions())
            generation=runtime.store.generation_id;rules=runtime.store.rules();manifest=runtime.store.generation()
            def ask(name,text,want_memory,expected):
                print('Starting '+name,flush=True);eid=runtime.submit(text);end=time.monotonic()+runtime.cfg['deadline_seconds']+15
                while not runtime.idle():
                    if time.monotonic()>end:runtime.cancel();raise TimeoutError('Second-attempt wait budget')
                    time.sleep(.05)
                answer=runtime.store.one("SELECT * FROM messages WHERE event_id=? AND role='assistant'",(eid,));meta=json.loads(answer['metadata']);trace=meta.get('memory_retrieval',[]);checks=[]
                for item in trace:
                    source=runtime.store.read_source(item['source_ref']);checks.append({'memory_id':item['memory_id'],'source_ref':item['source_ref'],'source_hash_matches_correction':digest(source)==digest(CORRECTION)})
                row={'case':name,'input':text,'event_id':eid,'output':answer['text'],'status':answer['status'],'metadata':meta,'retrieval_source_checks':checks,'expected_memory_use':want_memory,
                     'checks':{'native_final_output':answer['status']=='FINAL' and meta.get('model_generated') is True and meta.get('runner',{}).get('generated_tokens',0)>0,'memory_expectation':bool(trace)==want_memory,'source_lineage':all(x['source_hash_matches_correction'] for x in checks),'rules_unchanged':runtime.store.rules()==rules,'generation_unchanged':runtime.store.generation_id==generation},
                     'diagnostic_expected_number_presence':{str(n):bool(re.search(r'(?<![\d.,])'+str(n)+r'(?!\d)',answer['text'])) for n in expected}}
                report['turns'].append(row);save();return row
            first=ask('before_correction',QUESTION,False,[])
            memory_id=runtime.memory.feedback(first['event_id'],'fact',CORRECTION)
            memory=runtime.store.one('SELECT * FROM memories WHERE id=?',(memory_id,));report['correction']={'text':CORRECTION,'memory_id':memory_id,'source_id':memory['source_id'],'permission':'record','scope':'session'};save()
            for name,text,want_memory,expected in CASES:ask(name,text,want_memory,expected)
            session=runtime.session;runtime.close();runtime=Runtime(home);report['restart_same_session']=runtime.session==session
            ask('after_restart',QUESTION,True,[120])
            runtime.cfg['memory_top_k']=0;ask('memory_ablation',QUESTION,False,[]);runtime.cfg['memory_top_k']=cfg['memory_top_k']
            report['checks']={'all_case_checks':all(all(t['checks'].values()) for t in report['turns']),'restart_same_session':report['restart_same_session'],'manifest_unchanged':runtime.store.generation()==manifest,'no_weight_updates':not runtime.store.rows('SELECT * FROM updates'),'integrity':not runtime.store.integrity(True),'distinct_native_events':len({t['event_id'] for t in report['turns']})==len(report['turns'])}
            report['status']='FAMILY_CHECKS_PASS' if all(report['checks'].values()) else 'FAMILY_CHECKS_PARTIAL'
        except Exception as exc:report.update(status='INTERRUPTED',error_type=type(exc).__name__,error=str(exc)[:500])
        finally:
            if runtime:runtime.close()
            save()
    return report

def main():
    p=argparse.ArgumentParser();p.add_argument('--installed-home',required=True);p.add_argument('--out',required=True);a=p.parse_args();r=run(a.installed_home,a.out);print(json.dumps({'status':r['status'],'cases':len(r['turns']),'checks':r.get('checks',{})}));return 0 if r['status']=='FAMILY_CHECKS_PASS' else 2
if __name__=='__main__':sys.exit(main())
