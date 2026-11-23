"""WP-S3 in the AG6 pipeline: sparse memory (keyed slots + entity guard) as a WeightConsolidation trainer.

SparseMemoryAG6Trainer.fit(items, base_generation, cancel, deadline) trains v13.sparse_memory on the batch and measures
on the same torch model, before (memory values zero = exact base) and after:
  learned recall on the batch prompts, retention probes + forgetting, KL(base||candidate) on probe continuations,
  near-miss leak on automatically swapped questions ("my cat" -> "my friend", lora_trainer.locality_prompts).
It returns the gate inputs (eval) that WeightConsolidation.train_and_gate() uses. An approved artifact is bound through
AdapterRegistry under role 'C3_LANGUAGE#sparse_memory' as a native V13SMEM1 .bin (row map .bin.items.json, training
state .pt next to it). The live chat serves it through the patched llama-server-mem (v13/memory_server.py) only when
binary, model and file hashes match; otherwise the normal runner answers without the memory.
`forget_memory()` zeroes the slots of one memory in the bound artifact (`:forget`).
"""
import json,time
from pathlib import Path
from .common import file_hash,digest,dumps
from .lora_trainer import answer_hit,LoraTrainer

ROLE='C3_LANGUAGE#sparse_memory'

def merge_training_lineage(old,new):
    """Preserve accumulated slot ownership and immutable authored fact bindings."""
    bindings=dict(old.get('item_bindings',{}))
    for mid,binding in new.get('item_bindings',{}).items():
        if mid in bindings and bindings[mid]!=binding:raise ValueError('Sparse fact binding changed')
        bindings[mid]=binding
    forgotten=sorted(set(old.get('forgotten',[]))|set(new.get('forgotten',[])))
    new['slot_items']={**old.get('slot_items',{}),**new.get('slot_items',{})}
    new['slots']=list(old.get('slots',[]))+list(new.get('slots',[]))
    new['forgotten']=forgotten;new['item_bindings']={k:v for k,v in bindings.items() if k not in forgotten}
    return new

FRESH_TASK_CONTEXT={"action_type":None,"external_tool_execution":False,"task_request":None,"unresolved_observer_hypotheses":[]}

def live_system(cfg=None,memories=None):
    """The system message runtime._turn sends C3 in a fresh chat (stable layers + task-context block), optionally with the
    recalled-corrections block. Keys written in this context fire in the live chat; keys from a bare user turn mostly do not
    (bench-results/fast-trace-20261010: bare-written trace 1/8 in the live prompt)."""
    from .prompts import text as prompt
    cfg=cfg or {}
    s=prompt(cfg,'system')+' '+prompt(cfg,'conduct')+' '+prompt(cfg,'answer_rules')
    if memories:s+='\n'+prompt(cfg,'memories')+dumps(memories)
    return s+'\n'+prompt(cfg,'task_context')+dumps(FRESH_TASK_CONTEXT)

def answer_keys(item):
    """Words of the target that the question does not contain (e.g. 'Mitzi'), used for recall/leak checks."""
    import re
    if item.get('answer_keys'):return item['answer_keys']
    from .sparse_memory import STOP
    q=set(re.findall(r'[a-z0-9]+',item['prompt'].lower()))
    words=[w for w in re.findall(r'[A-Za-z0-9]+',item['target']) if w.lower() not in q and w.lower() not in STOP and len(w)>1]
    if not words:return [item['target']]
    first=(re.findall(r'[A-Za-z0-9]+',item['target']) or [''])[0]
    named=[w for w in words if (w[0].isupper() or w[0].isdigit()) and w!=first]  # names/numbers, not the sentence start
    return [(named or [max(words,key=len)])[0].lower()]

class SparseMemoryAG6Trainer:
    method='sparse-memory-keyed-guard';role=ROLE
    def __init__(self,master_dir,work_dir,background=(),probes=(),cfg=None,master_sha256=None,swaps=2,store=None):
        self.master=Path(master_dir);self.work=Path(work_dir);self.background=list(background);self.probes=list(probes)
        self.cfg=dict({'entity_guard':True},**(cfg or {}));self.master_sha=master_sha256;self.swaps=swaps;self.store=store;self.last=None
    def _measure(self,tr,items,near):
        import torch
        def gen(p,n=32):
            ids=tr.encode(p)[0]
            with torch.no_grad():o=tr.model.generate(torch.tensor([ids]),attention_mask=torch.ones(1,len(ids),dtype=torch.long),max_new_tokens=n,do_sample=False,pad_token_id=0)
            return tr.tok.decode(o[0][len(ids):],skip_special_tokens=True)
        probes=[(p,answer_hit(gen(p['prompt']),p['expect'])) for p in self.probes if p.get('expect')]
        return {'learned':[answer_hit(gen(i['prompt']),answer_keys(i)) for i in items],
                'near':[answer_hit(gen(q),answer_keys(i)) for q,i in near],
                'probes':{p['prompt']:ok for p,ok in probes},'unseen':{p['prompt']:ok for p,ok in probes if p.get('unseen')}}
    def _logp(self,tr,seqs):
        import torch
        with torch.no_grad():return [torch.log_softmax(tr.model(torch.tensor([s])).logits[0],-1)[n-1:-1] for n,s in seqs]
    def fit(self,items,base_generation,cancel=None,deadline=None):
        if not items:return {'artifact':None,'hash':None,'method':self.method,'metrics':{'reason':'EMPTY_BATCH'}}
        try:import torch
        except ImportError:return {'artifact':None,'hash':None,'method':self.method,'metrics':{'reason':'NO_TORCH'}}
        from .sparse_memory import SparseMemoryTrainer
        t0=time.monotonic()
        tr=SparseMemoryTrainer(self.master,self.work,background=self.background+LoraTrainer.locality_prompts(items,self.swaps),cfg=self.cfg,master_sha256=self.master_sha).load()
        prev=None
        if self.store is not None:  # memory accumulates: continue on the currently bound artifact (new slots after the old ones)
            from .lora_trainer import AdapterRegistry
            cur=AdapterRegistry(self.store).report().get('active',{}).get(ROLE)
            if cur and Path(cur['path']).is_file() and file_hash(cur['path'])==cur['sha256']:
                pt=source_pt(cur['path'])
                if pt:tr.load_artifact(pt);prev=pt
        near=[]
        for i in items:  # near-miss = swapped questions with a different noun pool offset than the background swaps
            for q in LoraTrainer.locality_prompts([i],self.swaps+2)[self.swaps:]:near.append((q,i))
        seqs=[]
        for p in self.probes:
            ids=tr.encode(p['prompt'])[0]
            with torch.no_grad():o=tr.model.generate(torch.tensor([ids]),attention_mask=torch.ones(1,len(ids),dtype=torch.long),max_new_tokens=16,do_sample=False,pad_token_id=0)
            seqs.append((len(ids),o[0].tolist()))
        base_lp=self._logp(tr,seqs);before=self._measure(tr,items,near)  # values are zero: exact base
        out=tr.fit(items,cancel=cancel,deadline=deadline)
        if prev and out.get('artifact'):
            old=torch.load(prev,weights_only=False);new=torch.load(out['artifact'],weights_only=False)
            merge_training_lineage(old,new)
            new['parent']=prev;torch.save(new,out['artifact']);out['hash']=file_hash(out['artifact'])
        native=None
        if out.get('artifact'):  # bound + served artifact = the native V13SMEM1 file (llama-server-mem); .pt stays for training
            from .sparse_memory import export_native
            b=Path(out['artifact']).with_suffix('.bin');native=export_native(out['artifact'],b);out['artifact']=str(b);out['hash']=native['sha256']
        after=self._measure(tr,items,near);cand_lp=self._logp(tr,seqs)
        kls=[float((b.exp()*(b-c)).sum(-1).mean()) for b,c in zip(base_lp,cand_lp)]
        rate=lambda d:sum(d.values())/len(d) if d else None
        ok=[k for k,v in before['probes'].items() if v];forgot=[k for k in ok if not after['probes'][k]]
        mean=lambda v:sum(v)/len(v) if v else None
        ev={'base_eval':{'overall':rate(before['probes']),'unseen':rate(before['unseen']),'near_miss_leak':mean(before['near'])},
            'candidate_eval':{'overall':rate(after['probes']),'unseen':rate(after['unseen']),'near_miss_leak':mean(after['near']),
                              'forgetting':{'rate':len(forgot)/len(ok) if ok else None,'forgotten':forgot}},
            'learned_recall':mean(after['learned'])}
        model_sha=(tr.deployed_base or {}).get('sha256') or file_hash(self.master/'model.safetensors')
        m=dict(out.get('metrics',{}),kl_to_base=mean(kls),kl_source='torch_'+('deployed_q4' if tr.deployed_base else 'master'),base_recall=mean(before['learned']),
               near_miss_prompts=len(near),seconds_total=round(time.monotonic()-t0,2),
               native=native,deployed={'model_sha256':model_sha,'path':'llama-server-mem (V13_MEMORY_FILE, v13/memory_server.py)','learned_recall':ev['learned_recall']})
        self.last={'artifact':out.get('artifact'),'hash':out.get('hash'),'method':self.method,'metrics':m,'eval':ev}
        return self.last

def source_pt(path):
    """Training state (.pt) behind a bound artifact: the .bin row map names it; a .pt binding (older) is its own source."""
    path=Path(path)
    if path.suffix!='.bin':return str(path)
    from .sparse_memory import native_items_path
    try:pt=json.loads(native_items_path(path).read_text()).get('source_pt')
    except (OSError,ValueError):return None
    return pt if pt and Path(pt).is_file() else None

def _forget_file(path,memory_id):
    """Zero one memory in a bound file: .bin with numpy only (phone), plus its .pt training state when torch is there."""
    from .sparse_memory import forget,forget_native
    path=Path(path);n=0
    if path.suffix=='.bin':
        n=forget_native(path,[memory_id]);pt=source_pt(path)
        if pt:
            try:forget(pt,[memory_id])
            except ImportError:pass  # no torch: the .pt is only used for later training, which needs torch anyway
        return n
    return forget(path,[memory_id])

def forget_memory(store,memory_id):
    """Zero the slots of `memory_id` in the bound sparse-memory artifact, re-bind the new bytes. Returns slots zeroed (0 = none)."""
    from .lora_trainer import AdapterRegistry
    reg=AdapterRegistry(store);cur=reg.report().get('active',{}).get(ROLE)
    if not cur or not Path(cur['path']).is_file():return 0
    n=_forget_file(cur['path'],memory_id)
    if n:reg.rebind_bytes(ROLE,file_hash(cur['path']),'forget '+str(memory_id))
    p=cur.get('previous')  # rollback targets must not bring the fact back either
    while p:
        if Path(p['path']).is_file():_forget_file(p['path'],memory_id)
        p=p.get('previous')
    if cur.get('previous'):
        st=reg._load();c=st['active'][ROLE];q=c.get('previous')
        while q:
            if Path(q['path']).is_file():
                q['sha256']=file_hash(q['path']);reg._bind_sidecar(q)
            q=q.get('previous')
        reg._save(st)
    store.log('sparse_memory_forget',None,{'memory_id':memory_id,'slots':n})
    return n

def prune_inactive(store):
    """§9.5 'redundant fast traces vanish': slots of memories the user superseded (a newer correction for the same key set
    the old row inactive) or deleted are zeroed in the bound memory, so the live chat cannot answer with the old value.
    Only ids of the memories table count (rating:/bench ids are kept). Returns {memory_id: slots}."""
    from .lora_trainer import AdapterRegistry
    from .sparse_memory import native_items_path
    cur=AdapterRegistry(store).report().get('active',{}).get(ROLE)
    if not cur or not Path(cur['path']).is_file():return {}
    path=Path(cur['path'])
    if path.suffix=='.bin':
        try:ids={m for m in json.loads(native_items_path(path).read_text())['rows'] if m}
        except (OSError,ValueError,KeyError):return {}
    else:
        try:
            import torch
            ids={str(m) for m in torch.load(path,weights_only=False).get('slot_items',{}).values()}
        except Exception:return {}
    stale=[]
    for m in sorted(ids):
        r=store.one('SELECT active FROM memories WHERE id=?',(m,))
        if (r and not r['active']) or (r is None and str(m).startswith('mem_')):stale.append(m)
    out={}
    for m in stale:
        n=forget_memory(store,m)
        if n:out[m]=n
    if out:store.log('sparse_memory_prune',None,{'memories':out})
    return out

def check_forget(store,memory_id):
    """Before `:forget`: a fact inside an active LoRA adapter cannot be removed from it (no false unlearning claim), so the
    user must roll that batch back first. Sparse-memory slots can be zeroed, so they never block."""
    from .lora_trainer import AdapterRegistry
    st=(store.state('G6_WEIGHT_CONSOLIDATION',None)[0] or {}).get('batches',{})
    active=AdapterRegistry(store).report().get('active',{})
    for role,cur in active.items():
        if not cur or role==ROLE:continue
        b=st.get(cur.get('batch_id'))
        if b and any(i.get('memory_id')==memory_id for i in b.get('items',[])):
            raise ValueError('Fakt steckt im aktiven Adapter %s (Batch %s). Zuerst Rollback dieses Batches, dann :forget.'%(role,cur['batch_id']))
