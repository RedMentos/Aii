#!/usr/bin/env python3
"""WP-T17 / §99 row "Dream helps": does offline dream rehearsal protect earlier learning better than plain replay?

C3 = LFM2.5-230M master (torch fp32), LoRA r8 on all DEFAULT_TARGETS (the dense learning path that forgets, R2).
Sequential learning: phase A trains facts A = FACTS[:4], phase B continues the same adapter on facts B = FACTS[4:]
plus one rehearsal mix per arm (same steps budget and stop rule for all arms):
  none               B only (the forgetting reference)
  replay_exact       B + the stored A records verbatim (Fast Episodic replay; the strong control a dream must beat)
  dream_validated    B + dream variants of A: C3-written rewordings of the stored A questions (--dreams JSON, written by the
                     runtime C3 GGUF), answer = the stored source answer; a variant survives only if it still names the
                     source entity (Sleep B anchor check) and is not an eval question (contamination filter)
  dream_self         B + the same reworded questions, answer = what the phase-A model itself says (generative /
                     pseudo-rehearsal, no source check; the classical "dream" without V13's validation)
  dream_unanchored   B + the dream variants that FAILED the anchor check, with the stored answers (what skipping
                     Sleep B validation would add)
Metrics after phase B: recall/paraphrase of A (retention) and B (new learning), near-miss leak, probe retention, KL.
  python3 scripts/dream_ablation_bench.py --master DIR --dreams JSON --out DIR [--seeds 13,21] [--b-steps 40]
"""
import argparse, fcntl, json, platform, re, sys, time
from importlib.metadata import version as package_version
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1])); sys.path.insert(0, str(Path(__file__).resolve().parent))
from lora_bench import FACTS, PARAPHRASES, NEAR_MISS, PROBES  # noqa: E402
from sparse_memory_bench import Bench  # noqa: E402
from v13.lora_trainer import answer_hit, DEFAULT_TARGETS  # noqa: E402
from v13.common import atomic_write, file_hash, digest  # noqa: E402

A, B = FACTS[:4], FACTS[4:]
ARMS = ('none', 'replay_exact', 'dream_validated', 'dream_self', 'dream_unanchored')
ENTITY = {'What is the name of my cat?': ('cat',), 'Where do I work?': ('work', 'job', 'employ'), 'What is my favourite colour?': ('colour', 'color'),
          'What is the name of my brother?': ('brother',)}
EVAL = {re.sub(r'\W+', ' ', q.lower()).strip() for q, *_ in FACTS+PARAPHRASES+NEAR_MISS}

def norm(q): return re.sub(r'\W+', ' ', q.lower()).strip()

def split_dreams(dreams):
    """Sleep B analog: keep a reworded question only if it still names the source entity; never an eval question."""
    ok, bad, dropped = {}, {}, 0
    for q, _, _ in A:
        for v in dict.fromkeys(dreams.get(q, [])):
            n = norm(v)
            if not n or n == norm(q) or n in EVAL: dropped += 1; continue
            (ok if any(e in n for e in ENTITY[q]) else bad).setdefault(q, []).append(v)
    return ok, bad, dropped

def run_binding(master, dreams, seeds, threads, per_fact, b_steps):
    """Bind a resumed cohort to actual input bytes, code and dependencies."""
    master = Path(master)
    if not (master/'model.safetensors').is_file():
        raise ValueError('Actual training master required')
    files = {p.relative_to(master).as_posix(): file_hash(p) for p in sorted(master.rglob('*'))
             if p.is_file() and (p.suffix in {'.json', '.safetensors', '.model', '.txt', '.jinja'}
                                  or p.name.upper().startswith('LICENSE'))}
    sources = ('scripts/dream_ablation_bench.py', 'scripts/sparse_memory_bench.py',
               'scripts/lora_bench.py', 'v13/lora_trainer.py', 'v13/sparse_memory.py', 'v13/common.py')
    root = Path(__file__).resolve().parents[1]
    return {'master_files_sha256': files, 'dreams_sha256': file_hash(Path(dreams)),
            'source_sha256': {p: file_hash(root/p) for p in sources},
            'packages': {p: package_version(p) for p in ('torch', 'transformers', 'peft', 'safetensors')},
            'config': {'seeds': seeds, 'threads': threads, 'per_fact': per_fact, 'b_steps': b_steps},
            'facts_sha256': digest(json.dumps([FACTS, PARAPHRASES, NEAR_MISS, PROBES], sort_keys=True)),
            'arms': list(ARMS), 'platform': platform.platform()}

def completed_pairs(doc, binding):
    if doc.get('proof_version') != 2 or doc.get('run_binding') != binding:
        raise ValueError('Resume artifact, source or configuration changed')
    expected = {(seed, arm) for seed in binding['config']['seeds'] for arm in ARMS}
    if doc.get('row_sha256') != [digest(json.dumps(row, sort_keys=True, allow_nan=False)) for row in doc['runs']]:
        raise ValueError('Completed arm bytes changed')
    pairs = set()
    for row in doc['runs']:
        pair = (row['seed'], row['arm'])
        if pair not in expected or pair in pairs or any(k not in row for k in ('phase_a', 'after_a', 'phase_b', 'after_b', 'raw_generations')):
            raise ValueError('Invalid or duplicate completed arm')
        if binding['config']['b_steps'] and row['phase_b']['steps'] != binding['config']['b_steps']:
            raise ValueError('Incomplete fixed-step arm')
        json.dumps(row, allow_nan=False)
        pairs.add(pair)
    return pairs

def save_progress(path, doc):
    """A crash can lose the current arm, never earlier completed controls."""
    atomic_write(path, json.dumps(doc, indent=1, allow_nan=False)+'\n')

class Dream(Bench):
    def __init__(self, master, threads):
        super().__init__(master, threads)
        self.generation_trace = []
    def gen(self, model, prompt, n=24):
        answer = super().gen(model, prompt, n)
        self.generation_trace.append({'prompt': prompt, 'answer': answer, 'max_new_tokens': n})
        return answer
    def lora(self, seed):
        from peft import LoraConfig, get_peft_model
        self.torch.manual_seed(seed)
        return get_peft_model(self.fresh(), LoraConfig(r=8, lora_alpha=16., lora_dropout=0., target_modules=list(DEFAULT_TARGETS), bias='none'))
    def fit(self, model, items, lr=3e-4, max_steps=60, target_ce=.05):
        torch = self.torch; data = [self.enc(q, a) for q, a in items]; params = [p for p in model.parameters() if p.requires_grad]
        opt = torch.optim.AdamW(params, lr=lr, weight_decay=0.); model.train(); ce = None; step = 0
        for step in range(1, max_steps+1):
            opt.zero_grad(); ce = 0.
            for ids, labels in data:
                out = model(torch.tensor([ids]), labels=torch.tensor([labels])); (out.loss/len(data)).backward(); ce += float(out.loss.detach())/len(data)
            opt.step()
            callback = getattr(self, 'progress_callback', None)
            if callback and (step == 1 or step % 10 == 0 or ce <= target_ce or step == max_steps):
                callback({'steps': step, 'final_ce': ce, 'items': len(items)})
            if ce <= target_ce: break
        model.eval(); return {'steps': step, 'final_ce': round(ce, 5), 'items': len(items)}
    def split_eval(self, model):
        ev = self.evaluate(model); keys = lambda fs: {k for _, _, ks in fs for k in ks}
        rate = lambda xs: round(sum(xs)/len(xs), 4) if xs else None
        part = lambda fs: {'recall': rate([answer_hit(self.gen(model, q), ks) for q, _, ks in fs]),
                           'paraphrase': rate([answer_hit(self.gen(model, q), ks) for q, ks in PARAPHRASES if set(ks) & keys(fs)])}
        return {'A': part(A), 'B': part(B), 'near_miss_leak': ev['near_miss_leak'], 'probe_retention': ev['probe_retention'],
                'kl_to_base': ev['kl_to_base'], 'forgotten': ev['forgotten']}

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--master', required=True); ap.add_argument('--dreams', required=True); ap.add_argument('--out', required=True)
    ap.add_argument('--seeds', default='13,21'); ap.add_argument('--threads', type=int, default=4); ap.add_argument('--per-fact', type=int, default=3)
    ap.add_argument('--b-steps', type=int, default=0, help='0 = stop at CE<=.05 (default); N = exactly N phase-B steps (forgetting stress)')
    ap.add_argument('--resume', action='store_true', help='Reuse only complete arms from an exactly bound cohort'); a = ap.parse_args()
    seeds = [int(s) for s in a.seeds.split(',')]
    if not seeds or len(set(seeds)) != len(seeds) or a.threads < 1 or a.per_fact < 1 or a.b_steps < 0:
        ap.error('Unique seeds and positive threads/per-fact required; b-steps must be nonnegative')
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    with (out/'dream-run.lock').open('a+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return run(a, out, seeds)

def run(a, out, seeds):
    path = out/('dream_ablation.json' if not a.b_steps else 'dream_ablation_b%d.json' % a.b_steps)
    binding = run_binding(a.master, a.dreams, seeds, a.threads, a.per_fact, a.b_steps)
    ok, bad, dropped = split_dreams(json.loads(Path(a.dreams).read_text()))
    doc = {'schema': 'v13-dream-ablation-v1', 'proof_version': 2, 'status': 'RUNNING', 'run_binding': binding,
           'phone_measured': False, 'canonical_gate_pass': False,
           'experiment': 'blueprint §99 Dream helps', 'date': time.strftime('%Y-%m-%d'), 'platform': platform.platform(),
           'facts': {'A': [q for q, _, _ in A], 'B': [q for q, _, _ in B]}, 'dreams': {'validated': ok, 'unanchored': bad, 'dropped_eval_or_duplicate': dropped},
           'per_fact': a.per_fact, 'b_steps': a.b_steps or 'until CE<=.05', 'runs': [], 'row_sha256': [],
           'claim_limit': '230M master, LoRA r8, 4+4 invented facts, dreams = reworded questions only. Only complete arms resume; an interrupted active arm restarts from base.'}
    if path.exists():
        if not a.resume: raise ValueError('Existing cohort preserved; use --resume with identical inputs')
        doc = json.loads(path.read_text()); done = completed_pairs(doc, binding)
    else:
        if a.resume: raise ValueError('No existing cohort to resume')
        done = set()
    if len(done) == len(seeds)*len(ARMS) and doc.get('status') == 'COMPLETE': return 0
    doc['status'] = 'RUNNING'; save_progress(path, doc)
    b = Dream(a.master, a.threads); b.generation_trace = []; b.reference()
    doc['base_evaluation'] = b.base_eval; doc['base_raw_generations'] = b.generation_trace
    elapsed = doc.get('seconds', 0.); t0 = time.monotonic()
    for seed in seeds:
        for arm in ARMS:
            if (seed, arm) in done: continue
            b.generation_trace = []; doc['active_arm'] = {'seed': seed, 'arm': arm, 'phase': 'A'}
            save_progress(path, doc)
            def progress(metrics):
                doc['active_arm']['training_progress'] = metrics
                doc['seconds'] = round(elapsed+time.monotonic()-t0, 1)
                save_progress(path, doc)
            b.progress_callback = progress
            m = b.lora(seed); fa = b.fit(m, [(q, ans) for q, ans, _ in A]); after_a = b.split_eval(m)
            mix = [(q, ans) for q, ans, _ in B]
            if arm == 'replay_exact': mix += [(q, ans) for q, ans, _ in A]
            elif arm == 'dream_validated': mix += [(v, ans) for q, ans, _ in A for v in ok.get(q, [])[:a.per_fact]]
            elif arm == 'dream_self': mix += [(v, b.gen(m, v).strip()) for q, ans, _ in A for v in ok.get(q, [])[:a.per_fact]]
            elif arm == 'dream_unanchored': mix += [(v, ans) for q, ans, _ in A for v in bad.get(q, [])[:a.per_fact]]
            doc['active_arm'].update(phase='B', phase_a=fa, after_a=after_a); save_progress(path, doc)
            fb = b.fit(m, mix, max_steps=a.b_steps, target_ce=-1.) if a.b_steps else b.fit(m, mix); r = {'seed': seed, 'arm': arm, 'phase_a': fa, 'after_a': after_a, 'phase_b': fb, 'after_b': b.split_eval(m),
                                     'rehearsal': [x for x in mix if x[0] not in {q for q, _, _ in B}], 'raw_generations': b.generation_trace}
            doc['runs'].append(r); doc['row_sha256'].append(digest(json.dumps(r, sort_keys=True, allow_nan=False)))
            print(json.dumps({'seed': seed, 'arm': arm, **{k: r['after_b'][k] for k in ('A', 'B', 'near_miss_leak', 'probe_retention')}, 'steps_b': fb['steps']}), flush=True)
            doc['seconds'] = round(elapsed+time.monotonic()-t0, 1); doc.pop('active_arm', None); save_progress(path, doc)
    doc['status'] = 'COMPLETE'; save_progress(path, doc)
    return 0

if __name__ == '__main__':
    sys.exit(main())
