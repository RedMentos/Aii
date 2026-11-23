import json
import os
import subprocess
import sys
import time
from .common import APP,uid,now,dumps,digest,atomic_write,file_hash,Cancelled,Unavailable
from .contracts import packet
from .resource_modes import allows  # §97.2: ORANGE/RED pause shadow learning
from .cognition import ROUTES,scaffold_route
from .runners import check,kill_process
POLICY_LABELS={'wake':('none','detail','gist','both'),'halt':('halt','continue'),
               # WP-T1 JEF_FAST_POLICY typed heads next to route/wake/halt (§3.3.1, G4): same label/shadow/approval path
               'skill':('none','skill'),'memory':('skip','recall','deep'),'channel':('NO_MESSAGE','SOURCE_EXACT','CONTROL','SYMBOLIC')}
FAST_HEADS=('wake','skill','memory','channel')  # read only the event source (one shared C2 embedding), no body trajectory
class Learner:
    def __init__(self,runtime):
        from .plasticity import Plasticity
        self.r=runtime;self.s=runtime.store;self.proc=None;self.plasticity=Plasticity(self.s)
    def training_config(self,component,update_id,manifest,modulate=True):
        # modulate=False: an offline candidate was already fitted with its exported F7 budget, so N10 cannot
        # rescale it after the fact; a standing modulator veto still refuses the import.
        gate=None
        if self.r.cfg['learning_mode']!='RECORD_ONLY':
            try:
                from .neuromod import controller
                gate=controller(self.r).gate(component)  # WP-N10: e×M×P scales this job's budget
            except Exception as exc:self.s.log('neuromod_gate_unavailable',None,{'component':component,'error':type(exc).__name__})
        if gate is not None and gate['veto']:raise ValueError('Lernen für '+component+' durch Modulator-Veto gesperrt')
        config=self.plasticity.budget(component,self.r.cfg,update_id,manifest,gate if modulate else None)
        # Persist the measured policy before spawning the optimizer so a crash
        # cannot leave a completed trial without its actual effective budget.
        with self.s.tx() as c:c.execute('UPDATE updates SET manifest=? WHERE id=?',(dumps(manifest),update_id))
        return config
    def observe_finished(self,update_id):
        # A diagnostic publication failure must not undo a finished, validated
        # candidate. Atomic F7 reconciliation repairs its observation on restart.
        try:return self.plasticity.observe(update_id)
        except Exception as exc:
            try:self.s.log('plasticity_observation_deferred',None,{'update_id':update_id,'error':type(exc).__name__})
            except Exception:pass
            return False
    def active(self,component='route'):
        m=self.s.generation();entry=self.s.components(m).get(component)
        if not entry:return None
        if entry.get('encoder_revision')!=self.r.models.revision(entry.get('encoder_role','C2_CONTROL')):raise Unavailable('Aktiver Head hat andere Encoder-Revision; rollback/erneut validieren')
        for role,revision in entry.get('dependency_revisions',{}).items():
            if self.r.models.revision(role)!=revision:raise Unavailable('Aktiver Head hat andere Modell-Abhängigkeit: '+role)
        self.s.validate_artifacts(m);return self.r.home/entry['path']
    def embedding(self,text,source_id,deadline):
        revision=self.r.models.revision('C2_CONTROL');key='native_embedding:'+revision+':'+source_id
        old,_=self.s.state(key)
        if old is not None:return old['values']
        vector=self.r.needle.embed(text,self.r.cancel_event,deadline)
        if not vector:raise Unavailable('Native embedding leer')
        self.s.set_state(key,{'values':vector,'encoder_revision':revision,'source_id':source_id});return vector
    def retrieval_context_revision(self):
        return digest(dumps({'worker':file_hash(APP/'v13/retrieval_worker.py'),'memory':file_hash(APP/'v13/memory.py'),'encoder':self.r.models.revision('C2_CONTROL')}))
    def retrieval_features(self,e,m,deadline):
        from .retrieval_worker import topic_view,pair_features
        query=self.s.read_source(e['source_ref']);key=self.s.read_source(m['key_ref'])
        if self.s.read_source(m['source_ref'])!=m['value'] or key!=m['key_text']:raise ValueError('Memory lineage changed')
        refs=[e['source_ref'],m['key_ref'],m['source_ref']];views=[]
        for text,ref in ((query,e['source_ref']),(key,m['key_ref'])):
            view=topic_view(text)
            if not view:raise ValueError('Empty memory cue')
            cache='retrieval-view:'+ref['source_id']+':'+digest(view);vr,_=self.s.state(cache)
            if vr is None:
                vr=self.s.source(view,'RETRIEVAL_VIEW');self.s.set_state(cache,vr)
            if self.s.read_source(vr)!=view:raise ValueError('Cue view changed')
            views.append(vr);refs.append(vr)
        vectors=[self.embedding(self.s.read_source(ref),ref['source_id'],deadline) for ref in (e['source_ref'],m['key_ref'],*views)]
        return pair_features(query,key,*vectors),refs
    def retrieve(self,e,m,deadline):
        prediction=None;reason='NO_APPROVED_COMPONENT';refs=[e['source_ref'],m['key_ref'],m['source_ref']];revision=self.retrieval_context_revision()
        try:
            check(self.r.cancel_event,deadline);path=self.active('memory_retrieval')
            if path:
                if self.s.components()['memory_retrieval'].get('context_revision')!=revision:raise Unavailable('Memory cue context changed')
                from .retrieval_worker import infer
                features,refs=self.retrieval_features(e,m,deadline);prediction=infer(features,path)
                reason='APPROVED_SOURCE_BOUND_RELEVANCE' if prediction['in_support'] else 'OUT_OF_SUPPORT'
        except Cancelled:raise
        except Exception as exc:reason=type(exc).__name__
        self.s.add_packet('MemoryRetrievalDecision',packet('MemoryRetrievalDecision','F3_CUE_RETRIEVAL',e['event_id'],self.s.generation_id,refs,
             query_ref=e['source_ref'],memory_ref=m['source_ref'],key_ref=m['key_ref'],memory_id=m['id'],context_revision=revision,prediction=prediction,semantic_truth_authority=False,fallback_reason=reason))
        self.s.log('memory_retrieval',e['event_id'],{'component':'memory_retrieval','memory_id':m['id'],'prediction':prediction,'fallback_reason':reason});return prediction
    def retrieval_labels(self):
        unique={}
        for row in self.s.rows("SELECT f.*,e.packet,e.session_id FROM feedback f JOIN events e ON e.id=f.event_id JOIN sources s ON s.id=f.source_id WHERE f.kind='retrieval' AND s.deleted=0 ORDER BY f.created DESC LIMIT 1024"):
            decision=self.s.one("SELECT payload FROM packets WHERE kind='HumanDecision' AND json_extract(payload,'$.source_ref.source_id')=?",(row['source_id'],))
            if not decision:continue
            d=json.loads(decision['payload']);selection=d.get('selection',{});e=json.loads(row['packet'])
            try:
                if d['kind']!='retrieval' or row['value'] not in {'relevant','irrelevant'} or d['learning_permission']!=row['permission'] or d['value']!=row['value'] or self.s.read_source(d['source_ref'])!=row['value']:raise ValueError('Decision mismatch')
                m=self.r.memory.candidate(selection['memory_id'],row['session_id'])
                if selection['query_ref']!=e['source_ref'] or selection['memory_ref']!=m['source_ref'] or selection['key_ref']!=m['key_ref'] or e['authority']!='AUTHORITATIVE':raise ValueError('Pair lineage mismatch')
                from .retrieval_worker import admissible
                if not admissible(self.s.read_source(e['source_ref']),m['key_text']):continue
                pair=digest(dumps([e['source_ref']['sha256'],m['key_ref']['sha256'],m['source_ref']['sha256']]))
                unique.setdefault(pair,(row,e,m,d,pair))
            except (KeyError,ValueError):continue
        return [v for v in reversed(list(unique.values())) if v[0]['permission']=='learn'][-256:]
    def shadow_retrieval(self):
        if self.r.cfg['learning_mode']=='RECORD_ONLY':raise ValueError('RECORD_ONLY: :learning shadow erforderlich')
        if self.r.guard.update(self.r.resources())!='NORMAL':raise Unavailable('Memory cue training waits for normal resources')
        data=self.retrieval_labels()
        if len(data)<48:raise ValueError('Mindestens 48 verschiedene explizite Memory/Query-Relevanzlabels --learn erforderlich')
        component='memory_retrieval';update=uid('upd');base=self.s.generation_id;folder=self.r.home/'shadow'/update;folder.mkdir();deadline=time.monotonic()+600;lineage=[]
        entry=self.s.components().get(component)
        if entry:
            old=self.s.one('SELECT manifest FROM updates WHERE id=?',(entry['update_id'],))
            if old:lineage.extend(json.loads(old['manifest']).get('source_ids',[]))
        manifest={'component':component,'base_generation':base,'encoder_role':'C2_CONTROL','encoder_revision':self.r.models.revision('C2_CONTROL'),
                  'dependency_revisions':{'C2_CONTROL':self.r.models.revision('C2_CONTROL')},'context_revision':self.retrieval_context_revision(),
                  'objective':'source-bound-semantic-retrieval-v1','commit_eligible':False,'body_learning':False,'semantic_truth_authority':False,'source_ids':lineage,'collected_pairs':0}
        with self.s.tx() as c:c.execute('INSERT INTO updates VALUES (?,?,?,?,?,?,?)',(update,base,'SHADOW_TRAINING',None,None,dumps(manifest),now()))
        try:
            self.r.pool.unload();features=[];labels=[];groups=[];pairs=[]
            for row,e,m,d,pair in data:
                check(self.r.cancel_event,deadline);x,refs=self.retrieval_features(e,m,deadline)
                features.append(x);labels.append(int(row['value']=='relevant'));groups.append(m['source_ref']['sha256']);pairs.append(pair)
                lineage.extend(ref['source_id'] for ref in refs+[d['source_ref']]);manifest.update(source_ids=sorted(set(lineage)),collected_pairs=len(pairs))
                with self.s.tx() as c:c.execute('UPDATE updates SET manifest=? WHERE id=?',(dumps(manifest),update))
                self.s.add_packet('LearningTrace',packet('LearningTrace','F6_LEARNING',e['event_id'],base,refs,path_id=component,activity=1.,eligibility=self.r.cfg['eligibility_decay'],authority='EXPLICIT_OPERATOR_MEMORY_RELEVANCE'))
            active=self.active(component);inp=folder/'input.json';atomic_write(inp,dumps({'config':self.training_config(component,update,manifest),'features':features,'labels':labels,'memory_groups':groups,'pair_ids':pairs,'active_checkpoint':str(active) if active else None}))
            self.r.needle.unload();env=os.environ.copy();env.update(PYTHONPATH=str(APP),OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1');last_check=time.monotonic()
            with (folder/'worker.log').open('wb') as log:
                self.proc=subprocess.Popen([sys.executable,'-m','v13.retrieval_worker',str(inp),str(folder)],stdout=log,stderr=log,env=env)
                while self.proc.poll() is None:
                    check(self.r.cancel_event,deadline);self.r.cancel_event.wait(.1)
                    if time.monotonic()-last_check>3:
                        if not allows(self.r.guard.update(self.r.resources()),'shadow_learning'):raise Unavailable('Memory cue resources critical')
                        last_check=time.monotonic()
                if self.proc.returncode:raise RuntimeError('Memory cue worker failed: '+str(folder/'worker.log'))
            check(self.r.cancel_event,deadline);metrics=json.loads((folder/'metrics.json').read_text());dest=self.r.home/'checkpoints'/(component+'-'+update+'.npz');os.replace(folder/'candidate.npz',dest);h=file_hash(dest)
            manifest.update(metrics=metrics,commit_eligible=metrics['commit_eligible']);status='PENDING_APPROVAL' if metrics['commit_eligible'] else 'EVALUATED_FAIL'
            with self.s.tx() as c:c.execute('UPDATE updates SET status=?,path=?,hash=?,manifest=? WHERE id=?',(status,str(dest.relative_to(self.r.home)),h,dumps(manifest),update))
            self.s.add_packet('UpdateManifest',packet('UpdateManifest','F6_LEARNING','TRAIN',base,update_id=update,base_brain_generation_id=base,status=status,artifact_hash=h,metrics=metrics))
            self.s.add_packet('TrainRunnerProof',packet('TrainRunnerProof','F10_RUNTIME','TRAIN',base,trainable_parameter_count=metrics['trainable_parameter_count'],runner_revision='numpy-native-memory-relevance-v1',device=metrics['device'],checks=metrics))
            self.observe_finished(update)
            self.s.log('shadow_result',None,{'component':component,'status':status,'metrics':metrics});return update+' '+status
        except BaseException as exc:
            kill_process(self.proc);manifest.update(source_ids=sorted(set(lineage)),abort_error_type=type(exc).__name__)
            with self.s.tx() as c:c.execute("UPDATE updates SET status='ABORTED',manifest=? WHERE id=?",(dumps(manifest),update))
            raise
        finally:self.proc=None;self.r.pool.unload();self.r.needle.unload();(folder/'input.json').unlink(missing_ok=True)
    def import_causal_output(self,dataset,trained_directory):
        """Verified offline shadow replay/import, never automatic activation."""
        from .causal_output import HEAD_FORMAT,execution_revision,dataset_authorizations,copy_dataset,validate_head
        from .causal_prepare import check_prepared
        from scripts.train_live_output_adapter import prepare
        from pathlib import Path
        import shutil
        if self.r.cfg['learning_mode']=='RECORD_ONLY':raise ValueError(':learning shadow required before importing an offline fitted candidate')
        if self.r.guard.update(self.r.resources())!='NORMAL':raise Unavailable('Causal shadow import waits for normal resources')
        check(self.r.cancel_event,time.monotonic()+1)
        dataset=Path(dataset).resolve();trained=Path(trained_directory).resolve();binding=check_prepared(self.r.home);abi=binding['feature_abi']
        inputs,observed_abi,_=prepare(dataset)
        if observed_abi!=abi:raise ValueError('Dataset requires exact installed streaming causal ABI')
        report=json.loads((trained/'report.json').read_text());candidate=trained/'candidate.npz'
        if report.get('schema')!='V13_CAUSAL_LIVE_OUTPUT_SHADOW_REPORT_V1' or report.get('format')!=HEAD_FORMAT or report.get('feature_abi')!=abi or report.get('dataset_sha256')!=file_hash(dataset) or report.get('candidate_sha256')!=file_hash(candidate) or report.get('numerical_worker_sha256')!=file_hash(APP/'v13/output_adapter_worker.py'):raise ValueError('Original offline shadow candidate/report/source binding differs')
        validate_head(candidate,abi)
        authorities,lineage=dataset_authorizations(self.s,dataset,self.r.models.revision('C3_LANGUAGE'),abi)
        active=self.s.components().get('output_adapter');parent=None
        if active:
            old=self.s.one('SELECT * FROM updates WHERE id=?',(active['update_id'],));old_manifest=json.loads(old['manifest'])
            if old_manifest.get('objective')!=HEAD_FORMAT:raise ValueError('Existing separate-prefill head cannot be converted; rollback before starting a causal lineage')
            from .causal_output import validate_update
            validate_update(self.s,old,self.r.revisions(),committed=True)
            if not inputs['active_checkpoint'] or file_hash(inputs['active_checkpoint'])!=active['sha256']:raise ValueError('Current same-ABI active retention checkpoint required')
            parent=active['update_id'];authorities+=old_manifest['human_authorizations'];lineage+=old_manifest['source_ids']
        elif inputs['active_checkpoint']:raise ValueError('No approved active checkpoint belongs to this Store')
        update=uid('upd');base=self.s.generation_id;folder=self.r.home/'shadow'/update;folder.mkdir()
        manifest={'component':'output_adapter','objective':HEAD_FORMAT,'base_generation':base,'commit_eligible':False,
            'encoder_role':'C3_LANGUAGE','encoder_revision':self.r.models.revision('C3_LANGUAGE'),
            'dependency_revisions':{'C3_LANGUAGE':self.r.models.revision('C3_LANGUAGE')},
            'context_revision':execution_revision(abi,self.r.models.revision('C3_LANGUAGE')),'feature_abi':abi,
            'source_ids':sorted(set(lineage)),'human_authorizations':list({a['original_decision_id']:a for a in authorities}.values()),
            'parent_output_update_id':parent,'body_learning':False,'native_body_parameters_modified':0,'semantic_truth_authority':False,
            'dataset_sha256':file_hash(dataset),'numerical_worker_sha256':file_hash(APP/'v13/output_adapter_worker.py'),
            'imported_candidate_sha256':file_hash(candidate),'native_calls':False}
        with self.s.tx() as c:c.execute('INSERT INTO updates VALUES (?,?,?,?,?,?,?)',(update,base,'SHADOW_TRAINING',None,None,dumps(manifest),now()))
        deadline=time.monotonic()+600
        try:
            effective=self.training_config('output_adapter',update,manifest,modulate=False)
            if any(inputs['config'][k]!=effective[k] for k in inputs['config']):raise ValueError('Exported optimizer config differs from current authorized F7 shadow budget')
            copied=copy_dataset(dataset,folder/'dataset');shutil.copyfile(candidate,folder/'imported-candidate.npz');shutil.copyfile(trained/'report.json',folder/'imported-report.json')
            self.r.pool.unload();self.r.needle.unload();env=os.environ.copy();env.update(PYTHONPATH=str(APP),OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
            with (folder/'worker.log').open('wb') as log:
                self.proc=subprocess.Popen([sys.executable,str(APP/'scripts/train_live_output_adapter.py'),'--dataset',str(copied),'--out',str(folder/'verified')],stdout=log,stderr=log,env=env)
                while self.proc.poll() is None:
                    check(self.r.cancel_event,deadline)
                    if not allows(self.r.guard.update(self.r.resources()),'shadow_learning'):raise Unavailable('Causal shadow-fit resources critical')
                    self.r.cancel_event.wait(.1)
            verified=json.loads((folder/'verified/report.json').read_text());metrics=verified['metrics'];actual=folder/'verified/candidate.npz'
            if file_hash(actual)!=manifest['imported_candidate_sha256']:raise ValueError('Imported weights differ from independently replayed exact shadow fit')
            if file_hash(folder/'imported-candidate.npz')!=manifest['imported_candidate_sha256'] or verified['dataset_sha256']!=manifest['dataset_sha256']:raise ValueError('Imported exact source bytes changed')
            after_auth,after_sources=dataset_authorizations(self.s,copied,self.r.models.revision('C3_LANGUAGE'),abi)
            if after_auth!=authorities[:len(after_auth)] or not set(after_sources).issubset(set(lineage)):raise ValueError('Human permissions changed during verified fit')
            check(self.r.cancel_event,deadline);validate_head(actual,abi)
            dest=self.r.home/'checkpoints'/('output_adapter-'+update+'.npz');shutil.copyfile(actual,dest);h=file_hash(dest)
            manifest.update(metrics=metrics,commit_eligible=metrics['commit_eligible'],candidate_sha256=h,
                verified_shadow_report={'path':str((folder/'verified/report.json').relative_to(self.r.home)),'sha256':file_hash(folder/'verified/report.json')})
            status='PENDING_APPROVAL' if metrics['commit_eligible'] else 'EVALUATED_FAIL'
            with self.s.tx() as c:c.execute('UPDATE updates SET status=?,path=?,hash=?,manifest=? WHERE id=?',(status,str(dest.relative_to(self.r.home)),h,dumps(manifest),update))
            self.s.add_packet('UpdateManifest',packet('UpdateManifest','F6_LEARNING','TRAIN',base,update_id=update,base_brain_generation_id=base,status=status,artifact_hash=h,metrics=metrics))
            self.observe_finished(update);return update+' '+status+'; exact same-causal shadow fit verified; individual :approve required'
        except BaseException as exc:
            kill_process(self.proc);manifest['abort_error_type']=type(exc).__name__
            with self.s.tx() as c:c.execute("UPDATE updates SET status='ABORTED',manifest=? WHERE id=?",(dumps(manifest),update))
            raise
        finally:self.proc=None;self.r.pool.unload();self.r.needle.unload()
    def causal_output_delta(self,e,observed):
        from .causal_output import approved_prediction
        prediction=None;reason='NO_APPROVED_SAME_CAUSAL_COMPONENT'
        try:prediction,reason=approved_prediction(self,observed)
        except Cancelled:raise
        except (ValueError,KeyError,OSError,RuntimeError,Unavailable) as exc:reason='REVOKED_OR_INCOMPATIBLE_SAME_CAUSAL_HEAD: '+type(exc).__name__
        row=self.s.one("SELECT payload FROM packets WHERE event_id=? AND kind='OutputAdapterContext' ORDER BY created DESC LIMIT 1",(e['event_id'],))
        if not row:raise ValueError('Output context receipt missing')
        ctx=json.loads(row['payload']);native=self.s.source(dumps(observed),'C3_SAME_CAUSAL_LIVE_OBSERVATION')
        self.s.add_packet('OutputAdapterDecision',packet('OutputAdapterDecision','C3_LANGUAGE',e['event_id'],self.s.generation_id,[*ctx['provenance'],native],context_ref=ctx['context_ref'],model_revision=ctx['model_revision'],context_revision=ctx['context_revision'],prediction=prediction,semantic_truth_authority=False,fallback_reason=reason,live_observation_ref=native,feature_abi=observed['feature_abi']))
        self.s.log('output_adapter',e['event_id'],{'component':'output_adapter','prediction':prediction,'fallback_reason':reason})
        return {'prediction':prediction,'fallback_reason':reason}
    def output_context_revision(self):
        return digest(dumps({'worker':file_hash(APP/'v13/output_adapter_worker.py'),'runner':file_hash(APP/'v13/runners.py'),'model':self.r.models.revision('C3_LANGUAGE')}))
    def output_delta(self,e,messages,deadline,context_refs=()):
        """Capture exact decoder context and optionally apply an approved delta."""
        text=self.s.read_source(e['source_ref'])
        if not messages or messages[-1]!={'role':'user','content':text}:raise ValueError('Native output context must end with the actual source query')
        refs=[e['source_ref'],*context_refs]
        for ref in refs:self.s.read_source(ref)
        revision=self.output_context_revision();context=self.s.source(dumps(messages),'C3_OUTPUT_CONTEXT');refs.append(context)
        self.s.add_packet('OutputAdapterContext',packet('OutputAdapterContext','C3_LANGUAGE',e['event_id'],self.s.generation_id,refs,context_ref=context,model_revision=self.r.models.revision('C3_LANGUAGE'),context_revision=revision,native_role='C3_LANGUAGE'))
        prediction=None;reason='NO_APPROVED_COMPONENT'
        try:
            path=self.active('output_adapter')
            if path:
                if self.s.components()['output_adapter'].get('context_revision')!=revision:raise Unavailable('Output adapter native context changed')
                from .output_adapter_worker import native_context,infer
                observed=native_context(self.r.pool,messages,self.r.cancel_event,deadline);prediction=infer(observed['feature'],path)
                reason='APPROVED_FIRST_NATIVE_TOKEN_DELTA' if prediction['in_support'] else 'OUT_OF_SUPPORT'
        except Cancelled:raise
        except Exception as exc:reason=type(exc).__name__
        self.s.add_packet('OutputAdapterDecision',packet('OutputAdapterDecision','C3_LANGUAGE',e['event_id'],self.s.generation_id,[e['source_ref'],context],context_ref=context,model_revision=self.r.models.revision('C3_LANGUAGE'),context_revision=revision,prediction=prediction,semantic_truth_authority=False,fallback_reason=reason))
        self.s.log('output_adapter',e['event_id'],{'component':'output_adapter','prediction':prediction,'fallback_reason':reason});return prediction
    def output_feedback(self,event_id,value,permission='record'):
        if permission not in {'record','learn'} or not value.strip() or len(value.encode())>4096:raise ValueError('Explicit bounded human output reference required')
        erow=self.s.one('SELECT packet,session_id FROM events WHERE id=?',(event_id,))
        if not erow or erow['session_id']!=self.r.session:raise ValueError('Output event must belong to this session')
        e=json.loads(erow['packet']);row=self.s.one("SELECT payload FROM packets WHERE kind='OutputAdapterContext' AND event_id=? ORDER BY created DESC LIMIT 1",(event_id,))
        if not row or e['authority']!='AUTHORITATIVE':raise ValueError('Actual C3 context for authoritative turn required')
        ctx=json.loads(row['payload']);self.s.read_source(ctx['context_ref'])
        if ctx['context_revision']!=self.output_context_revision():raise ValueError('Output context revision changed; produce a new C3 answer first')
        ref=self.s.source(value,'HUMAN_OUTPUT_REFERENCE');fid=uid('feedback')
        selection={'context_ref':ctx['context_ref'],'context_packet_id':ctx['packet_id'],'source_refs':ctx['provenance'],'context_revision':ctx['context_revision'],'model_revision':ctx['model_revision'],'target_position':0,'reference_only_without_human_learn':True}
        p=packet('HumanDecision','F5_HUMAN_CONTROL',event_id,e['brain_generation_id'],[*ctx['provenance'],ref],kind='output',value=value,source_ref=ref,learning_permission=permission,selection=selection)
        with self.s.tx() as c:c.execute('INSERT INTO feedback VALUES (?,?,?,?,?,?,?)',(fid,event_id,ref['source_id'],'output',value,permission,now()))
        self.s.add_packet('HumanDecision',p);return fid+' source='+ref['source_id']+' recorded; only first native token is a supported output target'
    def output_labels(self):
        unique={};revision=self.output_context_revision()
        for row in self.s.rows("SELECT f.*,e.packet FROM feedback f JOIN events e ON e.id=f.event_id JOIN sources s ON s.id=f.source_id WHERE f.kind='output' AND s.deleted=0 ORDER BY f.created DESC LIMIT 512"):
            decision=self.s.one("SELECT payload FROM packets WHERE kind='HumanDecision' AND json_extract(payload,'$.source_ref.source_id')=?",(row['source_id'],))
            if not decision:continue
            d=json.loads(decision['payload']);e=json.loads(row['packet'])
            try:
                ctx=d['selection'];ref=ctx['context_ref']
                recorded=self.s.one("SELECT payload FROM packets WHERE id=? AND kind='OutputAdapterContext' AND event_id=?",(ctx['context_packet_id'],e['event_id']))
                if not recorded:raise ValueError('Actual typed native context packet missing')
                native=json.loads(recorded['payload'])
                if native['provenance']!=ctx['source_refs'] or native['context_ref']!=ref:raise ValueError('Inherited native context provenance changed')
                for dependency in ctx['source_refs']:self.s.read_source(dependency)
                if d['kind']!='output' or d['value']!=row['value'] or d['learning_permission']!=row['permission'] or self.s.read_source(d['source_ref'])!=row['value'] or ctx['context_revision']!=revision or ctx['model_revision']!=self.r.models.revision('C3_LANGUAGE') or ctx['target_position']!=0 or e['authority']!='AUTHORITATIVE':raise ValueError('Output target lineage mismatch')
                messages=json.loads(self.s.read_source(ref))
                if not isinstance(messages,list) or not messages or any(not isinstance(m,dict) or m.get('role') not in {'system','user','assistant'} or not isinstance(m.get('content'),str) for m in messages):raise ValueError('Output native context invalid')
                unique.setdefault(ref['sha256'],(row,e,d,messages))
            except (ValueError,KeyError):continue
        return [x for x in reversed(list(unique.values())) if x[0]['permission']=='learn'][-128:]
    def shadow_output_adapter(self):
        if self.r.cfg['learning_mode']=='RECORD_ONLY':raise ValueError('RECORD_ONLY: :learning shadow required')
        if self.r.guard.update(self.r.resources())!='NORMAL':raise Unavailable('Output adapter waits for normal resources')
        from .output_adapter_worker import native_context
        data=self.output_labels()
        if len(data)<48:raise ValueError('At least 48 distinct explicit human output references --learn required')
        component='output_adapter';update=uid('upd');base=self.s.generation_id;folder=self.r.home/'shadow'/update;folder.mkdir();deadline=time.monotonic()+600;lineage=[]
        entry=self.s.components().get(component)
        if entry:
            old=self.s.one('SELECT manifest FROM updates WHERE id=?',(entry['update_id'],))
            if old:lineage.extend(json.loads(old['manifest']).get('source_ids',[]))
        manifest={'component':component,'base_generation':base,'encoder_role':'C3_LANGUAGE','encoder_revision':self.r.models.revision('C3_LANGUAGE'),'dependency_revisions':{'C3_LANGUAGE':self.r.models.revision('C3_LANGUAGE')},'context_revision':self.output_context_revision(),'objective':'c3-native-first-token-delta-v2','source_ids':lineage,'commit_eligible':False,'body_learning':False,'native_body_parameters_modified':0,'semantic_truth_authority':False,'native_observations':[]}
        with self.s.tx() as c:c.execute('INSERT INTO updates VALUES (?,?,?,?,?,?,?)',(update,base,'SHADOW_TRAINING',None,None,dumps(manifest),now()))
        try:
            self.r.needle.unload();runner=self.r.pool.get('C3_LANGUAGE');runner.load(self.r.cancel_event,deadline);targets=[]
            for row,_,_,_ in data:
                ids=runner._json('POST','/tokenize',{'content':row['value'],'add_special':False},deadline)['tokens']
                if not ids:raise ValueError('Human output reference has no native tokens')
                targets.append(ids[0])
            tokens=sorted(set(targets));active=self.active(component)
            if active:
                import numpy as np
                with np.load(active,allow_pickle=False) as a:tokens=a['token_ids'].tolist()
                if not set(targets)<=set(tokens):raise ValueError('Approved output vocabulary immutable; rollback before changing vocabulary')
            if not 2<=len(tokens)<=16:raise ValueError('Two to sixteen human-selected first native vocabulary tokens required')
            self.r.pool.unload();features=[];baselines=[];groups=[];labels=[]
            for (row,e,d,messages),target in zip(data,targets):
                check(self.r.cancel_event,deadline);observed=native_context(self.r.pool,messages,self.r.cancel_event,deadline,tokens)
                refs=[*d['selection']['source_refs'],d['source_ref']];lineage.extend(ref['source_id'] for ref in refs);features.append(observed['feature']);baselines.append(observed['base_log_probabilities']);groups.append(d['selection']['context_ref']['sha256']);labels.append(tokens.index(target))
                self.s.add_packet('LearningTrace',packet('LearningTrace','F6_LEARNING',e['event_id'],base,refs,path_id=component,activity=1.,eligibility=self.r.cfg['eligibility_decay'],authority='EXPLICIT_HUMAN_FIRST_NATIVE_TOKEN'))
                obsref=self.s.source(dumps(observed),'C3_OUTPUT_NATIVE_OBSERVATION');lineage.append(obsref['source_id']);manifest['native_observations'].append(obsref);manifest['source_ids']=sorted(set(lineage))
                with self.s.tx() as c:c.execute('UPDATE updates SET manifest=? WHERE id=?',(dumps(manifest),update))
            inp=folder/'input.json';atomic_write(inp,dumps({'config':self.training_config(component,update,manifest),'token_ids':tokens,'native_features':features,'base_log_probabilities':baselines,'target_indices':labels,'source_groups':groups,'active_checkpoint':str(active) if active else None}))
            env=os.environ.copy();env.update(PYTHONPATH=str(APP),OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
            with (folder/'worker.log').open('wb') as log:
                self.proc=subprocess.Popen([sys.executable,'-m','v13.output_adapter_worker',str(inp),str(folder)],stdout=log,stderr=log,env=env)
                while self.proc.poll() is None:
                    check(self.r.cancel_event,deadline);self.r.cancel_event.wait(.1)
                    if not allows(self.r.guard.update(self.r.resources()),'shadow_learning'):raise Unavailable('Output delta resources critical')
                if self.proc.returncode:raise RuntimeError('Output adapter worker failed: '+str(folder/'worker.log'))
            check(self.r.cancel_event,deadline);metrics=json.loads((folder/'metrics.json').read_text());dest=self.r.home/'checkpoints'/(component+'-'+update+'.npz');os.replace(folder/'candidate.npz',dest);manifest.update(metrics=metrics,commit_eligible=metrics['commit_eligible']);status='PENDING_APPROVAL' if metrics['commit_eligible'] else 'EVALUATED_FAIL';h=file_hash(dest)
            with self.s.tx() as c:c.execute('UPDATE updates SET status=?,path=?,hash=?,manifest=? WHERE id=?',(status,str(dest.relative_to(self.r.home)),h,dumps(manifest),update))
            self.s.add_packet('UpdateManifest',packet('UpdateManifest','F6_LEARNING','TRAIN',base,update_id=update,base_brain_generation_id=base,status=status,artifact_hash=h,metrics=metrics))
            self.s.add_packet('TrainRunnerProof',packet('TrainRunnerProof','F10_RUNTIME','TRAIN',base,trainable_parameter_count=metrics['trainable_parameter_count'],runner_revision='numpy-native-output-delta-v1',device=metrics['device'],checks=metrics));self.observe_finished(update)
            self.s.log('shadow_result',None,{'component':component,'status':status,'metrics':metrics});return update+' '+status+'; first native token delta only, base weights unchanged'
        except BaseException as exc:
            kill_process(self.proc);manifest.update(source_ids=sorted(set(lineage)),abort_error_type=type(exc).__name__)
            with self.s.tx() as c:c.execute("UPDATE updates SET status='ABORTED',manifest=? WHERE id=?",(dumps(manifest),update))
            raise
        finally:self.proc=None;self.r.pool.unload();self.r.needle.unload();(folder/'input.json').unlink(missing_ok=True)
    def control_context_revision(self):
        return digest(dumps({'version':'native-route-calibration-v2-first-proposal','model':self.r.models.revision('C2_CONTROL'),
                             'tools_sha256':file_hash(APP/'specs/control_tools.json'),'worker_sha256':file_hash(APP/'scripts/needle_worker.cpp')}))
    def control_calibrate(self,e,control):
        """Observe native confidence and optionally apply an approved scoped map."""
        if not isinstance(control,dict):raise ValueError('Native control object required')
        self.s.read_source(e['source_ref']);result=None;reason='NO_APPROVED_COMPONENT';revision=self.control_context_revision()
        try:
            path=self.active('control_calibration')
            if path:
                if self.s.components()['control_calibration'].get('context_revision')!=revision:raise Unavailable('Calibration native context changed')
                from .control_calibration_worker import infer
                result=infer(control,path);reason='HELD_OUT_NATIVE_ROUTE_AGREEMENT_ONLY' if result['in_support'] else 'OUT_OF_SUPPORT'
        except Cancelled:raise
        except Exception as exc:reason=type(exc).__name__
        p=packet('ControlCalibration','C2_CONTROL',e['event_id'],self.s.generation_id,[e['source_ref']],source_ref=e['source_ref'],native_control=control,
                 model_revision=self.r.models.revision('C2_CONTROL'),context_revision=revision,prediction=result,semantic_truth_authority=False,fallback_reason=reason)
        self.s.add_packet('ControlCalibration',p);self.s.log('control_calibration',e['event_id'],{'component':'control_calibration','prediction':result,'fallback_reason':reason})
        return result
    def control_labels(self):
        """Newest explicit permission per immutable source; no inferred labels."""
        unique={}
        for row in self.s.rows("SELECT f.*,e.packet FROM feedback f JOIN events e ON e.id=f.event_id JOIN sources s ON s.id=f.source_id WHERE f.kind='route' AND s.deleted=0 ORDER BY f.created DESC LIMIT 512"):
            e=json.loads(row['packet']);unique.setdefault(e['source_ref']['sha256'],(row,e))
        return [v for v in reversed(list(unique.values())) if v[0]['permission']=='learn'][-self.r.cfg['calibration_sources']:]
    def shadow_control_calibration(self):
        if self.r.cfg['learning_mode']=='RECORD_ONLY':raise ValueError('RECORD_ONLY: keine Calibration-Optimizer-Schritte. :learning shadow')
        if self.r.guard.update(self.r.resources())!='NORMAL':raise Unavailable('Kalibrierung wartet auf normale Ressourcen')
        from .control_calibration_worker import observation
        component='control_calibration';data=self.control_labels()
        if len(data)<32:raise ValueError('Mindestens 32 verschiedene explizite :feedback route ... --learn Quellen erforderlich')
        uid_=uid('upd');base=self.s.generation_id;folder=self.r.home/'shadow'/uid_;folder.mkdir();deadline=time.monotonic()+600;lineage=[]
        entry=self.s.components().get(component)
        if entry:
            old=self.s.one('SELECT manifest FROM updates WHERE id=?',(entry['update_id'],))
            if old:lineage.extend(json.loads(old['manifest']).get('source_ids',[]))
        manifest={'component':component,'commit_eligible':False,'encoder_role':'C2_CONTROL','encoder_revision':self.r.models.revision('C2_CONTROL'),
                  'dependency_revisions':{'C2_CONTROL':self.r.models.revision('C2_CONTROL')},'base_generation':base,'context_revision':self.control_context_revision(),
                  'source_ids':lineage,'objective':'native-route-confidence-calibration-v1','body_learning':False,'semantic_truth_authority':False,'native_observations':[],
                  'observation_budget_seconds':self.r.cfg['calibration_observation_seconds'],'job_budget_seconds':600,'native_attempts':[]}
        with self.s.tx() as c:c.execute('INSERT INTO updates VALUES (?,?,?,?,?,?,?)',(uid_,base,'SHADOW_TRAINING',None,None,dumps(manifest),now()))
        try:
            self.r.pool.unload();rows=[];labels=[];groups=[]
            for row,e in data:
                check(self.r.cancel_event,deadline);text=self.s.read_source(e['source_ref'])
                lineage.extend([e['source_ref']['source_id'],row['source_id']]);manifest['source_ids']=sorted(set(lineage))
                started=time.monotonic();observation_deadline=min(deadline,started+self.r.cfg['calibration_observation_seconds'])
                attempt={'event_id':e['event_id'],'source_id':e['source_ref']['source_id'],'source_sha256':e['source_ref']['sha256'],
                         'status':'RUNNING','available_budget_s':max(0.,observation_deadline-started)}
                manifest['native_attempts'].append(attempt);self.r.needle.last_metrics={}
                with self.s.tx() as c:c.execute('UPDATE updates SET manifest=? WHERE id=?',(dumps(manifest),uid_))
                try:
                    control=self.r.needle.control(text,self.r.cancel_event,observation_deadline)
                    attempt.update(status='FINAL',actual_control=control)
                except BaseException as exc:
                    attempt.update(status='FAILED',error_type=type(exc).__name__,error=str(exc)[:400]);raise
                finally:
                    attempt.update(duration_s=time.monotonic()-started,native_metrics=dict(self.r.needle.last_metrics))
                    with self.s.tx() as c:c.execute('UPDATE updates SET manifest=? WHERE id=?',(dumps(manifest),uid_))
                measured=observation(control);self.control_calibrate(e,control);p=self.s.one("SELECT id FROM packets WHERE kind='ControlCalibration' AND event_id=? ORDER BY created DESC LIMIT 1",(e['event_id'],))
                rows.append(measured);labels.append(int(measured['route']==row['value']));groups.append(e['source_ref']['sha256']);lineage.extend([e['source_ref']['source_id'],row['source_id']]);manifest['native_observations'].append(p['id'])
                manifest['source_ids']=sorted(set(lineage))
                # Keep actual collected observations through a mid-collection crash.
                with self.s.tx() as c:c.execute('UPDATE updates SET manifest=? WHERE id=?',(dumps(manifest),uid_))
                self.s.add_packet('LearningTrace',packet('LearningTrace','F6_LEARNING',e['event_id'],base,[e['source_ref']],path_id=component,activity=1.,eligibility=self.r.cfg['eligibility_decay'],authority='EXPLICIT_OPERATOR_ROUTE_LABEL'))
            inp=folder/'input.json';active=self.active(component);atomic_write(inp,dumps({'config':self.training_config(component,uid_,manifest),'observations':rows,'correct_labels':labels,'source_groups':groups,'active_checkpoint':str(active) if active else None}))
            self.r.needle.unload();env=os.environ.copy();env.update(PYTHONPATH=str(APP),OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1');last_check=time.monotonic()
            with (folder/'worker.log').open('wb') as log:
                self.proc=subprocess.Popen([sys.executable,'-m','v13.control_calibration_worker',str(inp),str(folder)],stdout=log,stderr=log,env=env)
                while self.proc.poll() is None:
                    check(self.r.cancel_event,deadline);self.r.cancel_event.wait(.1)
                    if time.monotonic()-last_check>3:
                        if not allows(self.r.guard.update(self.r.resources()),'shadow_learning'):raise Unavailable('Calibration resources critical')
                        last_check=time.monotonic()
                if self.proc.returncode:raise RuntimeError('Calibration worker failed: '+str(folder/'worker.log'))
            check(self.r.cancel_event,deadline);metrics=json.loads((folder/'metrics.json').read_text());dest=self.r.home/'checkpoints'/(component+'-'+uid_+'.npz');os.replace(folder/'candidate.npz',dest);h=file_hash(dest)
            manifest.update(source_ids=sorted(set(lineage)),metrics=metrics,commit_eligible=metrics['commit_eligible']);status='PENDING_APPROVAL' if metrics['commit_eligible'] else 'EVALUATED_FAIL'
            with self.s.tx() as c:c.execute('UPDATE updates SET status=?,path=?,hash=?,manifest=? WHERE id=?',(status,str(dest.relative_to(self.r.home)),h,dumps(manifest),uid_))
            self.s.add_packet('UpdateManifest',packet('UpdateManifest','F6_LEARNING','TRAIN',base,update_id=uid_,base_brain_generation_id=base,status=status,artifact_hash=h,metrics=metrics))
            self.s.add_packet('TrainRunnerProof',packet('TrainRunnerProof','F10_RUNTIME','TRAIN',base,trainable_parameter_count=metrics['trainable_parameter_count'],runner_revision='numpy-native-control-calibration-v1',device=metrics['device'],checks=metrics))
            self.observe_finished(uid_)
            self.s.log('shadow_result',None,{'component':component,'status':status,'metrics':metrics});return uid_+' '+status+'; native Routing-Übereinstimmung, keine semantische Wahrheitskonfidenz'
        except BaseException as exc:
            kill_process(self.proc);manifest.update(source_ids=sorted(set(lineage)),abort_error_type=type(exc).__name__)
            with self.s.tx() as c:c.execute("UPDATE updates SET status='ABORTED',manifest=? WHERE id=?",(dumps(manifest),uid_))
            raise
        finally:self.proc=None;self.r.pool.unload();self.r.needle.unload();(folder/'input.json').unlink(missing_ok=True)
    def uses_route_words(self,active=None):
        """Word channel on for new route heads (config route_head_words), and always kept once the active head has it."""
        if self.r.cfg.get('route_head_words'):return True
        if active is None:return False
        import numpy as np
        from .learning_worker import word_dim
        with np.load(active,allow_pickle=False) as z:return word_dim(z)>0
    def rule_anchors(self,labelled,deadline,limit=64):
        """WP-Z6i: while a --sofort rule exists, recent unlabelled questions outside every such rule's words become soft
        anchors at the active head's own route (weight .5), so learning the human's rule does not spill over to
        questions the human did not name. None without a rule."""
        from .route_supersede import rules
        from .route_words import vector
        targets=sorted({r['route'] for r in rules(self.s) if r.get('apply_now')})
        if not targets:return None
        words=[w for r in rules(self.s) if r.get('apply_now') for w in r['words']];out=[]
        for row in self.s.rows('SELECT e.packet,e.source_id FROM events e JOIN sources s ON s.id=e.source_id WHERE s.deleted=0 ORDER BY e.created DESC LIMIT 256'):
            e=json.loads(row['packet']);text=self.s.read_source(e['source_ref'])
            if text in labelled or any(w in text.lower() for w in words) or text in [t for t,_ in out]:continue
            out.append((text,row['source_id']))
            if len(out)>=limit:break
        if not out:return None
        emb=[self.embedding(t,sid,deadline) for t,sid in out];wv=[vector(t) for t,_ in out]
        return {'embeddings':emb,'words':wv,'weight':.5,'rule_routes':[ROUTES.index(t) for t in targets]}
    def propose(self,text,source_id,deadline):
        path=self.active()
        if path is None:return None
        import numpy as np
        from .learning_worker import route_logits
        emb=self.embedding(text,source_id,deadline)
        with np.load(path,allow_pickle=False) as z:logits=route_logits(z,emb,text)
        p=np.exp(logits-logits.max());p/=p.sum();order=np.argsort(p)
        return {'route':ROUTES[int(order[-1])],'probabilities':p.tolist(),'margin':float(p[order[-1]]-p[order[-2]]),'generation':self.s.generation_id,'calibrated':False}
    def context_revision(self,component):
        return digest(dumps({'format':'bounded-jef-readout-v2-source-and-trajectory','component':component,'models':self.dependencies(),
                             'channel':self.r.cfg['channel'],'observer_tokens':self.r.cfg['observer_tokens'],'b2_state_slots':self.r.cfg['b2_state_slots']}))
    def dependencies(self):return {role:self.r.models.revision(role) for role in ('C2_CONTROL','B1_DETAIL','B2_GIST')}
    def readout_embedding(self,component,context_ref,source_ref,deadline):
        context=self.s.read_source(context_ref)
        if component in FAST_HEADS:return self.embedding(context,context_ref['source_id'],deadline)
        # Keep the authoritative input distinct from fallible, changing offers.
        # The 0.2 trajectory scale is a bounded BOOT feature weight, not a learned
        # trust score. Both parts are actual frozen native embeddings.
        source=self.s.read_source(source_ref)
        source_vector=self.embedding(source,source_ref['source_id'],deadline)
        trajectory_vector=self.embedding(context,context_ref['source_id'],deadline)
        return source_vector+[.2*x for x in trajectory_vector]
    def decide(self,component,e,baseline,deadline,offers=(),enabled=True):
        """Readout for the existing observer/re-entry boundary, with a durable trace.

        Without an approved, supported readout the existing scaffold is unchanged.
        Generated offers are inputs tagged as hypotheses, never human labels.
        """
        if component not in POLICY_LABELS or baseline not in POLICY_LABELS[component]:raise ValueError('Executive action')
        text=self.s.read_source(e['source_ref']);refs=[e['source_ref']];stored=[]
        for p in offers:
            row=self.s.one("SELECT payload FROM packets WHERE id=? AND kind='OfferPacket'",(p['packet_id'],))
            if not row:raise ValueError('Trajectory packet missing')
            actual=json.loads(row['payload'])
            if actual['event_id']!=e['event_id'] or actual['brain_generation_id']!=e['brain_generation_id']:raise ValueError('Trajectory event/generation mismatch')
            if actual.get('model_revision')!=self.r.models.revision(actual['role']):raise ValueError('Trajectory model mismatch')
            stored.append(actual);refs.extend(actual.get('evidence_refs',[]))
        if component=='halt' and (len(stored)!=2 or [p['role'] for p in stored]!=['B1_DETAIL','B2_GIST']):raise ValueError('Halt benötigt eine gespeicherte B1/B2-Trajektorie')
        if component in FAST_HEADS:context_ref=e['source_ref']
        else:
            context=dumps({'input':text[:4000],'trajectory_kind':'TWO_FROZEN_BODY_OFFERS','offers':[{'role':p['role'],'hypothesis':p['offer']} for p in stored]})
            context_ref=self.s.source(context,'EXECUTIVE_TRAJECTORY');text=context;refs.append(context_ref)
        revision=self.context_revision(component);action=baseline;learned=False;prediction=None;reason='NO_APPROVED_COMPONENT'
        try:
            if not enabled:raise Unavailable('Operator override')
            entry=self.s.components().get(component);path=self.active(component)
            if path:
                if entry.get('context_revision')!=revision:raise Unavailable('Readout-Kontext geändert; erneut validieren')
                from .readout_worker import infer
                prediction=infer(self.readout_embedding(component,context_ref,e['source_ref'],deadline),path)
                if prediction['in_support'] and prediction['confidence']>=.6 and prediction['margin']>=.1:
                    action=POLICY_LABELS[component][prediction['index']];learned=True;reason='APPROVED_BOUNDED_READOUT'
                else:reason='OUT_OF_SUPPORT_OR_UNCERTAIN'
        except Cancelled:raise
        except Exception as exc:reason=type(exc).__name__
        result=packet('ExecutiveDecision','C2_CONTROL' if component in FAST_HEADS else 'C4_FOCAL',e['event_id'],self.s.generation_id,refs,
                      component=component,context_ref=context_ref,baseline=baseline,action=action,learned=learned,context_revision=revision,
                      trajectory_offer_ids=[p['packet_id'] for p in stored],prediction=prediction,fallback_reason=reason,
                      authority='BOUNDED_OBSERVER_POLICY_NOT_OUTPUT_OR_PERMISSION',dependency_revisions=self.dependencies())
        self.s.add_packet('ExecutiveDecision',result)
        self.s.log('executive_decision',e['event_id'],{'component':component,'action':action,'learned':learned,'prediction':prediction,'fallback_reason':reason})
        return result
    def shadow_readout(self,component):
        if component not in POLICY_LABELS:raise ValueError(':learn route|'+'|'.join(POLICY_LABELS))
        if self.r.cfg['learning_mode']=='RECORD_ONLY':raise ValueError('RECORD_ONLY: keine Optimizer-Schritte. :learning shadow')
        if self.r.guard.update(self.r.resources())!='NORMAL':raise Unavailable('Shadow-Lernen wartet auf normale RAM-/Temperaturwerte')
        import numpy  # Fail before creating a candidate if setup is incomplete.
        from .jefoutcome import _valid_human_receipt
        revision=self.context_revision(component);unique={}
        rows=self.s.rows("SELECT f.*,s.hash FROM feedback f JOIN sources s ON s.id=f.source_id WHERE f.kind=? AND s.deleted=0 ORDER BY f.created DESC LIMIT 512",(component,))
        for row in rows:
            decision=self.s.one("SELECT payload FROM packets WHERE kind='HumanDecision' AND event_id=? AND json_extract(payload,'$.source_ref.source_id')=?",(row['event_id'],row['source_id']))
            label=json.loads(decision['payload']) if decision else {};pid=label.get('decision_packet_id')
            saved=self.s.one("SELECT payload FROM packets WHERE kind='ExecutiveDecision' AND id=?",(pid,))
            if not saved:continue
            p=json.loads(saved['payload'])
            if not _valid_human_receipt(self.s,row,label,p):continue
            if p['component']!=component or p['context_revision']!=revision:continue
            key=p['context_ref']['sha256']
            # A newer RECORD label revokes prior permission for this exact context.
            if key not in unique:unique[key]=(row,p)
        data=[(key,row,p) for key,(row,p) in reversed(list(unique.items())) if row['permission']=='learn'][-128:]
        try:  # WP-U1 §3.3.8: outcome self-labels fill contexts without a human label (only after :fastpolicy outcomes learn)
            from .jefoutcome import training_rows
            # Every human decision, including RECORD-only and later revocations,
            # outranks a lower-authority self-outcome for the same context.
            data+=training_rows(self.s,component,revision,set(unique))
        except Exception as exc:self.s.log('jef_outcome_unavailable',None,{'stage':'training','error':type(exc).__name__})
        if any(sum(row['value']==label for _,row,_ in data)<6 for label in POLICY_LABELS[component]):raise ValueError('Je Klasse mindestens 6 verschiedene :feedback '+component+' <Wert> --learn; ohne gültige Entscheidung kein Trainingssample')
        deadline=time.monotonic()+240;base=self.s.generation_id;uid_=uid('upd');folder=self.r.home/'shadow'/uid_;folder.mkdir()
        lineage=[];active_entry=self.s.components().get(component)
        if active_entry:
            old=self.s.one('SELECT manifest FROM updates WHERE id=?',(active_entry.get('update_id'),))
            if old:lineage.extend(json.loads(old['manifest']).get('source_ids',[]))
        manifest={'component':component,'commit_eligible':False,'encoder_revision':self.r.models.revision('C2_CONTROL'),'dependency_revisions':self.dependencies(),
                  'context_revision':revision,'source_ids':lineage,'objective':'explicit-human-'+component+'-readout-v1','scope':'external_'+component+'_readout_only','body_learning':False,'base_generation':base}
        with self.s.tx() as c:c.execute('INSERT INTO updates VALUES (?,?,?,?,?,?,?)',(uid_,base,'SHADOW_TRAINING',None,None,dumps(manifest),now()))
        try:
            embeddings=[];labels=[];baselines=[];contexts=[];decision_ids=[]
            for context_hash,row,p in data:
                check(self.r.cancel_event,deadline)
                # Revalidate every exact input, source and label before the optimizer.
                for ref in p['provenance']:self.s.read_source(ref);lineage.append(ref['source_id'])
                source=self.s.one('SELECT * FROM sources WHERE id=?',(row['source_id'],));label_ref={'source_id':source['id'],'sha256':source['hash'],'char_start':0,'char_end':source['chars'],'modality':'text'}
                if self.s.read_source(label_ref)!=row['value']:raise ValueError('Human label/source mismatch')
                ref=p['context_ref'];embeddings.append(self.readout_embedding(component,ref,p['provenance'][0],deadline));labels.append(POLICY_LABELS[component].index(row['value']));baselines.append(POLICY_LABELS[component].index(p['baseline']));contexts.append(context_hash);decision_ids.append(p['packet_id']);lineage.append(row['source_id'])
                self.s.add_packet('LearningTrace',packet('LearningTrace','F6_LEARNING',row['event_id'],base,[ref,label_ref],path_id='C_'+component.upper()+'_READOUT',activity=1.,eligibility=self.r.cfg['eligibility_decay'],authority=row.get('authority') or 'EXPLICIT_HUMAN_LEARN'))
            active=self.active(component);request={'component':component,'config':self.training_config(component,uid_,manifest),'embeddings':embeddings,'labels':labels,'scaffold_labels':baselines,'context_hashes':contexts,'active_checkpoint':str(active) if active else None}
            inp=folder/'input.json';atomic_write(inp,dumps(request));self.r.pool.unload();self.r.needle.unload()
            env=os.environ.copy();env.update(PYTHONPATH=str(APP),OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1');last_check=time.monotonic()
            with (folder/'worker.log').open('wb') as log:
                self.proc=subprocess.Popen([sys.executable,'-m','v13.readout_worker',str(inp),str(folder)],stdout=log,stderr=log,env=env)
                while self.proc.poll() is None:
                    check(self.r.cancel_event,deadline);self.r.cancel_event.wait(.1)
                    if time.monotonic()-last_check>3:
                        if not allows(self.r.guard.update(self.r.resources()),'shadow_learning'):raise Unavailable('Ressourcenlimit im Readout-Training')
                        last_check=time.monotonic()
                if self.proc.returncode:raise RuntimeError('Readout-Worker fehlgeschlagen: '+str(folder/'worker.log'))
            metrics=json.loads((folder/'metrics.json').read_text());dest=self.r.home/'checkpoints'/(component+'-'+uid_+'.npz');os.replace(folder/'candidate.npz',dest);h=file_hash(dest)
            manifest.update(source_ids=sorted(set(lineage)),decision_packet_ids=decision_ids,context_hashes=contexts,metrics=metrics,commit_eligible=metrics['commit_eligible'])
            status='PENDING_APPROVAL' if metrics['commit_eligible'] else 'EVALUATED_FAIL'
            with self.s.tx() as c:c.execute('UPDATE updates SET status=?,path=?,hash=?,manifest=? WHERE id=?',(status,str(dest.relative_to(self.r.home)),h,dumps(manifest),uid_))
            self.s.add_packet('UpdateManifest',packet('UpdateManifest','F6_LEARNING','TRAIN',base,update_id=uid_,base_brain_generation_id=base,status=status,artifact_hash=h,metrics=metrics))
            self.s.add_packet('TrainRunnerProof',packet('TrainRunnerProof','F10_RUNTIME','TRAIN',base,trainable_parameter_count=metrics['trainable_parameter_count'],runner_revision='numpy-bounded-readout-v1',device=metrics['device'],checks=metrics))
            self.observe_finished(uid_)
            self.s.log('shadow_result',None,{'id':uid_,'component':component,'status':status,'metrics':metrics});return uid_+' '+status+'; aktive Generation unverändert'
        except BaseException:
            kill_process(self.proc)
            with self.s.tx() as c:c.execute("UPDATE updates SET status='ABORTED',manifest=? WHERE id=?",(dumps(manifest),uid_))
            raise
        finally:self.proc=None;(folder/'input.json').unlink(missing_ok=True)
    def predict_states(self,role,states):
        component='b1_predictor' if role=='B1_DETAIL' else 'b2_predictor';path=self.active(component)
        if not path:return None
        from .predictor_worker import predict
        return predict(states,path)|{'component':component,'generation':self.s.generation_id}
    def student_percept(self,text):
        path=self.active('a3_student')
        if path is None:return None
        from .student_worker import infer
        return infer(text,path)|{'generation':self.s.generation_id,'component':'a3_student','encoder_revision':self.r.models.revision('C2_CONTROL')}
    def student_route(self,e):
        """A3 student route from the stored percept features (no Needle call): None, a status dict or {route, percept}."""
        row=self.s.one("SELECT payload FROM packets WHERE kind='PerceptPacket' AND event_id=? ORDER BY created DESC LIMIT 1",(e['event_id'],))
        if not row:return None
        p=json.loads(row['payload'])
        if 'student_feature_path' not in p:return None
        if p['brain_generation_id']!=self.s.generation_id or p['source_ref']!=e['source_ref']:raise ValueError('A3 percept source/generation changed')
        self.s.read_source(p['source_ref']);path=(self.r.home/p['student_feature_path']).resolve()
        if not path.is_relative_to((self.r.home/'data/blobs').resolve()) or file_hash(path)!=p['student_feature_sha256']:raise ValueError('A3 feature hash/path invalid')
        features_=json.loads(path.read_text())
        if features_['generation']!=self.s.generation_id or features_['encoder_revision']!=self.r.models.revision('C2_CONTROL'):raise ValueError('A3 feature revision changed')
        if not features_['in_support']:return {'status':'OUT_OF_SUPPORT','routing_authority':0}
        import numpy as np
        from .learning_worker import route_logits
        with np.load(self.active(),allow_pickle=False) as a:logits=route_logits(a,features_['teacher_feature_prediction'],self.s.read_source(p['source_ref']))
        return {'route':ROUTES[int(np.argmax(logits))],'percept':p}
    def compare_student_route(self,e,teacher):
        """Actual JEF classifier consumer in T1 shadow (T2 fallback is gated in aplane.py)."""
        try:
            sr=self.student_route(e)
            if not sr or 'route' not in sr:return sr
            route=sr['route'];p=sr['percept']
            result=packet('StudentEvaluation','C2_CONTROL',e['event_id'],self.s.generation_id,[p['source_ref']],percept_packet_id=p['packet_id'],source_ref=p['source_ref'],student_route=route,teacher_route=teacher['route'],agreement=route==teacher['route'],routing_authority=0)
            self.s.add_packet('StudentEvaluation',result);self.s.log('student_route_shadow',e['event_id'],result)
            return {k:result[k] for k in ('packet_id','percept_packet_id','student_route','teacher_route','agreement','routing_authority')}
        except Exception as exc:
            self.s.log('student_route_unavailable',e['event_id'],{'error':type(exc).__name__});return {'status':'UNAVAILABLE','routing_authority':0}
    def shadow_student(self):
        """Explicit raw observations -> frozen A2 semantic features -> A3 update."""
        if self.r.cfg['learning_mode']=='RECORD_ONLY':raise ValueError('RECORD_ONLY: keine A3-Optimizer-Schritte. :learning shadow')
        if self.r.guard.update(self.r.resources())!='NORMAL':raise Unavailable('A3-Lernen wartet auf normale Ressourcen')
        import numpy
        from .student_worker import STEM
        component='a3_student';unique={}
        rows=self.s.rows("SELECT f.*,e.packet FROM feedback f JOIN events e ON e.id=f.event_id JOIN sources s ON s.id=f.source_id WHERE f.kind='alignment' AND s.deleted=0 ORDER BY f.created DESC LIMIT 256")
        for row in rows:
            e=json.loads(row['packet']);text=self.s.read_source(e['source_ref']);unique.setdefault(text,(row,e))
        data=[(text,pair) for text,pair in reversed(list(unique.items())) if pair[0]['permission']=='learn'][-128:]
        if len(data)<32:raise ValueError('Mindestens 32 verschiedene Quellen mit :feedback alignment observe --learn erforderlich')
        base=self.s.generation_id;uid_=uid('upd');folder=self.r.home/'shadow'/uid_;folder.mkdir();deadline=time.monotonic()+600;lineage=[]
        entry=self.s.components().get(component)
        if entry:
            row=self.s.one('SELECT manifest FROM updates WHERE id=?',(entry['update_id'],))
            if row:lineage.extend(json.loads(row['manifest']).get('source_ids',[]))
        manifest={'component':component,'commit_eligible':False,'encoder_role':'C2_CONTROL','encoder_revision':self.r.models.revision('C2_CONTROL'),
                  'dependency_revisions':{'C2_CONTROL':self.r.models.revision('C2_CONTROL')},'source_ids':lineage,'base_generation':base,
                  'objective':'a3-text-teacher-alignment-reconstruction-v1','context_revision':STEM,'teacher_role':'C2_CONTROL','teacher_lane':'A2_FROZEN_SEMANTIC_REFERENCE',
                  'teacher_truth_authority':False,'teacher_stop_gradient':True,'body_learning':False,'receiver_authority':0,'consumer_mode':'T1_SHADOW','target_packet_ids':[]}
        with self.s.tx() as c:c.execute('INSERT INTO updates VALUES (?,?,?,?,?,?,?)',(uid_,base,'SHADOW_TRAINING',None,None,dumps(manifest),now()))
        try:
            self.r.pool.unload();texts=[];targets=[];groups=[]
            for text,(row,e) in data:
                check(self.r.cancel_event,deadline)
                if not 0<len(text.encode())<=4096:raise ValueError('A3-Paar überschreitet 4096 UTF-8 Bytes')
                vector=self.embedding(text,e['source_ref']['source_id'],deadline)
                if len(vector)!=3072:raise Unavailable('A3 unterstützt aktuell den gepinnten 3072-dimensionalen Text-Encoder')
                path=self.r.home/'data/blobs'/(uid('a2')+'.json');atomic_write(path,dumps({'embedding':vector}))
                reference=packet('PerceptPacket','A2_FROZEN_REFERENCE',e['event_id'],base,[e['source_ref']],source_ref=e['source_ref'],segments=[],modality='text',teacher_truth_authority=False,
                                 encoder_revision=manifest['encoder_revision'],feature_path=str(path.relative_to(self.r.home)),feature_sha256=file_hash(path),feature_dim=len(vector),stop_gradient=True)
                self.s.add_packet('PerceptPacket',reference);manifest['target_packet_ids'].append(reference['packet_id'])
                texts.append(text);targets.append(vector);groups.append(e['source_ref']['sha256']);lineage.extend([e['source_ref']['source_id'],row['source_id']])
                self.s.add_packet('LearningTrace',packet('LearningTrace','F6_LEARNING',e['event_id'],base,[e['source_ref']],path_id=component,activity=1.,eligibility=self.r.cfg['eligibility_decay'],authority='EXPLICIT_OBSERVATION_LEARN'))
            active=self.active(component);inp=folder/'input.json';atomic_write(inp,dumps({'config':self.training_config(component,uid_,manifest),'texts':texts,'teacher_embeddings':targets,'source_groups':groups,'active_checkpoint':str(active) if active else None}))
            self.r.needle.unload();env=os.environ.copy();env.update(PYTHONPATH=str(APP),OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1');last_check=time.monotonic()
            with (folder/'worker.log').open('wb') as log:
                self.proc=subprocess.Popen([sys.executable,'-m','v13.student_worker',str(inp),str(folder)],stdout=log,stderr=log,env=env)
                while self.proc.poll() is None:
                    check(self.r.cancel_event,deadline);self.r.cancel_event.wait(.1)
                    if time.monotonic()-last_check>3:
                        if not allows(self.r.guard.update(self.r.resources()),'shadow_learning'):raise Unavailable('A3 resources critical')
                        last_check=time.monotonic()
                if self.proc.returncode:raise RuntimeError('A3 worker failed: '+str(folder/'worker.log'))
            check(self.r.cancel_event,deadline);metrics=json.loads((folder/'metrics.json').read_text());dest=self.r.home/'checkpoints'/(component+'-'+uid_+'.npz');os.replace(folder/'candidate.npz',dest);h=file_hash(dest)
            manifest.update(source_ids=sorted(set(lineage)),metrics=metrics,commit_eligible=metrics['commit_eligible']);status='PENDING_APPROVAL' if metrics['commit_eligible'] else 'EVALUATED_FAIL'
            with self.s.tx() as c:c.execute('UPDATE updates SET status=?,path=?,hash=?,manifest=? WHERE id=?',(status,str(dest.relative_to(self.r.home)),h,dumps(manifest),uid_))
            self.s.add_packet('UpdateManifest',packet('UpdateManifest','F6_LEARNING','TRAIN',base,update_id=uid_,base_brain_generation_id=base,status=status,artifact_hash=h,metrics=metrics))
            self.s.add_packet('TrainRunnerProof',packet('TrainRunnerProof','F10_RUNTIME','TRAIN',base,trainable_parameter_count=metrics['trainable_parameter_count'],runner_revision='numpy-a3-text-v1',device=metrics['device'],checks=metrics))
            self.observe_finished(uid_)
            self.s.log('shadow_result',None,{'id':uid_,'component':component,'status':status,'metrics':metrics});return uid_+' '+status+'; eingefrorener A2-Encoder unverändert'
        except BaseException:
            kill_process(self.proc)
            with self.s.tx() as c:c.execute("UPDATE updates SET status='ABORTED',manifest=? WHERE id=?",(dumps(manifest),uid_))
            raise
        finally:self.proc=None;self.r.pool.unload();self.r.needle.unload();(folder/'input.json').unlink(missing_ok=True)
    def world_context_revision(self):
        return digest(dumps({'version':'digital-raw-state-action-v2-measured-support','models':{role:self.r.models.revision(role) for role in ('C2_CONTROL','C3_LANGUAGE','B1_DETAIL','B2_GIST')},
                             'config':{k:self.r.cfg[k] for k in ('threads','context_tokens','answer_tokens','temperature','history_turns')},'rule_version':self.s.generation()['rule_version']}))
    def world_predict(self,e,role,deadline=None):
        path=self.active('world_predictor')
        if path is None:return None
        entry=self.s.components()['world_predictor']
        if entry.get('context_revision')!=self.world_context_revision():raise Unavailable('World context changed; revalidate/rollback')
        text=self.s.read_source(e['source_ref'])
        if not 0<len(text.encode())<=4096:raise Unavailable('World state observation exceeds 4096 UTF-8 bytes')
        from .world_worker import predict
        vector=self.embedding(text,e['source_ref']['source_id'],min(deadline or float('inf'),time.monotonic()+self.r.cfg['control_seconds']))
        result=predict(vector,role,path)
        self.s.log('world_coverage',e['event_id'],result['coverage'])
        if not result['coverage']['in_support']:return None
        return result|{'generation':self.s.generation_id,'context_revision':entry['context_revision'],'artifact_sha256':entry['sha256']}
    def world_score(self,transition,prediction):
        entry=self.s.components().get('world_predictor');path=self.active('world_predictor')
        if not entry or prediction.get('generation')!=self.s.generation_id or prediction.get('artifact_sha256')!=entry['sha256']:raise Unavailable('World prediction generation/artifact changed')
        if transition['action_role']!=prediction['action_role']:raise ValueError('World forecast/observed role mismatch')
        ref=transition['outcome_source_ref'];text=self.s.read_source(ref)
        if not 0<len(text.encode())<=4096:raise Unavailable('World outcome observation exceeds 4096 UTF-8 bytes')
        from .world_worker import score
        return score(self.embedding(text,ref['source_id'],time.monotonic()+self.r.cfg['control_seconds']),prediction,path)
    def shadow_world(self):
        if self.r.cfg['learning_mode']=='RECORD_ONLY':raise ValueError('RECORD_ONLY: keine World-Optimizer-Schritte. :learning shadow')
        if self.r.guard.update(self.r.resources())!='NORMAL':raise Unavailable('World-Lernen wartet auf normale Ressourcen')
        import numpy
        unique={};component='world_predictor'
        rows=self.s.rows("SELECT f.*,e.packet FROM feedback f JOIN events e ON e.id=f.event_id JOIN sources s ON s.id=f.source_id WHERE f.kind='world' AND s.deleted=0 ORDER BY f.created DESC LIMIT 256")
        for row in rows:
            e=json.loads(row['packet']);action=self.s.one("SELECT * FROM actions WHERE event_id=? AND status='FINAL' AND outcome IS NOT NULL ORDER BY created DESC LIMIT 1",(e['event_id'],))
            if not action:continue
            role=json.loads(action['outcome']).get('role');unique.setdefault((e['source_ref']['sha256'],role),(row,e,action))
        data=[v for v in reversed(list(unique.values())) if v[0]['permission']=='learn'][-128:]
        if len({v[1]['source_ref']['sha256'] for v in data})<12:raise ValueError('Mindestens zwölf unterschiedliche Quellen mit realen :feedback world observe --learn Outcomes erforderlich')
        uid_=uid('upd');base=self.s.generation_id;folder=self.r.home/'shadow'/uid_;folder.mkdir();deadline=time.monotonic()+600;lineage=[]
        entry=self.s.components().get(component)
        if entry:
            row=self.s.one('SELECT manifest FROM updates WHERE id=?',(entry['update_id'],))
            if row:lineage.extend(json.loads(row['manifest']).get('source_ids',[]))
        manifest={'component':component,'commit_eligible':False,'encoder_revision':self.r.models.revision('C2_CONTROL'),'encoder_role':'C2_CONTROL',
                  'dependency_revisions':{role:self.r.models.revision(role) for role in ('C2_CONTROL','C3_LANGUAGE','B1_DETAIL','B2_GIST')},'base_generation':base,'source_ids':lineage,
                  'context_revision':self.world_context_revision(),'objective':'world-digital-action-latent-v1','body_learning':False,'semantic_truth_authority':False,'transition_packet_ids':[]}
        with self.s.tx() as c:c.execute('INSERT INTO updates VALUES (?,?,?,?,?,?,?)',(uid_,base,'SHADOW_TRAINING',None,None,dumps(manifest),now()))
        try:
            self.r.pool.unload();states=[];outcomes=[];roles=[];groups=[]
            for row,e,action in data:
                check(self.r.cancel_event,deadline);transition=self.r.world.transition(action['id']);ref=transition['outcome_source_ref'];text=self.s.read_source(e['source_ref']);future=self.s.read_source(ref)
                if max(len(text.encode()),len(future.encode()))>4096:raise ValueError('World observation source exceeds 4096 UTF-8 bytes')
                states.append(self.embedding(text,e['source_ref']['source_id'],deadline));outcomes.append(self.embedding(future,ref['source_id'],deadline));roles.append(transition['action_role']);groups.append(e['source_ref']['sha256'])
                manifest['transition_packet_ids'].append(transition['packet_id']);lineage.extend([e['source_ref']['source_id'],ref['source_id'],row['source_id']])
                self.s.add_packet('LearningTrace',packet('LearningTrace','F6_LEARNING',e['event_id'],base,[e['source_ref'],ref],path_id=component,activity=1.,eligibility=self.r.cfg['eligibility_decay'],authority='EXPLICIT_OBSERVATION_LEARN'))
            active=self.active(component);inp=folder/'input.json';atomic_write(inp,dumps({'config':self.training_config(component,uid_,manifest),'state_embeddings':states,'outcome_embeddings':outcomes,'action_roles':roles,'source_groups':groups,'active_checkpoint':str(active) if active else None}))
            self.r.needle.unload();env=os.environ.copy();env.update(PYTHONPATH=str(APP),OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1');last_check=time.monotonic()
            with (folder/'worker.log').open('wb') as log:
                self.proc=subprocess.Popen([sys.executable,'-m','v13.world_worker',str(inp),str(folder)],stdout=log,stderr=log,env=env)
                while self.proc.poll() is None:
                    check(self.r.cancel_event,deadline);self.r.cancel_event.wait(.1)
                    if time.monotonic()-last_check>3:
                        if not allows(self.r.guard.update(self.r.resources()),'shadow_learning'):raise Unavailable('World resources critical')
                        last_check=time.monotonic()
                if self.proc.returncode:raise RuntimeError('World worker failed: '+str(folder/'worker.log'))
            check(self.r.cancel_event,deadline);metrics=json.loads((folder/'metrics.json').read_text());dest=self.r.home/'checkpoints'/(component+'-'+uid_+'.npz');os.replace(folder/'candidate.npz',dest);h=file_hash(dest)
            manifest.update(source_ids=sorted(set(lineage)),metrics=metrics,commit_eligible=metrics['commit_eligible']);status='PENDING_APPROVAL' if metrics['commit_eligible'] else 'EVALUATED_FAIL'
            with self.s.tx() as c:c.execute('UPDATE updates SET status=?,path=?,hash=?,manifest=? WHERE id=?',(status,str(dest.relative_to(self.r.home)),h,dumps(manifest),uid_))
            self.s.add_packet('UpdateManifest',packet('UpdateManifest','F6_LEARNING','TRAIN',base,update_id=uid_,base_brain_generation_id=base,status=status,artifact_hash=h,metrics=metrics))
            self.s.add_packet('TrainRunnerProof',packet('TrainRunnerProof','F10_RUNTIME','TRAIN',base,trainable_parameter_count=metrics['trainable_parameter_count'],runner_revision='numpy-digital-world-v1',device=metrics['device'],checks=metrics))
            self.observe_finished(uid_)
            self.s.log('shadow_result',None,{'id':uid_,'component':component,'status':status,'metrics':metrics});return uid_+' '+status+'; eigener digitaler World-Predictor, keine semantische Faktenfreigabe'
        except BaseException:
            kill_process(self.proc)
            with self.s.tx() as c:c.execute("UPDATE updates SET status='ABORTED',manifest=? WHERE id=?",(dumps(manifest),uid_))
            raise
        finally:self.proc=None;self.r.pool.unload();self.r.needle.unload();(folder/'input.json').unlink(missing_ok=True)
    def shadow_predictor(self,role):
        """Explicitly authorized observations -> causal pairs -> small EMA objective."""
        if role not in {'B1_DETAIL','B2_GIST'}:raise ValueError('Body predictor role')
        if self.r.cfg['learning_mode']=='RECORD_ONLY':raise ValueError('RECORD_ONLY: keine Optimizer-Schritte. :learning shadow')
        if self.r.guard.update(self.r.resources())!='NORMAL':raise Unavailable('Predictor-Lernen wartet auf normale Ressourcen')
        import numpy
        component='b1_predictor' if role=='B1_DETAIL' else 'b2_predictor';unique={}
        rows=self.s.rows("SELECT f.*,e.packet FROM feedback f JOIN events e ON e.id=f.event_id JOIN sources s ON s.id=f.source_id WHERE f.kind='prediction' AND s.deleted=0 ORDER BY f.created DESC LIMIT 256")
        for row in rows:
            e=json.loads(row['packet']);text=self.s.read_source(e['source_ref']);unique.setdefault(text,(row,e))
        data=[(text,pair) for text,pair in reversed(list(unique.items())) if pair[0]['permission']=='learn'][-32:]
        if len(data)<12:raise ValueError('Mindestens 12 verschiedene kurze Quellen mit :feedback prediction observe --learn erforderlich')
        uid_=uid('upd');base=self.s.generation_id;folder=self.r.home/'shadow'/uid_;folder.mkdir();deadline=time.monotonic()+600;lineage=[]
        entry=self.s.components().get(component)
        if entry:
            row=self.s.one('SELECT manifest FROM updates WHERE id=?',(entry['update_id'],))
            if row:lineage.extend(json.loads(row['manifest']).get('source_ids',[]))
        manifest={'component':component,'commit_eligible':False,'encoder_role':role,'encoder_revision':self.r.models.revision(role),
                  'dependency_revisions':{role:self.r.models.revision(role)},'source_ids':lineage,'objective':'dense-body-future-state-predictor-v1',
                  'scope':'external_projector_predictor_only','body_learning':False,'base_generation':base,'context_revision':'lfm2.result_norm.final.v1:horizon2',
                  'receiver_authority':0,'tap_packet_ids':[]}
        with self.s.tx() as c:c.execute('INSERT INTO updates VALUES (?,?,?,?,?,?,?)',(uid_,base,'SHADOW_TRAINING',None,None,dumps(manifest),now()))
        try:
            self.r.needle.unload();runner=self.r.pool.get_tap(role)
            one=runner.tap('Projekt Kausal: Wert 120 Euro. Danach Farbe blau.',self.r.cancel_event,deadline)
            two=runner.tap('Projekt Kausal: Wert 120 Euro. Danach Farbe gruen.',self.r.cancel_event,deadline)
            shared=0
            for a,b in zip(one['token_ids'],two['token_ids']):
                if a!=b:break
                shared+=1
            error=max((abs(a-b) for va,vb in zip(one['vectors'][:shared],two['vectors'][:shared]) for a,b in zip(va,vb)),default=None)
            manifest['causal_prefix_proof']={'shared_native_tokens':shared,'future_tokens_differ':one['token_ids']!=two['token_ids'],'max_prefix_error':error,'pass':shared>=4 and error is not None and error<1e-4 and one['token_ids']!=two['token_ids']}
            if not manifest['causal_prefix_proof']['pass']:raise Unavailable('Native Tap causal-prefix proof failed; no temporal training')
            contexts=[];futures=[];groups=[]
            for text,(row,e) in data:
                check(self.r.cancel_event,deadline)
                p=self.r.cognition.tap(role,e,e['source_ref'],deadline);tap=self.r.cognition.read_tap(p);vectors=tap['vectors']
                if len(vectors)<12:raise ValueError('Vorhersagequelle hat weniger als 12 native Tokens: '+e['event_id'])
                for index in range(3,len(vectors)-2,3):contexts.append(vectors[index]);futures.append(vectors[index+2]);groups.append(e['source_ref']['sha256'])
                lineage.extend([e['source_ref']['source_id'],row['source_id']]);manifest['tap_packet_ids'].append(p['packet_id'])
                self.s.add_packet('LearningTrace',packet('LearningTrace','F6_LEARNING',e['event_id'],base,[e['source_ref']],path_id=component,activity=1.,eligibility=self.r.cfg['eligibility_decay'],authority='EXPLICIT_OBSERVATION_LEARN'))
                self.s.add_packet('ModulatorPacket',packet('ModulatorPacket','F6_LEARNING',e['event_id'],base,[e['source_ref']],epistemic_evidence=1.,human_correction=0.,task_success=0.,resource_cost=0.,safety_veto=False,values_status='measured native state target; no semantic truth label'))
            active=self.active(component);inp=folder/'input.json';atomic_write(inp,dumps({'config':self.training_config(component,uid_,manifest),'context_states':contexts,'future_states':futures,'source_groups':groups,'active_checkpoint':str(active) if active else None}))
            self.r.pool.unload();env=os.environ.copy();env.update(PYTHONPATH=str(APP),OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1');last_check=time.monotonic()
            with (folder/'worker.log').open('wb') as log:
                self.proc=subprocess.Popen([sys.executable,'-m','v13.predictor_worker',str(inp),str(folder)],stdout=log,stderr=log,env=env)
                while self.proc.poll() is None:
                    check(self.r.cancel_event,deadline);self.r.cancel_event.wait(.1)
                    if time.monotonic()-last_check>3:
                        if not allows(self.r.guard.update(self.r.resources()),'shadow_learning'):raise Unavailable('Predictor resources critical')
                        last_check=time.monotonic()
                if self.proc.returncode:raise RuntimeError('Predictor worker failed: '+str(folder/'worker.log'))
            check(self.r.cancel_event,deadline);metrics=json.loads((folder/'metrics.json').read_text());dest=self.r.home/'checkpoints'/(component+'-'+uid_+'.npz');os.replace(folder/'candidate.npz',dest);h=file_hash(dest)
            manifest.update(source_ids=sorted(set(lineage)),metrics=metrics,commit_eligible=metrics['commit_eligible']);status='PENDING_APPROVAL' if metrics['commit_eligible'] else 'EVALUATED_FAIL'
            with self.s.tx() as c:c.execute('UPDATE updates SET status=?,path=?,hash=?,manifest=? WHERE id=?',(status,str(dest.relative_to(self.r.home)),h,dumps(manifest),uid_))
            self.s.add_packet('UpdateManifest',packet('UpdateManifest','F6_LEARNING','TRAIN',base,update_id=uid_,base_brain_generation_id=base,status=status,artifact_hash=h,metrics=metrics))
            self.s.add_packet('TrainRunnerProof',packet('TrainRunnerProof','F10_RUNTIME','TRAIN',base,trainable_parameter_count=metrics['trainable_parameter_count'],runner_revision='numpy-dense-state-predictor-v1',device=metrics['device'],checks=metrics|{'causal_prefix':manifest['causal_prefix_proof']}))
            self.observe_finished(uid_)
            self.s.log('shadow_result',None,{'id':uid_,'component':component,'status':status,'metrics':metrics});return uid_+' '+status+'; native Body-Gewichte unverändert'
        except BaseException:
            kill_process(self.proc)
            with self.s.tx() as c:c.execute("UPDATE updates SET status='ABORTED',manifest=? WHERE id=?",(dumps(manifest),uid_))
            raise
        finally:self.proc=None;self.r.pool.unload();(folder/'input.json').unlink(missing_ok=True)
    def shadow(self):
        if self.r.cfg['learning_mode']=='RECORD_ONLY':raise ValueError('RECORD_ONLY: keine Optimizer-Schritte. :learning shadow')
        if self.r.guard.update(self.r.resources())!='NORMAL':raise Unavailable('Shadow-Lernen wartet auf normale RAM-/Temperaturwerte')
        try:import numpy
        except ImportError:raise Unavailable('NumPy fehlt: setup.sh erneut starten')
        rows=self.s.rows("SELECT f.*,e.packet,e.session_id FROM feedback f JOIN events e ON e.id=f.event_id JOIN sources s ON s.id=f.source_id WHERE f.kind='route' AND s.deleted=0 ORDER BY f.created DESC LIMIT 256")
        unique={}
        for row in rows:
            e=json.loads(row['packet']);text=self.s.read_source(e['source_ref']);unique.setdefault(text,(row,e))
        data=[(text,item) for text,item in reversed(list(unique.items())) if item[0]['permission']=='learn']
        from .route_supersede import apply as supersede
        data,superseded=supersede(self.s,data)  # WP-Z6c: human-scoped replacement of older contradicting labels
        from .route_supersede import taught
        rule_taught=[];seen={text for text,_ in data}
        for ev,route,rid in taught(self.s):  # WP-Z6i --lehre: questions a human rule routed, labelled with the rule's route
            row=self.s.one('SELECT e.packet,e.source_id,e.created FROM events e JOIN sources s ON s.id=e.source_id WHERE e.id=? AND s.deleted=0',(ev,))
            if not row:continue
            e=json.loads(row['packet']);text=self.s.read_source(e['source_ref'])
            if text in seen:continue  # a human correction on the same question wins
            seen.add(text);rule_taught.append((text,({'value':route,'source_id':row['source_id'],'created':row['created'],'permission':'learn','rule':rid},e)))
        data=(rule_taught+data)[-128:]
        if len(data)<4:raise ValueError('Mindestens 4 verschiedene :feedback route <Route> --learn nötig; Freigabe benötigt mindestens 12 und alle 4 Routen.')
        deadline=time.monotonic()+180;uid_=uid('upd');base=self.s.generation_id;folder=self.r.home/'shadow'/uid_;folder.mkdir()
        lineage=[]
        for ancestor in [entry['update_id'] for kind,entry in self.s.components().items() if kind=='route' and entry.get('update_id')]:
            u=self.s.one('SELECT manifest FROM updates WHERE id=?',(ancestor,))
            if u:lineage.extend(json.loads(u['manifest']).get('source_ids',[]))
        emb=[];labels=[];baselines=[];manifest={'commit_eligible':False,'component':'route','encoder_revision':self.r.models.revision('C2_CONTROL'),'source_ids':lineage,'objective':'explicit-human-route-cross-entropy-v1','scope':'external_route_head_only','body_learning':False,'base_generation':base}
        if superseded:manifest['superseded_labels']=superseded
        if rule_taught:manifest['rule_taught_labels']=[{'source_id':row['source_id'],'route':row['value'],'rule':row['rule']} for _,(row,_) in rule_taught]
        with self.s.tx() as c:c.execute('INSERT INTO updates VALUES (?,?,?,?,?,?,?)',(uid_,base,'SHADOW_TRAINING',None,None,dumps(manifest),now()))
        try:
            for text,(row,e) in data:
                check(self.r.cancel_event,deadline);ref=e['source_ref'];emb.append(self.embedding(text,ref['source_id'],deadline));labels.append(ROUTES.index(row['value']));baselines.append(ROUTES.index(scaffold_route(text)));lineage.extend([ref['source_id'],row['source_id']])
                self.s.add_packet('LearningTrace',packet('LearningTrace','F4_LEARNING',e['event_id'],base,[ref],path_id='C2_EXTERNAL_ROUTE_HEAD',activity=1.,eligibility=self.r.cfg['eligibility_decay'],authority='EXPLICIT_HUMAN_RULE' if isinstance(row,dict) else 'EXPLICIT_HUMAN_LEARN'))
                self.s.add_packet('ModulatorPacket',packet('ModulatorPacket','F4_LEARNING',e['event_id'],base,[ref],epistemic_evidence=1.,human_correction=1.,task_success=0.,resource_cost=0.,safety_veto=False,values_status='human label present; task success and cost not optimizer rewards'))
            active=self.active();request={'config':self.training_config('route',uid_,manifest),'embeddings':emb,'labels':labels,'scaffold_labels':baselines,'active_checkpoint':str(active) if active else None}
            if self.uses_route_words(active):  # WP-Z6i: fixed word channel, so the head can learn a boundary the embedding does not carry
                from .route_words import vector,REVISION
                request['words']=[vector(text) for text,_ in data];manifest['route_words']=REVISION
                request['gate']=self.r.cfg.get('route_head_gate','fixed75');manifest['route_head_gate']=request['gate']
                request['recency_half_life']=int(self.r.cfg.get('route_recency_half_life',0))  # WP-Z6i3: newer corrections count more
                if request['recency_half_life']:manifest['route_recency_half_life']=request['recency_half_life']
                anchors=self.rule_anchors({text for text,_ in data},deadline)
                if anchors:request['anchors']=anchors;manifest['rule_anchors']=len(anchors['embeddings'])
            inp=folder/'input.json';atomic_write(inp,dumps(request))
            env=os.environ.copy();env.update(PYTHONPATH=str(APP),OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1');self.r.pool.unload();self.r.needle.unload()
            last_resource_check=time.monotonic()
            with open(folder/'worker.log','wb') as log:
                self.proc=subprocess.Popen([sys.executable,'-m','v13.learning_worker',str(inp),str(folder)],stdout=log,stderr=log,env=env)
                while self.proc.poll() is None:
                    check(self.r.cancel_event,deadline);self.r.cancel_event.wait(.1)
                    if time.monotonic()-last_resource_check>3:
                        if not allows(self.r.guard.update(self.r.resources()),'shadow_learning'):raise Unavailable('Shadow-Training wegen Ressourcenlimit abgebrochen')
                        last_resource_check=time.monotonic()
                if self.proc.returncode:raise RuntimeError('Shadow worker fehlgeschlagen; '+str(folder/'worker.log'))
            metrics=json.loads((folder/'metrics.json').read_text());dest=self.r.home/'checkpoints'/('head-'+uid_+'.npz');os.replace(folder/'candidate.npz',dest);h=file_hash(dest)
            manifest.update(source_ids=sorted(set(lineage)),metrics=metrics,commit_eligible=metrics['commit_eligible']);status='PENDING_APPROVAL' if metrics['commit_eligible'] else 'EVALUATED_FAIL'
            with self.s.tx() as c:c.execute('UPDATE updates SET status=?,path=?,hash=?,manifest=? WHERE id=?',(status,str(dest.relative_to(self.r.home)),h,dumps(manifest),uid_))
            self.s.add_packet('UpdateManifest',packet('UpdateManifest','F4_LEARNING','TRAIN',base,update_id=uid_,base_brain_generation_id=base,status=status,artifact_hash=h,metrics=metrics))
            self.s.add_packet('TrainRunnerProof',packet('TrainRunnerProof','F7_RUNTIME','TRAIN',base,trainable_parameter_count=metrics['trainable_parameter_count'],runner_revision='numpy-route-head-v1',device=metrics['device'],checks=metrics))
            self.observe_finished(uid_)
            self.s.log('shadow_result',None,{'id':uid_,'status':status,'metrics':metrics});return uid_+' '+status+'; aktive Generation unverändert'
        except BaseException:
            kill_process(self.proc)
            with self.s.tx() as c:c.execute("UPDATE updates SET status='ABORTED',manifest=? WHERE id=?",(dumps(manifest),uid_))
            raise
        finally:
            self.proc=None;(folder/'input.json').unlink(missing_ok=True)
