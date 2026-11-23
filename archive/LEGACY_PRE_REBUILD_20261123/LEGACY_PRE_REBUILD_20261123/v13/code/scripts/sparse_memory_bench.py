#!/usr/bin/env python3
"""WP-S3 ablation: sparse memory finetuning vs LoRA vs full finetuning on C3 (LFM2.5-230M master, torch fp32).

Same 8 invented facts, 6 paraphrases, 5 near-miss questions and 12 held-out probes as scripts/lora_bench.py.
Every method starts from a fresh copy of the base and is measured with the same functions:
  learned_recall, paraphrase_recall, near_miss_leak, probe retention (+ forgotten list), KL(base||cand) on probes
  (full vocabulary, teacher-forced along the base model's greedy continuation), trainable parameters, seconds.
  python3 scripts/sparse_memory_bench.py --master DIR --out bench-results/sparse-memory-<date> [--methods smf,lora,full]
Nothing is activated; this produces WP-S3 evidence only.
"""
import argparse, json, platform, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1])); sys.path.insert(0, str(Path(__file__).resolve().parent))
from lora_bench import FACTS, PARAPHRASES, NEAR_MISS, ANCHORS, PROBES  # noqa: E402
from v13.lora_trainer import answer_hit, SWAP_NOUNS, DEFAULT_TARGETS  # noqa: E402
from v13.sparse_memory import SparseMemoryTrainer, attach, DEFAULTS as SMF_DEFAULTS  # noqa: E402
from v13.common import file_hash  # noqa: E402

ITEMS = [{'prompt': q, 'target': a} for q, a, _ in FACTS]

def locality(k=2):
    import re
    out = []
    for n, (q, _, _) in enumerate(FACTS):
        m = re.search(r'\bmy (\w+)', q, re.I)
        if not m: continue
        pool = [w for w in SWAP_NOUNS if w != m.group(1).lower()]
        out += [q[:m.start(1)]+pool[(n*k+j) % len(pool)]+q[m.end(1):] for j in range(k)]
    return out

def negatives(k=4):
    """The fact with its entity noun swapped ("Your friend is called Mitzi."): positions that must not fire the new slots.
    Swap nouns come from SWAP_NOUNS, disjoint from the eval near-miss words."""
    import re
    out = []
    for n, (q, a, _) in enumerate(FACTS):
        m = re.search(r'\bmy (\w+)', q, re.I)
        if not m: continue
        noun = m.group(1); pool = [w for w in SWAP_NOUNS if w != noun.lower()]
        for j in range(k):
            w = pool[(n*k+j) % len(pool)]
            out.append({'prompt': re.sub(r'\b%s\b' % noun, w, q), 'target': re.sub(r'\b%s\b' % noun, w, a)})
    return out

class Bench:
    def __init__(self, master, threads):
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        self.torch = torch; self.master = master; torch.set_num_threads(threads)
        self.tok = AutoTokenizer.from_pretrained(master); self.Model = AutoModelForCausalLM
        self.background = ANCHORS + locality()
    def fresh(self):
        m = self.Model.from_pretrained(self.master, dtype=self.torch.float32).eval()
        for p in m.parameters(): p.requires_grad_(False)
        return m
    def enc(self, prompt, target=None):
        p = self.tok.apply_chat_template([{'role': 'user', 'content': prompt}], add_generation_prompt=True, tokenize=False)
        pid = self.tok(p, add_special_tokens=False)['input_ids']
        if target is None: return pid, None
        tid = self.tok(target+'<|im_end|>', add_special_tokens=False)['input_ids']; return pid+tid, [-100]*len(pid)+tid
    def gen(self, model, prompt, n=24):
        ids = self.enc(prompt)[0]
        with self.torch.no_grad():
            o = model.generate(self.torch.tensor([ids]), attention_mask=self.torch.ones(1, len(ids), dtype=self.torch.long), max_new_tokens=n, do_sample=False, pad_token_id=0)
        return self.tok.decode(o[0][len(ids):], skip_special_tokens=True)
    def reference(self):
        """Base answers and base log-probs along the base continuation of each probe (computed once)."""
        torch = self.torch; m = self.fresh(); ref = []
        for p in PROBES:
            ids = self.enc(p['prompt'])[0]
            with torch.no_grad():
                o = m.generate(torch.tensor([ids]), attention_mask=torch.ones(1, len(ids), dtype=torch.long), max_new_tokens=16, do_sample=False, pad_token_id=0)[0].tolist()
                lp = torch.log_softmax(m(torch.tensor([o])).logits[0], -1)[len(ids)-1:-1]
            ref.append((o, len(ids), lp))
        self.ref = ref; self.base_eval = self.evaluate(m, kl=False); return self.base_eval
    def evaluate(self, model, kl=True):
        torch = self.torch
        learned = [answer_hit(self.gen(model, q), keys) for q, _, keys in FACTS]
        para = [answer_hit(self.gen(model, q), keys) for q, keys in PARAPHRASES]
        leak = [answer_hit(self.gen(model, q), keys) for q, keys in NEAR_MISS]
        probes = {p['prompt']: answer_hit(self.gen(model, p['prompt'], 32), p['expect']) for p in PROBES}
        out = {'learned_recall': sum(learned)/len(learned), 'paraphrase_recall': sum(para)/len(para), 'near_miss_leak': sum(leak)/len(leak),
               'probe_retention': sum(probes.values())/len(probes), 'probes': probes}
        if kl:
            vals = []
            with torch.no_grad():
                for o, n, base in self.ref:
                    cur = torch.log_softmax(model(torch.tensor([o])).logits[0], -1)[n-1:-1]
                    vals.append(float((base.exp()*(base-cur)).sum(-1).mean()))
            out['kl_to_base'] = sum(vals)/len(vals)
            out['forgotten'] = [k for k, v in probes.items() if self.base_eval['probes'][k] and not v]
        return out
    def train_dense(self, model, params, lr, anchor_weight=0., max_steps=60, target_ce=.05):
        """Shared loop for LoRA and full finetuning (CE on answers, optional KL anchor on background continuations)."""
        torch = self.torch; data = [self.enc(i['prompt'], i['target']) for i in ITEMS]; anchors = []
        if anchor_weight > 0:
            for p in self.background:
                ids = self.enc(p)[0]
                with torch.no_grad():
                    o = model.generate(torch.tensor([ids]), attention_mask=torch.ones(1, len(ids), dtype=torch.long), max_new_tokens=24, do_sample=False, pad_token_id=0)[0].tolist()
                    anchors.append((o, torch.log_softmax(model(torch.tensor([o])).logits[0], -1)))
        opt = torch.optim.AdamW(params, lr=lr, weight_decay=0.); g = torch.Generator().manual_seed(13); step = 0; ce = None
        for step in range(1, max_steps+1):
            opt.zero_grad(); ce = 0.
            for ids, labels in data:
                out = model(torch.tensor([ids]), labels=torch.tensor([labels])); (out.loss/len(data)).backward(); ce += float(out.loss.detach())/len(data)
            for j in (torch.randperm(len(anchors), generator=g)[:8].tolist() if anchors else []):
                o, base = anchors[j]; cur = torch.log_softmax(model(torch.tensor([o])).logits[0], -1)
                (anchor_weight*(base.exp()*(base-cur)).sum(-1).mean()/8).backward()
            opt.step()
            if ce <= target_ce: break
        return {'steps': step, 'final_ce': round(ce, 5)}
    def run(self, name, cfg):
        torch = self.torch; t0 = time.monotonic(); kind = cfg['kind']
        if kind == 'smf':
            tr = SparseMemoryTrainer(self.master, '/tmp/v13-smf', background=self.background, cfg=cfg.get('smf', {}), negatives=negatives() if cfg.get('negatives') else ()); tr.tok = self.tok
            tr.model = self.fresh(); tr.memory, tr.layer = attach(torch, tr.model, tr.cfg)
            fit = tr.fit(ITEMS); model = tr.model; train = {k: fit['metrics'][k] for k in ('steps', 'final_ce', 'selected_slots', 'trainable_parameters', 'layer')}
        elif kind == 'lora':
            from peft import LoraConfig, get_peft_model
            model = get_peft_model(self.fresh(), LoraConfig(r=8, lora_alpha=16., lora_dropout=0., target_modules=list(DEFAULT_TARGETS), bias='none'))
            params = [p for p in model.parameters() if p.requires_grad]
            train = self.train_dense(model, params, cfg['lr'], cfg.get('anchor_weight', 0.)) | {'trainable_parameters': sum(p.numel() for p in params)}
        else:
            model = self.fresh(); params = [p for n, p in model.named_parameters() if 'embed' not in n]
            for p in params: p.requires_grad_(True)
            train = self.train_dense(model, params, cfg['lr'], cfg.get('anchor_weight', 0.)) | {'trainable_parameters': sum(p.numel() for p in params)}
        model.eval(); ev = self.evaluate(model)
        return {'name': name, 'cfg': cfg, 'train': train, 'eval': {k: v for k, v in ev.items() if k != 'probes'}, 'seconds': round(time.monotonic()-t0, 1)}

METHODS = {
    'smf_tfidf': {'kind': 'smf', 'smf': {'mode': 'tfidf'}},
    'smf_tfidf_anchor': {'kind': 'smf', 'smf': {'mode': 'tfidf', 'anchor_weight': 4.}},
    'smf_keyed_r80': {'kind': 'smf', 'smf': {'mode': 'keyed', 'theta_min': .8}},
    'smf_keyed_r90': {'kind': 'smf', 'smf': {'mode': 'keyed', 'theta_min': .9}},
    'smf_keyed_r90_neg': {'kind': 'smf', 'smf': {'mode': 'keyed', 'theta_min': .9}, 'negatives': True},
    'smf_keyed_r90_guard': {'kind': 'smf', 'smf': {'mode': 'keyed', 'theta_min': .9, 'entity_guard': True}},
    'smf_keyed_r80_guard': {'kind': 'smf', 'smf': {'mode': 'keyed', 'theta_min': .8, 'entity_guard': True}},
    'lora': {'kind': 'lora', 'lr': 3e-4},
    'lora_anchor': {'kind': 'lora', 'lr': 3e-4, 'anchor_weight': 4.},
    'full': {'kind': 'full', 'lr': 1e-5},
}

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--master', required=True); ap.add_argument('--out', required=True)
    ap.add_argument('--methods', default=','.join(METHODS)); ap.add_argument('--threads', type=int, default=4); a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True); b = Bench(a.master, a.threads)
    doc = {'schema': 'v13-sparse-memory-bench-v1', 'date': time.strftime('%Y-%m-%d'), 'platform': platform.platform(), 'torch': b.torch.__version__,
           'master_sha256': file_hash(Path(a.master)/'model.safetensors'), 'smf_defaults': SMF_DEFAULTS, 'base': None, 'runs': [],
           'task': '8 invented facts, 6 paraphrases, 5 near-miss, 12 probes (scripts/lora_bench.py); torch fp32 master path, not the Q4 runner'}
    doc['base'] = {k: v for k, v in b.reference().items() if k != 'probes'}
    for name in a.methods.split(','):
        r = b.run(name, METHODS[name]); doc['runs'].append(r); print(json.dumps({'name': name, **r['eval'], 'steps': r['train']['steps'], 's': r['seconds']}), flush=True)
        (out/'sparse_memory_bench.json').write_text(json.dumps(doc, indent=1))
    return 0

if __name__ == '__main__':
    sys.exit(main())
