"""WP-AG6 in the live runtime: which trainer turns a staged batch into a gated candidate.

Before this, Growth always used NullTrainer, so a nightly batch could only end as NO_TRAINER even when the
WP-S6/WP-S3 trainers were installed. select() picks, per user choice (`:growth trainer ...`):
  lora   lora_trainer.LoraTrainer on the HF master of C3, trained on the dequantized deployed GGUF, gated on the
         deployed llama.cpp path (LlamaCppEvaluator: recall, retention probes, near-miss leak, top-k KL). An approved
         adapter is served by the live runner (`--lora-scaled`, hash-bound), so approval changes real answers.
  sparse memory_trainer.SparseMemoryAG6Trainer (keyed slots + entity guard). Measured lower leak / no forgetting
         (bench-results/memory-350m-20261010). An approved memory is served live by bin/llama-server-mem
         (v13/memory_server.py, hash-bound like the adapter); without that build it is stored but not served.
  none   NullTrainer (honest NO_TRAINER).
  auto   (default) lora when master + torch + runner + C3 GGUF are present, else none. sparse is never chosen
         automatically: in the live chat prompt the trace alone matches exact retrieval (8/8) but exact + trace together
         is worse (7/8, leak .8; bench-results/fast-trace-20261010), so it stays an explicit `:growth trainer sparse`.
Gate inputs come from the trainer's own evaluation; nothing is activated without the user (weights.approve).
"""
import json
import os
from pathlib import Path
from ..common import file_hash
from .base import StateBox

KEY='G6_TRAINER_CHOICE';REVISION='g6-trainer-v1'
KINDS=('auto','lora','sparse','none')
ROLE='C3_LANGUAGE'

# Live LoRA values measured on the deployed path (bench-results/ag6-live-20261010, LFM2.5-350M Q4, 8 facts, 32 probes,
# 48 anchors): bench defaults (lr 1e-3, anchor 1, all targets) KL .107 -> GATE_FAIL; lr 3e-4/anchor 4 all targets 2/31
# forgotten; FFN only (w1-w3) + anchor 8 passed the gate (0 forgotten, leak 0, KL .014). lora_trainer.DEFAULTS stay the
# bench defaults; per-device overrides are stored with the choice (`:growth trainer cfg`, scripts/ag6_live_bench.py --cfg).
LIVE_LORA={'lr':3e-4,'anchor_weight':8.,'anchors_per_step':16,'targets':('w1','w2','w3')}

def _box(store):return StateBox(store,KEY,REVISION,lambda:{'kind':'auto','master':None,'master_sha256':None})

def probes(app=None):
    p=Path(app or Path(__file__).resolve().parents[2])/'specs/ag6-probes.json'
    d=json.loads(p.read_text());return d['anchors'],d['probes']

def _torch(kind='lora'):
    """Python stack of the trainer: LoRA needs peft; both read the deployed GGUF (gguf)."""
    import importlib.util as u
    need=('torch','transformers','gguf')+(('peft',) if kind=='lora' else ())
    return all(u.find_spec(m) is not None for m in need)

def arch_match(master,gguf_path):
    """Master (HF config) and deployed GGUF must be the same network: width and depth equal. None = cannot check
    (no gguf library); the trainer's own dequantize step then still fails loudly on a shape mismatch."""
    try:
        import gguf
        cfg=json.loads((Path(master)/'config.json').read_text());r=gguf.GGUFReader(str(gguf_path))
        arch=r.fields['general.architecture'].contents()
        width=r.fields[arch+'.embedding_length'].contents();depth=r.fields[arch+'.block_count'].contents()
        return int(width)==int(cfg.get('hidden_size',-1)) and int(depth)==int(cfg.get('num_hidden_layers',-1))
    except ImportError:return None
    except Exception:return False

def requirements(runtime,state=None):
    """What a real trainer needs on this device; each entry True/False plus paths."""
    st=state or _box(runtime.store).load()[0]
    master=Path(st['master']) if st['master'] else Path(runtime.home)/'models/master'/ROLE
    try:gguf=runtime.models.path_for(ROLE)
    except Exception:gguf=None
    server=Path(os.environ.get('V13_LLAMA_SERVER',str(Path(runtime.home)/'bin/llama-server')))
    ok=(master/'model.safetensors').is_file() and (master/'config.json').is_file()
    match=arch_match(master,gguf) if ok and gguf else None
    # C3 was switched 230M -> 350M once (WP-G): a stale master must not train against a different deployed body.
    return {'master':str(master),'master_ok':ok and match is not False,'arch_match':match,
            'torch':_torch('lora'),'torch_sparse':_torch('sparse'),'c3_gguf':str(gguf) if gguf else None,'runner':str(server),'runner_ok':server.is_file(),
            'memory_server_ok':_memory_server_ok(runtime.home)}

def _memory_server_ok(home):
    """bin/llama-server-mem built by v13.memory_server and unchanged since (manifest hash)."""
    try:
        from ..memory_server import MANIFEST
        m=json.loads((Path(home)/MANIFEST).read_text());b=Path(home)/'bin/llama-server-mem'
        return b.is_file() and file_hash(b)==m.get('binary_sha256')
    except (OSError,ValueError):return False

class LiveNearMissEvaluator:
    """LlamaCppEvaluator whose near-miss questions are derived from the batch (swapped nouns), like the sparse trainer.
    With a drift meter (WP-S5 drift.Drift) it also measures KL on the FROZEN generic probes (specs/drift-probes.json,
    never trained on, hash-pinned) on the same deployed server; weights.gate/approve check that report."""
    def __init__(self,inner,swaps=2,drift=None):self.inner=inner;self.swaps=swaps;self.drift=drift
    def evaluate(self,items,probes_,cancel=None,deadline=None):
        from ..lora_trainer import LoraTrainer
        from ..memory_trainer import answer_keys
        near=[(q,answer_keys(i)) for i in items for q in LoraTrainer.locality_prompts([i],self.swaps+2)[self.swaps:]]
        rep=self.inner.evaluate(items,probes_,cancel=cancel,deadline=deadline,near_miss=near)
        # weights.gate() checks specificity from candidate_eval/base_eval; LlamaCppEvaluator reports the leak at top level.
        rows=(rep.get('rows') or {}).get('near_miss') or []
        if rows:
            rep['base_eval']=dict(rep['base_eval'],near_miss_leak=sum(r['base'] for r in rows)/len(rows))
            rep['candidate_eval']=dict(rep['candidate_eval'],near_miss_leak=sum(r['candidate'] for r in rows)/len(rows))
        if self.drift is not None:
            try:rep['wp_s5_drift']=self.drift.measure_lm(ROLE,self.inner)
            except ValueError as exc:rep['wp_s5_drift']={'error':str(exc)[:200]}  # e.g. probe file changed without refreeze: gate fails
        return rep
    def close(self):self.inner.close()

def build(runtime,kind=None):
    """Return (trainer, info). Never raises for a missing piece: falls back to NullTrainer with the reason."""
    from .weights import NullTrainer
    st=_box(runtime.store).load()[0];kind=kind or st['kind'];req=requirements(runtime,st)
    want=kind
    if kind=='auto':want='lora' if req['master_ok'] and req['torch'] and req['runner_ok'] and req['c3_gguf'] else 'none'
    info={'choice':kind,'active':want,'requirements':req}
    if want=='none':return NullTrainer(),info
    missing=[k for k in (('master_ok','torch_sparse','c3_gguf') if want=='sparse' else ('master_ok','torch','c3_gguf','runner_ok')) if not req[k]]
    if missing:info['active']='none';info['missing']=missing;return NullTrainer(),info
    anchors,probe=probes();work=Path(runtime.home)/'training/ag6'/want;work.mkdir(parents=True,exist_ok=True)
    threads=int(runtime.cfg.get('threads',4));sha=st['master_sha256']
    if want=='lora':
        from ..lora_trainer import LoraTrainer,LlamaCppEvaluator
        from ..drift import Drift
        ev=lambda path:LiveNearMissEvaluator(LlamaCppEvaluator(req['runner'],req['c3_gguf'],path,threads=threads,log=str(Path(runtime.home)/'logs/ag6-eval.log')),
                                             drift=Drift(runtime.store,runtime.cfg))
        cfg=dict(LIVE_LORA,**(st.get('lora_cfg') or {}),threads=threads,base_gguf=req['c3_gguf']);info['lora_cfg']={k:v for k,v in cfg.items() if k!='base_gguf'}
        t=LoraTrainer(req['master'],work,master_sha256=sha,anchors=anchors,probes=probe,cfg=cfg,evaluator=ev)
        t.role=ROLE;info['served_live']=True;return t,info
    from ..memory_trainer import SparseMemoryAG6Trainer,live_system
    t=SparseMemoryAG6Trainer(req['master'],work,background=anchors,probes=probe,master_sha256=sha,store=runtime.store,
                             cfg={'threads':threads,'base_gguf':req['c3_gguf'],'entity_guard':True,
                                  'system':live_system(runtime.cfg),'contexts':[''],'max_tokens':256})  # keys in the live chat context
    info['served_live']=bool(req['memory_server_ok'])
    if not info['served_live']:info['note']='Freigegebene Slots wirken erst nach `python -m v13.memory_server --home ~/v13 build` im Chat'
    return t,info

def install(growth,runtime,kind=None):
    t,info=build(runtime,kind);growth.weights.trainer=t;growth.trainer_info=info;return info

def set_lora_cfg(growth,runtime,overrides):
    """Measured per-device LoRA overrides (keys of lora_trainer.DEFAULTS only)."""
    from ..lora_trainer import DEFAULTS
    bad=[k for k in overrides if k not in DEFAULTS or k in ('threads','base_gguf')]
    if bad:raise ValueError('Unbekannte LoRA-Regler: '+', '.join(bad))
    def f(st):st['lora_cfg']=dict(overrides)
    _box(runtime.store).mutate(f);return install(growth,runtime)

def choose(growth,runtime,kind,master=None):
    """User decision (:growth trainer <kind> [master_dir]). Master hash is pinned at choice time."""
    if kind not in KINDS:raise ValueError('Trainer: '+'|'.join(KINDS))
    def f(st):
        st['kind']=kind
        if master:
            m=Path(master).expanduser().resolve()
            if not (m/'model.safetensors').is_file():raise ValueError('Master-Ordner braucht model.safetensors + config.json')
            st['master']=str(m);st['master_sha256']=file_hash(m/'model.safetensors')
    _box(runtime.store).mutate(f)
    return install(growth,runtime)
