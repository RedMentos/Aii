"""WP-S6 / WP-I / WP-AG6: real in-model learning through a LoRA adapter, measured on the deployed llama.cpp path.

Three parts, each usable alone:
  LoraTrainer        AG6 trainer (fit(items, base_generation, cancel, deadline)). Trains a LoRA on the fp32/bf16 master
                     (HF safetensors, never the quantized GGUF), with
                       - answer-only cross entropy on the batch (human, replay-tested memories),
                       - KL-to-base anchor on fixed anchor prompts (RL's Razor: forgetting tracks KL to base),
                       - optional Body-JEPA term (LLM-JEPA style): the body's latent at the end of the question must
                         predict the frozen base's latent of the answer (cosine, stop-grad target = base).
                     Checkpoint/resume per dataset hash, cancel/deadline, exports a llama.cpp LoRA GGUF + PEFT safetensors.
  LlamaCppEvaluator  starts the pinned llama-server with the adapter (scale 0 = base, 1 = candidate) on the quantized
                     inference model and measures learned recall, paraphrase recall, retention probes, specificity
                     (near-miss questions must not get the learned answer) and top-k KL(base || candidate).
  AdapterRegistry    the only place where an adapter becomes live: after AG6 APPROVED (user) it is bound to a role,
                     the base model hash and its own hash; runners add --lora only for such a binding. Rollback unbinds.
Torch/peft/gguf are imported lazily; nothing here runs on import. Authority: learned weights never activate themselves.
"""
import json,os,time,socket,subprocess,http.client,resource,hashlib
from pathlib import Path
from .common import digest,dumps,atomic_write,file_hash,Cancelled,Limits,Unavailable

REVISION='v13-lora-trainer-v1'
REGISTRY_KEY='LORA_ADAPTERS';MIRROR='config/lora-active.json'
# LFM2 safe default: no q/k (llama.cpp may permute q/k rows for RoPE; v/o/conv/ffn are stored 1:1).
DEFAULT_TARGETS=('v_proj','out_proj','in_proj','w1','w2','w3')
# Locality (knowledge-editing "near miss"): for a fact prompt with "my <noun>", the same prompt about other nouns is
# KL-anchored to the base so the new answer does not leak to them. Keep this list disjoint from any eval near-miss set.
SWAP_NOUNS=('friend','neighbour','mother','father','aunt','uncle','teacher','boss','horse','bird','car','house','laptop','son',
            'daughter','cousin','grandmother','colleague','hamster','bike')
DEFAULTS={'rank':8,'alpha':16.,'lr':1e-3,'max_steps':120,'min_steps':20,'target_loss':.05,'anchor_weight':1.,'jepa_weight':0.,
          'weight_decay':0.,'ckpt_every':20,'anchors_per_step':8,'locality_swaps':2,'seed':13,'threads':4,'targets':DEFAULT_TARGETS,'max_tokens':160}

def _check(cancel,deadline):
    if cancel is not None and (cancel() if callable(cancel) else cancel.is_set()):raise Cancelled('abgebrochen')
    if deadline is not None and time.monotonic()>deadline:raise Limits('Zeitbudget erreicht')

def _rss_mb():return round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,1)

def answer_hit(text,keys):
    t=' '.join(str(text).lower().split())
    return any(' '.join(str(k).lower().split()) in t for k in keys)

class LoraTrainer:
    method='lora-torch-cpu';self_teaches=True  # resolves SDFT items (target None + teacher_prompt) on the base model before training
    def __init__(self,master_dir,work_dir,master_sha256=None,anchors=(),probes=(),cfg=None,evaluator=None,arch=None,clock=time.time):
        """master_dir: HF model dir (config.json, model.safetensors, tokenizer). anchors: prompts for the KL-to-base anchor.
        probes: held-out retention prompts (dicts with 'prompt' and optional 'expect'), never trained on.
        evaluator: optional LlamaCppEvaluator factory (callable(adapter_path)->evaluator) for deployed-path gate values."""
        self.master=Path(master_dir);self.work=Path(work_dir);self.master_sha=master_sha256;self.anchors=list(anchors);self.probes=list(probes)
        self.cfg=dict(DEFAULTS,**(cfg or {}));self.deployed_base=None;self.evaluator=evaluator;self.arch=arch;self.clock=clock;self.last=None
    # -- data ------------------------------------------------------------------------------------------
    def _encode(self,tok,prompt,target=None):
        p=tok.apply_chat_template([{'role':'user','content':prompt}],add_generation_prompt=True,tokenize=False)
        pid=tok(p,add_special_tokens=False)['input_ids']
        if target is None:return pid,None
        tid=tok(str(target)+'<|im_end|>',add_special_tokens=False)['input_ids']
        n=self.cfg['max_tokens'];ids=(pid+tid)[-n:];cut=len(pid+tid)-len(ids)
        labels=[-100]*max(0,len(pid)-cut)+tid[max(0,cut-len(pid)):]
        return ids,labels
    def _load(self):
        import torch
        from transformers import AutoModelForCausalLM,AutoTokenizer
        torch.set_num_threads(int(self.cfg['threads']));torch.manual_seed(int(self.cfg['seed']))
        st=self.master/'model.safetensors'
        if self.master_sha and file_hash(st)!=self.master_sha:raise Unavailable('Master-Gewichte: SHA-256 passt nicht')
        tok=AutoTokenizer.from_pretrained(str(self.master));model=AutoModelForCausalLM.from_pretrained(str(self.master),dtype=torch.float32)
        if self.cfg.get('base_gguf'):self.deployed_base=self._load_gguf_weights(torch,model,self.cfg['base_gguf'])
        model.eval()
        return torch,tok,model
    def _load_gguf_weights(self,torch,model,path):
        """Train on what is deployed: overwrite the master's linear/norm weights with the dequantized inference GGUF
        (QLoRA idea), so the adapter is fitted to the exact Q4 weights the runner uses."""
        import gguf
        from gguf.quants import dequantize
        cfg=json.loads((self.master/'config.json').read_text());arch=[a for a,n in gguf.MODEL_ARCH_NAMES.items() if n==(self.arch or cfg.get('model_type'))][0]
        tm=gguf.get_tensor_name_map(arch,int(cfg['num_hidden_layers']));r=gguf.GGUFReader(str(path))
        tensors={t.name:t for t in r.tensors};params=dict(model.named_parameters());done=0;maxdiff=0.
        with torch.no_grad():
            for name,p in params.items():
                g=tm.get_name(name[:-len('.weight')]) if name.endswith('.weight') else None
                t=tensors.get(g+'.weight') if g else None
                if t is None:continue
                w=torch.from_numpy(dequantize(t.data,t.tensor_type).astype('float32').copy()).reshape(p.shape)
                maxdiff=max(maxdiff,float((w-p).abs().max()));p.copy_(w);done+=1
        return {'gguf':str(path),'sha256':file_hash(path),'tensors_replaced':done,'max_abs_diff_vs_master':round(maxdiff,5)}
    @staticmethod
    def locality_prompts(items,k):
        import re
        out=[]
        for n,i in enumerate(items):
            m=re.search(r'\bmy (\w+)',i['prompt'],re.I)
            if not m or k<=0:continue
            pool=[w for w in SWAP_NOUNS if w!=m.group(1).lower()]
            for j in range(k):out.append(i['prompt'][:m.start(1)]+pool[(n*k+j)%len(pool)]+i['prompt'][m.end(1):])
        return out
    @staticmethod
    def _greedy(torch,model,ids,n):
        with torch.no_grad():
            out=model.generate(torch.tensor([ids]),attention_mask=torch.ones(1,len(ids),dtype=torch.long),max_new_tokens=n,do_sample=False,pad_token_id=0)
        return out[0][len(ids):].tolist()
    def self_teach(self,torch,tok,model,items,n=64):
        """SDFT (WP-S5): the base model answers the teacher prompt (question + human correction) greedily; that answer
        becomes the target for the student prompt (question alone). On-policy, so no correction text is trained verbatim.
        A teacher answer that misses the correction's key words is dropped (the model did not take the correction)."""
        out=[];st={'items':0,'kept':0,'dropped':[]}
        for i in items:
            if i.get('target') is not None or not i.get('teacher_prompt'):out.append(i);continue
            st['items']+=1;pid,_=self._encode(tok,i['teacher_prompt'])
            ans=tok.decode(self._greedy(torch,model,pid,n),skip_special_tokens=True).strip()
            keys=i.get('answer_keys')
            if not ans or (keys and not answer_hit(ans,keys)):st['dropped'].append(i.get('memory_id'));continue
            ans=self.teacher_prefix(ans,keys)
            out.append(dict(i,target=ans,target_source='SELF_TEACHER_IN_CONTEXT'));st['kept']+=1
            st.setdefault('targets',[]).append(ans[:160])
        return out,st
    @staticmethod
    def teacher_prefix(ans,keys=None):
        """Own answer cut after the first sentence that carries the correction (still the model's own words, a prefix).
        Long chatty self-targets moved the frozen-probe drift over the cap in the first real SDFT run (.053 vs .05)."""
        import re
        parts=[p for p in re.split(r'(?<=[.!?])\s+',ans.strip()) if p]
        for k,p in enumerate(parts):
            if not keys or answer_hit(p,keys):return ' '.join(parts[:k+1])
        return ans.strip()
    # -- training --------------------------------------------------------------------------------------
    def fit(self,items,base_generation,cancel=None,deadline=None):
        if not items:return {'artifact':None,'hash':None,'method':self.method,'metrics':{'reason':'EMPTY_BATCH'}}
        try:import torch,peft  # noqa: F401
        except ImportError:return {'artifact':None,'hash':None,'method':self.method,'metrics':{'reason':'NO_TORCH_PEFT'}}
        t0=time.monotonic();cfg=self.cfg
        torch,tok,model=self._load()
        items,sdft=self.self_teach(torch,tok,model,items)
        if not items:return {'artifact':None,'hash':None,'method':self.method,'metrics':{'reason':'EMPTY_BATCH','sdft':sdft}}
        from peft import LoraConfig,get_peft_model
        dh=digest(dumps([[i.get('memory_id'),i['prompt'],i['target']] for i in items]+[self.anchors,{k:v for k,v in cfg.items() if k!='threads'} ]))[:24]
        out=self.work/dh;out.mkdir(parents=True,exist_ok=True)
        # Base reference: anchors/probes continuations and base JEPA targets, computed before any adapter exists.
        anchor_seqs=[];anchors=list(self.anchors)+self.locality_prompts(items,int(cfg['locality_swaps']))
        for a in anchors:
            pid,_=self._encode(tok,a);cont=self._greedy(torch,model,pid,24);anchor_seqs.append(pid+cont)
        with torch.no_grad():
            anchor_logp=[torch.log_softmax(model(torch.tensor([s])).logits[0].float(),-1) for s in anchor_seqs]
        probe_seqs=[]
        for p in self.probes:
            pid,_=self._encode(tok,p['prompt']);probe_seqs.append((len(pid),pid+self._greedy(torch,model,pid,16)))
        with torch.no_grad():probe_logp=[torch.log_softmax(model(torch.tensor([s])).logits[0].float(),-1) for _,s in probe_seqs]
        data=[self._encode(tok,i['prompt'],i['target']) for i in items]
        jepa=float(cfg['jepa_weight'])>0
        def last_hidden(m,ids):
            o=m(torch.tensor([ids]),output_hidden_states=True);return o.hidden_states[-1][0]
        jepa_tgt=[]
        if True:  # targets also measured with jepa off, so the ablation reports the same metric
            with torch.no_grad():
                for i in items:
                    tid=tok(str(i['target']),add_special_tokens=False)['input_ids'];jepa_tgt.append(last_hidden(model,tid).mean(0))
        lc=LoraConfig(r=int(cfg['rank']),lora_alpha=float(cfg['alpha']),lora_dropout=0.,target_modules=list(cfg['targets']),bias='none')
        model=get_peft_model(model,lc)
        params=[p for p in model.parameters() if p.requires_grad];n_train=sum(p.numel() for p in params)
        opt=torch.optim.AdamW(params,lr=float(cfg['lr']),weight_decay=float(cfg['weight_decay']))
        def jepa_cos():
            vals=[]
            with torch.no_grad():
                for (ids,lab),tg in zip(data,jepa_tgt):
                    plen=next(k for k,v in enumerate(lab) if v!=-100);h=last_hidden(model,ids[:plen])[-1]
                    vals.append(float(torch.nn.functional.cosine_similarity(h,tg,dim=0)))
            return sum(vals)/len(vals)
        jepa_before=jepa_cos()
        ck=out/'ckpt.pt';step=0;hist=[];resumed=False
        if ck.is_file():
            st=torch.load(ck,weights_only=False)
            if st.get('dataset_hash')==dh:
                model.load_state_dict(st['lora'],strict=False);opt.load_state_dict(st['opt']);step=st['step'];hist=st['hist'];resumed=True
        def save_ckpt():
            tmp=ck.with_suffix('.tmp');lora={k:v for k,v in model.state_dict().items() if 'lora_' in k}
            torch.save({'dataset_hash':dh,'lora':lora,'opt':opt.state_dict(),'step':step,'hist':hist},tmp);os.replace(tmp,ck)
        model.train();g=torch.Generator().manual_seed(int(cfg['seed'])+step)
        while step<int(cfg['max_steps']):
            _check(cancel,deadline)
            order=torch.randperm(len(data),generator=g).tolist();ce_sum=0.;kl_sum=0.;jl_sum=0.
            opt.zero_grad()
            for k in order:  # one step = one pass over the (small) batch, gradient accumulated
                ids,lab=data[k];o=model(torch.tensor([ids]),labels=torch.tensor([lab]),output_hidden_states=jepa)
                loss=o.loss*float(items[k].get('weight',1.))/len(data);ce_sum+=float(o.loss.detach())  # weight: e.g. `:note` rating
                if jepa:
                    plen=next(j for j,v in enumerate(lab) if v!=-100);h=o.hidden_states[-1][0][plen-1]
                    jl=1-torch.nn.functional.cosine_similarity(h,jepa_tgt[k],dim=0);loss=loss+float(cfg['jepa_weight'])*jl/len(data);jl_sum+=float(jl)
                loss.backward()
            if anchor_seqs and float(cfg['anchor_weight'])>0:
                pick=torch.randperm(len(anchor_seqs),generator=g).tolist()[:int(cfg['anchors_per_step'])]
                for s,bl in ((anchor_seqs[j],anchor_logp[j]) for j in pick):
                    cl=torch.log_softmax(model(torch.tensor([s])).logits[0].float(),-1)
                    kl=(bl.exp()*(bl-cl)).sum(-1).mean();(float(cfg['anchor_weight'])*kl/len(pick)).backward();kl_sum+=float(kl.detach())
            opt.step();step+=1
            hist.append({'step':step,'ce':round(ce_sum/len(data),5),'anchor_kl':round(kl_sum/max(1,min(len(anchor_seqs),int(cfg['anchors_per_step']))),6),'jepa':round(jl_sum/len(data),5) if jepa else None})
            if step%int(cfg['ckpt_every'])==0:save_ckpt()
            if step>=int(cfg['min_steps']) and hist[-1]['ce']<=float(cfg['target_loss']):break
        save_ckpt();model.eval()
        # Master-path metrics (fp32): recall on the batch prompts, exact KL on held-out probes.
        recall=[]
        for i in [x for x in items if x.get('kind')!='rated_answer'] or items:
            pid,_=self._encode(tok,i['prompt']);txt=tok.decode(self._greedy(torch,model,pid,48),skip_special_tokens=True)
            recall.append(answer_hit(txt,i.get('answer_keys') or [i['target']]))
        with torch.no_grad():
            kls=[]
            for (plen,s),bl in zip(probe_seqs,probe_logp):
                cl=torch.log_softmax(model(torch.tensor([s])).logits[0].float(),-1)[plen-1:-1];b=bl[plen-1:-1]
                kls.append(float((b.exp()*(b-cl)).sum(-1).mean()))
        jepa_after=jepa_cos()
        adapter=self._export(torch,model,out,lc)
        metrics={'revision':REVISION,'dataset_hash':dh,'base_generation':base_generation,'steps':step,'resumed':resumed,'sdft':sdft,'loss_history':hist[-40:],
                 'final_ce':hist[-1]['ce'] if hist else None,'trainable_parameter_count':n_train,'rank':int(cfg['rank']),'alpha':float(cfg['alpha']),
                 'targets':list(cfg['targets']),'anchor_weight':float(cfg['anchor_weight']),'jepa_weight':float(cfg['jepa_weight']),
                 'master_learned_recall':sum(recall)/len(recall),'master_kl_to_base':sum(kls)/len(kls) if kls else None,
                 'body_jepa_cos_before':round(jepa_before,5),'body_jepa_cos_after':round(jepa_after,5),
                 'seconds':round(time.monotonic()-t0,2),'peak_rss_mb':_rss_mb(),
                 'device':{'backend':'torch-cpu','threads':int(cfg['threads']),'torch':torch.__version__},'kl_source':'master_fp32','trained_on':self.deployed_base or 'master'}
        metrics['kl_to_base']=metrics['master_kl_to_base']
        result={'artifact':str(adapter['gguf']),'hash':adapter['gguf_sha256'],'method':self.method,'metrics':metrics,'files':adapter}
        if self.evaluator is not None:
            ev=self.evaluator(adapter['gguf'])
            try:rep=ev.evaluate(items,self.probes,cancel=cancel,deadline=deadline)
            finally:ev.close()
            metrics.update({'deployed':rep,'kl_to_base':rep['kl_to_base'],'kl_source':'deployed_llama_cpp_topk'})
            result['eval']={'base_eval':rep['base_eval'],'candidate_eval':rep['candidate_eval'],'learned_recall':rep['learned_recall']}
            if 'wp_s5_drift' in rep:result['eval']['wp_s5_drift']=rep['wp_s5_drift']  # frozen-probe drift (agi.trainers.LiveNearMissEvaluator)
        atomic_write(out/'manifest.json',json.dumps({k:v for k,v in result.items()},indent=1,ensure_ascii=False))
        self.last=result
        return result
    # -- export ----------------------------------------------------------------------------------------
    def _export(self,torch,model,out,lc):
        import gguf
        from safetensors.torch import save_file
        cfg=json.loads((self.master/'config.json').read_text())
        arch_name=self.arch or cfg.get('model_type')
        arch=[a for a,n in gguf.MODEL_ARCH_NAMES.items() if n==arch_name]
        if not arch:raise Unavailable('Unbekannte GGUF-Architektur: '+str(arch_name))
        tm=gguf.get_tensor_name_map(arch[0],int(cfg['num_hidden_layers']))
        sd={k:v.detach().float().cpu().contiguous() for k,v in model.state_dict().items() if 'lora_' in k}
        save_file(sd,str(out/'adapter_model.safetensors'))
        atomic_write(out/'adapter_config.json',json.dumps({'r':lc.r,'lora_alpha':lc.lora_alpha,'target_modules':sorted(lc.target_modules),'peft_type':'LORA','base_model_name_or_path':str(self.master)}))
        w=gguf.GGUFWriter(str(out/'adapter.gguf.tmp'),arch_name)
        w.add_string(gguf.Keys.General.TYPE,gguf.GGUFType.ADAPTER);w.add_string(gguf.Keys.Adapter.TYPE,'lora')
        w.add_float32(gguf.Keys.Adapter.LORA_ALPHA,float(lc.lora_alpha))
        pairs={}
        for k,v in sd.items():
            base=k.replace('base_model.model.','').split('.lora_')[0];ab='a' if '.lora_A.' in k else 'b'
            pairs.setdefault(base,{})[ab]=v
        names=[]
        for base,ab in sorted(pairs.items()):
            g=tm.get_name(base)
            if g is None:raise Unavailable('Kein GGUF-Name für '+base)
            w.add_tensor(g+'.weight.lora_a',ab['a'].numpy());w.add_tensor(g+'.weight.lora_b',ab['b'].numpy());names.append(g)
        w.write_header_to_file();w.write_kv_data_to_file();w.write_tensors_to_file();w.close()
        os.replace(out/'adapter.gguf.tmp',out/'adapter.gguf')
        return {'gguf':str(out/'adapter.gguf'),'gguf_sha256':file_hash(out/'adapter.gguf'),'safetensors':str(out/'adapter_model.safetensors'),
                'safetensors_sha256':file_hash(out/'adapter_model.safetensors'),'gguf_tensors':len(names)*2,'bytes':(out/'adapter.gguf').stat().st_size}


class LlamaCppEvaluator:
    """Deployed-path measurement: quantized GGUF + adapter in the pinned llama-server, scale 0 (base) vs 1 (candidate)."""
    def __init__(self,server_bin,model_gguf,adapter_gguf,threads=4,ctx=2048,log=None,paraphrases=None,near_miss=None):
        self.paraphrases=paraphrases;self.near_miss=near_miss;self.bin=Path(server_bin);self.model=Path(model_gguf);self.adapter=Path(adapter_gguf) if adapter_gguf else None;self.proc=None;self.log=log
        with socket.socket() as s:s.bind(('127.0.0.1',0));self.port=s.getsockname()[1]
        cmd=[str(self.bin),'-m',str(self.model)]+(['--lora',str(self.adapter),'--lora-init-without-apply'] if adapter_gguf else [])+['--host','127.0.0.1','--port',str(self.port),
             '-c',str(ctx),'-np','1','-t',str(threads),'-tb',str(threads),'-ngl','0','--no-warmup','--no-webui']
        lh=open(log,'ab') if log else subprocess.DEVNULL
        self.proc=subprocess.Popen(cmd,stdin=subprocess.DEVNULL,stdout=lh,stderr=lh)
        t=time.monotonic()
        while time.monotonic()-t<120:
            if self.proc.poll() is not None:raise Unavailable('llama-server mit Adapter beendet sich (Log: %s)'%log)
            try:
                if self._j('GET','/health').get('status')=='ok':break
            except Exception:pass
            time.sleep(.2)
        else:raise Unavailable('llama-server startet nicht')
    def close(self):
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:self.proc.wait(5)
            except subprocess.TimeoutExpired:self.proc.kill()
    def _j(self,method,path,payload=None):
        c=http.client.HTTPConnection('127.0.0.1',self.port,timeout=120)
        try:
            c.request(method,path,json.dumps(payload).encode() if payload is not None else None,{'Content-Type':'application/json'});r=c.getresponse();d=r.read()
            if r.status!=200:raise RuntimeError('HTTP %s %s'%(r.status,d[:200]))
            return json.loads(d)
        finally:c.close()
    def template(self,prompt):return self._j('POST','/apply-template',{'messages':[{'role':'user','content':prompt}],'add_generation_prompt':True})['prompt']
    def _lora(self,scale):return {'lora':[{'id':0,'scale':float(scale)}]} if self.adapter else {}
    def generate(self,prompt,scale=0.,n=48):
        r=self._j('POST','/completion',{'prompt':self.template(prompt),'n_predict':n,'temperature':0,'seed':13,'cache_prompt':False}|self._lora(scale))
        return r['content']
    def _dist(self,tokens,scale,k):
        r=self._j('POST','/completion',{'prompt':tokens,'n_predict':1,'temperature':0,'n_probs':k,'post_sampling_probs':False,'cache_prompt':False,'lora':[{'id':0,'scale':float(scale)}]})
        cp=r.get('completion_probabilities') or []  # empty after an end-of-generation token: nothing to compare there
        return {t['id']:t['logprob'] for t in cp[0]['top_logprobs']} if cp else None
    def kl(self,prompts,positions=8,k=40):
        """Mean top-k KL(base||candidate) per position along the base's greedy continuation (teacher-forced)."""
        vals=[]
        for p in prompts:
            pt=self._j('POST','/tokenize',{'content':self.template(p),'add_special':True})['tokens']
            r=self._j('POST','/completion',{'prompt':pt,'n_predict':positions,'temperature':0,'cache_prompt':False,'return_tokens':True,'lora':[{'id':0,'scale':0.}]})
            cont=r.get('tokens') or []
            for j in range(min(positions,len(cont)+1)):
                seq=pt+cont[:j];b=self._dist(seq,0.,k)
                if not b:break  # base continuation ended (short answer + EOS)
                c=self._dist(seq,1.,k) or {}
                floor=min(c.values()) if c else -30.
                # renormalise base top-k mass; tokens missing from the candidate's top-k get its floor (upper-bound-ish)
                import math
                zb=math.log(sum(math.exp(v) for v in b.values()))
                vals.append(sum(math.exp(v-zb)*((v-zb)-c.get(t,floor)) for t,v in b.items()))
        return sum(vals)/len(vals) if vals else None
    def evaluate(self,items,probes,cancel=None,deadline=None,paraphrases=None,near_miss=None):
        def score(scale):
            rows=[]
            for p in probes:
                _check(cancel,deadline);txt=self.generate(p['prompt'],scale,40)
                rows.append({'prompt':p['prompt'],'unseen':bool(p.get('unseen')),'ok':answer_hit(txt,p['expect']) if p.get('expect') else None,'text':txt[:200]})
            return rows
        base=score(0.);cand=score(1.)
        def agg(rows,unseen=None):
            v=[r['ok'] for r in rows if r['ok'] is not None and (unseen is None or r['unseen']==unseen)]
            return sum(v)/len(v) if v else None
        b_ok={r['prompt'] for r in base if r['ok']};forgot=[r['prompt'] for r in cand if r['prompt'] in b_ok and not r['ok']]
        learned=[]
        for i in [x for x in items if x.get('kind')!='rated_answer']:  # rated answers are style examples, not recall targets
            _check(cancel,deadline);keys=i.get('answer_keys') or [i['target']]
            learned.append({'prompt':i['prompt'],'base':answer_hit(self.generate(i['prompt'],0.),keys),'candidate':answer_hit(self.generate(i['prompt'],1.),keys)})
        para=[];paraphrases=paraphrases if paraphrases is not None else self.paraphrases;near_miss=near_miss if near_miss is not None else self.near_miss
        for q,keys in (paraphrases or []):para.append({'prompt':q,'base':answer_hit(self.generate(q,0.),keys),'candidate':answer_hit(self.generate(q,1.),keys)})
        leak=[]
        for q,keys in (near_miss or []):leak.append({'prompt':q,'base':answer_hit(self.generate(q,0.),keys),'candidate':answer_hit(self.generate(q,1.),keys)})
        kl=self.kl([p['prompt'] for p in probes])
        rate=len(forgot)/len(b_ok) if b_ok else None
        return {'base_eval':{'overall':agg(base),'unseen':agg(base,True)},
                'candidate_eval':{'overall':agg(cand),'unseen':agg(cand,True),'forgetting':{'rate':rate,'forgotten':forgot}},
                'learned_recall':sum(x['candidate'] for x in learned)/len(learned) if learned else None,
                'base_recall':sum(x['base'] for x in learned)/len(learned) if learned else None,
                'paraphrase_recall':sum(x['candidate'] for x in para)/len(para) if para else None,
                'near_miss_leak':sum(x['candidate'] for x in leak)/len(leak) if leak else None,
                'kl_to_base':kl,'kl_method':'top40 teacher-forced along base greedy continuation, 8 positions/probe',
                'rows':{'learned':learned,'paraphrase':para,'near_miss':leak,'probes_base':base,'probes_candidate':cand},
                'model_sha256':file_hash(self.model),'adapter_sha256':file_hash(self.adapter) if self.adapter else None}


class AdapterRegistry:
    """Approved adapters per role. Bound to base-model hash + adapter hash; anything else is ignored by runners."""
    def __init__(self,store,clock=time.time):self.s=store;self.clock=clock
    def _load(self):return self.s.state(REGISTRY_KEY,None)[0] or {'active':{},'history':[]}
    def _save(self,st):
        self.s.set_state(REGISTRY_KEY,st)
        home=getattr(self.s,'home',None)  # mirror for runners, which have no store handle
        if home is not None:
            (Path(home)/'config').mkdir(parents=True,exist_ok=True)
            atomic_write(Path(home)/MIRROR,json.dumps({r:{k:v[k] for k in ('path','sha256','base_model_sha256','batch_id','scale')} for r,v in st['active'].items() if v},indent=1))
    def activate(self,role,adapter_path,adapter_sha256,base_model_sha256,batch_id,scale=1.):
        p=Path(adapter_path)
        if not p.is_file() or file_hash(p)!=adapter_sha256:raise ValueError('Adapter-Datei fehlt oder Hash passt nicht')
        st=self._load();prev=st['active'].get(role)
        st['active'][role]={'path':str(p),'sha256':adapter_sha256,'base_model_sha256':base_model_sha256,'batch_id':batch_id,'scale':float(scale),'at':self.clock(),'previous':prev}
        st['history']=(st['history']+[{'kind':'ACTIVATE','role':role,'batch_id':batch_id,'at':self.clock()}])[-64:];self._save(st)
        return st['active'][role]
    def deactivate(self,role,batch_id=None):
        st=self._load();cur=st['active'].get(role)
        if not cur or (batch_id and cur['batch_id']!=batch_id):return None
        prev=cur.get('previous');st['active'][role]=prev if prev else None
        if not prev:st['active'].pop(role,None)
        st['history']=(st['history']+[{'kind':'ROLLBACK','role':role,'batch_id':cur['batch_id'],'at':self.clock()}])[-64:];self._save(st)
        return cur
    def rebind_bytes(self,role,adapter_sha256,note):
        """Same binding, new bytes after an in-place edit (e.g. `:forget` zeroed memory slots). No 'previous' entry is kept for
        the old bytes, so a later rollback can never bring a forgotten fact back."""
        st=self._load();cur=st['active'].get(role)
        if not cur:return None
        cur['sha256']=adapter_sha256;cur['at']=self.clock()
        st['history']=(st['history']+[{'kind':'REBIND','role':role,'batch_id':cur['batch_id'],'note':str(note)[:80],'at':self.clock()}])[-64:];self._save(st)
        return cur
    def for_runner(self,role,model_path):return runner_lora_args(getattr(self.s,'home','.'),role,model_path,self._load()['active'].get(role))
    def report(self):return self._load()

def runner_lora_args(home,role,model_path,cur=None):
    """[--lora-scaled path scale] only if an approved binding matches the exact model file and adapter bytes; else []."""
    if cur is None:
        try:cur=json.loads((Path(home)/MIRROR).read_text()).get(role)
        except (OSError,ValueError):return []
    if not cur:return []
    try:
        if file_hash(model_path)!=cur['base_model_sha256'] or file_hash(cur['path'])!=cur['sha256']:return []
    except OSError:return []
    return ['--lora-scaled',cur['path'],str(cur['scale'])]
