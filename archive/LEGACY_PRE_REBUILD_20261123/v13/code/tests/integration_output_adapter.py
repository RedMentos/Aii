"""Actual frozen-C3 first-token preference delta; no answer text substitution."""
import argparse
import gzip
import json
from pathlib import Path
import shutil
import sys
import tempfile
import threading
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from v13.common import APP,atomic_write,dumps,file_hash
from v13.config import initialize
from v13.models import ModelManager
from v13.runners import RunnerPool
from v13.output_adapter_worker import native_context,train,infer
from v13.resources import device

def production_main(installed,out):
    from v13.runtime import Runtime
    from v13.operator import Operator
    from v13.config import save_config
    import v13.output_adapter_worker as worker
    report={'status':'RUNNING','device':device(),'scope':'Authored human opening-reference first native token preference on greet/thanks requests; source-held-out familiar template families, no full output correctness, arithmetic, general language or semantic OOD claim','checks':{},'corpus':[], 'native_calls':[],
        'source_hashes':{str(f.relative_to(APP)):file_hash(f) for f in (APP/'v13').glob('*.py')}}
    measured_features=[];original=worker.native_context
    def save():atomic_write(out,json.dumps(report,ensure_ascii=False,indent=2))
    def measured(pool,messages,cancel,deadline,token_ids=None):
        observed=original(pool,messages,cancel,deadline,token_ids)
        entry={'phase':report.get('phase'),'messages':messages,'token_ids':token_ids,'observation':observed};measured_features.append(entry)
        report['native_calls'].append({'phase':entry['phase'],'prompt_sha256':observed['prompt_sha256'],'dimension':len(observed['feature']),'native_baseline':observed['native_baseline'],'native_metrics':observed['native_metrics'],'native_context_binding':observed['native_context_binding']});save();return observed
    worker.native_context=measured;save()
    with tempfile.TemporaryDirectory(prefix='v13-output-production-') as folder:
        h=Path(folder);initialize(h)
        for n in ('models','bin'):shutil.rmtree(h/n);(h/n).symlink_to(installed/n,target_is_directory=True)
        shutil.copyfile(installed/'config/models.json',h/'config/models.json');r=Runtime(h)
        try:
            r.cfg.update(history_turns=0,observer_mode='off',route_override='simple',answer_tokens=16,threads=2);save_config(h,r.cfg)
            model_hash=file_hash(r.models.path_for('C3_LANGUAGE'));report['phase']='BASELINE_SELF_CANDIDATES'
            # Labels are fixed before any native candidate is observed.
            for i in range(64):
                for target,text in enumerate((f'Begrüße Gast {i+1} kurz.',f'Bedanke dich kurz für Hilfe beim Projekt {i+1}.')):
                    e=r.store.event(r.session,text);r._turn(e);answer=r.last_answer()
                    if answer['event_id']!=e['event_id'] or not json.loads(answer['metadata']).get('model_generated'):raise RuntimeError('Actual baseline C3 self candidate missing')
                    reference=('Hallo','Danke')[target];r.learner.output_feedback(e['event_id'],reference,'learn')
                    report['corpus'].append({'input':text,'human_reference':reference,'event_id':e['event_id'],'source_sha256':e['source_ref']['sha256'],'actual_self_candidate':{'text':answer['text'],'status':answer['status'],'metadata':json.loads(answer['metadata'])}});save()
                    if len(report['corpus'])==1:
                        # Check the actual production template before spending
                        # another 127 native baseline turns. Do not substitute
                        # a short synthetic context for the recorded messages.
                        report['phase']='NATIVE_CONTEXT_PREFLIGHT';deadline=time.monotonic()+60
                        runner=r.pool.get('C3_LANGUAGE');runner.load(r.cancel_event,deadline)
                        tokens=[runner._json('POST','/tokenize',{'content':word,'add_special':False},deadline)['tokens'][0] for word in ('Hallo','Danke')]
                        r.pool.unload();messages=r.learner.output_labels()[0][3]
                        observed=measured(r.pool,messages,r.cancel_event,deadline,tokens)
                        binding=observed['native_context_binding'];metrics=observed['native_metrics']
                        report['preflight']={'event_id':e['event_id'],'human_reference':reference,'native_context_binding':binding,'native_metrics':metrics,'dimension':len(observed['feature'])}
                        report['checks']['production_context_over_old_128_limit']=128<binding['template_token_count']<=512
                        report['checks']['production_whole_context_native_prefill']=len(observed['feature'])==1024 and binding['baseline_token_ids_match'] is True and binding['template_token_count']==binding['tap_token_count'] and metrics.get('whole_sequence_prefill') is True and metrics.get('physical_batch_tokens')==512
                        save()
                        if not all(report['checks'].values()):raise RuntimeError('Actual production context preflight failed; evidence retained')
                        report['phase']='BASELINE_SELF_CANDIDATES'
            base=r.store.generation_id;r.cfg['learning_mode']='SHADOW_UPDATE';report['phase']='INITIAL_FIT';r.learner.shadow_output_adapter()
            u=r.store.one('SELECT * FROM updates ORDER BY created DESC LIMIT 1');manifest=json.loads(u['manifest']);m=manifest['metrics'];report['update']={'status':u['status'],'manifest':manifest}
            report['checks'].update(explicit_human_targets=len(r.learner.output_labels())==128,actual_native_state_and_full_vocabulary=len(manifest['native_observations'])==128 and all(c['dimension']==1024 and c['native_baseline']['vocabulary_size']==65536 for c in report['native_calls'] if c['phase']=='INITIAL_FIT'),shadow_no_commit=r.store.generation_id==base,gradient=m['gradient_check'],repeat=m['deterministic_repeat'],reload=m['checkpoint_reload'],utility=m['utility_pass'],calibration=m['calibration_pass'],support=m['held_out_support_pass'],first_token_accuracy=m['first_native_token_accuracy_pass'],retention=m['retention_pass']);save()
            if u['status']!='PENDING_APPROVAL':raise RuntimeError('Actual native output candidate refused gate; evidence retained')
            r.cfg['learning_mode']='APPROVED_COMMIT';save_config(h,r.cfg);Operator(r).run(':approve '+u['id']);session=r.session;generation=r.store.generation_id;r.close();r=Runtime(h)
            report['checks']['approved_restart']=r.session==session and r.store.generation_id==generation and r.learner.active('output_adapter') is not None
            report['phase']='ACTUAL_RUNTIME_CONSUMER';report['held_out_consumers']=[]
            for idx in m['partition']['test']:
                item=report['corpus'][idx];e=r.store.event(r.session,item['input']);r._turn(e);answer=r.last_answer();meta=json.loads(answer['metadata']);p=r.store.one("SELECT payload FROM packets WHERE kind='OutputAdapterDecision' AND event_id=? ORDER BY created DESC LIMIT 1",(e['event_id'],));decision=json.loads(p['payload'])
                # Worker vocab is sorted native IDs, not label order; tokenize
                # the immutable human target with the actual pinned runner.
                runner=r.pool.get('C3_LANGUAGE');runner.load(r.cancel_event,time.monotonic()+30);target=runner._json('POST','/tokenize',{'content':item['human_reference'],'add_special':False},time.monotonic()+30)['tokens'][0]
                step=meta.get('runner',{}).get('output_adapter_native_first_step',{})
                report['held_out_consumers'].append({'index':idx,'actual_output':answer['text'],'status':answer['status'],'metadata':meta,'decision':decision,'correct_first_native_token':step.get('token_ids')==[target]});save()
            rows=report['held_out_consumers'];report['checks']['actual_turn_native_decoder_consumer']=bool(rows) and sum(x['correct_first_native_token'] for x in rows)/len(rows)>=.8 and all(x['status']=='FINAL' and x['metadata'].get('model_generated') for x in rows)
            report['checks']['later_positions_unbiased']=all(x['metadata'].get('runner',{}).get('output_adapter_native_first_step',{}).get('remaining_positions_unbiased') is True for x in rows)
            report['phase']='UNRELATED_QUERY';e=r.store.event(r.session,'Welche Farbe hat der Himmel?');r._turn(e);answer=r.last_answer();p=r.store.one("SELECT payload FROM packets WHERE kind='OutputAdapterDecision' AND event_id=? ORDER BY created DESC LIMIT 1",(e['event_id'],));report['unrelated_query']={'actual_output':answer['text'],'status':answer['status'],'metadata':json.loads(answer['metadata']),'decision':json.loads(p['payload']),'semantic_ood_claim':False};save()
            report['checks']['unrelated_support_observed']=report['unrelated_query']['decision']['prediction'] is not None and report['unrelated_query']['status']=='FINAL'
            active=r.learner.active('output_adapter');active_hash=file_hash(active);prior=r.store.generation_id;report['phase']='RETENTION_CANDIDATE'
            for i in range(8):
                for target,text in enumerate((f'Begrüße Gast {i+101} kurz.',f'Bedanke dich kurz für Hilfe beim Projekt {i+101}.')):
                    e=r.store.event(r.session,text);r._turn(e);r.learner.output_feedback(e['event_id'],('Hallo','Danke')[target],'learn')
            r.cfg['learning_mode']='SHADOW_UPDATE';r.learner.shadow_output_adapter();ret=r.store.one('SELECT * FROM updates ORDER BY created DESC LIMIT 1');rm=json.loads(ret['manifest'])['metrics'];report['retention_candidate']={'status':ret['status'],'metrics':rm}
            report['checks']['fixed_old_retention']=rm['retained_test']['n']==len(m['partition']['test']) and len(rm['retained_test']['per_native_token'])==len(m['vocabulary_rows']) and (rm['retention_pass'] or ret['status']=='EVALUATED_FAIL')
            report['checks']['candidate_parent_unchanged']=r.store.generation_id==prior and file_hash(active)==active_hash
            r.store.rollback(u['id']);report['checks']['rollback_restores_baseline']=r.learner.active('output_adapter') is None
            e=r.store.event(r.session,report['corpus'][0]['input']);r._turn(e);answer=r.last_answer();report['rollback_answer']={'actual_output':answer['text'],'metadata':json.loads(answer['metadata'])}
            report['checks']['rollback_native_output_has_no_delta']=answer['status']=='FINAL' and 'output_adapter_native_first_step' not in report['rollback_answer']['metadata'].get('runner',{})
            report['checks']['native_weights_unchanged']=file_hash(r.models.path_for('C3_LANGUAGE'))==model_hash;report['checks']['integrity']=not r.store.integrity(True)
            report['status']='OUTPUT_ADAPTER_PASS' if all(report['checks'].values()) else 'OUTPUT_ADAPTER_PARTIAL'
        except Exception as exc:report.update(status='OUTPUT_ADAPTER_PARTIAL',error=type(exc).__name__+': '+str(exc));report['worker_logs']=[p.read_text()[-4000:] for p in (h/'shadow').glob('*/worker.log')]
        finally:
            r.close();worker.native_context=original;features_path=out.with_suffix('.features.json.gz')
            with gzip.open(features_path,'wt',encoding='utf-8') as f:json.dump({'schema':'V13_NATIVE_OUTPUT_ADAPTER_OBSERVATIONS_V1','observations':measured_features},f)
            report['feature_artifact']={'name':features_path.name,'sha256':file_hash(features_path)};save()
    print(dumps({'status':report['status'],'checks':report['checks'],'error':report.get('error')}));return 0 if report['status']=='OUTPUT_ADAPTER_PASS' else 2

def main():
    p=argparse.ArgumentParser();p.add_argument('--installed-home',required=True);p.add_argument('--out',required=True);p.add_argument('--production',action='store_true');args=p.parse_args();installed=Path(args.installed_home).resolve();out=Path(args.out)
    if args.production:return production_main(installed,out)
    report={'status':'RUNNING','device':device(),'scope':'Human-labelled German first-word preference on binary comparison questions; no domain-wide language or semantic truth claim','checks':{},'corpus':[],
        'source_hashes':{str(f.relative_to(APP)):file_hash(f) for f in (APP/'v13').glob('*.py')}}
    def save():atomic_write(out,json.dumps(report,ensure_ascii=False,indent=2))
    save()
    with tempfile.TemporaryDirectory(prefix='v13-output-adapter-') as folder:
        h=Path(folder);cfg=initialize(h);cfg.update(history_turns=0,answer_tokens=16,threads=2,output_adapter_steps=1600,output_adapter_lr=.1,output_adapter_max_bias=12.,output_adapter_support_cosine=.95)
        for n in ('models','bin'):shutil.rmtree(h/n);(h/n).symlink_to(installed/n,target_is_directory=True)
        shutil.copyfile(installed/'config/models.json',h/'config/models.json');models=ModelManager(h);pool=RunnerPool(h,models,cfg);cancel=threading.Event();deadline=time.monotonic()+600
        try:
            runner=pool.get('C3_LANGUAGE');runner.load(cancel,deadline);token_ids=[]
            for text in ('Ja','Nein'):
                ids=runner._json('POST','/tokenize',{'content':text,'add_special':False},deadline)['tokens']
                if not ids:raise RuntimeError('Human reference first word requires actual native tokens')
                token_ids.append(ids[0])
            pool.unload();model_hash=file_hash(models.path_for('C3_LANGUAGE'));report['actual_token_ids']=token_ids;report['native_model_sha256']=model_hash
            # All 96 labelled queries and targets are fixed before collecting
            # any model result, and every collected failure remains in the proof.
            inputs=[]
            for i in range(48):
                for target,(a,b) in enumerate(((i+51,i+7),(i+7,i+51))):
                    text=f'Ist {a} größer als {b}?';messages=[{'role':'user','content':text}];inputs.append((messages,target))
            x=[];base=[];y=[];groups=[]
            for messages,target in inputs:
                observed=native_context(pool,messages,cancel,deadline,token_ids);x.append(observed['feature']);base.append(observed['base_log_probabilities']);y.append(target);groups.append(observed['prompt_sha256'])
                report['corpus'].append({'messages':messages,'human_target':('Ja','Nein')[target],'target_native_token_id':token_ids[target],'actual_native':{k:v for k,v in observed.items() if k!='feature'}});save()
            request={'config':cfg,'token_ids':token_ids,'native_features':x,'base_log_probabilities':base,'target_indices':y,'source_groups':groups}
            features_path=out.with_suffix('.features.json.gz')
            with gzip.open(features_path,'wt',encoding='utf-8') as f:json.dump(request,f)
            report['feature_artifact']={'name':features_path.name,'sha256':file_hash(features_path)};save();m=train(request,h/'shadow');report['metrics']=m
            report['checks'].update(actual_native_states=len(x)==96 and all(len(v)==1024 for v in x),complete_native_vocabulary=all(r['actual_native']['native_baseline']['vocabulary_size']==65536 for r in report['corpus']),gradient=m['gradient_check'],reload=m['checkpoint_reload'],repeat=m['deterministic_repeat'],retention=m['retention_pass'],support=m['held_out_support_pass'],calibration=m['calibration_pass'],utility=m['utility_pass'])
            # This isolated port proof is deliberately separate from production
            # generation approval; it cannot activate any user's runtime.
            if not m['commit_eligible']:raise RuntimeError('Measured native output delta refused activation gate; all evidence retained')
            report['held_out_native_consumers']=[]
            for idx in m['partition']['test']:
                decision=infer(x[idx],h/'shadow/candidate.npz');runner=pool.get('C3_LANGUAGE');messages=inputs[idx][0]
                output=''.join(runner.generate(messages,cancel,deadline,max_tokens=8,first_token_bias=decision['first_token_bias']));metrics=dict(runner.last_metrics)
                report['held_out_native_consumers'].append({'index':idx,'actual_output':output,'human_first_word':('Ja','Nein')[y[idx]],'decision':decision,'actual_metrics':metrics,'target_first_token':bool(metrics.get('output_adapter_native_first_step',{}).get('token_ids')==[token_ids[y[idx]]])});save()
            rows=report['held_out_native_consumers'];report['checks']['actual_native_decoder_consumes_delta']=bool(rows) and sum(r['target_first_token'] for r in rows)/len(rows)>=.8
            report['checks']['later_positions_unbiased']=all(r['actual_metrics'].get('output_adapter_native_first_step',{}).get('remaining_positions_unbiased') for r in rows)
            report['checks']['native_weights_unchanged']=file_hash(models.path_for('C3_LANGUAGE'))==model_hash
            report['status']='OUTPUT_ADAPTER_NATIVE_PORT_PASS' if all(report['checks'].values()) else 'OUTPUT_ADAPTER_PARTIAL'
        except Exception as exc:report.update(status='OUTPUT_ADAPTER_PARTIAL',error=type(exc).__name__+': '+str(exc))
        finally:pool.unload();save()
    print(dumps({'status':report['status'],'checks':report['checks'],'error':report.get('error')}));return 0 if report['status']=='OUTPUT_ADAPTER_NATIVE_PORT_PASS' else 2

if __name__=='__main__':sys.exit(main())
