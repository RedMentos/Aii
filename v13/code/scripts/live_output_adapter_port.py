"""Unintegrated C3 one-context pause/resume port; zero approval authority.

The caller supplies already measured exact template tokens and owns Runtime
residency/approval. No template server, additional prefill, or artifact activation
is performed here. The current worker decodes one first token and three unbiased
continuations; this is not yet the production streaming decoder.
"""
import json
import math
import os
from pathlib import Path
import secrets
import selectors
import signal
import subprocess
import time
import numpy as np
from v13.common import APP,atomic_write,digest,dumps,file_hash,Cancelled,Limits,Unavailable,safe_text
from v13.output_adapter_worker import features
from v13.resources import process_memory
from v13.runners import check

HEAD_FORMAT='c3-live-prefill-first-token-delta-v1'
ABI={'tap_id':'lfm2.result_norm.causal.last.v1','dimension':1024,'vocabulary':65536,
     'n_batch':128,'n_ubatch':128,'context_tokens':2048,'threads':2,'sequence_id':0,
     'embeddings':False,'pooling':'NONE','attention':'MODEL_DEFAULT_UNSPECIFIED',
     'feature_schema':'V13_PAUSED_CAUSAL_PREFILL_FEATURES_V1'}

def unique_json(raw):
    def pairs(rows):
        out={}
        for key,value in rows:
            if key in out:raise Unavailable('Duplicate protocol JSON key')
            out[key]=value
        return out
    def nonfinite(_):raise Unavailable('Nonfinite protocol JSON')
    return json.loads(raw,object_pairs_hook=pairs,parse_constant=nonfinite)

def read_json(path,limit=16*1024*1024):
    path=Path(path)
    if path.stat().st_size>limit:raise Unavailable('Session artifact size bound exceeded')
    return unique_json(path.read_bytes())

def feature_abi(binding):
    ident=binding['identity']
    return dict(ABI,model_sha256=ident['model_sha256'],runner_tag=binding['runner_tag'],
                worker_sha256=binding['binary_sha256'],worker_sources=binding['source_hashes'],
                library_sha256={Path(p).name:sha for p,sha in sorted(ident['libraries'].items())})

def bind_installed(home):
    """Bind a previously prepared pinned build; no download/build/native call."""
    from scripts.test_native_prefill_port import installed_identity
    from v13.models import ModelManager,catalog
    home=Path(home).resolve();spec=catalog();models=ModelManager(home)
    identity=installed_identity(home,models.path_for('C3_LANGUAGE'),spec['runner'])
    if identity['model_sha256']!=spec['models']['language']['files'][0]['sha256'] or models.revision('C3_LANGUAGE')!=spec['models']['language']['revision']:raise Unavailable('Exact pinned C3 model/revision required')
    marker=read_json(home/'config/native-prefill-session.json');key=marker['identity_key'];base=key['base_build_identity'];binary=home/'bin/native-prefill-session'
    if marker['schema']!='V13_PREFILL_SESSION_BUILD_V1' or marker['binary_sha256']!=file_hash(binary) or base['installed']!=identity:raise Unavailable('Prepared binary/installation changed')
    source={'scripts/native_prefill_session.cpp':key['source_sha256'],'scripts/test_native_prefill_session.py':key['helper_sha256'],
            'scripts/native_prefill_worker.cpp':base['worker_source_sha256'],'scripts/test_native_prefill_port.py':base['collector_source_sha256']}
    binding={'binary':str(binary),'binary_sha256':marker['binary_sha256'],'identity':identity,'source_hashes':source,'runner_tag':spec['runner']['tag']}
    binding['feature_abi']=feature_abi(binding);verify_binding(binding);return binding

def verify_binding(binding):
    ident=binding['identity'];files={binding['binary']:binding['binary_sha256'],ident['model_path']:ident['model_sha256'],ident['server_path']:ident['server_sha256'],**ident['libraries']}
    if any(file_hash(p)!=sha for p,sha in files.items()) or any(file_hash(APP/p)!=sha for p,sha in binding['source_hashes'].items()):raise Unavailable('Prepared native binary/model/library/source bytes changed')
    if binding['feature_abi']!=feature_abi(binding):raise Unavailable('Prepared causal feature ABI changed')

def bias_rows(rows):
    if not isinstance(rows,list) or len(rows)>16:raise Unavailable('At most16 first-token rows required')
    seen=set();out=[]
    for row in rows:
        if not isinstance(row,list) or len(row)!=2:raise Unavailable('Malformed first-token bias row')
        token,value=row
        if type(token) is not int or not 0<=token<65536 or token in seen or isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or abs(value)>12:raise Unavailable('Duplicate/nonfinite/out-of-range first-token bias')
        seen.add(token);out.append([token,float(value)])
    return out

def loaded_library_pins_match(loaded,pins):
    """Match dladdr aliases exactly as the native worker does: realpath + SHA."""
    try:
        canonical=[str(Path(row['path']).resolve(strict=True)) for row in loaded]
        return len(loaded)>=4 and len(set(canonical))==len(loaded) and all(
            pins.get(path)==row['sha256'] and file_hash(path)==row['sha256']
            for path,row in zip(canonical,loaded))
    except (OSError,KeyError,TypeError):return False

def infer_live_head(observed,checkpoint,expected_sha256,expected_abi):
    """Existing pure delta math, gated on a new explicit causal feature ABI.

Hash/ABI are supplied by the existing artifact owner. Matching does not grant
human approval. Legacy separate-prefill v2 heads are rejected, never converted.
"""
    if observed['feature_abi']!=expected_abi or file_hash(checkpoint)!=expected_sha256:raise Unavailable('Live output artifact/feature ABI mismatch')
    x=features([observed['feature']])
    with np.load(checkpoint,allow_pickle=False) as a:
        if str(a['format'])!=HEAD_FORMAT:raise Unavailable('Old separate-prefill output head is incompatible')
        if unique_json(str(a['feature_abi']))!=expected_abi:raise Unavailable('Live head trained on different causal feature ABI')
        ids=a['token_ids'];w=a['weights'];anchors=a['anchors'];offset=a['feature_offset'];scale=a['feature_scale'];t=float(a['temperature']);cap=float(a['max_bias']);threshold=float(a['support_cosine'])
        if ids.ndim!=1 or ids.dtype.kind not in 'iu' or not 1<=len(ids)<=16 or len(set(ids.tolist()))!=len(ids) or np.any(ids<0) or np.any(ids>=65536):raise Unavailable('Malformed live vocabulary rows')
        if w.shape!=(1025,len(ids)) or not np.isfinite(w).all() or anchors.ndim!=2 or anchors.shape[1]!=1024 or not 1<=len(anchors)<=512 or not np.isfinite(anchors).all():raise Unavailable('Malformed live output weights/support')
        if not np.allclose(np.linalg.norm(anchors,axis=1),1.,atol=1e-6) or not .5<=t<=2. or not 0<cap<=12. or not 0<=threshold<=1.:raise Unavailable('Malformed live output scalar/support policy')
        if offset.shape!=(1024,) or scale.shape!=(1024,) or not np.isfinite(offset).all() or not np.isfinite(scale).all() or np.any(scale<.001):raise Unavailable('Malformed live train-only normalizer')
        cosine=float((x[:,1:]@anchors.T).max());supported=cosine>=threshold;x[:,1:]=np.clip((x[:,1:]-offset)/scale,-8.,8.);delta=np.clip(x@w/t,-cap,cap)[0]
        rows=bias_rows([[int(i),float(v)] for i,v in zip(ids,delta)]) if supported else []
    if file_hash(checkpoint)!=expected_sha256:raise Unavailable('Live output head changed during inference')
    return {'in_support':supported,'nearest_native_cosine':cosine,'first_token_bias':rows,'scope':'EXTERNAL_FIRST_NATIVE_TOKEN_VOCABULARY_ROW_DELTA',
            'semantic_truth_authority':False,'native_body_parameters_modified':0,'approval_authority':0,'feature_abi':expected_abi}

class PausedOutputSession:
    """One context/one consume. Context-manager cleanup always reaps its child."""
    def __init__(self,binding,context,out,cancel,deadline,*,rss_limit_bytes=768*1024*1024):
        if isinstance(deadline,bool) or not isinstance(deadline,(int,float)) or not math.isfinite(deadline):raise ValueError('Finite absolute deadline required')
        check(cancel,deadline)
        if type(rss_limit_bytes) is not int or rss_limit_bytes<=0:raise ValueError('Positive resource bound required')
        if set(context)!={'messages','prompt','token_ids','history_trimmed'} or context['history_trimmed'] is not False or not isinstance(context['prompt'],str) or not isinstance(context['messages'],list):raise Unavailable('Exact untrimmed measured template context required')
        if not isinstance(context['token_ids'],list) or not 1<=len(context['token_ids'])<=512 or any(type(i) is not int or not 0<=i<65536 for i in context['token_ids']):raise Unavailable('Exact bounded native token IDs required')
        self.binding=unique_json(dumps(binding));self.context=unique_json(dumps(context));self.out=Path(out);self.cancel=cancel;self.deadline=deadline;self.rss_limit_bytes=rss_limit_bytes
        self.context_sha=digest(dumps(self.context));self.nonce=secrets.token_hex(16);self.proc=None;self.selector=None;self.stderr=None;self.pending=b'';self.claimed=False;self.ready=None;self.finished=False
        self.metrics={'status':'NOT_STARTED','resume_commands_sent':0,'resource_samples':[],'resource_sample_count':0,'sampled_peak_rss_bytes':None,'sampled_peak_pss_bytes':None,'process_reaped':False,'production_integration':False,'approval_authority':0}
    def __enter__(self):
        try:self.start();return self
        except BaseException as exc:self._failed(exc);raise
    def __exit__(self,kind,exc,traceback):
        if exc is not None:self._failed(exc)
        else:self.close()
    def _failed(self,exc):
        self.metrics.setdefault('error_type',type(exc).__name__)
        self.metrics.setdefault('error',str(exc)[:500])
        reason='CANCELLED' if isinstance(exc,Cancelled) else ('RSS_LIMIT' if isinstance(exc,Limits) and 'RSS' in str(exc) else ('DEADLINE' if isinstance(exc,Limits) else 'PROTOCOL_OR_CONTEXT_REJECTED'))
        self.metrics.setdefault('stop_reason',reason);self.close()
    def _guard(self):
        check(self.cancel,self.deadline)
        if self.proc is not None:
            m=process_memory(self.proc.pid);self.metrics['resource_sample_count']+=1
            for field in ('rss_bytes','pss_bytes'):
                if m.get(field) is not None:
                    key='sampled_peak_'+field;self.metrics[key]=max(self.metrics[key] or 0,m[field])
            self.metrics['resource_samples'].append(m)
            if len(self.metrics['resource_samples'])>64:del self.metrics['resource_samples'][1]
            if (m.get('rss_bytes') or 0)>self.rss_limit_bytes:raise Limits('Paused-context RSS bound exceeded')
    def _save(self):
        if self.out.exists():atomic_write(self.out/'controller.json',dumps(self.metrics))
    def start(self):
        if self.proc is not None or self.finished:raise Unavailable('Session already started/closed')
        self._guard();verify_binding(self.binding);self.out.mkdir(parents=True,exist_ok=False)
        self.token_path=self.out/'tokens.json';self.features_path=self.out/'features.json';self.result_path=self.out/'result.json';self.pins_path=self.out/'pins.json'
        atomic_write(self.token_path,dumps({'token_ids':self.context['token_ids'],'context_source_sha256':self.context_sha}));atomic_write(self.pins_path,dumps({'libraries':self.binding['identity']['libraries']}));atomic_write(self.out/'context.json',dumps(self.context))
        remaining=self.deadline-time.monotonic()
        if remaining<1:raise Limits('Session needs at least one remaining second')
        ident=self.binding['identity'];cmd=[self.binding['binary'],'--model',ident['model_path'],'--tokens',str(self.token_path),'--output',str(self.result_path),'--features',str(self.features_path),'--model-sha256',ident['model_sha256'],'--lib-sha256',ident['libraries'][ident['llama_library']],'--backend-pins',str(self.pins_path),'--context-source-sha256',self.context_sha,'--nonce',self.nonce,'--wait-seconds','15','--seconds',str(min(120,math.ceil(remaining)))]
        self.stderr=(self.out/'native.log').open('wb');self.proc=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=self.stderr,start_new_session=True)
        self.metrics.update(status='WAITING_READY',pid=self.proc.pid,command=cmd);self.selector=selectors.DefaultSelector();self.selector.register(self.proc.stdout,selectors.EVENT_READ);self._save()
    def _message(self):
        while True:
            self._guard()
            if b'\n' in self.pending:
                line,self.pending=self.pending.split(b'\n',1);return unique_json(line)
            for key,_ in self.selector.select(min(.05,max(0,self.deadline-time.monotonic()))):
                data=os.read(key.fileobj.fileno(),8192)
                if not data:raise Unavailable('Session protocol closed before completion')
                self.pending+=data
                if len(self.pending)>65536:raise Unavailable('Session protocol exceeds64KiB')
            if self.proc.poll() is not None and b'\n' not in self.pending:raise Unavailable('Session exited before expected message')
    def pause(self,token_ids=None):
        try:
            if self.ready is not None or self.claimed or self.finished:raise Unavailable('Prefill observation may be claimed only once')
            msg=self._message()
            if msg.get('status')!='PREFILLED_READY':raise Unavailable('Unexpected native ready status')
            h=msg['handle'];bare=dict(h);bare.pop('handle_id',None);ident=self.binding['identity']
            required={'schema':'V13_CAUSAL_PREFILL_HANDLE_V1','nonce':self.nonce,'pid':self.proc.pid,'model_sha256':ident['model_sha256'],'lib_sha256':ident['libraries'][ident['llama_library']],'backend_pins_sha256':file_hash(self.pins_path),'token_file_sha256':file_hash(self.token_path),'context_source_sha256':self.context_sha,'features_sha256':file_hash(self.features_path),'sequence_id':0,'next_position':len(self.context['token_ids']),'context_tokens':2048,'prefill_generation':1,'wait_ttl_seconds':15}
            if set(h)!=set(required)|{'handle_id'} or any(type(h[k]) is not type(v) or h[k]!=v for k,v in required.items()) or digest(dumps(bare))!=h['handle_id'] or msg.get('features_path')!=str(self.features_path):raise Unavailable('Paused handle/token/model/library binding mismatch')
            f=read_json(self.features_path)
            if f.get('schema')!=ABI['feature_schema'] or type(f.get('pid')) is not int or f.get('pid')!=self.proc.pid or f.get('token_ids')!=self.context['token_ids'] or any(type(i) is not int for i in f.get('token_ids',[])) or f.get('context_source_sha256')!=self.context_sha or f.get('model_sha256')!=ident['model_sha256'] or f.get('lib_sha256')!=required['lib_sha256']:raise Unavailable('Paused feature/process/context binding mismatch')
            hidden=np.asarray(f['live_last_state'],dtype=float);features([hidden]);logits=np.asarray(f['first_position']['logits'],dtype=float);probs=np.asarray(f['first_position']['probabilities'],dtype=float)
            if logits.shape!=(65536,) or probs.shape!=(65536,) or not np.isfinite(logits).all() or not np.isfinite(probs).all() or np.any(probs<0) or abs(float(probs.sum())-1)>1e-9:raise Unavailable('Complete finite native65536 distribution required')
            expected=np.exp(logits-logits.max());expected/=expected.sum()
            if not np.allclose(probs,expected,rtol=1e-8,atol=1e-12) or type(f['first_position']['greedy_token_id']) is not int or f['first_position']['greedy_token_id']!=int(logits.argmax()):raise Unavailable('Native logits/probabilities/greedy binding mismatch')
            baseline=None
            if token_ids is not None:
                bias_rows([[i,0.] for i in token_ids]);values=[float(probs[i]) for i in token_ids];other=1.-sum(values)
                if not values or min(values)<=0 or other<=0:raise Unavailable('Selected/unchanged probability mass empty')
                baseline=[math.log(v) for v in values]+[math.log(other)]
            self._guard();self.ready=h;self.logits=logits;self.features_sha=h['features_sha256'];self.ready_deadline=min(self.deadline,time.monotonic()+15)
            observed={'feature':hidden.tolist(),'native_prompt_token_ids':self.context['token_ids'],'prompt_sha256':digest(self.context['prompt']),'base_log_probabilities':baseline,'feature_abi':self.binding['feature_abi'],'native_context_binding':{'scope':'EXACT_SAME_CAUSAL_PREFILL','live_generation_kv_tap':True,'handle_id':h['handle_id'],'context_source_sha256':self.context_sha,'features_sha256':self.features_sha,'pid':self.proc.pid},'native_metrics':dict(self.metrics)}
            self.metrics['status']='PAUSED_READY';self._save();return unique_json(dumps(observed))
        except BaseException as exc:self._failed(exc);raise
    def resume(self,rows):
        try:
            self._guard()
            if self.ready is None or self.claimed or self.finished:raise Unavailable('Only one paused handle may resume')
            check(self.cancel,self.ready_deadline);rows=bias_rows(rows)
            if file_hash(self.features_path)!=self.features_sha or file_hash(self.token_path)!=self.ready['token_file_sha256']:raise Unavailable('Paused token/features changed before resume')
            command={'command':'resume','handle_id':self.ready['handle_id'],'nonce':self.nonce,'context_source_sha256':self.context_sha,'bias':rows};self.claimed=True
            self.proc.stdin.write((dumps(command)+'\n').encode());self.proc.stdin.flush();self.proc.stdin.close();self.metrics['resume_commands_sent']=1;atomic_write(self.out/'resume.json',dumps(command))
            if self._message()!={'status':'PAUSE_RESUME_DIAGNOSTIC_COMPLETE','handle_consumed':True}:raise Unavailable('Unexpected native resume completion')
            while self.proc.poll() is None:self._guard();time.sleep(min(.01,max(0,self.deadline-time.monotonic())))
            self.metrics['exit_code']=self.proc.wait();self.metrics['process_reaped']=True;raw=read_json(self.result_path);ident=self.binding['identity']
            checks={'status':raw.get('status')=='PAUSE_RESUME_DIAGNOSTIC_COMPLETE' and self.metrics['exit_code']==0,'pid':raw.get('pid')==self.proc.pid,'handle':raw.get('handle')==self.ready,'command':raw.get('accepted_command')==command and raw.get('handle_consumed') is True,'same_context':raw.get('same_context_lifetime') is True and raw.get('resume_prefill_calls')==0,'single_resume':raw.get('additional_commands_accepted')==0,'tokens':raw.get('token_ids')==self.context['token_ids'] and raw.get('token_file_sha256')==file_hash(self.token_path),'source':raw.get('context_source_sha256')==self.context_sha,'libraries':raw.get('all_loaded_libraries_verified') is True and raw.get('backend_pins_sha256')==file_hash(self.pins_path),'continuation':raw.get('resume_decode_calls')==raw.get('unbiased_continuation_steps')==3 and len(raw.get('continuation',[]))==3 and all(x.get('bias_applied') is False for x in raw.get('continuation',[])),'bias_position':raw.get('bias_applied_positions')==(1 if rows else 0),'model':raw.get('model',{}).get('sha256')==ident['model_sha256']}
            loaded=[raw.get(k,{}) for k in ('loaded_llama_library','loaded_ggml_library','loaded_ggml_base_library')]+raw.get('loaded_cpu_backend_libraries',[])
            checks['actual_loaded_library_pins']=loaded_library_pins_match(loaded,ident['libraries'])
            biased=self.logits.astype(np.float32).copy()
            for token,value in rows:biased[token]+=np.float32(value)
            predicted_first=int(biased.argmax());decoded=raw.get('decoded_native_token_ids',[]);continuation=raw.get('continuation',[])
            checks['exact_first_position_delta']=raw.get('first_native_greedy_token_id')==int(self.logits.argmax()) and raw.get('first_biased_token_id')==predicted_first
            checks['decoded_sequence_binding']=isinstance(decoded,list) and len(decoded)==4 and all(type(i) is int and 0<=i<65536 for i in decoded) and decoded[0]==predicted_first and len(continuation)==3 and all(step.get('input_token_id')==decoded[i] and step.get('greedy_next_token_id')==decoded[i+1] and step.get('position')==len(self.context['token_ids'])+i for i,step in enumerate(continuation));self.metrics['checks']=checks
            if not all(checks.values()):raise Unavailable('Native same-context completion binding failed')
            verify_binding(self.binding);check(self.cancel,self.deadline);self.metrics['status']='SAME_CONTEXT_PORT_COMPLETE';self.finished=True;self._save()
            return {'text':safe_text(raw['decoded_native_preview']),'native_token_ids':raw['decoded_native_token_ids'],'raw_result':raw,'metrics':dict(self.metrics),'feature_abi':self.binding['feature_abi'],'production_integration':False,'approval_authority':0}
        except BaseException as exc:self._failed(exc);raise
    def close(self):
        if self.selector is not None:self.selector.close();self.selector=None
        if self.proc is not None:
            if self.proc.poll() is None:
                try:os.killpg(self.proc.pid,signal.SIGTERM)
                except ProcessLookupError:pass
                try:self.proc.wait(timeout=1.5)
                except subprocess.TimeoutExpired:
                    try:os.killpg(self.proc.pid,signal.SIGKILL)
                    except ProcessLookupError:pass
                    self.proc.wait(timeout=2)
            self.metrics['exit_code']=self.proc.wait();self.metrics['process_reaped']=True
            for stream in (self.proc.stdin,self.proc.stdout):
                if stream is not None and not stream.closed:stream.close()
        if self.stderr is not None:self.stderr.close();self.stderr=None
        if self.metrics['status']!='SAME_CONTEXT_PORT_COMPLETE':self.metrics['status']='CLOSED_WITHOUT_COMPLETE_RESULT'
        self.finished=True;self._save()
