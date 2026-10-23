#!/usr/bin/env python3
"""WP-Z9 / §99 row "Dream helps": the two missing controls "dream no writes" and "dream policy-only".

Reuses the Dream2v3 protocol unchanged (scripts/dream_ablation_bench.py: 230M master, LoRA r8, phase A facts A, exactly
--b-steps phase-B steps on facts B + one rehearsal mix per arm). New arms:
  dream_no_writes        validated dreams are produced and counted but write nothing (mix = B only); must equal `none`
  dream_policy_only      B + the validated dream questions with the stored source answer, loss masked on every token that
                         carries the fact value (fact_write_gain = 0, blueprint §15.6/§94.3): only the answer frame learns
  replay_dream_policy    B + exact A replay (Sleep A may write) + the dream_policy_only mix (blueprint-conform Sleep A+B)
  replay_dream_validated B + exact A replay + the writing dream_validated mix (price of writing facts from dreams)
Preregistration: docs/proofs/continuation-20261022/z9-dream-policy-only/PREREG.md (committed before the run).
  python3 scripts/z9_dream_policy_only.py --master DIR --dreams JSON --out DIR --seeds 13 --arms dream_no_writes,...
  python3 scripts/z9_dream_policy_only.py --analyze --runs DIR [DIR ...] --dream2 REPORT --out JSON
"""
import argparse, json, platform, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1])); sys.path.insert(0, str(Path(__file__).resolve().parent))
from dream_ablation_bench import A, B, Dream, split_dreams, save_progress  # noqa: E402
from v13.common import file_hash, digest  # noqa: E402

ARMS = ('dream_no_writes', 'dream_policy_only', 'replay_dream_policy', 'replay_dream_validated')
KEYS = {q: ks for q, _, ks in A}

def key_spans(text, keys):
    low = text.lower(); spans = []
    for k in keys:
        i = low.find(k)
        while i >= 0:
            spans.append((i, i+len(k))); i = low.find(k, i+1)
    return spans

class PolicyDream(Dream):
    def enc_masked(self, prompt, target, keys):
        """Same tokens as enc(); labels of every target token overlapping a fact key are -100 (no write to the fact value)."""
        ids, labels = self.enc(prompt, target)
        full = target+'<|im_end|>'
        t = self.tok(full, add_special_tokens=False, return_offsets_mapping=True)
        assert t['input_ids'] == ids[len(ids)-len(t['input_ids']):], 'target tokenization differs from enc()'
        spans = key_spans(full, keys); off = len(ids)-len(t['input_ids']); masked = 0
        for j, (s, e) in enumerate(t['offset_mapping']):
            if any(s < ke and e > ks for ks, ke in spans):
                labels[off+j] = -100; masked += 1
        kept = self.tok.decode([x for x in labels[off:] if x != -100]).lower()
        if not masked or any(k in kept for k in keys): raise ValueError('fact value not fully masked: %r' % target)
        return ids, labels, masked
    def fit(self, model, items, lr=3e-4, max_steps=60, target_ce=.05):
        """Dream.fit with optional per-item key masks: item = (q, a) or (q, a, keys)."""
        torch = self.torch; data = []; self.mask_log = []
        for it in items:
            if len(it) == 3:
                ids, labels, n = self.enc_masked(*it); data.append((ids, labels)); self.mask_log.append({'q': it[0], 'masked_tokens': n})
            else: data.append(self.enc(*it))
        params = [p for p in model.parameters() if p.requires_grad]
        opt = torch.optim.AdamW(params, lr=lr, weight_decay=0.); model.train(); ce = None; step = 0
        for step in range(1, max_steps+1):
            opt.zero_grad(); ce = 0.
            for ids, labels in data:
                out = model(torch.tensor([ids]), labels=torch.tensor([labels])); (out.loss/len(data)).backward(); ce += float(out.loss.detach())/len(data)
            opt.step()
            if ce <= target_ce: break
        model.eval(); return {'steps': step, 'final_ce': round(ce, 5), 'items': len(items), 'masked_items': len(self.mask_log)}

def mix_for(arm, ok, per_fact):
    mix = [(q, ans) for q, ans, _ in B]
    replay = [(q, ans) for q, ans, _ in A]
    validated = [(v, ans) for q, ans, _ in A for v in ok.get(q, [])[:per_fact]]
    policy = [(v, ans, KEYS[q]) for q, ans, _ in A for v in ok.get(q, [])[:per_fact]]
    return mix + {'dream_no_writes': [], 'dream_policy_only': policy, 'replay_dream_policy': replay+policy,
                  'replay_dream_validated': replay+validated}[arm], len(validated)

def run(a):
    seeds = [int(s) for s in a.seeds.split(',')]; arms = a.arms.split(',')
    if any(x not in ARMS for x in arms): raise SystemExit('unknown arm')
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True); path = out/'z9.json'
    if path.exists(): raise SystemExit('existing result preserved: %s' % path)
    ok, bad, dropped = split_dreams(json.loads(Path(a.dreams).read_text()))
    root = Path(__file__).resolve().parents[1]
    doc = {'schema': 'v13-z9-dream-policy-only-v1', 'status': 'RUNNING', 'phone_measured': False, 'canonical_gate_pass': False,
           'prereg': 'docs/proofs/continuation-20261022/z9-dream-policy-only/PREREG.md',
           'prereg_sha256': file_hash(root/'docs/proofs/continuation-20261022/z9-dream-policy-only/PREREG.md'),
           'binding': {'master_safetensors_sha256': file_hash(Path(a.master)/'model.safetensors'), 'dreams_sha256': file_hash(Path(a.dreams)),
                       'source_sha256': {p: file_hash(root/p) for p in ('scripts/z9_dream_policy_only.py', 'scripts/dream_ablation_bench.py',
                                         'scripts/sparse_memory_bench.py', 'scripts/lora_bench.py', 'v13/lora_trainer.py')},
                       'seeds': seeds, 'arms': arms, 'threads': a.threads, 'per_fact': a.per_fact, 'b_steps': a.b_steps, 'platform': platform.platform()},
           'dreams': {'validated_counts': {q: len(v) for q, v in ok.items()}, 'dropped_eval_or_duplicate': dropped}, 'runs': []}
    b = PolicyDream(a.master, a.threads); b.generation_trace = []; b.reference()
    doc['base_evaluation'] = b.base_eval; doc['base_raw_generations'] = b.generation_trace; t0 = time.monotonic()
    save_progress(path, doc)
    for seed in seeds:
        for arm in arms:
            b.generation_trace = []
            m = b.lora(seed); fa = b.fit(m, [(q, ans) for q, ans, _ in A]); after_a = b.split_eval(m)
            mix, n_dreams = mix_for(arm, ok, a.per_fact)
            fb = b.fit(m, mix, max_steps=a.b_steps, target_ce=-1.)
            r = {'seed': seed, 'arm': arm, 'phase_a': fa, 'after_a': after_a, 'phase_b': fb, 'after_b': b.split_eval(m),
                 'dreams_produced': n_dreams, 'mask_log': b.mask_log,
                 'rehearsal': [list(x) for x in mix if x[0] not in {q for q, _, _ in B}], 'raw_generations': b.generation_trace}
            doc['runs'].append(r)
            print(json.dumps({'seed': seed, 'arm': arm, **{k: r['after_b'][k] for k in ('A', 'B', 'near_miss_leak', 'probe_retention')}}), flush=True)
            doc['seconds'] = round(time.monotonic()-t0, 1); save_progress(path, doc)
    doc['row_sha256'] = [digest(json.dumps(r, sort_keys=True, allow_nan=False)) for r in doc['runs']]
    doc['status'] = 'COMPLETE'; save_progress(path, doc); return 0

def mean(xs): return round(sum(xs)/len(xs), 4)

def analyze(a):
    d2 = json.loads(Path(a.dream2).read_text()); rows = {}
    base_ok = True
    for r in d2['runs']: rows[(r['seed'], r['arm'])] = r['after_b']
    for p in a.runs:
        doc = json.loads((Path(p)/'z9.json').read_text())
        if doc['status'] != 'COMPLETE': raise SystemExit('incomplete run %s' % p)
        base_ok &= doc['base_evaluation'] == d2['base_evaluation'] and doc['base_raw_generations'] == d2['base_raw_generations']
        for r in doc['runs']: rows[(r['seed'], r['arm'])] = r['after_b']
    seeds = [13, 21, 34]
    def m(arm, f): return mean([f(rows[(s, arm)]) for s in seeds])
    para = lambda x: x['A']['paraphrase']; rec = lambda x: x['A']['recall']; probe = lambda x: x['probe_retention']; leak = lambda x: x['near_miss_leak']
    table = {arm: {'A_recall': m(arm, rec), 'A_paraphrase': m(arm, para), 'B_recall': m(arm, lambda x: x['B']['recall']),
                   'probe_retention': m(arm, probe), 'near_miss_leak': m(arm, leak), 'kl_to_base': m(arm, lambda x: x['kl_to_base'])}
             for arm in ('none', 'replay_exact', 'dream_validated', 'dream_policy_only', 'replay_dream_policy', 'replay_dream_validated')}
    identity = rows.get((13, 'dream_no_writes')) == rows[(13, 'none')] if (13, 'dream_no_writes') in rows else None
    t, c = table['replay_dream_policy'], table['replay_exact']
    dpara = round(t['A_paraphrase']-c['A_paraphrase'], 4)
    worse_seed = any(para(rows[(s, 'replay_dream_policy')]) < para(rows[(s, 'replay_exact')]) for s in seeds)
    costs = t['probe_retention']-c['probe_retention'] < -.09 or t['A_recall']-c['A_recall'] < -.09
    if not base_ok or identity is False: main = 'NOT_COMPARABLE'
    elif dpara >= .17 and not worse_seed: main = 'Z9_POLICY_DREAM_COSTS' if costs else 'Z9_POLICY_DREAM_HELPS'
    elif dpara >= .17 and costs: main = 'Z9_POLICY_DREAM_COSTS'
    else: main = 'Z9_POLICY_DREAM_NO_GAIN'
    po, dv, no = table['dream_policy_only']['A_paraphrase'], table['dream_validated']['A_paraphrase'], table['none']['A_paraphrase']
    attribution = 'POLICY_CARRIES' if po >= dv-.09 else 'FACT_WRITE_CARRIES' if po <= no+.09 else 'MIXED'
    res = {'schema': 'v13-z9-analysis-v1', 'verdict': main, 'attribution': attribution, 'base_reproduces_dream2v3': base_ok,
           'no_writes_identical_to_none_seed13': identity, 'delta_paraphrase_vs_replay': dpara, 'any_seed_worse': worse_seed,
           'means': table, 'per_seed': {'%s/%s' % k: v for k, v in sorted(rows.items(), key=str)},
           'phone_measured': False, 'canonical_gate_pass': False}
    Path(a.out).write_text(json.dumps(res, indent=1)+'\n'); print(json.dumps({k: res[k] for k in list(res)[:7]}, indent=1)); return 0

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--master'); ap.add_argument('--dreams'); ap.add_argument('--out', required=True)
    ap.add_argument('--seeds', default='13,21,34'); ap.add_argument('--arms', default=','.join(ARMS[1:]))
    ap.add_argument('--threads', type=int, default=1); ap.add_argument('--per-fact', type=int, default=3); ap.add_argument('--b-steps', type=int, default=40)
    ap.add_argument('--analyze', action='store_true'); ap.add_argument('--runs', nargs='*'); ap.add_argument('--dream2'); a = ap.parse_args()
    return analyze(a) if a.analyze else run(a)

if __name__ == '__main__':
    sys.exit(main())
