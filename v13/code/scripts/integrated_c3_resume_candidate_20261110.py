"""Layer fail-closed C3 LoRA restore onto the combined Body/World test copy."""
import hashlib
import importlib.util
from pathlib import Path

BASE_BUILDER_SHA = 'e38f7ba57a5f8fdb33c3eab269d434c2213b744a6f6d14122e88f08f733af7f4'
HELPER_SHA = 'efe4c3c96d3dafc11045f0f831ea0e97b949b5169a031429ff6c23692158de58'
LORA_SHA = '6383f957060116d3750f5c266cc83bac414fc9d6136eac0c4cd4317fbbb9f3f4'
INPUT_OLD = b'''        from peft import LoraConfig,get_peft_model
        dh=digest(dumps([[i.get('memory_id'),i['prompt'],i['target']] for i in items]+[self.anchors,{k:v for k,v in cfg.items() if k!='threads'} ]))[:24]
'''
INPUT_NEW = b'''        from peft import LoraConfig,get_peft_model
        from .lora_resume_atomic_candidate import binding,optimizer_layout,restore as restore_c3_resume
        resume_source_sha=binding(self.master_sha,base_generation,items,self.anchors,self.probes,cfg)
        if resume_source_sha is None:raise Unavailable('C3 resume needs verified master hash and base generation')
        dh=digest(dumps([[i.get('memory_id'),i['prompt'],i['target']] for i in items]+[self.anchors,{k:v for k,v in cfg.items() if k!='threads'} ]))[:24]
'''
RESUME_OLD = b'''            if not isinstance(st,dict):
                raise Unavailable('Invalid LoRA training checkpoint')
            if st.get('dataset_hash')==dh:
                if not _valid_lora_resume(st,dh,int(cfg['max_steps'])):
                    raise Unavailable('Invalid LoRA training checkpoint')
                if not _valid_lora_tensors(torch,st['lora'],model.state_dict()):
                    raise Unavailable('Incompatible or nonfinite LoRA checkpoint weights')
                model.load_state_dict(st['lora'],strict=False)
                opt.load_state_dict(st['opt'])
                step=st['step'];hist=st['hist'];resume_rng=st.get('shuffle_rng_state');resumed=True
'''
RESUME_NEW = b'''            if not isinstance(st,dict) or st.get('dataset_hash')!=dh:
                raise Unavailable('Invalid or foreign LoRA training checkpoint')
            try:
                g=restore_c3_resume(torch,model,opt,st,dh,int(cfg['max_steps']),resume_source_sha,
                                    cfg['seed'],len(data),len(anchor_seqs),float(cfg['anchor_weight']))
            except (ValueError,TypeError,KeyError,RuntimeError) as exc:
                raise Unavailable('Unbound or invalid LoRA training checkpoint') from exc
            step=st['step'];hist=st['hist'];resumed=True
'''
SAVE_OLD = b"            torch.save({'dataset_hash':dh,'lora':lora,'opt':opt.state_dict(),'step':step,'hist':hist,'shuffle_rng_state':g.get_state()},tmp);os.replace(tmp,ck)\n"
SAVE_NEW = b"            torch.save({'dataset_hash':dh,'lora':lora,'opt':opt.state_dict(),'step':step,'hist':hist,'shuffle_rng_state':g.get_state(),'torch_rng_state':torch.get_rng_state(),'resume_source_sha256':resume_source_sha,'optimizer_layout':optimizer_layout(model,opt)},tmp);os.replace(tmp,ck)\n"
RNG_OLD = b"        model.train();g=_resume_shuffle_rng(torch,cfg['seed'],step,resume_rng,len(data),len(anchor_seqs),float(cfg['anchor_weight']))\n"
RNG_NEW = b"        model.train()\n        if not resumed:g=_resume_shuffle_rng(torch,cfg['seed'],step,None,len(data),len(anchor_seqs),float(cfg['anchor_weight']))\n"


def _replace_once(data, old, new, label):
    if data.count(old) != 1:
        raise ValueError('unexpected C3 ' + label + ' source')
    return data.replace(old, new, 1)


def build_sources(code_dir):
    code_dir = Path(code_dir)
    path = code_dir / 'scripts/integrated_body_world_candidate_20261110.py'
    if hashlib.sha256(path.read_bytes()).hexdigest() != BASE_BUILDER_SHA:
        raise ValueError('Body/World integration builder source changed')
    helper = (code_dir / 'v13/lora_resume_atomic_candidate.py').read_bytes()
    if hashlib.sha256(helper).hexdigest() != HELPER_SHA:
        raise ValueError('C3 resume helper source changed')
    lora = (code_dir / 'v13/lora_trainer.py').read_bytes()
    if hashlib.sha256(lora).hexdigest() != LORA_SHA:
        raise ValueError('C3 LoRA source changed')
    spec = importlib.util.spec_from_file_location('verified_body_world_builder', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    sources = module.build_sources(code_dir)
    if 'v13/lora_trainer.py' in sources:
        raise ValueError('C3 trainer already changed by upstream composition')
    for old, new, label in ((INPUT_OLD, INPUT_NEW, 'binding'), (RESUME_OLD, RESUME_NEW, 'restore'),
                            (SAVE_OLD, SAVE_NEW, 'save'), (RNG_OLD, RNG_NEW, 'shuffle')):
        lora = _replace_once(lora, old, new, label)
    sources['v13/lora_trainer.py'] = lora
    sources['v13/lora_resume_atomic_candidate.py'] = helper
    return sources
