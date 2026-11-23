"""R4 (§31/§79): C-native vs. large-body wake, real C3/B1/B2 on the 60 WP-T3b tasks (cloud, English).

Canon R4 compares: always A+B, C_native only, heuristic selective wake, learned calibrated wake.
  c_native_only         observers off: C3 answers alone (no body offer, no background observer)
  c_native_only_repeat  same again: reproducibility of C3 alone (WP-T3b found the full runtime nondeterministic)
  always_ab             user-forced effort 'max': both bodies every turn (re-entry within cfg/Age limits)
  heuristic             shipped adaptive effort (scaffold signals pick none/one/both)
  learned_wake          adaptive + learned wake readout; recorded as UNAVAILABLE when no trained head decides
Same bench mode as WP-T3b (temperature 0, greedy C3, 600 s deadline, 180 s observers), fresh home per arm.
Metrics: pass rate per kind, wake rate (bodies that sent an offer), escalation recall = share of tasks that C3
alone fails but always_ab passes on which the selective arm woke at least one body, turn latency.
Claim limit: generated tasks, regex checks on the final answer, one seed; no energy or user-correction data.
Usage: r4_wake_bench.py <installed_home> <out.json> [arm,arm,...] [--limit N]"""
import json
import math
import shutil
import sys
import tempfile
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from v13.common import atomic_write  # noqa: E402
import utility_bench as U  # noqa: E402
import utility_bench2 as U2  # noqa: E402

ARMS = ('c_native_only', 'c_native_only_repeat', 'always_ab', 'heuristic', 'learned_wake')
SELECTIVE = ('heuristic', 'learned_wake')


def arm_cfg(arm):
    base = arm.replace('_repeat', '')
    return {'observer_mode': 'off'} if base == 'c_native_only' else {}


def run_arm(installed, arm, fixtures):
    from v13 import effort as EF
    from v13.config import initialize, save_config
    from v13.proofs import audit_event
    from v13.runtime import Runtime
    rows = []
    with tempfile.TemporaryDirectory(prefix='v13-r4-') as tmp:
        home = Path(tmp); cfg = initialize(home)
        for n in ('models', 'bin'):
            shutil.rmtree(home/n); (home/n).symlink_to(installed/n, target_is_directory=True)
        shutil.copyfile(installed/'config/models.json', home/'config/models.json')
        save_config(home, cfg | {'learning_mode': 'RECORD_ONLY', 'teacher_enabled': False, 'history_turns': 0}
                    | U2.BENCH_CFG | arm_cfg(arm))
        r = Runtime(home)
        if arm == 'always_ab':
            EF.set_mode(r.store, 'max')
        try:
            for fid, text, nums, checks in fixtures:
                r.session = r.store.new_session(); t0 = time.monotonic(); eid = r.submit(text); end = t0+900
                while not r.idle():
                    if time.monotonic() > end:
                        r.cancel(); break
                    time.sleep(.1)
                a = audit_event(r.store, eid); out = a.get('output') or ''; meta = a.get('output_metadata') or {}
                ok, num = U.score(out, nums, checks)
                wd = meta.get('wake_decision') or {}
                rows.append({'fixture': fid, 'arm': arm, 'pass': all(ok.values()) and all(num.values()),
                             'turn_s': round(time.monotonic()-t0, 2), 'status': a.get('status'),
                             'offers': sorted({o['role'] for o in a.get('offers', [])}),
                             'learned_wake': bool(wd.get('learned')), 'wake_decision': wd.get('action'),
                             'output': out[:400]})
                print(json.dumps({k: rows[-1][k] for k in ('arm', 'fixture', 'pass', 'turn_s', 'offers')}), flush=True)
        finally:
            r.close()
    return rows


def sign_test(wins, losses):
    n = wins+losses
    return 1. if n == 0 else min(1., 2*sum(math.comb(n, i) for i in range(min(wins, losses)+1))/2**n)


def paired(a, b):
    common = [f for f in a if f in b]
    w = sum(a[f]['pass'] and not b[f]['pass'] for f in common); l = sum(b[f]['pass'] and not a[f]['pass'] for f in common)
    return {'n': len(common), 'first_only_pass': w, 'second_only_pass': l, 'sign_test_p': round(sign_test(w, l), 4)}


def analyse(rows):
    by = {}
    for r in rows:
        by.setdefault(r['arm'], {})[r['fixture']] = r
    kinds = lambda fs: sorted({f.rstrip('0123456789') for f in fs})
    out = {'arms': {}, 'escalation': {}, 'reproducibility': {}}
    for arm, m in by.items():
        n = len(m); woke = [bool(r['offers']) for r in m.values()]
        out['arms'][arm] = {'n': n, 'pass_rate': round(sum(r['pass'] for r in m.values())/n, 3),
                            'by_kind': {k: round(sum(r['pass'] for f, r in m.items() if f.rstrip('0123456789') == k)
                                                 / sum(1 for f in m if f.rstrip('0123456789') == k), 3) for k in kinds(m)},
                            'wake_rate': round(sum(woke)/n, 3),
                            'offers_per_turn': round(sum(len(r['offers']) for r in m.values())/n, 3),
                            'mean_turn_s': round(sum(r['turn_s'] for r in m.values())/n, 2),
                            'learned_wake_turns': sum(r['learned_wake'] for r in m.values()),
                            'status_not_final': sum(r['status'] not in (None, 'FINAL') for r in m.values())}
    c, ab = by.get('c_native_only', {}), by.get('always_ab', {})
    rescuable = [f for f in c if f in ab and not c[f]['pass'] and ab[f]['pass']]
    simple = [f for f in c if c[f]['pass']]
    for arm in SELECTIVE:
        m = by.get(arm)
        if not m:
            continue
        esc = [f for f in rescuable if f in m and m[f]['offers']]
        spared = [f for f in simple if f in m and not m[f]['offers']]
        out['escalation'][arm] = {'rescuable_tasks': len(rescuable), 'woke_on_rescuable': len(esc),
                                  'escalation_recall': round(len(esc)/len(rescuable), 3) if rescuable else None,
                                  'c_native_solvable': len(simple), 'spared_on_solvable': len(spared),
                                  'passed_rescuable': sum(m[f]['pass'] for f in rescuable if f in m)}
    rep = by.get('c_native_only_repeat')
    if c and rep:
        common = [f for f in c if f in rep]
        out['reproducibility']['c_native_only'] = {'n': len(common),
                                                   'identical_output': sum(c[f]['output'] == rep[f]['output'] for f in common),
                                                   'pass_flips': sum(c[f]['pass'] != rep[f]['pass'] for f in common)}
    out['paired'] = {f'{x}_vs_{y}': paired(by[x], by[y]) for x, y in
                     (('c_native_only', 'always_ab'), ('c_native_only', 'heuristic'), ('always_ab', 'heuristic'))
                     if x in by and y in by}
    learned = by.get('learned_wake')
    if learned is not None:
        out['learned_wake_status'] = 'MEASURED' if any(r['learned_wake'] for r in learned.values()) else 'UNAVAILABLE_NO_TRAINED_HEAD'
    return out


def main(installed, out, arms=None, limit=None):
    installed = Path(installed).resolve(); out = Path(out); arms = arms.split(',') if arms else ARMS; fx = U2.tasks()
    if limit:
        fx = [f for i, f in enumerate(fx) if i % (len(fx)//limit) == 0][:limit]
    prev = json.loads(out.read_text()) if out.exists() else {'rows': []}
    rows = [r for r in prev['rows'] if r['arm'] not in arms]
    for arm in arms:
        rows += run_arm(installed, arm, fx)
        atomic_write(out, json.dumps({'kind': 'V13_R4_WAKE_BENCH', 'bench_cfg': U2.BENCH_CFG, 'fixtures': [f[0] for f in fx],
                                      **analyse(rows), 'rows': rows, 'phone_measured': False, 'canonical_gate_pass': False,
                                      'claim_limit': 'deterministic bench decoding, generated English tasks, regex checks on the final answer, one seed, cloud CPU'}, indent=1))
    print(json.dumps({k: v for k, v in analyse(rows).items()}, indent=1))


if __name__ == '__main__':
    a = sys.argv[1:]; lim = None
    if '--limit' in a:
        i = a.index('--limit'); lim = int(a[i+1]); del a[i:i+2]
    main(a[0], a[1], a[2] if len(a) > 2 else None, lim)
