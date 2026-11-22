"""Real frozen C3/replay consumers for approved exact confirmation compaction.

Fixture corrections are explicitly authored by the harness as HumanDecisions.
The test does not represent a scientific truth or unseen-cue skill benchmark.
"""
# German fixtures = WP-V9 German transfer test: run them with answer_language='de' (English prompts made C3 ignore German memory/targets).
import argparse
import json
from pathlib import Path
import shutil
import sys
import tempfile
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from v13.common import APP,atomic_write,dumps,file_hash
from v13.config import initialize,save_config
from v13.runtime import Runtime
from v13.operator import Operator
from v13.resources import device
from v13.proofs import archive_previous

def run(installed,out):
    installed=Path(installed).resolve();out=Path(out).resolve();archive_previous(out)
    report={'status':'RUNNING','schema':'V13_CONSOLIDATION_PROOF_V1','device':device(),'phone_measured':device()['android'],
        'fixture_authority':'explicit harness HumanDecisions, not acquired world truth','checks':{},'turns':[],
        'source_hashes':{str(p.relative_to(APP)):file_hash(p) for p in list((APP/'v13').glob('*.py'))+[Path(__file__).resolve()]},
        'claim_limits':['Exact repeated human-confirmation semantic compaction and authored-cue procedure only.',
                        'No native base-weight merge, automatic dream truth, or unseen semantic/procedural generalization.',
                        'Expected-number presence is a consumer diagnostic, not factual or reasoning validation.']}
    def save():atomic_write(out,json.dumps(report,ensure_ascii=False,indent=2))
    save()
    with tempfile.TemporaryDirectory(prefix='v13-consolidation-') as folder:
        home=Path(folder);cfg=initialize(home);cfg.update(observer_mode='off',route_override='simple',history_turns=0,answer_language='de',answer_tokens=64,replay_tokens=64,learning_mode='SHADOW_UPDATE');save_config(home,cfg)
        for name in ('models','bin'):shutil.rmtree(home/name);(home/name).symlink_to(installed/name,target_is_directory=True)
        shutil.copyfile(installed/'config/models.json',home/'config/models.json');r=Runtime(home);op=Operator(r)
        try:
            if not hasattr(r,'consolidation'):raise RuntimeError('Production Runtime consolidation hook missing')
            hashes={role:file_hash(r.models.path_for(role)) for role in ('C3_LANGUAGE','C2_CONTROL','B1_DETAIL')};report['model_revisions']=r.revisions()
            def confirm(kind,value,keys):
                ids=[]
                for i,key in enumerate(keys):
                    query=key+' bestätigt '+str(i) if kind=='route' else 'Welcher Betrag gilt für '+key+'? Bestätigung Nr. '+str(i)+'.'
                    e=r.store.event(r.session,query);ids.append(r.memory.feedback(e['event_id'],kind,value,'learn',key=key))
                return ids
            keys=['Projekt Liora Budget','Projekt Liora Finanzrahmen','Projekt Liora verfügbare Mittel'];members=confirm('fact','400 Euro',keys)
            result=json.loads(op.run(':consolidate semantic'));rid=result['requests'][0];report['semantic_request']=r.store.one('SELECT * FROM requests WHERE id=?',(rid,));save()
            report['checks']['shadow_no_activation']=not r.consolidation.active(r.session) and len(r.store.rows('SELECT id FROM memories WHERE active=1'))==3
            op.run(':learning commit');cid=op.run(':approve '+rid);report['approved_index']=r.consolidation.active(r.session)[0];save()
            query='Welches Budget, welcher Finanzrahmen und welche verfügbaren Mittel hat Projekt Liora? Nenne nur den Betrag.'
            recalled=r.memory.recall(query,r.session);report['compacted_recall']=recalled
            report['checks']['production_compaction']=len(recalled)==1 and recalled[0]['id']==cid and recalled[0]['value']=='400 Euro' and set(recalled[0]['consolidation']['members'])==set(members)
            report['checks']['lineage_complete']=len(recalled[0]['consolidation']['source_refs'])==9
            report['checks']['consumer_lineage_complete']=len(r.consolidation.source_refs(recalled))==9
            report['checks']['other_entity_refused']=not r.memory.recall('Projekt Anderer Budget',r.session)
            def ask(name,text):
                eid=r.submit(text);end=time.monotonic()+r.cfg['deadline_seconds']+20
                while not r.idle():
                    if time.monotonic()>end:r.cancel();raise TimeoutError('Consolidation turn deadline')
                    time.sleep(.05)
                row=r.store.one("SELECT * FROM messages WHERE event_id=? AND role='assistant'",(eid,));meta=json.loads(row['metadata'])
                report['turns'].append({'name':name,'input':text,'status':row['status'],'actual_output':row['text'],'metadata':meta});save();return row,meta
            row,meta=ask('compacted_semantic_consumer',query)
            report['checks']['actual_native_c3_consumer']=row['status']=='FINAL' and meta['model_generated'] and '400' in row['text'] and meta['memory_ids']==[cid] and bool(meta.get('runner'))
            r._replay(1);replay=json.loads((home/'exports/replay-last.json').read_text());report['replay']=replay
            report['checks']['actual_replay_consumer']=replay['status']=='REPLAY_COMPLETE' and bool(replay['rows']) and '400' in replay['rows'][0].get('output','') and bool(replay['rows'][0].get('native_metrics'))
            report['checks']['replay_lineage_complete']=len(replay['rows'][0]['source_refs'])==10
            original_session=r.session;r.close();r=Runtime(home);r.cfg.update(observer_mode='off',route_override='simple',history_turns=0,answer_language='de',learning_mode='APPROVED_COMMIT');op=Operator(r)
            report['checks']['restart_retains_approved_index']=r.session==original_session and r.memory.recall(query,r.session)[0]['id']==cid
            routekeys=['Projekt Liora Rechnung prüfen','Projekt Liora Kosten berechnen','Projekt Liora Betrag kontrollieren'];confirm('route','detail',routekeys)
            proc=json.loads(op.run(':consolidate procedural'))['requests'][0];pid=op.run(':approve '+proc);r.cfg['route_override']='auto'
            authored=routekeys[1]+' bestätigt 1';event=r.store.event(r.session,authored);route,info=r._route(authored,event,time.monotonic()+5)
            report['procedural_consumer']=info;report['checks']['production_procedural_consumer']=route=='detail' and info['source']=='APPROVED_SOURCE_BOUND_PROCEDURE' and info['index_id']==pid
            report['checks']['unseen_procedural_cue_refused']=r.consolidation.route('Projekt Liora Kosten schätzen',r.session) is None
            op.run(':consolidate rollback '+pid);report['checks']['procedural_rollback']=r.consolidation.route(authored,r.session) is None
            op.run(':consolidate rollback '+cid);report['checks']['semantic_rollback']=len(r.memory.recall(query,r.session))==3
            report['checks']['rollback_keeps_experience']=len(r.store.rows('SELECT id FROM memories WHERE active=1 AND kind=?',('fact',)))==3
            changed=r.store.event(r.session,'Neue Budget-Korrektur');r.memory.feedback(changed['event_id'],'fact','500 Euro','learn',key=keys[0])
            report['checks']['current_correction_retained']=any(m['value']=='500 Euro' for m in r.memory.recall('Projekt Liora Budget',r.session))
            r.memory.forget(members[1]);report['checks']['forget_removes_source']=not r.store.one('SELECT id FROM sources WHERE id=? AND deleted=0',(report['approved_index']['members'][1]['value_ref']['source_id'],))
            report['checks']['native_weights_unchanged']=all(file_hash(r.models.path_for(role))==h for role,h in hashes.items())
            report['checks']['integrity']=not r.store.integrity(True);report['status']='CONSOLIDATION_PASS' if all(report['checks'].values()) else 'CONSOLIDATION_PARTIAL';save()
        except Exception as exc:report.update(status='CONSOLIDATION_PARTIAL',error=type(exc).__name__+': '+str(exc));save()
        finally:r.close()
    print(dumps({'status':report['status'],'checks':report['checks'],'error':report.get('error')}));return 0 if report['status']=='CONSOLIDATION_PASS' else 2

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--installed-home',required=True);p.add_argument('--out',required=True);a=p.parse_args();sys.exit(run(a.installed_home,a.out))
