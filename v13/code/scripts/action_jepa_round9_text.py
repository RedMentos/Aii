#!/usr/bin/env python3
"""Action-JEPA round 9: the one text tap arm that held in round 7 (l_out-11 last token), on more never-used topics.

Round 7 text was NOT_CONFIRMED (11/30 runs), but l11_last passed 6/6 on a 72-episode test from only three topics.
This driver re-runs that arm with the unchanged scripts on a larger fresh test:
  generate  scripts/action_jepa_round3.py generate (C3, temperature 0, reserve rule) on the preregistered topics
  capture   round-3 mean-final capture (needed by the round-3 export) and round-4 native layer taps, layer 11 only
  export    round-3 export (train/calibration/retention = plan-v2 episodes, test = the new topics only), round-4 arm
  train     scripts/action_jepa_round6_ridge.py train, arms full/proj x seeds 13/21/34, dim 16
  report    per-run gates and the family verdict fixed in the preregistration
Every step writes into its own folder and is skipped when that folder already holds its result (resume).
Nothing here changes runtime code, native parameters or authority.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys

APP = Path(__file__).resolve().parents[1]
SCRIPTS = APP / 'scripts'
sys.path.insert(0, str(SCRIPTS))
from export_action_jepa_dataset import sha

BENCH = APP.parent / 'bench-results'
OLD_SENTENCES = BENCH / 'jepa-ablation-20261010/sentences.json'
OLD_ACTIONS = BENCH / 'jepa-action-20261010/actions.json'
OLD_PLAN = APP / 'docs/proofs/continuation-20261011/action-jepa-preregistered-plan-v2.json'
ARM = 'l11_last'
RUNS = [(arm, seed) for arm in ('full', 'proj') for seed in (13, 21, 34)]


def check_preregistration(prereg):
    """Sources unchanged since registration; fresh topics never generated, captured or scored before."""
    for rel, want in prereg['sources'].items():
        if sha(APP / rel) != want:
            raise ValueError('Source changed since preregistration: ' + rel)
    for path, want in prereg['inputs'].items():
        if sha(APP / path) != want:
            raise ValueError('Input changed since preregistration: ' + path)
    new = prereg['fresh_topics'] + prereg['reserve_topics']
    if len(set(new)) != len(new) or set(new) & set(prereg['topics_used_before']):
        raise ValueError('Fresh/reserve topics must be distinct and never used before')


def step(name, out, command, env=None):
    done = out / '.done.json'
    if done.exists():
        return json.loads(done.read_text())
    out.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env)
    (out / ('%s.log' % name)).write_bytes(proc.stdout)
    if proc.returncode:
        raise RuntimeError('%s failed (%d), see %s' % (name, proc.returncode, out / ('%s.log' % name)))
    last = proc.stdout.decode(errors='replace').strip().split('\n')[-1]
    record = {'step': name, 'command': command, 'utc': datetime.now(timezone.utc).isoformat(), 'result': json.loads(last)}
    done.write_text(json.dumps(record, indent=1) + '\n')
    return record


def run(args):
    prereg_path = Path(args.preregistration).resolve()
    prereg = json.loads(prereg_path.read_text())
    check_preregistration(prereg)
    w = Path(args.work).resolve()
    py = [sys.executable, '-I']
    gen = w / 'generation'
    step('generate', gen, py + [str(SCRIPTS / 'action_jepa_round3.py'), 'generate', '--server', args.server,
                                '--model', args.c3, '--preregistration', str(prereg_path), '--out', str(gen)])
    fresh = ['--old-sentences', str(OLD_SENTENCES), '--old-actions', str(OLD_ACTIONS),
             '--fresh-sentences', str(gen / 'fresh-sentences.json'), '--fresh-actions', str(gen / 'fresh-actions.json')]
    mean = w / 'capture-mean-final'
    step('capture-mean-final', mean, py + [str(SCRIPTS / 'action_jepa_round3.py'), 'capture', *fresh, '--server', args.server,
                                           '--model', args.b2, '--out', str(mean)])
    layers = w / 'capture-layers'
    env = dict(os.environ, V13_GGML_BACKEND_DIR=args.backend_dir) if args.backend_dir else None
    step('capture-layers', layers, py + [str(SCRIPTS / 'action_jepa_round4.py'), 'capture', '--tool', args.tool, '--model', args.b2,
                                         '--round3-taps', str(mean / 'taps.npz'), '--layers', '11', '--out', str(layers),
                                         '--threads', str(args.threads)], env=env)
    r3 = w / 'export-round3'
    step('export-round3', w / 'export-round3-log', py + [str(SCRIPTS / 'action_jepa_round3.py'), 'export', *fresh,
                                                         '--old-plan', str(OLD_PLAN), '--taps', str(mean / 'taps.npz'),
                                                         '--registration', str(mean / 'registration.json'), '--out', str(r3)])
    arm = w / ('export-' + ARM)
    step('export-' + ARM, w / ('export-%s-log' % ARM), py + [str(SCRIPTS / 'action_jepa_round4.py'), 'export', '--round3-export', str(r3),
                                                            '--taps', str(layers / ('taps-%s.npz' % ARM)),
                                                            '--capture-report', str(layers / 'capture-report.json'),
                                                            '--arm', ARM, '--out', str(arm)])
    for kind, seed in RUNS:
        out = w / 'results' / ('%s-%s-s%d' % (ARM, kind, seed))
        step('train', out, py + [str(SCRIPTS / 'action_jepa_round6_ridge.py'), 'train', '--dataset', str(arm / 'dataset.json'),
                                 '--out', str(out), '--seed', str(seed), '--arm', kind, '--dim', '16'])
    report = summarize(w, prereg, prereg_path)
    (w / 'report.json').write_text(json.dumps(report, indent=1) + '\n')
    print(json.dumps({k: report[k] for k in ('verdict', 'passes', 'test_episodes', 'test_topics')}))
    return report


def summarize(w, prereg, prereg_path):
    runs = {}
    for kind, seed in RUNS:
        m = json.loads((w / 'results' / ('%s-%s-s%d' % (ARM, kind, seed)) / 'metrics.json').read_text())
        test = m['after']['test']['per_action']
        runs['%s-s%d' % (kind, seed)] = {
            'pass': m['candidate_gate_pass'], 'gates': m['gates'], 'checkpoint_sha256': m['checkpoint_sha256'],
            'test_ratio_to_best_control': {m['actions'][int(j)]: round(v['prediction_mse'] / min(v['copy_mse'], v['mean_delta_mse'], v['shuffled_target_mse']), 4)
                                           for j, v in test.items()},
            'retention_delta': {m['actions'][int(j)]: v['prediction_mse'] - m['before']['retention']['per_action'][j]['prediction_mse']
                                for j, v in m['after']['retention']['per_action'].items()}}
    passes = sum(r['pass'] for r in runs.values())
    gen = json.loads((w / 'generation' / 'generation-report.json').read_text())
    receipt = json.loads((w / 'export-round3' / 'export-receipt.json').read_text())
    return {'schema': 'v13-action-jepa-round9-text-report-v1', 'utc': datetime.now(timezone.utc).isoformat(),
            'preregistration_sha256': sha(prereg_path), 'arm': ARM, 'runs': runs, 'passes': passes, 'of': len(runs),
            'verdict': 'CONFIRMED' if passes > len(runs) / 2 else 'NOT_CONFIRMED',
            'test_topics': gen['topics'], 'sentences': gen['sentences'], 'test_episodes': receipt['episodes']['test'],
            'episodes': receipt['episodes'], 'excluded_fresh': receipt['excluded_fresh'],
            'capture_layers': json.loads((w / 'capture-layers' / 'capture-report.json').read_text()),
            'receiver_authority': 0, 'learn_authority': 0, 'runtime_integrated': False, 'canonical_architecture_complete': False,
            'claim_limit': prereg['decision_rule']}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='command', required=True)
    c = sub.add_parser('check')
    c.add_argument('--preregistration', required=True)
    r = sub.add_parser('run')
    for name in ('--preregistration', '--work', '--server', '--c3', '--b2', '--tool'):
        r.add_argument(name, required=True)
    r.add_argument('--backend-dir', default=None, help='ggml backend folder for a GGML_BACKEND_DL tap build (pinned release)')
    r.add_argument('--threads', type=int, default=4)
    args = ap.parse_args()
    if args.command == 'check':
        check_preregistration(json.loads(Path(args.preregistration).read_text()))
        print(json.dumps({'status': 'PREREGISTRATION_MATCHES_SOURCES'}))
        return 0
    run(args)
    return 0


if __name__ == '__main__':
    sys.exit(main())
