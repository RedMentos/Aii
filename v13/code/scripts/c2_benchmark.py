"""C2 control benchmark (§57, G12C, WP-V7): Needle 3 vs FunctionGemma-270M vs the regex scaffold on route selection.

Same frozen corpus (specs/c2-benchmark.json, 4 routes, author labels from the select_processing tool definition) and the
same tool (specs/control_tools.json). Cloud comparison only: no candidate is promoted (§57 / G12C: separate JEF heads stay
the baseline, a sidecar may take over a concrete function only after success *and* a Redmi measurement).

Candidates
  scaffold             v13.cognition.scaffold_route (current C2 fallback, no model)
  needle               native Needle worker of an installed V13 home (setup.sh), actual `C` call, native confidence
  functiongemma_tool   FunctionGemma-270M (GGUF Q8_0, pinned) via llama-server --jinja, OpenAI `tools`, free tool choice
  functiongemma_forced same model, output constrained by a JSON schema with the route enum (upper bound of the head)

Metrics per candidate: accuracy, macro-F1, confusion, valid-call rate (a missing/invalid call counts as wrong),
latency p50/p95, peak RSS of the model process, file size; Needle also AUROC(confidence -> correct).
Usage: python3 scripts/c2_benchmark.py --home $V13_HOME --cache DIR --out DIR [--only needle scaffold ...]
"""
import argparse, json, os, re, sys, threading, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1])); sys.path.insert(0, str(Path(__file__).resolve().parent))
from v13.cognition import scaffold_route
from cloud_candidates import fetch, post, serve, sha256

APP = Path(__file__).resolve().parents[1]
ROUTES = ('simple', 'detail', 'gist', 'both')
NATIVE_CALL = re.compile(r'<start_function_call>call:select_processing\{route:(?:<escape>)?(simple|detail|gist|both)')
FG = {'id': 'functiongemma_270m', 'model_id': 'unsloth/functiongemma-270m-it-GGUF', 'revision': '1de0f7fc7cae0062012c2e91ef02e642c161aa57',
      'local_name': 'functiongemma-270m-it-Q8_0.gguf', 'size': 291558624,
      'sha256': '8a17a4eda2b28eaf685a487129fd5295eeff3f722b9c6451dd3d98c18c23a98d', 'license_id': 'gemma'}

def corpus():
    d = json.loads((APP/'specs/c2-benchmark.json').read_text())
    import hashlib
    if hashlib.sha256(json.dumps(d['items'], ensure_ascii=False, sort_keys=True).encode()).hexdigest() != d['items_sha256']:
        raise SystemExit('c2-benchmark corpus changed without re-freeze')
    return d

def tool():
    return json.loads((APP/'specs/control_tools.json').read_text())[0]

def route_of(args):
    if isinstance(args, str):
        try: args = json.loads(args)
        except Exception: m = re.search(r'\b(simple|detail|gist|both)\b', args); return m.group(1) if m else None
    r = args.get('route') if isinstance(args, dict) else None
    return r if r in ROUTES else None

def vmhwm(pid):
    try:
        for line in open(f'/proc/{pid}/status'):
            if line.startswith('VmHWM:'): return int(line.split()[1]) * 1024
    except Exception: return None

def auroc(scores, labels):
    pos = [s for s, l in zip(scores, labels) if l]; neg = [s for s, l in zip(scores, labels) if not l]
    if not pos or not neg: return None
    return sum((p > n) + .5*(p == n) for p in pos for n in neg) / (len(pos)*len(neg))

def summarize(rows, extra=None):
    n = len(rows); ok = [r['pred'] == r['label'] for r in rows]
    conf = {a: {b: sum(r['label'] == a and r['pred'] == b for r in rows) for b in ROUTES + (None,)} for a in ROUTES}
    f1 = []
    for c in ROUTES:
        tp = conf[c][c]; fp = sum(conf[a][c] for a in ROUTES if a != c); fn = sum(v for b, v in conf[c].items() if b != c)
        f1.append(0. if tp == 0 else 2*tp/(2*tp+fp+fn))
    lat = sorted(r['latency_s'] for r in rows)
    out = {'n': n, 'accuracy': round(sum(ok)/n, 4), 'macro_f1': round(sum(f1)/4, 4), 'per_class_f1': dict(zip(ROUTES, [round(x, 4) for x in f1])),
           'valid_rate': round(sum(r['pred'] is not None for r in rows)/n, 4),
           'latency_p50_s': round(lat[n//2], 4), 'latency_p95_s': round(lat[min(n-1, int(.95*n))], 4),
           'confusion': {a: {str(b): v for b, v in d.items() if v} for a, d in conf.items()}}
    return out | (extra or {})

def run_scaffold(items):
    rows = []
    for it in items:
        t0 = time.perf_counter(); p = scaffold_route(it['text'])
        rows.append({'id': it['id'], 'label': it['label'], 'pred': p, 'latency_s': time.perf_counter()-t0})
    return rows, {}

def run_needle(items, home):
    from v13.runtime import Runtime
    from v13.control_calibration_worker import observation
    r = Runtime(home); cancel = threading.Event(); rows = []; peak = 0
    try:
        r.needle.load(cancel, time.monotonic()+120)
        for it in items:
            t0 = time.perf_counter(); pred = conf = None; err = None; raw = None
            try:
                raw = r.needle.control(it['text'], cancel, time.monotonic()+60)
                calls = raw.get('function_calls') or []
                pred = next((route_of(c.get('arguments', {})) for c in calls if isinstance(c, dict) and route_of(c.get('arguments', {}))), None)
                conf = raw.get('confidence')
                try: observation(raw); valid = True
                except Exception as e: valid = False; err = 'validation:'+str(e)[:60]
            except Exception as e: err = type(e).__name__+':'+str(e)[:80]; valid = False
            rows.append({'id': it['id'], 'label': it['label'], 'pred': pred, 'latency_s': time.perf_counter()-t0, 'confidence': conf,
                         'validated': valid, 'error': err})
            if r.needle.proc: peak = max(peak, vmhwm(r.needle.proc.pid) or 0)
        model = r.models.path_for('C2_CONTROL')
        scored = [(x['confidence'], x['pred'] == x['label']) for x in rows if isinstance(x['confidence'], (int, float))]
        extra = {'peak_rss_bytes': peak or None, 'model_file': Path(model).name, 'model_bytes': Path(model).stat().st_size,
                 'validated_rate': round(sum(x['validated'] for x in rows)/len(rows), 4),
                 'confidence_auroc': None if not scored else auroc([s for s, _ in scored], [c for _, c in scored]),
                 'accuracy_validated_only': round(sum(x['pred'] == x['label'] for x in rows if x['validated'])/max(1, sum(x['validated'] for x in rows)), 4)}
        return rows, extra
    finally: r.close()

def run_needle_probe(items, home, folds=4, l2=1.):
    """Do Needle embeddings carry the route? Stratified k-fold softmax head on native `E` embeddings (C2.embedding_gain path).
    A probe of representation quality, not a deployable head (that is control_calibration / readouts with retention gates)."""
    import numpy as np
    from v13.runtime import Runtime
    r = Runtime(home); cancel = threading.Event()
    try:
        t0 = time.perf_counter(); X = np.array([r.needle.embed(it['text'], cancel, time.monotonic()+60) for it in items], dtype=float)
        emb_s = (time.perf_counter()-t0)/len(items)
    finally: r.close()
    X = X/np.maximum(np.linalg.norm(X, axis=1, keepdims=True), 1e-9); y = np.array([ROUTES.index(it['label']) for it in items])
    pred = np.zeros(len(items), dtype=int); idx = {c: [i for i in range(len(items)) if y[i] == c] for c in range(4)}
    for f in range(folds):
        te = [i for c in range(4) for k, i in enumerate(idx[c]) if k % folds == f]; tr = [i for i in range(len(items)) if i not in te]
        W = np.zeros((X.shape[1], 4)); b = np.zeros(4); Y = np.eye(4)[y[tr]]
        for _ in range(400):  # full-batch gradient descent, cross-entropy + L2
            Z = X[tr]@W+b; P = np.exp(Z-Z.max(1, keepdims=True)); P /= P.sum(1, keepdims=True)
            W -= .5*(X[tr].T@(P-Y)/len(tr)+l2*1e-2*W); b -= .5*(P-Y).mean(0)
        pred[te] = (X[te]@W+b).argmax(1)
    rows = [{'id': it['id'], 'label': it['label'], 'pred': ROUTES[p], 'latency_s': emb_s} for it, p in zip(items, pred)]
    return rows, {'embedding_dim': int(X.shape[1]), 'folds': folds, 'note': 'k-fold probe on author labels; deployable head = control_calibration with retention gate'}

def run_fg(items, home, cache, out, forced):
    server = next((Path(home)/'bin').glob('b*/llama-*/llama-server'))
    model = fetch(FG, Path(cache)); t = tool()
    fn = {'type': 'function', 'function': {'name': t['name'], 'description': t['description'], 'parameters': t['parameters']}}
    log = open(Path(out)/(('fg_forced' if forced else 'fg_tool')+'.server.log'), 'w')
    proc, port, state = serve(server, model, [], log); rows = []
    if state != 'OK': raise SystemExit('llama-server '+state)
    try:
        for it in items:
            t0 = time.perf_counter(); pred = None; err = None
            try:
                if forced:
                    body = {'messages': [{'role': 'system', 'content': 'Choose the processing route. '+t['description']}, {'role': 'user', 'content': it['text']}],
                            'temperature': 0, 'max_tokens': 24,
                            'response_format': {'type': 'json_schema', 'json_schema': {'name': 'route', 'schema': t['parameters']}}}
                    res = post(port, '/v1/chat/completions', body, 120); pred = route_of(res['choices'][0]['message'].get('content') or '')
                else:
                    body = {'messages': [{'role': 'developer', 'content': 'You are a model that can do function calling with the following functions'},
                                         {'role': 'user', 'content': it['text']}], 'tools': [fn], 'temperature': 0, 'max_tokens': 64}
                    msg = post(port, '/v1/chat/completions', body, 120)['choices'][0]['message']
                    calls = msg.get('tool_calls') or []
                    pred = next((route_of(c['function'].get('arguments')) for c in calls if c.get('function', {}).get('name') == t['name']), None)
                    if pred is None:  # llama.cpp b10964 does not parse FunctionGemma's native call syntax; read it from content
                        m = NATIVE_CALL.search(msg.get('content') or '')
                        pred = m.group(1) if m else None
                    if pred is None: err = 'no_tool_call:'+str(msg.get('content'))[:60]
            except Exception as e: err = type(e).__name__+':'+str(e)[:80]
            rows.append({'id': it['id'], 'label': it['label'], 'pred': pred, 'latency_s': time.perf_counter()-t0, 'error': err})
        return rows, {'peak_rss_bytes': vmhwm(proc.pid), 'model_file': FG['local_name'], 'model_bytes': model.stat().st_size,
                      'model_revision': FG['revision'], 'license_id': FG['license_id']}
    finally:
        proc.terminate()
        try: proc.wait(10)
        except Exception: proc.kill()
        log.close()

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--home', required=True); ap.add_argument('--cache', required=True)
    ap.add_argument('--out', required=True); ap.add_argument('--only', nargs='*'); a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True); Path(a.cache).mkdir(parents=True, exist_ok=True)
    d = corpus(); items = d['items']; report = {'schema': 'c2-benchmark-report-v1', 'corpus_sha256': d['items_sha256'], 'n': len(items),
        'label_source': d['label_source'], 'host': os.uname().machine, 'cpus': os.cpu_count(), 'claim_limit':
        'cloud x86 latency/RSS are not Redmi numbers; author labels; no production promotion', 'candidates': {}}
    runs = {'scaffold': lambda: run_scaffold(items), 'needle': lambda: run_needle(items, Path(a.home)), 'needle_embedding_probe': lambda: run_needle_probe(items, Path(a.home)),
            'functiongemma_tool': lambda: run_fg(items, a.home, a.cache, out, False), 'functiongemma_forced': lambda: run_fg(items, a.home, a.cache, out, True)}
    for name, fn in runs.items():
        if a.only and name not in a.only: continue
        print('run', name, flush=True)
        try:
            rows, extra = fn(); report['candidates'][name] = summarize(rows, extra)
            (out/f'{name}.rows.json').write_text(json.dumps(rows, indent=1))
        except BaseException as e: report['candidates'][name] = {'status': 'FAILED', 'error': type(e).__name__+': '+str(e)[:200]}
        print(name, json.dumps({k: v for k, v in report['candidates'][name].items() if k not in ('confusion', 'per_class_f1')}), flush=True)
    (out/'report.json').write_text(json.dumps(report, indent=1))

if __name__ == '__main__': main()
