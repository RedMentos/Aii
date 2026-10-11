"""Actual Needle cue pairs, explicit fixture authority, native answer consumer."""
import argparse
import json
import gzip
from pathlib import Path
import shutil
import sys
import tempfile
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from v13.common import APP,atomic_write,dumps,file_hash,digest
from v13.config import initialize,save_config
from v13.runtime import Runtime
from v13.operator import Operator
from v13.resources import device

TOPICS=[('Budget','Euro',('Finanzrahmen','verfügbare Mittel','Geldbetrag','Finanzierung'),('Abgabefrist','Kontaktperson','Ort','Termin')),
        ('Abgabefrist','Mai',('Einreichungstermin','Zeitpunkt der Abgabe','spätester Termin','Einreichungsfrist'),('Geldbetrag','Kontaktperson','Ort','Finanzierung')),
        ('Ansprechpartner','Leitung',('Kontaktperson','zuständige Person','Kontakt','Projektverantwortlicher'),('Geldbetrag','Abgabefrist','Ort','Termin')),
        ('Standort','Berlin',('Ort','Adresse','Stadt','Projektort'),('Geldbetrag','Abgabefrist','Kontaktperson','Finanzierung'))]

def capture_generation(runner, records, phase, save):
    """Observe the existing native call without changing messages or arguments."""
    original=runner.generate
    def measured(messages,*args,**kwargs):
        frozen=json.loads(dumps(messages))
        item={'phase':phase(),'role':runner.role,'messages':frozen,
              'messages_sha256':digest(dumps(frozen)),'completed':False}
        records.append(item);save()
        try:
            yield from original(messages,*args,**kwargs)
            item['completed']=True
        except BaseException as exc:
            item['error_type']=type(exc).__name__;raise
        finally:
            item['native_metrics']=dict(runner.last_metrics);save()
    runner.generate=measured

from v13.prompts import TEXT as PROMPT_TEXT
MEMORY_PREFIXES=tuple(PROMPT_TEXT[l]['memories'] for l in PROMPT_TEXT)

def audit_source_context(capture,fixture,metadata,read_source,expected_role):
    """Check exact admitted correction, raw query and durable source lineage.

    This measures delivery and identity only. The independent output check must
    still observe the expected amount in a genuine native FINAL response.
    """
    messages=capture['messages'];corrections=[];errors=[];source_texts=[]
    for message in messages:
        if message.get('role')!='system':continue
        for line in message.get('content','').splitlines():
            # WP-V9 made English the working language; accept the prompt prefix of either language (prompts.TEXT).
            prefix=next((x for x in MEMORY_PREFIXES if line.startswith(x)),None)
            if prefix:
                try:
                    rows=json.loads(line[len(prefix):])
                    if isinstance(rows,list):corrections.extend(rows)
                except (ValueError,TypeError):errors.append('invalid_correction_json')
    refs=metadata.get('context_source_refs',[])
    for ref in refs:
        try:source_texts.append(read_source(ref))
        except Exception as exc:errors.append(type(exc).__name__)
    exact_row={'topic':fixture['key'],'correction':fixture['value'],'matched_query':fixture['input']}
    metrics=capture.get('native_metrics',{})
    checks={
        'messages_sha256_matches':capture.get('messages_sha256')==digest(dumps(messages)),
        'actual_native_role':capture.get('role')==expected_role and metrics.get('role')==expected_role,
        'generation_completed':capture.get('completed') is True,
        'exact_correction_and_binding':any(isinstance(row,dict) and all(row.get(k)==v for k,v in exact_row.items()) for row in corrections),
        'raw_query_received':bool(messages) and messages[-1]=={'role':'user','content':fixture['input']},
        'source_lineage_valid':bool(refs) and not errors,
        'exact_query_source_present':fixture['input'] in source_texts,
        'exact_correction_source_present':fixture['value'] in source_texts,
        'native_prompt_not_trimmed':metrics.get('history_trimmed') is False,
        'admitted_memory_present':fixture['memory_id'] in metadata.get('memory_ids',[]),
    }
    return {'checks':checks,'pass':all(checks.values()),'source_errors':errors}

def main():
    p=argparse.ArgumentParser();p.add_argument('--installed-home',required=True);p.add_argument('--out',required=True);a=p.parse_args();installed=Path(a.installed_home).resolve();out=Path(a.out)
    report={'status':'RUNNING','device':device(),'scope':'Explicit human relevance, frozen Needle pairs, source-backed native answer; not learned factual truth',
            'source_hashes':{str(f.relative_to(APP)):file_hash(f) for f in (APP/'v13').glob('*.py')},'checks':{},'corpus':[],'native_embeddings':[],'pairs':[],
            'native_generation_calls':[],'collector_sha256':file_hash(Path(__file__))}
    feature_rows=[]
    def save():atomic_write(out,json.dumps(report,ensure_ascii=False,indent=2))
    def instrument(r):
        original_get=r.pool.get;observed=set()
        def observed_get(*args,**kwargs):
            runner=original_get(*args,**kwargs)
            if runner not in observed:
                observed.add(runner)
                capture_generation(runner,report['native_generation_calls'],lambda:report.get('phase'),save)
            return runner
        r.pool.get=observed_get
        original=r.needle.embed
        def measured(text,cancel,deadline):
            start=time.monotonic();vector=original(text,cancel,deadline);report['native_embeddings'].append({'phase':report.get('phase'),'input':text,'dimension':len(vector),'duration_s':time.monotonic()-start,'metrics':dict(r.needle.last_metrics)});save();return vector
        r.needle.embed=measured
        original_pair=r.learner.retrieval_features
        def pair(e,m,deadline):
            x,refs=original_pair(e,m,deadline);item={'phase':report.get('phase'),'event_id':e['event_id'],'memory_id':m['id'],'features':x,'refs':refs};feature_rows.append(item)
            report['pairs'].append(item|{'features':x[:7],'feature_dim':len(x),'feature_sha256':digest(dumps(x))});save();return x,refs
        r.learner.retrieval_features=pair
    save()
    with tempfile.TemporaryDirectory(prefix='v13-retrieval-') as folder:
        h=Path(folder);initialize(h)
        for name in ('models','bin'):shutil.rmtree(h/name);(h/name).symlink_to(installed/name,target_is_directory=True)
        shutil.copyfile(installed/'config/models.json',h/'config/models.json');r=Runtime(h);instrument(r)
        try:
            r.cfg.update(history_turns=0,observer_mode='off',route_override='simple',answer_tokens=64,retrieval_seconds=20.);save_config(h,r.cfg)
            original_hashes={role:file_hash(r.models.path_for(role)) for role in ('C2_CONTROL','C3_LANGUAGE','B1_DETAIL')}
            for i in range(32):
                topic,unit,positive,negative=TOPICS[i%4];name='Kelmo'+str(i);key=f'Projekt {name} {topic}';value=f'{128+i*17} {unit}' if i%4==0 else f'Projekt {name}: {i+1}. Mai' if i%4==1 else f'Projekt {name}: Frau Berg{i}' if i%4==2 else f'Projekt {name}: Berlin, Weg {i+1}'
                e=r.store.event(r.session,key);mid=r.memory.feedback(e['event_id'],'fact',value,key=key)
                for j,cue in enumerate(positive+negative):
                    text=f'Projekt {name}: {cue}?';q=r.store.event(r.session,text);label='relevant' if j<4 else 'irrelevant';r.memory.retrieval_feedback(q['event_id'],mid,label,'learn')
                    report['corpus'].append({'input':text,'label':label,'key':key,'memory_id':mid,'value':value,'event_id':q['event_id']})
            save();base=r.store.generation_id;r.cfg['learning_mode']='SHADOW_UPDATE';report['phase']='INITIAL_FIT';r.learner.shadow_retrieval()
            u=r.store.one('SELECT * FROM updates ORDER BY created DESC LIMIT 1');manifest=json.loads(u['manifest']);m=manifest['metrics'];report['initial_update']={'status':u['status'],'manifest':manifest}
            report['checks'].update(actual_native_features=len(report['native_embeddings'])>256 and all(x['dimension']==3072 for x in report['native_embeddings']),
              shadow_no_commit=r.store.generation_id==base,gradient=m['gradient_check'],retrieval_gain=m['retrieval_gain'],semantic_ablation=m['semantic_ablation_pass'],held_out_support=m['held_out_support_pass'],reload=m['checkpoint_reload'],repeat=m['deterministic_repeat']);save()
            if u['status']!='PENDING_APPROVAL':raise RuntimeError('Actual native cue gate refused candidate; evidence retained')
            # Learner order follows ascending explicit feedback timestamps.
            held=[i for i in m['partition']['test'] if report['corpus'][i]['label']=='relevant']
            selected=next(i for i in held if report['corpus'][i]['key'].endswith('Budget'))
            fixture=report['corpus'][selected];report['checks']['held_out_source_consumer']=selected in m['partition']['test']
            report['checks']['lexical_synonym_miss']=not r.memory.recall(fixture['input'],r.session)
            r.cfg['learning_mode']='APPROVED_COMMIT';Operator(r).run(':approve '+u['id']);session=r.session;r.close();r=Runtime(h);instrument(r)
            report['checks']['restart']=r.session==session and r.learner.active('memory_retrieval') is not None;report['phase']='NATIVE_ANSWER'
            q=r.store.event(r.session,fixture['input']);r._turn(q);answer=r.last_answer();metadata=json.loads(answer['metadata']);report['native_turn']={'input':fixture['input'],'expected_source_value':fixture['value'],'actual_output':answer['text'],'status':answer['status'],'metadata':metadata}
            report['c3_source_answer_observed']=answer['status']=='FINAL' and fixture['value'].split()[0] in answer['text']
            report['checks']['native_language_context_receives_source']=answer['status']=='FINAL' and metadata['model_generated'] and fixture['memory_id'] in metadata['memory_ids']
            capture=report['native_generation_calls'][-1]
            report['native_turn']['source_context_audit']=audit_source_context(capture,fixture,metadata,r.store.read_source,'C3_LANGUAGE')
            report['checks']['native_language_exact_source_delivery']=report['native_turn']['source_context_audit']['pass']
            report['checks']['native_language_answer_uses_human_source']=report['c3_source_answer_observed'] and report['checks']['native_language_context_receives_source']
            # Both existing native output roles are measured; no prompt or source
            # text is changed to hide a small language body's factual miss.
            r.cfg['route_override']='detail';q=r.store.event(r.session,fixture['input']);r._turn(q);detail=r.last_answer();dm=json.loads(detail['metadata'])
            report['native_detail_turn']={'input':fixture['input'],'expected_source_value':fixture['value'],'actual_output':detail['text'],'status':detail['status'],'metadata':dm}
            capture=report['native_generation_calls'][-1]
            report['native_detail_turn']['source_context_audit']=audit_source_context(capture,fixture,dm,r.store.read_source,'B1_DETAIL')
            report['checks']['native_detail_exact_source_delivery']=report['native_detail_turn']['source_context_audit']['pass']
            report['checks']['native_detail_answer_uses_human_source']=detail['status']=='FINAL' and dm['model_generated'] and fixture['value'].split()[0] in detail['text'] and fixture['memory_id'] in dm['memory_ids'];save()
            negative=next(row for i,row in enumerate(report['corpus']) if i in m['partition']['test'] and row['memory_id']==fixture['memory_id'] and row['label']=='irrelevant')
            q=r.store.event(r.session,negative['input']);hits=r.memory.recall(negative['input'],r.session,lambda memory:r.learner.retrieve(q,memory,time.monotonic()+20));report['negative_hits']=hits
            report['checks']['same_entity_wrong_topic_rejected']=not hits
            q=r.store.event(r.session,'Projekt Fremdo: Finanzrahmen?');report['checks']['different_entity_rejected']=not r.memory.recall('Projekt Fremdo: Finanzrahmen?',r.session,lambda memory:r.learner.retrieve(q,memory,time.monotonic()+20))
            other=r.store.new_session();report['checks']['different_session_rejected']=not r.memory.recall(fixture['input'],other)
            try:r.memory.forget(fixture['memory_id']);protected=False
            except ValueError:protected=True
            report['checks']['active_lineage_forget_refused']=protected
            # New explicit experiences displace some old training rows in the
            # bounded corpus; saved old test cases/support must still be retained.
            for i in range(32,40):
                topic,unit,positive,negative=TOPICS[i%4];key=f'Projekt Kelmo{i} {topic}'
                e=r.store.event(r.session,key);mid=r.memory.feedback(e['event_id'],'fact',f'Neue Quelle Kelmo{i}: {900+i} {unit}',key=key)
                for j,cue in enumerate(positive+negative):
                    q=r.store.event(r.session,f'Projekt Kelmo{i}: {cue}?');r.memory.retrieval_feedback(q['event_id'],mid,'relevant' if j<4 else 'irrelevant','learn')
            report['checks']['new_source_retention_batch']=len(r.learner.retrieval_labels())==256
            path=r.learner.active('memory_retrieval');parent=r.store.generation_id;parent_hash=file_hash(path);r.cfg['learning_mode']='SHADOW_UPDATE';report['phase']='ACTIVE_RETENTION';r.learner.shadow_retrieval()
            ret=r.store.one('SELECT * FROM updates ORDER BY created DESC LIMIT 1');rm=json.loads(ret['manifest']);report['active_retention']={'status':ret['status'],'manifest':rm}
            report['checks']['active_retention_enforced']=rm['metrics']['retained_test']['n']>0 and (rm['metrics']['retention_pass'] or ret['status']=='EVALUATED_FAIL')
            report['checks']['second_fit_no_auto_commit']=r.store.generation_id==parent and file_hash(path)==parent_hash
            r.store.rollback(u['id']);report['checks']['rollback_restores_lexical']=r.learner.active('memory_retrieval') is None and not r.memory.recall(fixture['input'],r.session)
            report['checks']['native_weights_unchanged']=all(file_hash(r.models.path_for(role))==sha for role,sha in original_hashes.items());report['checks']['integrity']=not r.store.integrity(True)
            report['checks']['runtime_source_unchanged']={str(f.relative_to(APP)):file_hash(f) for f in (APP/'v13').glob('*.py')}==report['source_hashes']
            report['checks']['collector_unchanged']=file_hash(Path(__file__))==report['collector_sha256']
            report['status']='MEMORY_RETRIEVAL_PASS' if all(report['checks'].values()) else 'MEMORY_RETRIEVAL_PARTIAL'
        except Exception as exc:
            report.update(status='MEMORY_RETRIEVAL_PARTIAL',error=type(exc).__name__+': '+str(exc));report['worker_logs']=[f.read_text()[-4000:] for f in (h/'shadow').glob('*/worker.log')]
        finally:
            r.close();features_file=out.with_suffix('.features.json.gz')
            interactions={};rows=[]
            for item in feature_rows:
                h=digest(dumps(item['features'][7:]));interactions.setdefault(h,item['features'][7:]);rows.append(item|{'features':item['features'][:7],'native_interaction_ref':h})
            with gzip.open(features_file,'wt',encoding='utf-8') as stream:json.dump({'schema':'V13_NATIVE_RETRIEVAL_PAIRS_V1','native_interactions':interactions,'rows':rows},stream,ensure_ascii=False)
            report['native_feature_artifact']={'file':features_file.name,'sha256':file_hash(features_file),'rows':len(feature_rows),'format':'V13_NATIVE_RETRIEVAL_PAIRS_V1'};save()
    print(dumps({'status':report['status'],'checks':report['checks'],'error':report.get('error')}));return 0 if report['status']=='MEMORY_RETRIEVAL_PASS' else 2

if __name__=='__main__':sys.exit(main())
