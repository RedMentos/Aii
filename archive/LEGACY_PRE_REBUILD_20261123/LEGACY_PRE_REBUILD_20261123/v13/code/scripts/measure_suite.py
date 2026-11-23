#!/usr/bin/env python3
"""WP-N12: the §24 core benchmarks and §99 ablations as one command, plus register and gate audit.

  python3 scripts/measure_suite.py --out DIR            # model-free: runs the mapped unit tests once each
  python3 scripts/measure_suite.py --out DIR --models --server S --cache C   # + real-model benches available in the cloud

Status per benchmark: NOT_IMPLEMENTED | TEST_FAIL | TESTED (behaviour test only) | MEASURED (real-run artifact
with passing verdict) | MEASURED_FAILING (artifact says fail) | NEEDS_REDMI. Nothing is promoted; this is an audit.
"""
import argparse, io, json, subprocess, sys, time, unittest
from pathlib import Path

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP)); sys.path.insert(0, str(APP/'tests'))
from v13.gates import verdicts, summary as gate_summary  # noqa: E402
from v13.register import summary as register_summary  # noqa: E402

def run_tests(modules):
    out = {}
    for m in modules:
        stream = io.StringIO(); t0 = time.monotonic()
        try:
            suite = unittest.defaultTestLoader.loadTestsFromName(m)
            res = unittest.TextTestRunner(stream=stream, verbosity=0).run(suite)
            out[m] = {'ran': res.testsRun, 'failures': len(res.failures), 'errors': len(res.errors), 'skipped': len(res.skipped), 'ok': res.wasSuccessful(), 'seconds': round(time.monotonic()-t0, 2)}
        except Exception as exc: out[m] = {'ok': False, 'error': type(exc).__name__+': '+str(exc)[:200]}
    return out

def classify(b, tests):
    if not b['implemented']: return 'NOT_IMPLEMENTED'
    if b['tests'] and not all(tests[t]['ok'] for t in b['tests']): return 'TEST_FAIL'
    if b.get('verdict'): return 'MEASURED' if not verdicts(b) else 'MEASURED_FAILING'
    if b['needs'] == 'redmi': return 'NEEDS_REDMI'
    return 'MEASURED' if any(a.startswith('../bench-results/') for a in b['artifacts']) else 'TESTED'

def models(a, out):
    """Real-model benches that run in the cloud container (currently: semantic recall)."""
    res = {}
    if a.server and a.cache:
        p = subprocess.run([sys.executable, str(APP/'scripts/semantic_recall_bench.py'), '--server', a.server, '--cache', a.cache, '--out', str(out/'semantic_recall.json')],
                           capture_output=True, text=True, timeout=1800)
        res['semantic_recall'] = {'rc': p.returncode, 'tail': p.stdout[-400:] or p.stderr[-400:]}
    return res

def markdown(doc):
    lines = ['# V13 Messsuite '+doc['created_utc'], '', '| § | Benchmark | Status | Braucht | Hinweis |', '|---|---|---|---|---|']
    for b in doc['benchmarks']: lines.append(f"| {b['id']} | {b['title']} | {b['status']} | {b['needs']} | {b['note']} |")
    lines += ['', '## §99 Ablationen', '', '| Hypothese | Kontrollen vorhanden | fehlend |', '|---|---|---|']
    for x in doc['ablations']: lines.append(f"| {x['hypothesis']} | {', '.join(x['controls_available']) or '–'} | {', '.join(x['missing']) or '–'} |")
    g = doc['gates']['counts']; r = doc['register']
    lines += ['', f"Gates: {g}", f"Register: {r['blueprint_knobs']} Blueprint-Regler, {r['match']} im Code gleich, {r['drift']} abweichend, {r['declared_only']} nur deklariert (Abdeckung {r['coverage']:.0%})."]
    return '\n'.join(lines)+'\n'

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--out', required=True); ap.add_argument('--models', action='store_true')
    ap.add_argument('--server'); ap.add_argument('--cache'); a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    spec = json.loads((APP/'specs/benchmarks.json').read_text())
    tests = run_tests(sorted({t for b in spec['benchmarks'] for t in b['tests']}))
    rows = [b | {'status': classify(b, tests), 'verdict_failures': verdicts(b)} for b in spec['benchmarks']]
    abl = [x | {'missing': [c for c in x['controls'] if c not in x['controls_available']]} for x in spec['ablations']]
    counts = {}
    for b in rows: counts[b['status']] = counts.get(b['status'], 0)+1
    doc = {'schema': 'V13_MEASUREMENT_SUITE_RESULT_V1', 'created_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'counts': counts,
           'benchmarks': rows, 'ablations': abl, 'tests': tests, 'gates': gate_summary(), 'register': {k: v for k, v in register_summary().items() if k != 'groups'},
           'models': models(a, out) if a.models else None, 'rule': spec['rule'], 'phone_measured': False}
    (out/'suite.json').write_text(json.dumps(doc, indent=1, ensure_ascii=False)); (out/'SUITE.md').write_text(markdown(doc))
    print(json.dumps({'counts': counts, 'gates': doc['gates']['counts'], 'register_coverage': doc['register']['coverage'], 'out': str(out)}))
    return 0 if all(t['ok'] for t in tests.values()) else 1

if __name__ == '__main__':
    sys.exit(main())
