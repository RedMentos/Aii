"""WP-S3 sparse memory finetuning: a parametric fast memory for C3 (F3, §24.18 fast episodic parametric trace).

Retrofit (arXiv 2604.05248 idea, Lin et al. "continual learning via sparse memory finetuning"): a key-value memory
layer is added next to the FFN of one middle block of the frozen language model. Each token's FFN input queries the
memory, the top-k slots answer with a softmax-weighted sum of their values. Values start at zero, so the model is
bit-identical to the base until something is learned.

Learning touches only a few slots: for a new batch, slots are ranked by TF-IDF of their accesses
(tf = how often the batch's answer tokens hit the slot, idf = how rarely a background corpus of generic and
"near" prompts hits it) and only the top-t slots get gradient. Generic text keeps its slots untouched, which is
the mechanism the paper credits for far less forgetting than LoRA or full finetuning.

Pure numpy parts (tfidf_select) are always available; the torch parts load lazily. The trained artifact is the
memory state (keys, values, query projection, selected slots). Claim limit: llama.cpp has no memory-layer op, so
this path runs in torch (cloud/master) only; on the phone it needs a torch runtime or a native op (open).
"""
import json
import math
import time
from pathlib import Path
from .common import atomic_write,digest,dumps,file_hash

DEFAULTS={'slots':8192,'key_dim':64,'topk':32,'train_slots':128,'layer':None,'lr':.05,'max_steps':60,'target_ce':.05,'seed':13,
          'threads':4,'max_tokens':96,'train_keys':False,'anchor_weight':0.,'scale':1.,'background_tokens':24,'anchors_per_step':8,
          'mode':'keyed','keyed_slots':1024,'tau':.01,'margin':.02,'theta_min':.9,
          'entity_guard':False,'entity_width':12,'base_gguf':None,
          'system':None,'contexts':None,'guard_distinct':False,'guard_vocab':None,'guard_scope':'prompt'}
# system: write keys and measure in the live chat context (runtime system prompt), else bare user turn.
# contexts: extra system prompts ('' = bare turn) whose answer positions also get keyed slots (context augmentation).
# guard_distinct: entity-guard words only where they separate facts (document frequency 1 over the batch + guard_vocab, e.g. the
#   questions of the exact store), so 'favourite' no longer lets the 'favourite dish' slot fire on 'favourite colour'.
# guard_scope: 'prompt' = guard context is the whole prompt (system + exact blocks + question, as before); 'last_user' = only
#   the last user turn and the assistant header, so an exact block that mentions another fact does not open its slots.
#   Native: V13SMEM1 header field 6 = 0 off, 1 whole prompt, 2+m last turn after chat-marker token m (old readers: whole prompt).  # keyed r90 won the WP-S3 ablation
REVISION='wp-s3-sparse-memory-v1'
DELIVERY_SCHEMA='V13_SPARSE_DELIVERY_BINDINGS_V1'

def fact_item_bindings(items):
    """Exact authored training facts, never inferred from a slot's generated text."""
    return {str(i['memory_id']):{'prompt':i['prompt'],'target':i['target'],'source_ref':dict(i['source_ref'])}
            for i in items if i.get('kind')=='fact' and isinstance(i.get('memory_id'),str)
            and isinstance(i.get('prompt'),str) and isinstance(i.get('target'),str)
            and isinstance(i.get('source_ref'),dict)}
STOP=set('a an the of my me i you your is are am was do does did what which who whom whose when where why how name called tell please '
         'to in on at for with and or it this that be have has had can could would should most like'.split())

def entity_words(prompt):
    """Content words of a fact's question (entity guard keys): 'What is the name of my cat?' -> ['cat']."""
    import re
    return [w for w in re.findall(r"[a-z0-9]+",prompt.lower()) if w not in STOP and len(w)>1]

def guard_words(prompt,vocab=None):
    """Entity-guard words of a fact question. vocab=None: all content words (as before). With vocab (the other fact
    questions the memory must tell apart): only words no other question shares; if every word is shared, all of them."""
    own=entity_words(prompt)
    if vocab is None:return own
    other=[set(entity_words(q)) for q in dict.fromkeys(vocab) if q!=prompt]
    keep=[w for w in own if not any(w in o for o in other)]
    return keep or own

def guard_header(cfg,mark=None):
    """V13SMEM1 header field 6 (see DEFAULTS comment)."""
    if not cfg.get('entity_guard'):return 0
    if cfg.get('guard_scope','prompt')=='last_user':
        if mark is None or mark<0:raise ValueError('guard_scope last_user braucht das Chat-Marker-Token')
        return 2+int(mark)
    return 1

def scoped_context(ids,mark):
    """Tokens of the last user turn: from the second-to-last chat marker on (user turn + assistant header)."""
    if mark is None:return ids
    pos=[k for k,t in enumerate(ids) if t==mark]
    return ids[pos[-2]:] if len(pos)>=2 else ids

def entity_token_ids(tok,prompt,width,words=None):
    """First sub-token of each content word in its common spellings (leading space, capitalised)."""
    ids=[]
    for w in (entity_words(prompt) if words is None else words):
        for v in (' '+w,w,' '+w.capitalize(),w.capitalize()):
            t=tok(v,add_special_tokens=False)['input_ids']
            if t and t[0] not in ids:ids.append(t[0])
    return ids[:width]

def tfidf_select(batch_hits,background_hits,slots,t):
    """batch_hits: list of slot-index lists (one per batch token); background_hits: list of sets (one per background doc).
    Returns the top-t slots by tf * idf (idf = log((D+1)/(df+1))) and the scores used."""
    tf=[0]*slots;df=[0]*slots
    for hits in batch_hits:
        for s in hits:tf[s]+=1
    for doc in background_hits:
        for s in set(doc):df[s]+=1
    d=len(background_hits)
    score=[tf[s]*math.log((d+1)/(df[s]+1)) for s in range(slots)]
    order=sorted((s for s in range(slots) if tf[s]>0),key=lambda s:(-score[s],s))[:t]
    return order,{s:round(score[s],6) for s in order}

def _torch():
    import torch
    return torch

def build_memory(torch,hidden,cfg):
    """Memory layer module: q = W_q x; top-k over keys; out = scale * softmax(q.K_topk) @ V_topk. V starts at zero."""
    nn=torch.nn
    class MemoryLayer(nn.Module):
        def __init__(self):
            super().__init__()
            g=torch.Generator().manual_seed(int(cfg['seed']))
            self.wq=nn.Parameter(torch.randn(cfg['key_dim'],hidden,generator=g)/math.sqrt(hidden),requires_grad=False)
            self.keys=nn.Parameter(torch.randn(cfg['slots'],cfg['key_dim'],generator=g)/math.sqrt(cfg['key_dim']),requires_grad=bool(cfg['train_keys']))
            self.values=nn.Parameter(torch.zeros(cfg['slots'],hidden))
            self.topk=int(cfg['topk']);self.scale=float(cfg['scale']);self.record=None;self.record_q=None;self.mode=cfg['mode']
            if self.mode=='keyed':  # written keys in the full hidden space + per-slot radius (GRACE-style deferral)
                n=int(cfg['keyed_slots']);self.values=nn.Parameter(torch.zeros(n,hidden))
                self.register_buffer('hkeys',torch.zeros(n,hidden));self.register_buffer('theta',torch.ones(n));self.register_buffer('written',torch.zeros(n));self.register_buffer('mu',torch.zeros(hidden))
                self.tau=float(cfg['tau'])
                # Entity guard: a slot may only fire when one of its fact's content-word tokens is in the current context
                # ("my dog" must not recall the "my cat" slot even though their hidden states are ~0.99 cosine).
                self.register_buffer('ent',torch.full((n,int(cfg['entity_width'])),-1,dtype=torch.long));self.register_buffer('slot_item',torch.full((n,),-1,dtype=torch.long))
                self.guard=bool(cfg['entity_guard']);self.ctx=None;self.scope_mark=None
        def forward(self,x):
            if self.mode=='keyed':
                if self.record_q is not None:self.record_q.append(x.detach().reshape(-1,x.shape[-1]))
                qn=torch.nn.functional.normalize(x-self.mu,dim=-1)  # centred: raw hidden states are anisotropic
                c,idx=(qn@self.hkeys.t()).topk(min(self.topk,self.hkeys.shape[0]),dim=-1)
                g=torch.sigmoid((c-self.theta[idx])/self.tau)*self.written[idx]  # fires only inside a slot's radius
                if self.guard and self.ctx is not None:
                    e=self.ent[idx];ok=((e.unsqueeze(-1)==self.ctx).any(-1)).any(-1)|(e<0).all(-1)
                    g=g*ok.to(g.dtype)
                return self.scale*(g.unsqueeze(-1)*self.values[idx]).sum(-2)
            q=torch.nn.functional.normalize(x@self.wq.t(),dim=-1)*math.sqrt(self.wq.shape[0])
            s,idx=(q@self.keys.t()).topk(self.topk,dim=-1)
            if self.record is not None:self.record.append(idx.detach().reshape(-1,self.topk))
            w=torch.softmax(s,dim=-1)
            return self.scale*(w.unsqueeze(-1)*self.values[idx]).sum(-2)
    return MemoryLayer()

def attach(torch,model,cfg):
    """Wrap the FFN of the chosen block: ffn(x) + memory(x). Returns (memory, layer index)."""
    layers=model.model.layers;i=cfg['layer'] if cfg['layer'] is not None else len(layers)//2
    blk=layers[i];ff=getattr(blk,'feed_forward',None) or getattr(blk,'mlp')
    mem=build_memory(torch,model.config.hidden_size,cfg)
    class WithMemory(torch.nn.Module):
        def __init__(self):super().__init__();self.ff=ff;self.memory=mem
        def forward(self,x):return self.ff(x)+self.memory(x)
    if hasattr(blk,'feed_forward'):blk.feed_forward=WithMemory()
    else:blk.mlp=WithMemory()
    def ctx_hook(module,args,kwargs):  # context token set for the entity guard (prefill resets, decode appends)
        ids=kwargs.get('input_ids',args[0] if args else None)
        if ids is None or not hasattr(mem,'ctx'):return
        ids=ids.reshape(-1)
        if ids.numel()>1 and getattr(mem,'scope_mark',None) is not None:ids=torch.tensor(scoped_context(ids.tolist(),mem.scope_mark),dtype=ids.dtype)
        mem.ctx=ids.unique() if ids.numel()>1 or mem.ctx is None else torch.cat([mem.ctx,ids]).unique()
    model.register_forward_pre_hook(ctx_hook,with_kwargs=True)
    return mem,i

class SparseMemoryTrainer:
    method='sparse-memory-torch-cpu'
    def __init__(self,master_dir,work_dir,background=(),cfg=None,master_sha256=None,clock=time.time,negatives=()):
        """background: generic + near-miss-style prompts for idf (never the eval near-miss set). negatives (keyed mode):
        {'prompt','target'} pairs that must NOT trigger the new slots, e.g. the fact with its entity swapped."""
        self.master=Path(master_dir);self.work=Path(work_dir);self.background=list(background);self.negatives=list(negatives);self.cfg=dict(DEFAULTS,**(cfg or {}))
        self.master_sha=master_sha256;self.clock=clock;self.model=None;self.tok=None;self.memory=None;self.deployed_base=None
    def encode(self,prompt,target=None,system=False):
        system=self.cfg.get('system') if system is False else system
        tok=self.tok;msgs=([{'role':'system','content':system}] if system else [])+[{'role':'user','content':prompt}]
        p=tok.apply_chat_template(msgs,add_generation_prompt=True,tokenize=False)
        pid=tok(p,add_special_tokens=False)['input_ids']
        if target is None:return pid,None
        tid=tok(str(target)+'<|im_end|>',add_special_tokens=False)['input_ids'];full=pid+tid
        ids=full[-self.cfg['max_tokens']:];cut=len(full)-len(ids)
        return ids,([-100]*len(pid)+tid)[cut:]
    def load(self):
        torch=_torch()
        from transformers import AutoModelForCausalLM,AutoTokenizer
        torch.set_num_threads(int(self.cfg['threads']));torch.manual_seed(int(self.cfg['seed']))
        if self.master_sha and file_hash(self.master/'model.safetensors')!=self.master_sha:raise ValueError('Master-Gewichte: SHA-256 passt nicht')
        self.tok=AutoTokenizer.from_pretrained(str(self.master))
        self.model=AutoModelForCausalLM.from_pretrained(str(self.master),dtype=torch.float32).eval()
        for p in self.model.parameters():p.requires_grad_(False)
        if self.cfg.get('base_gguf'):  # write keys on the deployed (dequantized Q4) weights, so native lookups see the same hidden states
            from .lora_trainer import LoraTrainer
            self.deployed_base=LoraTrainer(self.master,self.work)._load_gguf_weights(torch,self.model,self.cfg['base_gguf'])
        self.memory,self.layer=attach(torch,self.model,self.cfg)
        if self.cfg.get('guard_scope','prompt')=='last_user':
            self.memory.scope_mark=self.tok.convert_tokens_to_ids('<|im_start|>');self.cfg['guard_mark']=int(self.memory.scope_mark)
        return self
    def _hits(self,ids,positions=None):
        torch=_torch();self.memory.record=[]
        with torch.no_grad():self.model(torch.tensor([ids]))
        rows=self.memory.record[0];self.memory.record=None
        sel=range(rows.shape[0]) if positions is None else positions
        return [rows[i].tolist() for i in sel]
    def _queries(self,ids):
        torch=_torch();self.memory.record_q=[]
        with torch.no_grad():self.model(torch.tensor([ids]))
        q=self.memory.record_q[0];self.memory.record_q=None;return q
    def _write_keys(self,data,seqs,items=()):
        """Keyed mode: one slot per answer-predicting position, key = its normalized hidden state, radius = just above the
        closest background position (generic + near prompts with the base continuation), so the slot stays silent there."""
        torch=_torch();m=self.memory;cfg=self.cfg
        neg=[self.encode(n['prompt'],n['target'])[0] for n in self.negatives]
        raw=torch.cat([self._queries(ids) for ids in seqs+neg]) if seqs or neg else torch.zeros(0,m.hkeys.shape[1])
        if raw.shape[0] and not bool(m.written.any()):
            with torch.no_grad():m.mu.copy_(raw.mean(0))
        norm=lambda v:torch.nn.functional.normalize(v-m.mu,dim=-1);bg=norm(raw)
        free=int((m.written==0).nonzero()[0]) if bool((m.written==0).any()) else None;chosen=[];radius={}
        for n,(ids,labels) in enumerate(data):
            q=norm(self._queries(ids))
            words=guard_words(items[n]['prompt'],[i['prompt'] for i in items]+list(cfg.get('guard_vocab') or [])) if n<len(items) and cfg.get('guard_distinct') else None
            ent=entity_token_ids(self.tok,items[n]['prompt'],int(cfg['entity_width']),words) if n<len(items) else []
            for k in [k-1 for k,l in enumerate(labels) if l!=-100 and k>0]:
                if free is None or free>=m.hkeys.shape[0]:raise ValueError('Memory-Slots voll')
                key=q[k];th=float((bg@key).max()) if bg.shape[0] else 0.
                th=min(.999,max(float(cfg['theta_min']),th+float(cfg['margin'])))
                with torch.no_grad():
                    m.hkeys[free]=key;m.theta[free]=th;m.written[free]=1.;m.slot_item[free]=n
                    m.ent[free]=-1
                    if ent:m.ent[free,:len(ent)]=torch.tensor(ent)
                chosen.append(free);radius[free]=round(th,4);free+=1
        mask=torch.zeros(m.values.shape[0],1);mask[chosen]=1.
        return chosen,dict(list(radius.items())[:5]),mask
    def fit(self,items,cancel=None,deadline=None):
        """items: [{'prompt','target'}]. Trains only TF-IDF-selected memory slots. Returns metrics + artifact path."""
        if not items:return {'artifact':None,'metrics':{'reason':'EMPTY_BATCH'}}
        try:torch=_torch()
        except ImportError:return {'artifact':None,'metrics':{'reason':'NO_TORCH'}}
        if self.model is None:self.load()
        t0=time.monotonic();cfg=self.cfg
        ctxs=[cfg.get('system')]+[c for c in (cfg.get('contexts') or []) if c!=cfg.get('system')]
        if len(ctxs)>1:items=[dict(i,_system=c) for i in items for c in ctxs]  # same memory_id per variant: :forget hits all
        data=[self.encode(i['prompt'],i['target'],i.get('_system',False)) for i in items];batch_hits=[]
        if cfg['mode']!='keyed':
            for ids,labels in data:
                pos=[k-1 for k,l in enumerate(labels) if l!=-100 and k>0]  # the token positions that predict answer tokens
                for h in self._hits(ids,pos):batch_hits.append(h)
        # Background docs = prompt + the base model's own continuation, so answer-position slots of generic and
        # near ("my dog" vs "my cat") questions count as common and stay frozen. Values are still zero here.
        seqs=[]
        for p in [(b,c) for b in self.background for c in ctxs]:
            ids=self.encode(p[0],system=p[1])[0]
            with torch.no_grad():o=self.model.generate(torch.tensor([ids]),attention_mask=torch.ones(1,len(ids),dtype=torch.long),max_new_tokens=int(cfg['background_tokens']),do_sample=False,pad_token_id=0)
            seqs.append(o[0].tolist())
        if cfg['mode']=='keyed':chosen,scores,mask=self._write_keys(data,seqs,items)
        else:
            background=[set(s for row in self._hits(ids) for s in row) for ids in seqs]
            chosen,scores=tfidf_select(batch_hits,background,cfg['slots'],int(cfg['train_slots']))
            mask=torch.zeros(cfg['slots'],1);mask[chosen]=1.
        params=[self.memory.values]+([self.memory.keys] if cfg['train_keys'] else [])
        opt=torch.optim.Adam(params,lr=float(cfg['lr']))
        anchors=[]
        if cfg['anchor_weight']>0:
            with torch.no_grad():
                for ids in seqs:anchors.append((ids,torch.log_softmax(self.model(torch.tensor([ids])).logits[0],-1)))
        g=torch.Generator().manual_seed(int(cfg['seed']))
        hist=[];step=0
        for step in range(1,int(cfg['max_steps'])+1):
            if cancel is not None and cancel.is_set():raise RuntimeError('cancelled')
            if deadline is not None and time.monotonic()>deadline:break
            opt.zero_grad();ce=0.
            for ids,labels in data:
                out=self.model(torch.tensor([ids]),labels=torch.tensor([labels]));(out.loss/len(data)).backward();ce+=float(out.loss.detach())/len(data)
            kl=0.;k=min(int(cfg['anchors_per_step']),len(anchors))
            for j in (torch.randperm(len(anchors),generator=g)[:k].tolist() if anchors else []):
                ids,base=anchors[j];cur=torch.log_softmax(self.model(torch.tensor([ids])).logits[0],-1);x=(base.exp()*(base-cur)).sum(-1).mean()
                (float(cfg['anchor_weight'])*x/k).backward();kl+=float(x.detach())/k
            self.memory.values.grad*=mask
            if cfg['train_keys'] and self.memory.keys.grad is not None:self.memory.keys.grad*=mask
            opt.step();hist.append({'step':step,'ce':round(ce,5),'anchor_kl':round(kl,6)})
            if ce<=float(cfg['target_ce']):break
        self.work.mkdir(parents=True,exist_ok=True)
        key=digest(dumps([[i['prompt'],i['target'],i.get('_system')] for i in items]+[{k:v for k,v in cfg.items() if k!='threads'}]))[:24]
        path=self.work/('memory-'+key+'.pt')
        slot_items={}
        if cfg['mode']=='keyed':
            for sl in chosen:slot_items[sl]=items[int(self.memory.slot_item[sl])].get('memory_id',int(self.memory.slot_item[sl]))
        torch.save({'revision':REVISION,'layer':self.layer,'cfg':cfg,'state':{k:v.detach() for k,v in self.memory.state_dict().items()},'slots':chosen,'slot_items':slot_items,'item_bindings':fact_item_bindings(items)},path)
        changed=int((self.memory.values.data.abs().sum(-1)>0).sum())
        return {'artifact':str(path),'hash':file_hash(path),'method':self.method,
                'metrics':{'steps':step,'final_ce':hist[-1]['ce'] if hist else None,'history':hist[-5:],'selected_slots':len(chosen),'changed_slots':changed,
                           'trainable_parameters':len(chosen)*self.model.config.hidden_size,'layer':self.layer,'seconds':round(time.monotonic()-t0,2),
                           'top_scores':scores,'background_docs':len(seqs),'mode':cfg['mode']}}
    def load_artifact(self,path):
        torch=_torch();st=torch.load(path)
        if st['revision']!=REVISION:raise ValueError('Memory-Artefakt passt nicht')
        self.memory.load_state_dict(st['state'],strict=False)  # older artifacts lack the entity-guard buffers
        return st['slots']

def forget(path,memory_ids,out=None):
    """`:forget`: zero the slots written for these memories (value, gate, key) and save a new artifact. Returns slot count."""
    torch=_torch();st=torch.load(path);ids={str(m) for m in memory_ids}
    slots=[int(s) for s,m in st.get('slot_items',{}).items() if str(m) in ids]
    for s in slots:
        for k in ('values','hkeys'):st['state'][k][s]=0
        st['state']['written'][s]=0;st['state']['ent'][s]=-1
    st['slot_items']={s:m for s,m in st['slot_items'].items() if int(s) not in slots};st['slots']=[s for s in st['slots'] if int(s) not in slots]
    st['forgotten']=sorted(set(st.get('forgotten',[]))|ids)
    st['item_bindings']={k:v for k,v in st.get('item_bindings',{}).items() if str(k) not in ids}
    target=Path(out or path);tmp=target.with_suffix('.tmp');torch.save(st,tmp);tmp.replace(target)
    return len(slots)

def export_native(path,out):
    """Write the written keyed slots as V13SMEM1 for scripts/native_memory_hook.cpp (mu, keys, theta, values, entity tokens)."""
    import struct,numpy as np
    torch=_torch();st=torch.load(path);cfg=st['cfg'];S=st['state']
    if cfg.get('mode')!='keyed':raise ValueError('Nativ nur für keyed')
    w=(S['written']>0).nonzero().reshape(-1)
    f=lambda t:np.ascontiguousarray(t.detach().float().numpy(),dtype='<f4').tobytes()
    ent=S.get('ent',torch.full((S['written'].shape[0],1),-1,dtype=torch.long))[w]
    with open(out,'wb') as fh:
        fh.write(b'V13SMEM1');fh.write(struct.pack('<6i',int(st['layer']),int(S['mu'].shape[0]),int(w.numel()),int(ent.shape[1]),int(cfg['topk']),guard_header(cfg,cfg.get('guard_mark'))))
        fh.write(struct.pack('<2f',float(cfg['tau']),float(cfg['scale'])))
        fh.write(f(S['mu']));fh.write(f(S['hkeys'][w]));fh.write(f(S['theta'][w]));fh.write(f(S['values'][w]))
        fh.write(np.ascontiguousarray(ent.numpy(),dtype='<i4').tobytes())
    si={int(k):v for k,v in st.get('slot_items',{}).items()}
    side={'schema':DELIVERY_SCHEMA,'native_sha256':file_hash(out),'source_pt':str(Path(path).resolve()),
          'rows':[si.get(int(s)) for s in w.tolist()],'forgotten':sorted(st.get('forgotten',[])),
          'item_bindings':st.get('item_bindings',{})}
    atomic_write(native_items_path(out),json.dumps(side))
    return {'slots':int(w.numel()),'layer':int(st['layer']),'bytes':Path(out).stat().st_size,'sha256':file_hash(out)}

def native_items_path(path):return Path(str(path)+'.items.json')

def forget_native(path,memory_ids):
    """`:forget` on the phone without torch: in a V13SMEM1 file zero the key/value rows of these memories and set their
    threshold out of reach (gate 0), using the row map written by export_native. Rewrites in place; returns rows zeroed."""
    import struct,numpy as np
    path=Path(path);sp=native_items_path(path);side=json.loads(sp.read_text());ids={str(m) for m in memory_ids}
    rows=[r for r,m in enumerate(side['rows']) if m is not None and str(m) in ids]
    if not rows:return 0
    b=bytearray(path.read_bytes());lay,hid,n,ew,topk,g=struct.unpack_from('<6i',b,8);o=8+24+8
    mu=o;keys=mu+4*hid;theta=keys+4*n*hid;values=theta+4*n;ent=values+4*n*hid
    for r in rows:
        b[keys+4*hid*r:keys+4*hid*(r+1)]=bytes(4*hid);b[values+4*hid*r:values+4*hid*(r+1)]=bytes(4*hid)
        struct.pack_into('<f',b,theta+4*r,1e9);b[ent+4*ew*r:ent+4*ew*(r+1)]=np.full(ew,-1,dtype='<i4').tobytes()
        side['rows'][r]=None
    side['forgotten']=sorted(set(side.get('forgotten',[]))|ids)
    side['item_bindings']={k:v for k,v in side.get('item_bindings',{}).items() if str(k) not in ids}
    tmp=path.with_suffix('.tmp');tmp.write_bytes(bytes(b));tmp.replace(path)
    if side.get('schema')==DELIVERY_SCHEMA:
        side['native_sha256']=file_hash(path)
    atomic_write(sp,json.dumps(side))
    return len(rows)

def report(path):
    torch=_torch();st=torch.load(path)
    return {'revision':st['revision'],'layer':st['layer'],'slots':len(st['slots']),'cfg':{k:st['cfg'][k] for k in ('slots','key_dim','topk','train_slots')}}
