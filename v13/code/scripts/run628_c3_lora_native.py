#!/usr/bin/env python3
"""Run628: pinned public C3 SmolLM2 master -> real CPU LoRA shadow adapter.

No deployed llama.cpp parity, Redmi, B1/B2 update or production authority.
The experiment cohort is frozen before source and native execution.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

MODEL_REPO = 'HuggingFaceTB/SmolLM2-135M-Instruct'
MODEL_REV = '12fd25f77366fa6b3b4b768ec3050bf629380bac'
MODEL_SHA = '5af571cbf074e6d21a03528d2330792e532ca608f24ac70a143f6b369968ab8c'
SCHEMA = 'V13_RUN628_C3_NATIVE_LORA_PROBE_V1'


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def cohort_load(path):
    d = json.loads(Path(path).read_text())
    if d.get('schema') != SCHEMA:
        raise ValueError('wrong cohort schema')
    model = d.get('model')
    if not isinstance(model, dict) or (
        model.get('repo_id'), model.get('revision'), model.get('master_sha256'),
        model.get('license')
    ) != (MODEL_REPO, MODEL_REV, MODEL_SHA, 'apache-2.0'):
        raise ValueError('model revision/hash/license mismatch')
    train, heldout = d.get('train'), d.get('heldout')
    if not isinstance(train, list) or len(train) != 2 or not isinstance(heldout, list) or len(heldout) != 2:
        raise ValueError('frozen cohort count mismatch')
    prompts = [x.get('prompt') for x in train + heldout]
    if any(not isinstance(p, str) or not p.strip() for p in prompts) or len(set(prompts)) != 4:
        raise ValueError('train/heldout overlap or invalid prompts')
    if any(x.get('kind') != 'synthetic' or not x.get('target') or not x.get('answer_keys') for x in train):
        raise ValueError('training must be synthetic and explicitly labelled')
    cfg = d.get('config')
    if not isinstance(cfg, dict) or cfg.get('jepa_weight') != 0 or cfg.get('targets') != ['q_proj', 'v_proj']:
        raise ValueError('unapproved training mode')
    if (cfg.get('max_steps'), cfg.get('min_steps'), cfg.get('rank'), cfg.get('alpha')) != (2, 2, 2, 4):
        raise ValueError('training configuration drift')
    return d


def master_check(path, cohort):
    p = Path(path)
    model = p / cohort['model']['master_file']
    if not model.is_file() or sha(model) != MODEL_SHA:
        raise ValueError('master SHA256 mismatch before training')
    cfg = json.loads((p / 'config.json').read_text())
    if cfg.get('model_type') != 'llama' or 'LlamaForCausalLM' not in cfg.get('architectures', []):
        raise ValueError('master architecture mismatch')
    return {'path': str(model), 'sha256': MODEL_SHA, 'bytes': model.stat().st_size}


def execute(cohort_path, model_dir, out_dir):
    cohort_path = Path(cohort_path)
    d = cohort_load(cohort_path)
    master = master_check(model_dir, d)
    from v13.lora_trainer import LoraTrainer
    from safetensors.torch import load_file
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    trainer = LoraTrainer(model_dir, out_dir / 'training', master_sha256=MODEL_SHA,
                          anchors=(), probes=d['heldout'], cfg=d['config'], arch='llama')
    result = trainer.fit(d['train'], base_generation='RUN628_SYNTHETIC_MASTER_ONLY')
    if not result.get('artifact') or not result.get('files'):
        raise RuntimeError('LoRA trainer returned no adapter')
    metrics = result['metrics']
    if metrics['steps'] != 2 or metrics['trainable_parameter_count'] <= 0:
        raise RuntimeError('No bounded trainable LoRA update')
    if metrics.get('jepa_weight') != 0 or not math.isfinite(metrics['final_ce']):
        raise RuntimeError('Invalid training metrics/authority')
    kl = metrics.get('master_kl_to_base')
    if kl is None or not math.isfinite(kl):
        raise RuntimeError('Missing heldout master KL')
    adapter = result['files']
    if sha(adapter['gguf']) != adapter['gguf_sha256'] or sha(adapter['safetensors']) != adapter['safetensors_sha256']:
        raise RuntimeError('Adapter SHA mismatch')
    weights = load_file(adapter['safetensors'])
    b = [v for k, v in weights.items() if '.lora_B.' in k]
    if not b or not all(v.isfinite().all().item() for v in b):
        raise RuntimeError('Missing or nonfinite LoRA-B weights')
    nonzero = sum(int((v != 0).sum().item()) for v in b)
    if nonzero <= 0:
        raise RuntimeError('LoRA-B unchanged after real optimizer steps')
    proof = {
        'schema': 'V13_RUN628_C3_LORA_CPU_PROOF_V1',
        'evidence_scope': 'LINUX_NATIVE_C3_MASTER_LORA_CPU_EXPERIMENT',
        'status': 'TRAINED_SHADOW_ADAPTER_NOT_DEPLOYED',
        'cohort_sha256': sha(cohort_path),
        'master': master,
        'source_revision': MODEL_REV,
        'license': 'apache-2.0',
        'adapter_gguf_sha256': adapter['gguf_sha256'],
        'adapter_safetensors_sha256': adapter['safetensors_sha256'],
        'adapter_gguf_bytes': Path(adapter['gguf']).stat().st_size,
        'adapter_nonzero_lora_b_elements': nonzero,
        'metrics': metrics,
        'deployed_llama_cpp_evaluated': False,
        'redmi_measured': False,
        'production_weight_authority': 0,
        'body_jepa_proven': False,
        'gates': d['negative_gates'],
    }
    (out_dir / 'RUN628_PROOF.json').write_text(json.dumps(proof, indent=2, sort_keys=True) + '\n')
    (out_dir / 'RUN628_ADAPTER_PATH.txt').write_text(str(adapter['gguf']) + '\n')
    print(json.dumps({k: v for k, v in proof.items() if k != 'metrics'}, sort_keys=True))
    return proof


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--cohort', type=Path, required=True)
    p.add_argument('--model-dir', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    execute(a.cohort, a.model_dir, a.out)


if __name__ == '__main__':
    main()
