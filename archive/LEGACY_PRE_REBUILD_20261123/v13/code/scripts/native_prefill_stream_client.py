"""Adjacent streaming C3 BodyPort client; old four-token client stays unchanged.
Exact measured template context in, actual native token events out. One prefill,
one bounded first-position numeric command, unbiased same-context continuation.
No trained-head loading, production activation, approval or receiver authority.
"""
import codecs
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
from v13.resources import process_memory
from v13.runners import check

STREAM_ABI='V13_C3_CAUSAL_STREAM_STATE_LOGITS_1024_65536_V2'
ABI={'tap_id':'lfm2.result_norm.causal.last.v1','dimension':1024,'vocabulary':65536,
     'n_batch':128,'n_ubatch':128,'context_tokens':2048,'threads':2,'sequence_id':0,
     'embeddings':False,'pooling':'NONE','attention':'MODEL_DEFAULT_UNSPECIFIED',
     'feature_schema':'V13_PAUSED_CAUSAL_STREAM_FEATURES_V2','stream_abi':STREAM_ABI,'first_bias_position_limit':1,'max_output_tokens':[64,128]}

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
    marker=read_json(home/'config/native-prefill-stream.json');key=marker['identity_key'];base=key['base_build_identity'];binary=home/'bin/native-prefill-stream'
    if marker['schema']!='V13_PREFILL_STREAM_BUILD_V2' or marker['binary_sha256']!=file_hash(binary) or base['installed']!=identity:raise Unavailable('Prepared binary/installation changed')
    source={'scripts/native_prefill_stream.cpp':key['source_sha256'],'scripts/test_native_prefill_stream.py':key['helper_sha256'],
            'scripts/native_prefill_worker.cpp':base['worker_source_sha256'],'scripts/test_native_prefill_port.py':base['collector_source_sha256'],
            'scripts/native_prefill_stream_client.py':key['client_sha256']}
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

def validate_token_event(event, handle, position, max_tokens, has_bias, after_eos=False):
    keys={'event','sequence','token_id','piece_hex','text','text_encoding','is_eog',
          'first_position_bias','handle_id','feature_abi'}
    if not isinstance(event,dict) or set(event)!=keys or after_eos or not 0<=position<max_tokens:
        raise Unavailable('Unexpected/extra/late native token event')
    if event['event']!='TOKEN' or type(event['sequence']) is not int or event['sequence']!=position or type(event['token_id']) is not int or not 0<=event['token_id']<65536:
        raise Unavailable('Actual bounded sequential native token ID required')
    if event['handle_id']!=handle['handle_id'] or event['feature_abi']!=STREAM_ABI:
        raise Unavailable('Stale token stream handle/ABI')
    if type(event['is_eog']) is not bool or type(event['first_position_bias']) is not bool or event['first_position_bias']!=(position==0 and has_bias):
        raise Unavailable('Only first-position bias and exact EOG flag permitted')
    encoded=event['piece_hex']
    if not isinstance(encoded,str) or len(encoded)>32768 or len(encoded)%2 or any(c not in '0123456789abcdef' for c in encoded):
        raise Unavailable('Bounded exact token-piece hexadecimal bytes required')
    if not isinstance(event['text'],str) or len(event['text'])>32768 or event['text_encoding']!='UTF8_WITH_REPLACEMENT_IF_PARTIAL; piece_hex_is_exact':
        raise Unavailable('Native token text encoding required')
    piece=bytes.fromhex(encoded)
    if event['is_eog'] and piece:raise Unavailable('EOG must carry no rendered text bytes')
    return piece


def completion_checks(raw,events,prompt_ids,stream_bytes,max_tokens,predicted_first):
    decoded=raw.get('decoded_native_token_ids',[])
    continuation=raw.get('continuation',[])
    count=len(events)
    return {
        'bounded_actual_output_count': 1<=count<=max_tokens and raw.get('max_tokens')==max_tokens and type(raw.get('generated_token_count')) is int and raw['generated_token_count']==count,
        'actual_event_token_sequence': isinstance(decoded,list) and all(type(i) is int and 0<=i<65536 for i in decoded) and decoded==[e['token_id'] for e in events] and bool(decoded) and decoded[0]==predicted_first,
        'actual_output_byte_binding': raw.get('decoded_native_preview_hex')==stream_bytes.hex() and raw.get('decoded_native_preview_sha256')==digest(stream_bytes),
        'unbiased_same_context_continuation': type(raw.get('resume_decode_calls')) is int and raw['resume_decode_calls']==count-1 and raw.get('unbiased_continuation_steps')==count-1 and len(continuation)==count-1 and len(decoded)==count and all(step.get('input_token_id')==decoded[i] and step.get('greedy_next_token_id')==decoded[i+1] and step.get('position')==len(prompt_ids)+i and step.get('bias_applied') is False for i,step in enumerate(continuation)),
        'real_eos_or_token_limit': bool(events) and not any(e['is_eog'] for e in events[:-1]) and ((raw.get('stop_reason')=='EOS' and events[-1]['is_eog']) or (raw.get('stop_reason')=='TOKEN_LIMIT' and count==max_tokens and not events[-1]['is_eog'])),
    }


class StreamingOutputSession:
    """One context/one consume. Context-manager cleanup always reaps its child."""
    def __init__(self,binding,context,out,cancel,deadline,*,rss_limit_bytes=768*1024*1024,max_tokens=64,learned_head=None):
        if learned_head is not None:raise Unavailable('Streaming V2 ABI refuses old approved heads; no learned-head loading implemented')
        if type(max_tokens) is not int or max_tokens not in (64,128):raise ValueError('Output limit64 or128 required')
        self.max_tokens=max_tokens
        if isinstance(deadline,bool) or not isinstance(deadline,(int,float)) or not math.isfinite(deadline):raise ValueError('Finite absolute deadline required')
        check(cancel,deadline)
        if type(rss_limit_bytes) is not int or rss_limit_bytes<=0:raise ValueError('Positive resource bound required')
        if set(context)!={'messages','prompt','token_ids','history_trimmed'} or context['history_trimmed'] is not False or not isinstance(context['prompt'],str) or not isinstance(context['messages'],list):raise Unavailable('Exact untrimmed measured template context required')
        if not isinstance(context['token_ids'],list) or not 1<=len(context['token_ids'])<=512 or any(type(i) is not int or not 0<=i<65536 for i in context['token_ids']):raise Unavailable('Exact bounded native token IDs required')
        self.binding=unique_json(dumps(binding));self.context=unique_json(dumps(context));self.out=Path(out);self.cancel=cancel;self.deadline=deadline;self.rss_limit_bytes=rss_limit_bytes
        self.context_sha=digest(dumps(self.context));self.nonce=secrets.token_hex(16);self.proc=None;self.selector=None;self.stderr=None;self.pending=b'';self.claimed=False;self.ready=None;self.finished=False;self.token_events=[];self.stream_bytes=bytearray();self.decoder=codecs.getincrementaldecoder('utf-8')('replace')
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
        self.deadline=min(self.deadline,time.monotonic()+90)
        if remaining<5:raise Limits('Session needs at least five remaining seconds')
        ident=self.binding['identity'];cmd=[self.binding['binary'],'--model',ident['model_path'],'--tokens',str(self.token_path),'--output',str(self.result_path),'--features',str(self.features_path),'--model-sha256',ident['model_sha256'],'--lib-sha256',ident['libraries'][ident['llama_library']],'--backend-pins',str(self.pins_path),'--context-source-sha256',self.context_sha,'--nonce',self.nonce,'--wait-seconds','15','--seconds',str(min(90,math.ceil(remaining))),'--max-tokens',str(self.max_tokens),'--worker-source-sha256',self.binding['source_hashes']['scripts/native_prefill_stream.cpp']]
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
            # Drain stdout until actual pipe EOF; an exited worker can still
            # have a complete token event buffered beyond the first read.
    def pause(self,token_ids=None):
        try:
            if self.ready is not None or self.claimed or self.finished:raise Unavailable('Prefill observation may be claimed only once')
            msg=self._message()
            if msg.get('status')!='PREFILLED_READY':raise Unavailable('Unexpected native ready status')
            h=msg['handle'];bare=dict(h);bare.pop('handle_id',None);ident=self.binding['identity']
            required={'schema':'V13_CAUSAL_STREAM_HANDLE_V2','feature_abi':STREAM_ABI,'worker_source_sha256':self.binding['source_hashes']['scripts/native_prefill_stream.cpp'],'executable_sha256':self.binding['binary_sha256'],'max_tokens':self.max_tokens,'nonce':self.nonce,'pid':self.proc.pid,'model_sha256':ident['model_sha256'],'lib_sha256':ident['libraries'][ident['llama_library']],'backend_pins_sha256':file_hash(self.pins_path),'token_file_sha256':file_hash(self.token_path),'context_source_sha256':self.context_sha,'features_sha256':file_hash(self.features_path),'sequence_id':0,'next_position':len(self.context['token_ids']),'context_tokens':2048,'prefill_generation':1,'wait_ttl_seconds':15}
            if set(h)!=set(required)|{'handle_id'} or any(type(h[k]) is not type(v) or h[k]!=v for k,v in required.items()) or digest(dumps(bare))!=h['handle_id'] or msg.get('features_path')!=str(self.features_path):raise Unavailable('Paused handle/token/model/library binding mismatch')
            f=read_json(self.features_path)
            if f.get('schema')!=ABI['feature_schema'] or type(f.get('pid')) is not int or f.get('pid')!=self.proc.pid or f.get('token_ids')!=self.context['token_ids'] or any(type(i) is not int for i in f.get('token_ids',[])) or f.get('context_source_sha256')!=self.context_sha or f.get('model_sha256')!=ident['model_sha256'] or f.get('lib_sha256')!=required['lib_sha256']:raise Unavailable('Paused feature/process/context binding mismatch')
            hidden=np.asarray(f['live_last_state'],dtype=float)
            if hidden.shape!=(1024,) or not np.isfinite(hidden).all() or float(np.dot(hidden,hidden))<=1e-20:raise Unavailable('Actual finite nonzero1024 hidden state required')
            if f.get('feature_abi')!=STREAM_ABI or f.get('worker_source_sha256')!=required['worker_source_sha256']:raise Unavailable('New streaming causal feature ABI required; old heads refused')
            logits=np.asarray(f['first_position']['logits'],dtype=float);probs=np.asarray(f['first_position']['probabilities'],dtype=float)
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
        """Yield checked actual token events, then one COMPLETE result event."""
        try:
            self._guard()
            if self.ready is None or self.claimed or self.finished:raise Unavailable('Only one paused streaming handle may resume')
            check(self.cancel,self.ready_deadline);rows=bias_rows(rows)
            if file_hash(self.features_path)!=self.features_sha or file_hash(self.token_path)!=self.ready['token_file_sha256']:raise Unavailable('Paused token/features changed before resume')
            command={'command':'resume','handle_id':self.ready['handle_id'],'nonce':self.nonce,'context_source_sha256':self.context_sha,'feature_abi':STREAM_ABI,'worker_source_sha256':self.binding['source_hashes']['scripts/native_prefill_stream.cpp'],'bias':rows};self.claimed=True
            self.proc.stdin.write((dumps(command)+'\n').encode());self.proc.stdin.flush();self.proc.stdin.close();self.metrics['resume_commands_sent']=1;atomic_write(self.out/'resume.json',dumps(command))
            while True:
                message=self._message()
                if message.get('event')=='TOKEN':
                    piece=validate_token_event(message,self.ready,len(self.token_events),self.max_tokens,bool(rows),bool(self.token_events and self.token_events[-1]['is_eog']))
                    self.token_events.append(message);self.stream_bytes.extend(piece)
                    text=self.decoder.decode(piece,final=message['is_eog'] or len(self.token_events)==self.max_tokens)
                    atomic_write(self.out/'events.json',dumps(self.token_events))
                    yield dict(message,text=text,text_encoding='INCREMENTAL_UTF8_FROM_EXACT_PIECE_HEX')
                    continue
                if message!={'status':'CAUSAL_STREAM_DIAGNOSTIC_COMPLETE','handle_consumed':True}:raise Unavailable('Unexpected native streaming completion')
                break
            while self.proc.poll() is None:self._guard();time.sleep(min(.01,max(0,self.deadline-time.monotonic())))
            self.metrics['exit_code']=self.proc.wait();self.metrics['process_reaped']=True;raw=read_json(self.result_path);ident=self.binding['identity']
            checks={'status':raw.get('status')=='CAUSAL_STREAM_DIAGNOSTIC_COMPLETE' and self.metrics['exit_code']==0,'pid':raw.get('pid')==self.proc.pid,'handle':raw.get('handle')==self.ready,'command':raw.get('accepted_command')==command and raw.get('handle_consumed') is True,'same_context':raw.get('same_context_lifetime') is True and raw.get('resume_prefill_calls')==0,'single_resume':raw.get('additional_commands_accepted')==0,'tokens':raw.get('token_ids')==self.context['token_ids'] and raw.get('token_file_sha256')==file_hash(self.token_path),'source':raw.get('context_source_sha256')==self.context_sha,'libraries':raw.get('all_loaded_libraries_verified') is True and raw.get('backend_pins_sha256')==file_hash(self.pins_path),'bias_position':raw.get('bias_applied_positions')==(1 if rows else 0),'model':raw.get('model',{}).get('sha256')==ident['model_sha256']==raw.get('model_sha256_after'),'new_abi':raw.get('feature_abi')==STREAM_ABI and raw.get('worker_source_sha256')==command['worker_source_sha256'] and raw.get('executable_sha256')==self.binding['binary_sha256']}
            loaded=[raw.get(k,{}) for k in ('loaded_llama_library','loaded_ggml_library','loaded_ggml_base_library')]+raw.get('loaded_cpu_backend_libraries',[])
            checks['actual_loaded_library_pins']=loaded_library_pins_match(loaded,ident['libraries'])
            biased=self.logits.astype(np.float32).copy()
            for token,value in rows:biased[token]+=np.float32(value)
            predicted_first=int(biased.argmax())
            checks['exact_first_position_delta']=raw.get('first_native_greedy_token_id')==int(self.logits.argmax()) and raw.get('first_biased_token_id')==predicted_first
            checks.update(completion_checks(raw,self.token_events,self.context['token_ids'],bytes(self.stream_bytes),self.max_tokens,predicted_first))
            self.metrics['checks']=checks
            if not all(checks.values()):raise Unavailable('Native same-context streaming completion binding failed')
            verify_binding(self.binding);check(self.cancel,self.deadline);self.metrics['status']='SAME_CONTEXT_STREAM_COMPLETE';self.finished=True;self._save()
            yield {'event':'COMPLETE','text':bytes(self.stream_bytes).decode('utf-8','replace'),'native_token_ids':raw['decoded_native_token_ids'],'raw_result':raw,'metrics':dict(self.metrics),'feature_abi':self.binding['feature_abi'],'production_integration':False,'approval_authority':0}
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
        if self.metrics['status']!='SAME_CONTEXT_STREAM_COMPLETE':self.metrics['status']='CLOSED_WITHOUT_COMPLETE_RESULT'
        self.finished=True;self._save()
