#!/usr/bin/env python3
"""WP-T14 / §31 R2 (dense part): where does forgetting come from when C3 learns new facts?

Same 8 invented facts, paraphrases, near-miss questions and 12 held-out probes as lora_bench / sparse_memory_bench,
LFM2.5-230M master in torch fp32. Each scope trains only one part of the body, from a fresh copy, same data, same step
budget and early stop:
  attn_lora     LoRA r8 on the attention blocks only (q/k/v/out of self_attn)      shared attention
  conv_lora     LoRA r8 on the short-conv mixers only (conv.in_proj/out_proj)       shared token mixing
  ffn_lora      LoRA r8 on the feed-forward w1/w2/w3 only                           dense stand-in for "experts only"
  all_lora      LoRA r8 on all of the above (lora_trainer.DEFAULT_TARGETS)          mixed delta
  norms_only    only the RMSNorm gains                                              smallest dense slice
  top_block     full weights of the last block only                                 "heads/projectors only"
  smf_keyed     sparse memory slots at layer 7 (sparse_memory.py, keyed r90)        adapter slice with gate
  full          every weight except the embeddings
Measured per scope: acquisition (learned/paraphrase recall), retention (probe accuracy, forgotten list), KL(base||cand)
on probes, shared-layer representation drift (1 - cosine of mean hidden state at layers 3/7/13 on the probes),
near-miss leak, trainable parameters and rollback cost (bytes of the delta), seconds.
Claim limit: dense 230M body, one seed, 8 facts; router-only / expert-only arms need a MoE body (WP-N11, §24.19).
  python3 scripts/r2_scope_bench.py --master DIR --out bench-results/r2-scope-<date> [--scopes a,b]
"""
import argparse, json, platform, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1])); sys.path.insert(0, str(Path(__file__).resolve().parent))
from sparse_memory_bench import Bench, ITEMS, METHODS as SMF_METHODS  # noqa: E402
from lora_bench import PROBES  # noqa: E402
from v13.lora_trainer import DEFAULT_TARGETS  # noqa: E402
from v13.common import file_hash  # noqa: E402

DRIFT_LAYERS = (3, 7, 13)
SCOPES = {
    'attn_lora': {'kind': 'lora', 'targets': r'.*self_attn\.(q_proj|k_proj|v_proj|out_proj)', 'lr': 3e-4},
    'conv_lora': {'kind': 'lora', 'targets': r'.*conv\.(in_proj|out_proj)', 'lr': 3e-4},
    'ffn_lora': {'kind': 'lora', 'targets': ['w1', 'w2', 'w3'], 'lr': 3e-4},
    'all_lora': {'kind': 'lora', 'targets': list(DEFAULT_TARGETS), 'lr': 3e-4},
    'norms_only': {'kind': 'dense', 'select': 'norm', 'lr': 1e-2},
    'top_block': {'kind': 'dense', 'select': 'layers.13.', 'lr': 1e-4},
    'smf_keyed': {'kind': 'smf'},
    'full': {'kind': 'dense', 'select': '', 'lr': 1e-5},
}

class ScopeBench(Bench):
    def hidden(self, model):
        """Mean hidden state per drift layer over every probe prompt (the shared representation the scope may move)."""
        torch = self.torch; out = {l: [] for l in DRIFT_LAYERS}
        with torch.no_grad():
            for p in PROBES:
                hs = model(torch.tensor([self.enc(p['prompt'])[0]]), output_hidden_states=True).hidden_states
                for l in DRIFT_LAYERS: out[l].append(hs[l+1][0].mean(0))
        return {l: torch.stack(v) for l, v in out.items()}
    def drift(self, model):
        F = self.torch.nn.functional; cur = self.hidden(model)
        return {str(l): round(float(1-F.cosine_similarity(cur[l], self.base_hidden[l], dim=-1).mean()), 6) for l in DRIFT_LAYERS}
    def scope(self, name, cfg):
        torch = self.torch; t0 = time.monotonic(); kind = cfg['kind']
        if kind == 'smf':
            r = self.run(name, SMF_METHODS['smf_keyed_r90']); r['eval']['representation_drift'] = None
            r['rollback_bytes'] = r['train']['trainable_parameters']*4; return r
        if kind == 'lora':
            from peft import LoraConfig, get_peft_model
            model = get_peft_model(self.fresh(), LoraConfig(r=8, lora_alpha=16., lora_dropout=0., target_modules=cfg['targets'], bias='none'))
            params = [p for p in model.parameters() if p.requires_grad]
        else:
            model = self.fresh(); params = [p for n, p in model.named_parameters() if 'embed' not in n and cfg['select'] in n]
            for p in params: p.requires_grad_(True)
        n = sum(p.numel() for p in params)
        train = self.train_dense(model, params, cfg['lr']) | {'trainable_parameters': n}
        model.eval(); ev = self.evaluate(model)
        ev ={k: v for k, v in ev.items() if k != 'probes'} | {'representation_drift': self.drift(model)}
        return {'name': name, 'cfg': {k: v for k, v in cfg.items()}, 'train': train, 'eval': ev, 'rollback_bytes': n*4, 'seconds': round(time.monotonic()-t0, 1)}

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--master', required=True); ap.add_argument('--out', required=True)
    ap.add_argument('--scopes', default=','.join(SCOPES)); ap.add_argument('--threads', type=int, default=4); a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True); b = ScopeBench(a.master, a.threads)
    doc = {'schema': 'v13-r2-scope-bench-v1', 'experiment': 'blueprint §31 R2 (dense part)', 'date': time.strftime('%Y-%m-%d'), 'platform': platform.platform(),
           'torch': b.torch.__version__, 'master_sha256': file_hash(Path(a.master)/'model.safetensors'), 'drift_layers': DRIFT_LAYERS, 'runs': [],
           'claim_limit': 'dense LFM2.5-230M, one seed, 8 facts / 12 probes; router-only and expert-only arms need the MoE body (WP-N11)'}
    doc['base'] = {k: v for k, v in b.reference().items() if k != 'probes'}; b.base_hidden = b.hidden(b.fresh())
    for name in a.scopes.split(','):
        r = b.scope(name, SCOPES[name]); doc['runs'].append(r)
        print(json.dumps({'name': name, **{k: v for k, v in r['eval'].items()}, 'params': r['train']['trainable_parameters'], 'steps': r['train']['steps'], 's': r['seconds']}), flush=True)
        (out/'r2_scope_bench.json').write_text(json.dumps(doc, indent=1))
    return 0

if __name__ == '__main__':
    sys.exit(main())
