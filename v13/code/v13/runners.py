import contextlib
import copy
import http.client
import json
import math
import os
from pathlib import Path
import secrets
import select
import re
import shutil
import socket
import subprocess
import threading
import time
from .common import APP,dumps,digest,atomic_write,Cancelled,Unavailable,Limits
from .resources import process_memory
def wire_json(v):
    """Request body for llama-server. Unlike common.dumps it keeps key order: the server builds the JSON-schema
    grammar in property order, so sorting would make the model decide e.g. `action` before `options` or
    `needs_reentry` before `summary` (WP-W1). Hashes/logs keep using the sorted common.dumps."""
    return json.dumps(v,ensure_ascii=False,separators=(",",":"),allow_nan=False)
def check(cancel,deadline):
    if cancel.is_set():raise Cancelled("Abgebrochen")
    if time.monotonic()>=deadline:raise Limits("Zeitbudget erreicht")
def kill_process(proc):
    if proc is None:return
    if proc.poll() is None:
        proc.terminate()
        try:proc.wait(timeout=1.5)
        except subprocess.TimeoutExpired:proc.kill();proc.wait(timeout=2)
def native_cache_args(cfg):
    # b10964 defaults (--cache-ram 8192 MiB host prompt cache, 32 context
    # checkpoints per slot) assume a desktop. Qwen3.5 checkpoints are ~19 MiB
    # each (docs/NATIVE_CACHE.md), so a 6 GB phone needs explicit bounds.
    from .config import DEFAULTS
    ram=cfg.get('native_cache_ram_mb',DEFAULTS['native_cache_ram_mb'])
    checkpoints=cfg.get('native_ctx_checkpoints',DEFAULTS['native_ctx_checkpoints'])
    return ['--cache-ram',str(ram),'--ctx-checkpoints',str(checkpoints)]
def rotate_log(path,cap=3*1024*1024):
    if path.exists() and path.stat().st_size>cap:os.replace(path,path.with_suffix(".previous.log"))
class LlamaRunner:
    def __init__(self,home,role,model,config,purpose='generate',approval_store=None):
        self.home=Path(home);self.role=role;self.model=model;self.cfg=config;self.purpose=purpose;self.proc=None;self.port=None;self.key=secrets.token_hex(24);self.last_metrics={};self.log_handle=None
        self.approval_store=approval_store;self._asset_snapshot=None;self._launch_assets={};self._asset_snapshot_hashes={};self._approved_asset_paths=[]
        self.binary=os.environ.get("V13_LLAMA_SERVER",str(home/"bin/llama-server"))
        self._audit_enabled=False;self._audit_window=None;self._audit_unavailable=None;self._audit_lock=threading.Lock()
        self.memory=None;self._memory_delivery_binding=None;self._loaded_stamp=None;self._loaded_binary=None
    def _lifecycle_stamp(self):
        # Warm generation checks metadata only. Approval/model/native hashes are
        # revalidated on load, never reread for every prompt on a healthy child.
        paths=[self.model,self.binary]
        if self.purpose=='generate':
            paths += [self.home/'config/lora-active.json',self.home/'config/memory-server.json',self.home/'bin/llama-server-mem']
        if self._loaded_binary:paths.append(self._loaded_binary)
        for binary in (self.binary,self._loaded_binary):
            if binary:paths += sorted(Path(binary).resolve().parent.glob('*.so*'))
        if self.memory:
            native=self.memory.get('env',{}).get('V13_MEMORY_FILE')
            if native:paths += [native,str(native)+'.items.json']
        def stamp(path):
            path=Path(path)
            try:
                own=path.lstat();target=path.stat()
                return (str(path),*( (s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns,s.st_mode) for s in (own,target)))
            except OSError:return (str(path),None)
        paths += self._approved_asset_paths+list(self._launch_assets.values())
        return (('native_memory_audit',self.cfg.get('native_memory_audit',False) is True),)+tuple(stamp(p) for p in paths)
    @property
    def memory_delivery_binding(self):
        # The binding describes the child that completed its health handshake,
        # not a registry proposal or a dead/stale process.
        if self.proc is None or self.proc.poll() is not None or self._loaded_stamp!=self._lifecycle_stamp():return None
        return copy.deepcopy(self._memory_delivery_binding) if self._memory_delivery_binding else None
    def pids(self):return [self.proc.pid] if self.proc and self.proc.poll() is None else []
    def unload(self):
        before=process_memory(self.proc.pid) if self.proc else None;kill_process(self.proc);self.proc=None
        self.memory=None;self._memory_delivery_binding=None;self._loaded_stamp=None;self._loaded_binary=None
        if self.log_handle:self.log_handle.close();self.log_handle=None
        if self._asset_snapshot is not None:shutil.rmtree(self._asset_snapshot,ignore_errors=True)
        self._asset_snapshot=None;self._launch_assets={};self._asset_snapshot_hashes={};self._approved_asset_paths=[]
        return {"before":before,"process_reaped":True}
    def _json(self,method,path,payload,deadline,timeout_cap=3.):
        remaining=deadline-time.monotonic()
        if remaining<=0:raise Limits('Zeitbudget erreicht')
        conn=http.client.HTTPConnection("127.0.0.1",self.port,timeout=max(.001,remaining if timeout_cap is None else min(timeout_cap,remaining)))
        try:
            conn.request(method,path,wire_json(payload).encode() if payload is not None else None,{"Authorization":"Bearer "+self.key,"Content-Type":"application/json"});r=conn.getresponse();data=r.read()
            if r.status!=200:raise RuntimeError(f"Runner HTTP {r.status}: {data[:200].decode(errors='replace')}")
            return json.loads(data)
        finally:conn.close()
    @contextlib.contextmanager
    def _approval_guard(self,cancel,deadline):
        # Approval can hold the writer mutex across filesystem recovery. A
        # reader waiting for it must still honour its cancellation/deadline.
        check(cancel,deadline)
        if self.approval_store is None:
            yield
            return
        acquired=False
        try:
            while not acquired:
                check(cancel,deadline)
                acquired=self.approval_store.mutex.acquire(timeout=max(0.,min(.05,deadline-time.monotonic())))
            check(cancel,deadline)
            yield
        finally:
            if acquired:self.approval_store.mutex.release()
    def _verify_approval_mirror(self):
        # Caller holds Store.mutex. The database remains authoritative even
        # when a failed mirror recovery leaves an ACTIVATING journal behind.
        if self.approval_store is None:return
        from .lora_trainer import REGISTRY_KEY,MIRROR
        active=(self.approval_store.state(REGISTRY_KEY,None)[0] or {}).get('active',{})
        expected={r:{k:b[k] for k in ('path','sha256','base_model_sha256','batch_id','scale','sidecar_sha256') if k in b}
                  for r,b in active.items() if b}
        try:actual=json.loads((self.home/MIRROR).read_text())
        except FileNotFoundError:actual={}
        except (OSError,ValueError) as exc:raise Unavailable('Adapter mirror unreadable') from exc
        if actual!=expected:raise Unavailable('Adapter mirror differs from committed approval')
    def _snapshot_assets(self,cmd,env):
        if self.approval_store is None or self.purpose!='generate':return
        from .common import file_hash
        from .lora_trainer import REGISTRY_KEY
        active=(self.approval_store.state(REGISTRY_KEY,None)[0] or {}).get('active',{})
        specs=[]
        if '--lora-scaled' in cmd:
            i=cmd.index('--lora-scaled')+1
            specs.append(('adapter',cmd[i],active[self.role]['sha256'],i))
        if self.memory:
            cur=active[self.role+'#sparse_memory'];path=self.memory['env']['V13_MEMORY_FILE']
            specs.append(('memory',path,cur['sha256'],None))
            if cur.get('sidecar_sha256'):
                specs.append(('memory.items',str(path)+'.items.json',cur['sidecar_sha256'],None))
        if not specs:return
        folder=self.home/'tmp'/('runner-assets-'+secrets.token_hex(16));folder.mkdir(parents=True,mode=0o700)
        self._asset_snapshot=folder;self._launch_assets={};self._approved_asset_paths=[p for _,p,_,_ in specs]
        try:
            for kind,path,expected,index in specs:
                dest=Path(str(self._launch_assets['memory'])+'.items.json') if kind=='memory.items' else folder/(kind+Path(path).suffix)
                shutil.copyfile(path,dest)
                if file_hash(dest)!=expected:raise Unavailable('Approved adapter bytes changed during snapshot')
                dest.chmod(0o400);self._launch_assets[kind]=str(dest)
                if index is not None:cmd[index]=str(dest)
                elif kind=='memory':env['V13_MEMORY_FILE']=str(dest)
            # Record hashes independently from original paths; the child opens
            # these private bytes after Store.mutex has been released.
            self._asset_snapshot_hashes={p:file_hash(p) for p in self._launch_assets.values()}
        except BaseException:
            shutil.rmtree(folder,ignore_errors=True);self._asset_snapshot=None;self._launch_assets={};self._asset_snapshot_hashes={};self._approved_asset_paths=[]
            raise
    def load(self,cancel,deadline):
        try:return self._load_validated(cancel,deadline)
        except BaseException:self.unload();raise
    def _load_validated(self,cancel,deadline):
        check(cancel,deadline)
        if self.proc and self.proc.poll() is None:
            with self._approval_guard(cancel,deadline):
                self._verify_approval_mirror()
                if self._loaded_stamp==self._lifecycle_stamp():return
            # Forget/rebind may rewrite a native memory while the old server
            # still owns its loaded copy. Reap it before validating a new child.
            self.unload()
        elif self.proc or self.log_handle:self.unload()
        self.memory=None;self._memory_delivery_binding=None;self._loaded_stamp=None;self._loaded_binary=None
        if not Path(self.binary).is_file():raise Unavailable("llama-server fehlt; setup.sh erneut ausführen")
        with socket.socket() as s:s.bind(("127.0.0.1",0));self.port=s.getsockname()[1]
        lp=self.home/"logs"/(self.role+".log");rotate_log(lp);self.log_handle=open(lp,"ab");env=os.environ.copy();env.pop('V13_MEMORY_FILE',None);env["LLAMA_API_KEY"]=self.key
        # Noncausal embedding prefill must fit the whole admitted sequence in
        # one physical batch. Chunking changes the feature being measured.
        batch=512 if (self.purpose=='tap' and self.role=='C3_LANGUAGE') or self.purpose=='embed' else 128
        cmd=[self.binary,"-m",str(self.model),"--host","127.0.0.1","--port",str(self.port),"-c",str(512 if self.purpose=='embed' else self.cfg["context_tokens"]),"-np","1","-t",str(self.cfg["threads"]),"-tb",str(self.cfg["threads"]),"-b",str(batch),"-ub",str(batch),"-ngl","0","--no-warmup","--no-webui","--log-disable"]
        cmd += native_cache_args(self.cfg)
        if self.purpose=='tap':cmd += ['--embedding','--pooling','none']
        elif self.purpose=='embed':cmd += ['--embedding','--no-repack']  # pooled vectors (model pooling, EmbeddingGemma: mean); no repack halves RSS (cloud 737->393 MB)
        elif self.purpose=='generate':
            with self._approval_guard(cancel,deadline):
                self._verify_approval_mirror()
                try:
                    from .lora_trainer import runner_lora_args
                    cmd += runner_lora_args(self.home,self.role,self.model)  # only a user-approved, hash-bound AG6 adapter
                except Exception:pass
                try:  # approved keyed fact memory (WP-S3): patched llama-server-mem, only if binary/model/memory hashes match
                    from .memory_server import runner_memory
                    mem=runner_memory(self.home,self.role,self.model)
                    if mem:cmd[0]=mem['binary'];env.update(mem['env'])
                    self.memory=mem
                except Exception:self.memory=None
                try:self._snapshot_assets(cmd,env)
                except BaseException:self.unload();raise
        env.pop('V13_MEMORY_AUDIT',None)
        self._audit_enabled=self.purpose=='generate' and bool(self.memory) and self.cfg.get('native_memory_audit',False) is True
        if self._audit_enabled:env['V13_MEMORY_AUDIT']='1'
        self._loaded_binary=cmd[0];launch_stamp=self._lifecycle_stamp()
        check(cancel,deadline)
        try:
            self.proc=subprocess.Popen(cmd,stdin=subprocess.DEVNULL,stdout=self.log_handle,stderr=self.log_handle,env=env)
            while True:
                check(cancel,deadline)
                if self.proc.poll() is not None:raise Unavailable(self.role+": Runner beendet; :logs runner")
                try:
                    if self._json("GET","/health",None,min(deadline,time.monotonic()+1)).get("status")=="ok":break
                except (OSError,RuntimeError,http.client.HTTPException,json.JSONDecodeError):pass
                cancel.wait(.1)
            with self._approval_guard(cancel,deadline):
                self._verify_approval_mirror()
                for path,expected in self._asset_snapshot_hashes.items():
                    from .common import file_hash
                    if file_hash(path)!=expected:raise Unavailable("Runner asset snapshot changed")
                binding=None
                if self.memory:
                    from .memory_server import captured_delivery_binding
                    binding=captured_delivery_binding(self.home,self.role,self.model)
                    if binding and str(binding.get('path'))!=self.memory['env']['V13_MEMORY_FILE']:binding=None
                if launch_stamp!=self._lifecycle_stamp():raise Unavailable(self.role+': Runner-Bindung während des Ladens geändert; erneut versuchen')
                self._loaded_stamp=launch_stamp;self._memory_delivery_binding=binding
        except BaseException:self.unload();raise
    def _audit_begin_window(self,multiple_steps=False):
        self._audit_window=None
        if not self._audit_enabled:return
        reason='MULTIPLE_NATIVE_STEPS' if multiple_steps else 'NO_MATCHING_LOADED_BINDING'
        self._audit_unavailable=reason
        binding=self.memory_delivery_binding
        if multiple_steps or not binding:return
        try:
            self.log_handle.flush();stat=os.fstat(self.log_handle.fileno())
            self._audit_window={'path':self.home/'logs'/(self.role+'.log'),
                'offset':stat.st_size,'identity':(stat.st_dev,stat.st_ino),
                'pid':self.proc.pid,'binding':binding}
            self._audit_unavailable=None
        except (OSError,ValueError,AttributeError):self._audit_unavailable='AUDIT_LOG_UNREADABLE'
    def _audit_finish_window(self,status):
        if not self._audit_enabled:return None
        base={'status':'UNAVAILABLE','exact_retained':True,'quality_proven':False,
              'activation_authorized':False,'semantic_truth_authority':False}
        window=self._audit_window
        if status!='FINAL':return dict(base,reason='REQUEST_NOT_FINAL',request_status=status)
        if not window:return dict(base,reason=self._audit_unavailable or 'NO_REQUEST_WINDOW')
        if not self._audit_completed:return dict(base,reason='REQUEST_NOT_COMPLETED')
        if (self.proc is None or self.proc.poll() is not None or self.proc.pid!=window['pid']
                or self.memory_delivery_binding!=window['binding']):
            return dict(base,reason='REQUEST_BINDING_CHANGED')
        try:
            stat=window['path'].stat()
            if (stat.st_dev,stat.st_ino)!=window['identity'] or stat.st_size<window['offset']:
                return dict(base,reason='AUDIT_LOG_CHANGED')
            from .sparse_audit import read_firing_window
            observed=read_firing_window(window['path'],window['offset'])
        except OSError:return dict(base,reason='AUDIT_LOG_UNREADABLE')
        if self.memory_delivery_binding!=window['binding']:
            return dict(base,reason='REQUEST_BINDING_CHANGED')
        return dict(observed,request_status=status,loaded_binding=window['binding'],
                    semantic_truth_authority=False)
    def embed(self,texts,cancel,deadline):
        """Pooled sentence embeddings (WP-H). Only for purpose='embed'; vectors are relevance keys, never facts."""
        if self.purpose!='embed':raise Unavailable('Nur der Embedding-Runner liefert Satzvektoren')
        self.load(cancel,deadline);check(cancel,deadline)
        data=self._json('POST','/v1/embeddings',{'input':list(texts)},deadline,timeout_cap=None)['data']
        vectors=[row['embedding'] for row in sorted(data,key=lambda row:row['index'])]
        if len(vectors)!=len(texts) or any(not v or not all(math.isfinite(x) for x in v) for v in vectors):raise Unavailable('Embedding-Antwort ungültig')
        return vectors
    def _prompt(self,messages,cancel,deadline,reserve):
        work=[dict(x) for x in messages];truncated=False
        while True:
            check(cancel,deadline);p=self._json("POST","/apply-template",{"messages":work,"add_generation_prompt":True,"chat_template_kwargs":{"enable_thinking":False}},deadline)["prompt"]  # Qwen3.5 B2: no hidden thinking; LFM ignores it
            tokens=self._json("POST","/tokenize",{"content":p,"add_special":True},deadline)["tokens"]
            if len(tokens)+reserve+16<=self.cfg["context_tokens"]:return p,len(tokens),truncated
            if len(work)>2:work.pop(1);truncated=True
            else:raise Limits("Frage + Regeln überschreiten das native Kontextfenster. Kürzer fragen oder :budget context_tokens erhöhen.")
    def generate(self,messages,cancel,deadline,max_tokens=None,schema=None,seed=13,first_token_bias=None,confidence_field='summary'):
        if self.purpose!='generate':raise Unavailable('Tap-Runner erzeugt keine Antworten; Generation-Runner anfordern')
        audit_requested=self.cfg.get('native_memory_audit',False) is True
        audit_locked=False
        if audit_requested:
            audit_locked=self._audit_lock.acquire(blocking=False)
            if not audit_locked:raise Unavailable('Concurrent native audit request')
        self._audit_window=None;self._audit_unavailable=None;self._audit_completed=False
        # Measure cold load, prefill and streaming, including failed/cancelled calls.
        started=time.monotonic();done=threading.Event();samples=[];peaks={'rss_bytes':None,'pss_bytes':None};count=0;self.last_metrics={};self.phase='load';self.phase_started=started;self.stage_times={};status='FINAL'
        def sample():
            nonlocal count
            proc=self.proc
            if proc is None or proc.poll() is not None:return
            m=process_memory(proc.pid);count+=1
            for key in peaks:
                if m.get(key) is not None:peaks[key]=max(peaks[key] or 0,m[key])
            row={'elapsed_s':time.monotonic()-started,'phase':self.phase,**m}
            samples.append(row)
            if len(samples)>64:del samples[1]  # retain first sample, bounded recent tail, aggregate peaks
        def monitor():
            while not done.wait(.25):sample()
        watcher=threading.Thread(target=monitor,daemon=True);watcher.start()
        try:
            yield from self._generate(messages,cancel,deadline,max_tokens,schema,seed,first_token_bias,confidence_field)
        except BaseException as exc:
            status='CANCELLED' if isinstance(exc,Cancelled) else ('DEADLINE' if isinstance(exc,Limits) and time.monotonic()>=deadline else 'ERROR')
            raise
        finally:
            done.set();watcher.join(timeout=1);sample()
            if self.phase=='stream':self.stage_times['stream_s']=time.monotonic()-self.phase_started
            self.last_metrics.update(stage_durations_s=dict(self.stage_times),last_phase=self.phase,elapsed_in_last_phase_s=time.monotonic()-self.phase_started,requested_tokens=max_tokens or self.cfg['answer_tokens'],input_message_count=len(messages))
            self.last_metrics.update(role=self.role,duration_s=time.monotonic()-started,status=status,actual_model=self.model.name,resource_sample_count=count,resource_samples=samples,sample_interval_s=.25,sampled_peak_pss_bytes=peaks['pss_bytes'],CAN_LATENT_TAP=False,CAN_LATENT_INJECT=False,CAN_TRAIN_BODY=False)
            values=[v for v in [self.last_metrics.get('sampled_peak_rss_bytes'),peaks['rss_bytes']] if v is not None]
            self.last_metrics['sampled_peak_rss_bytes']=max(values) if values else None
            self.last_metrics.setdefault('generated_tokens',0);self.last_metrics.setdefault('ttft_s',None)
            # A synchronous check may beat the watchdog. Do not stop its watcher
            # and leave the old native request running after declaring idle.
            if audit_locked:
                try:
                    observed=self._audit_finish_window(status)
                    if observed is not None:self.last_metrics['native_memory_firing']=observed
                finally:self._audit_lock.release()
            if status!='FINAL':self.last_metrics['interruption_unload']=self.unload()
    def completion_one(self,payload,cancel,deadline):
        """One real native decoder step with cancellation, not a text substitute."""
        self.load(cancel,deadline);check(cancel,deadline)
        conn=http.client.HTTPConnection('127.0.0.1',self.port,timeout=max(.1,deadline-time.monotonic()));done=threading.Event()
        def watchdog():
            while not done.wait(.05):
                if cancel.is_set() or time.monotonic()>=deadline:
                    kill_process(self.proc)
                    with contextlib.suppress(Exception):conn.close()
                    return
        watcher=threading.Thread(target=watchdog,daemon=True);watcher.start()
        try:
            conn.request('POST','/completion',wire_json(payload|{'n_predict':1,'stream':False,'return_tokens':True}).encode(),{'Authorization':'Bearer '+self.key,'Content-Type':'application/json'})
            response=conn.getresponse();raw=response.read();check(cancel,deadline)
            if response.status!=200:raise Unavailable('Native output step HTTP '+str(response.status))
            result=json.loads(raw)
            if result.get('error'):raise Unavailable('Native output step failed')
            return result
        except (OSError,http.client.HTTPException):
            check(cancel,deadline);self.unload();raise Unavailable('Native output step interrupted')
        finally:done.set();conn.close();watcher.join(.2)
    def _generate(self,messages,cancel,deadline,max_tokens=None,schema=None,seed=13,first_token_bias=None,confidence_field='summary'):
        started=time.monotonic();self.load(cancel,deadline);self.stage_times['load_s']=time.monotonic()-started
        self.phase='template';self.phase_started=time.monotonic();cap=max_tokens or self.cfg["answer_tokens"];prompt,n,truncated=self._prompt(messages,cancel,deadline,cap)
        self.stage_times['template_s']=time.monotonic()-self.phase_started;self.phase='prefill';self.phase_started=time.monotonic()
        payload={"prompt":prompt,"n_predict":cap,"stream":True,"temperature":self.cfg["temperature"],"top_k":50,"repeat_penalty":1.05,"seed":seed,"cache_prompt":True,"id_slot":0,"return_tokens":True}
        if self.role=='C3_LANGUAGE' and not schema and self.cfg.get('c3_sampling','anti_echo')=='anti_echo':
            from .guards import C3_DECODER
            payload.update(C3_DECODER)  # WP-V3: v4 §65 start values against query echo
        if schema:payload["json_schema"]=schema
        lp_pairs=[] if schema and self.cfg.get('offer_logprobs',True) else None
        if lp_pairs is not None:payload['n_probs']=1  # WP-KAL2: token confidence for focal.offer_uncertainty
        self._audit_begin_window(multiple_steps=bool(first_token_bias))
        first_step=None;first_tokens=0
        if first_token_bias:
            if self.role!='C3_LANGUAGE' or schema:raise Unavailable('Output delta is C3 first-token text only')
            if not isinstance(first_token_bias,list) or not 1<=len(first_token_bias)<=16:raise ValueError('Bounded native output delta required')
            for pair in first_token_bias:
                if not isinstance(pair,(list,tuple)) or len(pair)!=2 or isinstance(pair[0],bool) or not isinstance(pair[0],int) or not 0<=pair[0]<65536 or isinstance(pair[1],bool) or not isinstance(pair[1],(int,float)) or not math.isfinite(pair[1]) or abs(pair[1])>12:raise ValueError('Invalid native output delta')
            if len({p[0] for p in first_token_bias})!=len(first_token_bias):raise ValueError('Duplicate native vocabulary row')
            native_prompt=self._json('POST','/tokenize',{'content':prompt,'add_special':True},deadline)['tokens']
            first_step=self.completion_one(payload|{'logit_bias':first_token_bias},cancel,deadline);ids=first_step.get('tokens',[])
            if len(ids)>1 or first_step.get('tokens_predicted',0)>1:raise Unavailable('Native output step exceeded first-position contract')
            first_tokens=len(ids)
            if first_step.get('content'):
                self.stage_times['prefill_to_first_token_s']=time.monotonic()-self.phase_started;self.phase_started=time.monotonic();self.phase='stream';yield first_step['content']
            if cap==1 or not ids or first_step.get('stop_type') in {'eos','word'}:
                self.last_metrics={'generated_tokens':first_tokens,'prompt_tokens':n,'history_trimmed':truncated,'timings':first_step.get('timings',{}),'output_adapter_native_first_step':{'token_ids':ids,'bias':first_token_bias,'remaining_positions_unbiased':True},'ttft_s':time.monotonic()-started}
                return
            payload['prompt']=native_prompt+ids;payload['n_predict']=cap-1
        conn=http.client.HTTPConnection("127.0.0.1",self.port,timeout=max(1,deadline-time.monotonic()));stop_watch=threading.Event()
        def watchdog():
            while not stop_watch.wait(.05):
                if cancel.is_set() or time.monotonic()>=deadline:
                    kill_process(self.proc)
                    with contextlib.suppress(Exception):conn.close()
                    return
        watcher=threading.Thread(target=watchdog,daemon=True);watcher.start();first=time.monotonic() if first_step and first_step.get('content') else None;tokens=first_tokens;timings={};peak=None
        try:
            conn.request("POST","/completion",wire_json(payload).encode(),{"Content-Type":"application/json","Authorization":"Bearer "+self.key});response=conn.getresponse()
            if response.status!=200:raise RuntimeError(f"Inferenz HTTP {response.status}: {response.read(200).decode(errors='replace')}")
            while True:
                check(cancel,deadline);line=response.readline()
                if not line:break
                if not line.startswith(b"data: "):continue
                data=json.loads(line[6:])
                if "error" in data:raise RuntimeError(str(data["error"])[:200])
                content=data.get("content","");tokens+=len(data.get("tokens",[]))
                if lp_pairs is not None:lp_pairs.extend((x.get('token',''),x['logprob']) for x in data.get('completion_probabilities') or [] if isinstance(x.get('logprob'),(int,float)))
                if content:
                    if first is None:
                        first=time.monotonic();self.stage_times['prefill_to_first_token_s']=first-self.phase_started;self.phase_started=first
                    self.phase='stream';yield content
                if data.get("timings"):timings=data["timings"]
                if tokens%16==0:
                    rss=process_memory(self.proc.pid).get('rss_bytes')
                    if rss is not None:peak=rss if peak is None else max(peak,rss)
                if data.get("stop"):
                    if self._audit_enabled:self._audit_completed=True
                    break
            check(cancel,deadline)
        except (OSError,http.client.HTTPException):
            check(cancel,deadline);self.unload();raise Unavailable("Native Inferenz unterbrochen")
        finally:
            stop_watch.set();conn.close();watcher.join(timeout=2);end=time.monotonic();mem=process_memory(self.proc.pid) if self.proc and self.proc.poll() is None else {}
            rss_values=[v for v in (peak,mem.get('rss_bytes')) if v is not None]
            self.last_metrics={"role":self.role,"duration_s":end-started,"ttft_s":None if first is None else first-started,"generated_tokens":tokens,"prompt_tokens":n,"history_trimmed":truncated,"timings":timings,"sampled_peak_rss_bytes":max(rss_values) if rss_values else None,"memory":mem,"actual_model":self.model.name,"CAN_LATENT_TAP":False,"CAN_LATENT_INJECT":False,"CAN_TRAIN_BODY":False}
            if first_step:self.last_metrics['output_adapter_native_first_step']={'token_ids':first_step.get('tokens',[]),'bias':first_token_bias,'remaining_positions_unbiased':True,'timings':first_step.get('timings',{})}
            if lp_pairs:
                from .focal import token_confidence
                self.last_metrics['token_confidence']=token_confidence(lp_pairs,confidence_field)  # AG12 solver: field 'answer'
    def tap(self,text,cancel,deadline,max_tokens=64):
        """Pinned LFM2 result_norm, after final RMSNorm, before output projection.

        A separate read-only prefill, not a tap of another runner's live KV.
        Native token IDs and unnormalized vectors are returned without pooling.
        """
        if self.purpose!='tap':raise Unavailable('Separaten Tap-Modus anfordern')
        ceiling=512 if self.role=='C3_LANGUAGE' else 64
        dimension=getattr(self,'tap_dim',None) or (1024 if self.role=='C3_LANGUAGE' else 2048)
        if not 1<=max_tokens<=ceiling:raise ValueError('Tap-Budget 1..'+str(ceiling)+' native Tokens')
        started=time.monotonic();done=threading.Event()
        def watchdog():
            while not done.wait(.05):
                if cancel.is_set() or time.monotonic()>=deadline:kill_process(self.proc);return
        monitor=threading.Thread(target=watchdog,daemon=True);monitor.start()
        try:
            self.load(cancel,deadline);check(cancel,deadline)
            tokens=self._json('POST','/tokenize',{'content':text,'add_special':True},deadline)['tokens']
            if not tokens or len(tokens)>max_tokens:raise Limits('Tap-Quelle über '+str(max_tokens)+' native Tokens; expliziten kürzeren SourceRef wählen')
            # The native watchdog already terminates this read-only request on
            # cancellation/deadline. Mobile prefill may legitimately exceed the
            # short health/control HTTP timeout; retain the actual job budget.
            result=self._json('POST','/embeddings',{'input':tokens,'embd_normalize':-1},deadline,timeout_cap=None);check(cancel,deadline)
            vectors=result[0]['embedding']
            if len(vectors)!=len(tokens) or any(len(v)!=dimension or any(isinstance(x,bool) or not isinstance(x,(float,int)) or not math.isfinite(x) for x in v) for v in vectors):raise Unavailable('Native Tap-Dimension/Token-Bindung ungültig')
            if any(sum(x*x for x in v)<=1e-20 for v in vectors):raise Unavailable('Native Tap lieferte Null-Vektor')
            self.last_metrics={'role':self.role,'operation':'PREFILL_TAP','duration_s':time.monotonic()-started,'prompt_tokens':len(tokens),'embedding_dim':dimension,
                               'memory':process_memory(self.proc.pid),'CAN_LATENT_TAP':True,'CAN_LATENT_INJECT':False,'CAN_TRAIN_BODY':False,
                               'tap_id':'lfm2.result_norm.final.v1','pooling':'none','normalization':'native_final_RMSNorm_only','runner_revision':'b10964',
                               'physical_batch_tokens':512 if self.role=='C3_LANGUAGE' else 128,'whole_sequence_prefill':True}
            return {'token_ids':tokens,'vectors':vectors,'metrics':dict(self.last_metrics)}
        except BaseException:
            self.unload();check(cancel,deadline);raise
        finally:done.set();monitor.join(.2)

class CausalStreamRunner:
    """Opt-in C3 output using one checked causal prefill and its continuation.

    The temporary llama server only applies the real template/tokenizer. It is
    reaped before the stream child starts; no separate feature prefill or old
    learned delta is admitted. Other generation/tap paths keep LlamaRunner.
    """
    role='C3_LANGUAGE'
    purpose='causal_stream'
    def __init__(self,home,model,config,approval_store=None):
        self.home=Path(home);self.model=model;self.cfg=config;self.approval_store=approval_store
        self.template=None;self.session=None;self.last_metrics={};self.bias_provider=None
    def pids(self):
        out=self.template.pids() if self.template else []
        proc=self.session.proc if self.session else None
        if proc is not None and proc.poll() is None:out.append(proc.pid)
        return out
    def unload(self):
        release=self.template.unload() if self.template else {'process_reaped':True,'was_loaded':False}
        self.template=None
        if self.session is not None:
            self.session.close();release={'template':release,**self.session.metrics};self.session=None
        return release
    def prune_completed(self,keep=8):
        """Only our completed/reaped raw diagnostics; durable Store is untouched."""
        parent=self.home/'tmp';completed=[]
        if not parent.is_dir():return []
        for folder in parent.iterdir():
            if folder.is_symlink() or not folder.is_dir() or not re.fullmatch(r'c3-causal-stream-[0-9a-f]{32}',folder.name):continue
            marker=folder/'controller.json'
            try:
                if marker.is_symlink() or marker.stat().st_size>256*1024:continue
                metrics=json.loads(marker.read_text())
                if metrics.get('status') not in {'SAME_CONTEXT_STREAM_COMPLETE','CLOSED_WITHOUT_COMPLETE_RESULT'}:continue
                if metrics.get('process_reaped') is not True and metrics.get('pid') is not None:continue
                completed.append((folder.stat().st_mtime_ns,folder))
            except (OSError,ValueError):continue
        removed=[]
        for _,folder in sorted(completed,reverse=True)[keep:]:
            # Own nonce directories contain no sources/checkpoints or exports.
            try:shutil.rmtree(folder);removed.append(folder.name)
            except OSError:pass
        return removed
    def generate(self,messages,cancel,deadline,max_tokens=None,schema=None,seed=13,first_token_bias=None):
        from scripts.native_prefill_stream_client import StreamingOutputSession
        from .causal_prepare import check_prepared
        started=time.monotonic();status='FINAL';observed=None;complete=None
        self.last_metrics={'role':self.role,'actual_model':self.model.name,
            'decode_mode':self.cfg.get('c3_decode_mode','same_causal_zero'),'production_integration':True,
            'requested_tokens':max_tokens or self.cfg['answer_tokens'],
            'temperature_requested':self.cfg['temperature'],'sampling':'NATIVE_GREEDY',
            'seed_requested':seed,'seed_effect':'NONE_DETERMINISTIC_GREEDY',
            'learned_head_loaded':False,'approval_authority':0,
            'generated_tokens':0,'ttft_s':None,
            'CAN_LATENT_TAP':True,'CAN_LATENT_INJECT':False,'CAN_TRAIN_BODY':False}
        try:
            check(cancel,deadline)
            if schema is not None or first_token_bias is not None:
                raise Unavailable('Same-causal zero path refuses schema and separate-prefill learned deltas')
            cap=max_tokens or self.cfg['answer_tokens']
            if type(cap) is not int or cap not in (64,128):
                raise Unavailable('Same-causal output requires answer_tokens=64 or128')
            try:binding=check_prepared(self.home)
            except (OSError,KeyError,ValueError) as exc:
                raise Unavailable('Same-causal build unavailable; run bash VORBEREITEN_CAUSAL.sh: '+str(exc)[:160]) from exc
            if self.model.resolve()!=Path(binding['identity']['model_path']).resolve():raise Unavailable('Same-causal runner/model binding differs')
            self.last_metrics['feature_abi']=binding['feature_abi']
            self.last_metrics['native_parameters']={'context_tokens':2048,'threads':2,'n_batch':128,'n_ubatch':128,'prompt_token_limit':512,'output_token_limit':cap}
            # No history or rule text is silently removed to satisfy this ABI.
            self.template=LlamaRunner(self.home,self.role,self.model,dict(self.cfg,context_tokens=2048,threads=2),approval_store=self.approval_store)
            self.template.binary=binding['identity']['server_path']
            context_started=time.monotonic()
            try:
                self.template.load(cancel,deadline)
                check(cancel,deadline)
                prompt=self.template._json('POST','/apply-template',{'messages':messages,'add_generation_prompt':True},deadline)['prompt']
                ids=self.template._json('POST','/tokenize',{'content':prompt,'add_special':True},deadline)['tokens']
                if not isinstance(ids,list) or not 1<=len(ids)<=512:
                    raise Limits('Same-causal prompt exceeds512 native tokens; shorten context or use server decode mode')
                context={'messages':messages,'prompt':prompt,'token_ids':ids,'history_trimmed':False}
            finally:
                self.last_metrics['template_release']=self.template.unload();self.template=None
                self.last_metrics['template_and_tokenizer_seconds']=time.monotonic()-context_started
            check(cancel,deadline)
            self.prune_completed()
            if shutil.disk_usage(self.home).free<32*1024*1024:raise Limits('Same-causal diagnostics need32 MiB free disk')
            out=self.home/'tmp'/('c3-causal-stream-'+secrets.token_hex(16))
            self.last_metrics['artifact_directory']=str(out)
            self.session=StreamingOutputSession(binding,context,out,cancel,deadline,max_tokens=cap)
            prefill_started=time.monotonic()
            with self.session as active:
                observed=active.pause()
                atomic_write(out/'observed.json',dumps(observed))
                self.last_metrics['observed_sha256']=digest(dumps(observed))
                self.last_metrics.update(prompt_tokens=len(ids),history_trimmed=False,
                    native_context_binding=observed['native_context_binding'],
                    causal_load_and_prefill_seconds=time.monotonic()-prefill_started)
                rows=[]
                if self.cfg.get('c3_decode_mode')=='same_causal' and self.bias_provider is not None:
                    selected=self.bias_provider(observed);prediction=selected.get('prediction')
                    self.last_metrics['learned_head_status']=selected.get('fallback_reason')
                    if prediction is not None:
                        if prediction.get('individually_approved') is not True or not prediction.get('approved_update_id'):raise Unavailable('Causal delta lacks individual approved generation owner')
                        rows=prediction['first_token_bias'] if prediction['in_support'] else []
                        self.last_metrics.update(learned_head_loaded=True,approved_update_id=prediction['approved_update_id'],learned_first_token_delta_applied=bool(rows),nearest_native_cosine=prediction['nearest_native_cosine'])
                    check(cancel,deadline)
                for event in active.resume(rows):
                    if event['event']=='TOKEN':
                        self.last_metrics['generated_tokens']+=1
                        if event['text']:
                            if self.last_metrics['ttft_s'] is None:self.last_metrics['ttft_s']=time.monotonic()-started
                            yield event['text']
                    elif event['event']=='COMPLETE':complete=event
            if complete is None:raise Unavailable('Same-causal stream ended without verified completion')
            raw=complete['raw_result']
            self.last_metrics.update(native_token_ids=complete['native_token_ids'],
                stop_reason=raw['stop_reason'],resume_prefill_calls=raw['resume_prefill_calls'],
                resume_decode_calls=raw['resume_decode_calls'],
                unbiased_continuation_steps=raw['unbiased_continuation_steps'],
                same_context_lifetime=raw['same_context_lifetime'])
        except BaseException as original:
            exc=original
            try:check(cancel,deadline)
            except (Cancelled,Limits) as interrupted:exc=interrupted
            status='CANCELLED' if isinstance(exc,Cancelled) else ('DEADLINE' if isinstance(exc,Limits) and time.monotonic()>=deadline else 'ERROR')
            self.last_metrics.update(error_type=type(exc).__name__,error=str(exc)[:500])
            if exc is not original:raise exc from original
            raise
        finally:
            if self.template is not None:
                self.last_metrics['template_release']=self.template.unload();self.template=None
            if self.session is not None:
                self.session.close();self.last_metrics['causal_controller']=dict(self.session.metrics)
                self.last_metrics['process_reaped']=self.session.metrics['process_reaped']
                self.session=None
            self.last_metrics.setdefault('learned_head_status','UNAVAILABLE_NO_APPROVED_SAME_CAUSAL_HEAD')
            self.last_metrics.update(status=status,duration_s=time.monotonic()-started,completed_diagnostic_limit=8)
            self.last_metrics['removed_completed_diagnostics']=self.prune_completed()

# Validated read-only final-state taps per pinned model (models.json key): (tap_id, hidden size).
# gist = Qwen3.5-0.8B (B2): checked on b10964 2026-10-09, --embedding --pooling none gives 1024-dim
# per-token rows, repeatable for the same input (WP-N11).
TAP_SPECS={'body':('lfm2.result_norm.final.v1',2048),'language':('lfm2.result_norm.final.v1',1024),'gist':('qwen35.result_norm.final.v1',1024)}
class RunnerPool:
    """Native runners. WP-N11: several generate runners may stay resident under the AG13 body budget
    (bodies.BodyFabric decides load/evict); tap and causal-stream runners stay exclusive. Without a fabric
    or with body_residency_mb=0 this is the old one-process-at-a-time pool."""
    def __init__(self,home,models,cfg,approval_store=None):self.home=home;self.models=models;self.cfg=cfg;self.approval_store=approval_store;self.current=None;self.resident={};self.fabric=None;self.mutex=threading.RLock();self.release_history=[]
    def resident_roles(self):return [k[0] for k,v in self.resident.items() if v.pids()]
    def _adopt_current(self):
        # A runner set directly on .current (tests, older callers) is owned like a resident one.
        if self.current is not None and not any(self.current is v for v in self.resident.values()):
            self.resident[(self.current.role,getattr(self.current,'purpose','generate')+'#'+str(id(self.current)))]=self.current
    def _release(self,key):
        runner=self.resident.pop(key,None)
        if runner is None:return {"process_reaped":True,"was_loaded":False}
        if self.current is runner:self.current=None
        result=runner.unload()
        self.release_history.append({'role':key[0],'released_monotonic_ns':time.monotonic_ns(),**result});del self.release_history[:-64]
        if self.fabric:
            try:self.fabric.released(key[0])
            except Exception:pass
            self._port(key[0],'RELEASED')
        return result
    def _port(self,role,state,path=None):
        """WP-T13 IH-H8: report a lifecycle transition to the role's BodyPort (fail open)."""
        try:self.fabric.ports.event(role,state,path)
        except Exception:pass
    def _exclusive(self,key,make):
        self._adopt_current()
        for k in [k for k in self.resident if k!=key]:self._release(k)
        if key not in self.resident:self.resident[key]=make()
        self.current=self.resident[key];return self.current
    def get(self,role):
        with self.mutex:
            self._adopt_current();key=(role,'generate')
            for k in [k for k in self.resident if k[1]!='generate']:self._release(k)
            if self.fabric is None:
                for k in [k for k in self.resident if k!=key]:self._release(k)
            else:
                for r in self.fabric.admit(role,[k[0] for k in self.resident]):self._release((r,'generate'))
            path=self.models.path_for(role);cur=self.resident.get(key)
            if cur is not None and Path(str(cur.model)).resolve()!=Path(str(path)).resolve():  # WP-T13: another file serves this role now
                if self.fabric is not None and getattr(self.fabric,'ports',None) is not None:
                    try:self.fabric.ports.model_change(role,cur.model,path)  # IH-H21 bridge key checked before the new body serves
                    except Exception:pass
                self._release(key)
            if key not in self.resident:
                self.resident[key]=LlamaRunner(self.home,role,path,self.cfg)
                self.resident[key].approval_store=self.approval_store
                if self.fabric is not None:self._port(role,'ASSIGNED',path)
            self.current=self.resident[key];return self.current
    def get_output(self,role):
        if role!='C3_LANGUAGE' or self.cfg.get('c3_decode_mode','server')=='server':return self.get(role)
        with self.mutex:return self._exclusive((role,'causal_stream'),lambda:CausalStreamRunner(self.home,self.models.path_for(role),self.cfg,approval_store=self.approval_store))
    def get_tap(self,role):
        from .common import file_hash
        from .models import model_key
        if role not in {'B1_DETAIL','B2_GIST','C3_LANGUAGE'}:raise Unavailable('Tap nur für B1/B2/C3')
        key=model_key(role,self.models.b2_control)
        if key not in TAP_SPECS:raise Unavailable('Kein validierter Tap für Modell '+key)
        spec=json.loads((APP/'specs/models.json').read_text())['models'][key];path=self.models.path_for(role)
        if self.models.revision(role)!=spec['revision'] or file_hash(path)!=spec['files'][0]['sha256']:raise Unavailable('Dieser Tap ist nicht für den importierten/geänderten Body validiert')
        with self.mutex:
            runner=self._exclusive((role,'tap'),lambda:LlamaRunner(self.home,role,path,self.cfg,purpose='tap'))
            runner.tap_id,runner.tap_dim=TAP_SPECS[key];return runner
    def unload(self,role=None):
        """Release every runner (default) or only those of one role."""
        with self.mutex:
            self._adopt_current()
            results=[self._release(k) for k in [k for k in self.resident if role is None or k[0]==role]]
            if not results:return {"process_reaped":True,"was_loaded":False}
            return results[0] if len(results)==1 else {'process_reaped':all(r.get('process_reaped') for r in results),'released':len(results)}
    def pids(self):
        with self.mutex:
            self._adopt_current();return [p for r in self.resident.values() for p in r.pids()]
class NeedleRunner:
    def __init__(self,home,models):self.home=home;self.models=models;self.proc=None;self.log=None;self.buffer=b"";self.mutex=threading.RLock();self.last_metrics={}
    def unload(self):
        kill_process(self.proc);self.proc=None;self.buffer=b""
        if self.log:self.log.close();self.log=None
    def pids(self):return [self.proc.pid] if self.proc and self.proc.poll() is None else []
    def _read(self,cancel,deadline):
        n=None
        while True:
            check(cancel,deadline)
            if n is None and b"\n" in self.buffer:
                hdr,self.buffer=self.buffer.split(b"\n",1);n=int(hdr)
                if not 0<=n<=2*1024*1024:raise ValueError("Native frame too large")
            if n is not None and len(self.buffer)>=n:result=json.loads(self.buffer[:n]);self.buffer=self.buffer[n:];return result
            if self.proc.poll() is not None:raise Unavailable("Needle worker beendet; :logs runner")
            if select.select([self.proc.stdout],[],[],.05)[0]:
                chunk=os.read(self.proc.stdout.fileno(),65536)
                if not chunk:raise Unavailable("Needle EOF")
                self.buffer+=chunk
    def load(self,cancel,deadline):
        if self.proc and self.proc.poll() is None:return
        exe=self.home/"bin/needle-worker"
        if not exe.exists():raise Unavailable("Needle-Embedding-Worker fehlt; setup erneut ausführen")
        lp=self.home/"logs/C2_CONTROL.log";rotate_log(lp);self.log=open(lp,"ab");env=os.environ.copy();env.update(NEEDLE_TELEMETRY="0",DO_NOT_TRACK="1",OMP_NUM_THREADS="2")
        self.proc=subprocess.Popen([str(exe),str(self.models.path_for("C2_CONTROL")),str(APP/"specs/control_tools.json")],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=self.log,bufsize=0,env=env)
        if self._read(cancel,deadline).get("ready") is not True:raise Unavailable("Needle konnte nicht starten")
    def run(self,text,op,cancel,deadline):
        with self.mutex:
            start=time.monotonic();self.last_metrics={}
            try:
                self.load(cancel,deadline);check(cancel,deadline);b=text.encode()
                if len(b)>65536:raise Limits("Needle-Eingabe zu groß")
                self.proc.stdin.write(f"{op} {len(b)}\n".encode()+b);self.proc.stdin.flush();result=self._read(cancel,deadline)
                if result.get("error"):raise Unavailable(str(result["error"]))
                self.last_metrics={"role":"C2_CONTROL","operation":op,"duration_s":time.monotonic()-start,"status":"FINAL","memory":process_memory(self.proc.pid)};return result
            except BaseException as exc:
                status='CANCELLED' if isinstance(exc,Cancelled) else ('DEADLINE' if isinstance(exc,Limits) and time.monotonic()>=deadline else 'ERROR')
                self.last_metrics={"role":"C2_CONTROL","operation":op,"duration_s":time.monotonic()-start,"status":status,"memory":process_memory(self.proc.pid) if self.proc and self.proc.poll() is None else {}}
                self.unload();raise
    def control(self,text,cancel,deadline):
        if (self.home/"bin/needle-worker").exists():return self.run(text,"C",cancel,deadline)
        binary=self.home/"models/needle/needle"
        if not binary.exists():raise Unavailable("Needle CLI fehlt")
        env=os.environ.copy();env.update(NEEDLE_TELEMETRY="0",DO_NOT_TRACK="1")
        self.proc=subprocess.Popen([str(binary),"--model",str(self.models.path_for("C2_CONTROL")),"--tools",str(APP/"specs/control_tools.json"),"--prompt",text,"--max","160","--depth","8","--threads","2"],stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env)
        try:
            while self.proc.poll() is None:check(cancel,deadline);cancel.wait(.05)
            out,err=self.proc.communicate(timeout=1)
            if self.proc.returncode:raise Unavailable("Needle CLI fehlgeschlagen")
            self.last_metrics={"role":"C2_CONTROL","mode":"native_cli_fallback","embeddings_available":False};return json.loads(out)
        finally:kill_process(self.proc);self.proc=None
    def embed(self,text,cancel,deadline):return self.run(text,"E",cancel,deadline)["embedding"]
