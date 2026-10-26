#!/usr/bin/env python3
"""WP-Z6g: do body offers break correct C3 answers through unchecked numbers? Offer number guard, in-process only.

Z6e: every body arm broke 12-13 tasks C3 alone solved, mostly exact totals (the body hypothesis carries a wrong total
and C3 copies it). Guard (bench hook only, no runtime change): in the hypotheses handed to C3
(Cognition.analyst_context), every number in a body's summary that does not occur as a number in the user's message is
replaced by '[?]'. Source-verified quotes are exact substrings of the message and stay. Arms (fresh homes, Z6a/Z6e
bench mode): disabled, max, max+guard, max+hide (C3 sees no hypotheses at all), adaptive+guard on the Z6e task generator with a fresh seed.
Criteria G1-G3: docs/proofs/continuation-20261026/z6g-offer-number-guard/PREREG.md.
Usage: z6g_offer_number_guard.py <installed_home> <out.json> [--seed 43] [--arms disabled,max,max+guard,adaptive+guard] [--limit N]
"""
import argparse
import json
import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from v13.common import atomic_write  # noqa: E402
from z6a_effort_bench import run_arm  # noqa: E402
from z6e_wake_bench import fixtures, CLASS  # noqa: E402
import utility_bench2 as U2  # noqa: E402

NUM = re.compile(r'\d+(?:[.,]\d+)?')
MASKED = {'calls': 0, 'numbers': 0}


def guard_summary(summary, source):
    allowed = set(NUM.findall(source))
    return NUM.sub(lambda m: m.group(0) if m.group(0) in allowed else '[?]', summary)


def install_guard(on, hide=False):
    from v13.cognition import Cognition
    orig = getattr(Cognition, '_z6g_orig', None) or Cognition.analyst_context
    Cognition._z6g_orig = orig
    if not on:
        Cognition.analyst_context = orig; return
    def guarded(self, offers, e, version):
        out = orig(self, offers, e, version)
        if hide: MASKED['calls'] += 1; return []  # control: bodies still run, C3 sees no hypotheses
        src = self.s.read_source(e['source_ref'])
        for o in out:
            old = o['hypothesis'].get('summary') or ''; new = guard_summary(old, src)
            MASKED['calls'] += 1; MASKED['numbers'] += new.count('[?]')-old.count('[?]')
            o['hypothesis'] = dict(o['hypothesis'], summary=new)
        return out
    Cognition.analyst_context = guarded


def analyse(rows):
    by = {}
    for r in rows: by.setdefault(r['arm'], {})[r['fixture']] = r
    kind = lambda f: f.rstrip('0123456789')
    out = {'arms': {a: {'passed': sum(r['pass'] for r in m.values()), 'n': len(m), 'mean_turn_s': round(sum(r['turn_s'] for r in m.values())/len(m), 2),
                        'by_class': {CLASS[k]: sum(r['pass'] for f, r in m.items() if kind(f) == k) for k in CLASS}} for a, m in by.items()}}
    if not all(a in by for a in ('disabled', 'max', 'max+guard')): return out
    d, mx, g = by['disabled'], by['max'], by['max+guard']
    breaks = lambda arm: [f for f in d if d[f]['pass'] and not arm[f]['pass']]
    rescues = lambda arm: [f for f in d if not d[f]['pass'] and arm[f]['pass']]
    P = out['arms']
    crit = {'G1_guard_near_c_native': {'max+guard': P['max+guard']['passed'], 'disabled': P['disabled']['passed'], 'pass': P['max+guard']['passed'] >= P['disabled']['passed']-2},
            'G2_few_breaks': {'breaks': breaks(g), 'pass': len(breaks(g)) <= 4},
            'G3_guard_beats_unguarded': {'max+guard': P['max+guard']['passed'], 'max': P['max']['passed'], 'pass': P['max+guard']['passed'] >= P['max']['passed']+5}}
    out['criteria'] = crit; out['verdict'] = 'Z6G_NUMBER_GUARD_PASS' if all(c['pass'] for c in crit.values()) else 'Z6G_NUMBER_GUARD_FAIL'
    out['descriptive'] = {'breaks': {a: breaks(by[a]) for a in by if a != 'disabled'}, 'rescues': {a: rescues(by[a]) for a in by if a != 'disabled'}}
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('installed'); ap.add_argument('out'); ap.add_argument('--seed', type=int, default=43)
    ap.add_argument('--arms', default='disabled,max,max+guard,max+hide,adaptive+guard'); ap.add_argument('--limit', type=int)
    a = ap.parse_args(); installed = Path(a.installed).resolve(); out = Path(a.out); fx = fixtures(a.seed)
    if a.limit: fx = [f for i, f in enumerate(fx) if i % (len(fx)//a.limit) == 0][:a.limit]
    prev = json.loads(out.read_text()) if out.exists() else {'rows': []}; arms = a.arms.split(',')
    rows = [r for r in prev['rows'] if r['arm'] not in arms]; masked = prev.get('guard_hook', {})
    for arm in arms:
        mode, _, flag = arm.partition('+'); install_guard(flag in ('guard', 'hide'), hide=flag == 'hide'); MASKED.update(calls=0, numbers=0)
        try: new = run_arm(installed, mode, fx)
        finally: install_guard(False)
        for r in new: r['arm'] = arm
        rows += new; masked[arm] = dict(MASKED)
        atomic_write(out, json.dumps({'kind': 'V13_Z6G_OFFER_NUMBER_GUARD', 'seed': a.seed, 'bench_cfg': U2.BENCH_CFG, **analyse(rows), 'guard_hook': masked, 'rows': rows,
                                      'prereg': 'docs/proofs/continuation-20261026/z6g-offer-number-guard/PREREG.md', 'phone_measured': False,
                                      'claim_limit': 'in-process bench hook, not the runtime; generated English tasks, regex checks, one seed, cloud'}, indent=1))
    print(json.dumps({k: v for k, v in analyse(rows).items() if k != 'arms'}, indent=1))


if __name__ == '__main__':
    main()
