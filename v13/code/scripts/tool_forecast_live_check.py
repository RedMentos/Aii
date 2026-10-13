#!/usr/bin/env python3
"""Live-path check of the SHADOW tool forecast (v13/toolforecast.py) with the parity-checked native encoder.

Every call goes through the runtime's own components in a fresh store: ToolForecast.predict before the effect, the
ToolRegistry IH-H14 transaction with the forecast in `predicted`, the outcome sink after the effect.
  calc        user-typed `calc` (origin USER, tool enabled) on start values no round ever used (1..999 minus the
              round-5 and round-7 worlds), and on out-of-range values 1000..9999.
  note        `Mark/make/uppercase note <name>` through ToolStep.plan -> propose_call -> `:tx approve` (this script
              approves as the user), on unused round-8 vocabulary notes and on free sentences outside that vocabulary.
Verdict rule (fixed in preregistration.json before the run): the two in-world arms pass when, per action, the mean
forecast MSE < .98 x min(mean copy MSE, mean mean-delta MSE), the candidate's own gate. Out-of-world arms are reported
only. No authority is granted; this measures the integration, not a new learning claim.
"""
import argparse
import json
import os
import platform
import resource
from pathlib import Path
import shutil
import sys
import time

import numpy as np

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))
from v13 import toolforecast as F
from v13 import toolstep as T
from v13.agi import hub
from v13.runtime import Runtime
from v13.transaction import operator_command as tx_command, settle_turn

SEED = 20261015
N_CALC, N_CALC_OOR, N_NOTE, N_FREE = 25, 10, 25, 10
FREE = ('Buy oat milk and two lemons.', 'Water the tomato plants on the balcony.', 'Renew the passport before June.',
        'Send the slides to Mara after lunch.', 'Fix the squeaky hinge in the kitchen.', 'Book a table for six on Saturday.',
        'Return the drill to Jonas.', 'Check the tyre pressure.', 'Read chapter four of the novel.', 'Back up the phone photos.')
CALC_PHRASE = {'double': '{n}*2', 'add_15': '{n}+15', 'quarter': '{n}/4', 'subtract_7': '{n}-7'}
NOTE_PHRASE = {'append_done': 'Mark note {name} as done', 'prefix_urgent': 'Make note {name} urgent', 'uppercase': 'Uppercase note {name}'}


def plan(restored):
    rng = np.random.default_rng(SEED)
    used = {e['value'] for p in ('round5-raw/r5world/world.json', 'round7-fresh-raw/world/world.json')
            for e in json.loads((Path(restored) / p).read_text())['episodes']}
    free_values = [v for v in range(1, 1000) if v not in used]
    seen_notes = {e['content'] for e in json.loads((Path(restored) / 'round8-note-tool-raw/world/world.json').read_text())['episodes']}
    unused_notes = sorted(F.NOTE_WORLD - seen_notes)
    return {'calc_in_world': sorted(rng.choice(free_values, N_CALC, replace=False).tolist()),
            'calc_out_of_range': sorted(rng.choice(np.arange(1000, 10000), N_CALC_OOR, replace=False).tolist()),
            'note_in_world': sorted(rng.choice(unused_notes, N_NOTE, replace=False).tolist()),
            'note_free': list(FREE[:N_FREE]),
            'counts': {'unused_values': len(free_values), 'unused_notes': len(unused_notes)}}


def verdict(rows):
    per = {}
    for r in rows:
        if r['status'] == 'SCORED':
            a = per.setdefault(r['action'], {'forecast': [], 'copy': [], 'mean_delta': []})
            for k in a:
                a[k].append(r['mse'][k])
    out = {a: {k: float(np.mean(v)) for k, v in m.items()} | {'n': len(m['forecast'])} for a, m in per.items()}
    for v in out.values():
        v['ratio_to_best_control'] = round(v['forecast'] / min(v['copy'], v['mean_delta']), 4)
        v['pass'] = v['forecast'] < .98 * min(v['copy'], v['mean_delta'])
    return out


def run(args, encoder_json=None):
    p = json.loads(Path(args.plan).read_text())['plan'] if args.plan else plan(args.restored)
    home = Path(args.out) / 'home'
    if home.exists():
        raise SystemExit('fresh output folder required')
    (home / 'data' / 'tool_forecast').mkdir(parents=True)
    shutil.copyfile(encoder_json or Path(args.encoder_home) / 'data' / 'tool_forecast' / 'encoder.json', home / 'data' / 'tool_forecast' / 'encoder.json')
    r = Runtime(home)
    rows = []
    try:
        r.sleep.cycle.set_policy('enabled', 'off')
        g = hub(r)
        tf = F.for_runtime(r)
        tf.set_mode('SHADOW')
        g.tools.enable('calc')
        g.tools.enable('sandbox_note')
        for arm in ('calc_in_world', 'calc_out_of_range'):
            for n in p[arm]:
                for action, expr in CALC_PHRASE.items():
                    e = r.store.event(r.session, 'calc ' + expr.format(n=n))
                    args_ = {'expression': expr.format(n=n)}
                    t0 = time.monotonic()
                    pred = tf.predict('calc', args_, e['event_id'])
                    tx = g.tools.call('calc', args_, origin='USER', predicted=pred, event_id=e['event_id'], idempotency_key=e['event_id'])
                    settle_turn(r, e['event_id'], 'FINAL')
                    rows.append(record(tf, arm, action, pred, tx, time.monotonic() - t0, n))
        sandbox = home / 'data' / 'tool_sandbox'
        sandbox.mkdir(parents=True, exist_ok=True)
        for arm in ('note_in_world', 'note_free'):
            for i, content in enumerate(p[arm]):
                for action, phrase in NOTE_PHRASE.items():
                    name = 'n%d_%s' % (i, arm.split('_')[1])
                    (sandbox / (name + '.txt')).write_text(content)   # setup outside the tool path, like round 8's setup write
                    text = phrase.format(name=name)
                    e = r.store.event(r.session, text)
                    t0 = time.monotonic()
                    ts = T.ToolStep(r)
                    pl = ts.plan(e, text)
                    pending = ts.propose_call(e, pl)
                    out = json.loads(tx_command(r, ['approve', pending['call_id']]))
                    tx = next(c for c in g.tools.box.load()[0]['calls'] if c['id'] == out['id'])
                    rows.append(record(tf, arm, action, tx.get('predicted'), tx, time.monotonic() - t0, content))
        report = {'schema': 'v13-tool-forecast-live-check-v1', 'utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                  'plan': p, 'encoder': json.loads((home / 'data' / 'tool_forecast' / 'encoder.json').read_text()),
                  'arms': {arm: verdict([x for x in rows if x['arm'] == arm]) for arm in ('calc_in_world', 'calc_out_of_range', 'note_in_world', 'note_free')},
                  'statuses': {s: sum(x['status'] == s for x in rows) for s in sorted({x['status'] for x in rows})},
                  'seconds_per_call_median': float(np.median([x['seconds'] for x in rows])),
                  'tap_process_max_rss_mb': round(resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss / 1024, 1),
                  'device': {'machine': platform.machine(), 'system': platform.system(), 'release': platform.release(),
                             'termux': 'com.termux' in os.environ.get('PREFIX', '')},
                  'runtime_report': tf.report()}
        gate_arms = ('calc_in_world', 'note_in_world')
        ok = report['statuses'].get('SCORED', 0) == len(rows) and all(
            v['pass'] for a in gate_arms for v in report['arms'][a].values()) and all(report['arms'][a] for a in gate_arms)
        report['verdict'] = 'LIVE_PATH_CONFIRMED' if ok else 'LIVE_PATH_NOT_CONFIRMED'
        report['claim_limit'] = ('Runtime components with a script acting as the user; closed rounds-7/8 worlds; Linux x86 cloud, '
                                 'not the Redmi. SHADOW only: nothing reads the forecast.')
    finally:
        r.close()
    out = Path(args.out)
    (out / 'rows.json').write_text(json.dumps(rows, indent=0) + '\n')
    (out / 'report.json').write_text(json.dumps(report, indent=1) + '\n')
    print(json.dumps({k: report[k] for k in ('verdict', 'statuses', 'seconds_per_call_median')} |
                     {'ratios': {a: {k: v['ratio_to_best_control'] for k, v in m.items()} for a, m in report['arms'].items()}}, indent=1))
    return 0


def record(tf, arm, action, pred, tx, seconds, state=None):
    rec = next((x for x in reversed(tf.box.load()[0]['scored']) if pred and x['id'] == pred['forecast_id']), None)
    return {'arm': arm, 'action': action, 'call': tx['id'], 'tool_status': tx['status'], 'forecast_id': (pred or {}).get('forecast_id'),
            'status': rec['status'] if rec else ('NO_FORECAST' if not pred else 'PENDING'), 'mse': (rec or {}).get('mse'),
            'in_world_range': (rec or {}).get('in_world_range'), 'outcome_text': (rec or {}).get('outcome_text'), 'seconds': round(seconds, 3),
            'state': state, 'competence': (rec or {}).get('competence'), 'ratio_to_best_control': (rec or {}).get('ratio_to_best_control')}


def main():
    a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    a.add_argument('command', choices=('plan', 'run'))
    a.add_argument('--restored', help='restored round-5/7/8 evidence (to draw the plan)')
    a.add_argument('--plan', help='fixed plan file instead, e.g. specs/tool_forecast/live-plan.json (phone)')
    a.add_argument('--encoder-home')
    a.add_argument('--out')
    args = a.parse_args()
    if not (args.restored or args.plan) or (args.command == 'plan' and not args.restored):
        a.error('--restored (or --plan for run) required')
    if args.command == 'plan':
        print(json.dumps(plan(args.restored), indent=1))
        return 0
    return run(args)


if __name__ == '__main__':
    sys.exit(main())
