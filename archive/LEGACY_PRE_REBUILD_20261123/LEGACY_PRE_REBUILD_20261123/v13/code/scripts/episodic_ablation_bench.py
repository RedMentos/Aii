#!/usr/bin/env python3
"""WP-T14 / §99 row "Episodic fast memory helps": experience retrieval vs response cache vs no memory vs param delta.

C3 = LFM2.5-230M master (torch fp32), same 8 invented facts / 6 paraphrases / 5 near-miss / 12 probes as lora_bench.
Arms (each answers every question; nothing is trained except in param_delta):
  no_memory        the frozen base
  response_cache   exact question -> stored answer string, else base (the §99 trap: must not count as learning)
  retrieval        V13 Fast Episodic: lexical `memory.relevance` over stored (question, answer) records with the runtime
                   threshold, best record injected as a source-tagged note before the question; base weights frozen
  param_delta      sparse-memory keyed slots trained on the facts (WP-S3), no context
§99: "No positive result may be claimed from a benchmark that allows response caching to fake learning" -> the cache arm
must win only on the exact wording; a mechanism counts only if it beats the cache on paraphrases without leaking on
near-miss questions or hurting probes.
  python3 scripts/episodic_ablation_bench.py --master DIR --out bench-results/episodic-ablation-<date>
"""
import argparse, json, platform, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1])); sys.path.insert(0, str(Path(__file__).resolve().parent))
from lora_bench import FACTS, PARAPHRASES, NEAR_MISS, PROBES  # noqa: E402
from sparse_memory_bench import Bench, METHODS  # noqa: E402
from v13.lora_trainer import answer_hit  # noqa: E402
from v13.memory import relevance  # noqa: E402
from v13.config import KNOBS  # noqa: E402

THRESHOLD = KNOBS['memory_threshold'][0]
RECORDS = [(q, a) for q, a, _ in FACTS]

def retrieve(query):
    best = max(((relevance(query, q+' '+a), q, a) for q, a in RECORDS), default=(0., None, None))
    return best if best[0] >= THRESHOLD else (best[0], None, None)

class Ablation(Bench):
    def answer(self, model, arm, q, n=24):
        if arm == 'response_cache':
            hit = next((a for k, a in RECORDS if k == q), None)
            if hit: return hit, {'cache_hit': True}
        if arm == 'retrieval':
            score, key, ans = retrieve(q)
            if ans:
                prompt = 'Stored note from the user (source, not a guess): %s\n\nQuestion: %s' % (ans, q)
                return self.gen(model, prompt, n), {'retrieved': key, 'score': round(score, 3)}
            return self.gen(model, q, n), {'retrieved': None, 'score': round(score, 3)}
        return self.gen(model, q, n), {}
    def evaluate_arm(self, model, arm):
        rows = {}
        for name, items in (('exact', [(q, k) for q, _, k in FACTS]), ('paraphrase', PARAPHRASES), ('near_miss', NEAR_MISS)):
            rs = []
            for q, keys in items:
                out, info = self.answer(model, arm, q); rs.append({'q': q, 'hit': answer_hit(out, keys), 'out': out[:120]} | info)
            rows[name] = rs
        probes = []
        for p in PROBES:
            out, info = self.answer(model, arm, p['prompt'], 32); probes.append({'q': p['prompt'], 'hit': answer_hit(out, p['expect'])} | info)
        rate = lambda rs: sum(r['hit'] for r in rs)/len(rs)
        return {'exact_recall': rate(rows['exact']), 'paraphrase_recall': rate(rows['paraphrase']), 'near_miss_leak': rate(rows['near_miss']),
                'probe_retention': rate(probes), 'retrieved_on_near_miss': sum(1 for r in rows['near_miss'] if r.get('retrieved')),
                'retrieved_on_probes': sum(1 for r in probes if r.get('retrieved')), 'rows': rows}

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--master', required=True); ap.add_argument('--out', required=True); ap.add_argument('--threads', type=int, default=4); a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True); b = Ablation(a.master, a.threads); t0 = time.monotonic()
    doc = {'schema': 'v13-episodic-ablation-v1', 'experiment': 'blueprint §99 Episodic fast memory helps', 'date': time.strftime('%Y-%m-%d'), 'platform': platform.platform(),
           'memory_threshold': THRESHOLD, 'arms': {}, 'claim_limit': '230M master, 8 facts, one seed; retrieval = lexical runtime path without embeddings'}
    base = b.fresh()
    for arm in ('no_memory', 'response_cache', 'retrieval'):
        doc['arms'][arm] = b.evaluate_arm(base, arm); print(arm, json.dumps({k: v for k, v in doc['arms'][arm].items() if k != 'rows'}), flush=True)
    b.reference(); r = b.run('param_delta', METHODS['smf_keyed_r90'])
    doc['arms']['param_delta'] = {'exact_recall': r['eval']['learned_recall'], 'paraphrase_recall': r['eval']['paraphrase_recall'], 'near_miss_leak': r['eval']['near_miss_leak'],
                                  'probe_retention': r['eval']['probe_retention'], 'kl_to_base': r['eval']['kl_to_base'], 'trainable_parameters': r['train']['trainable_parameters']}
    print('param_delta', json.dumps(doc['arms']['param_delta']), flush=True)
    doc['seconds'] = round(time.monotonic()-t0, 1); (out/'episodic_ablation.json').write_text(json.dumps(doc, indent=1)); return 0

if __name__ == '__main__':
    sys.exit(main())
