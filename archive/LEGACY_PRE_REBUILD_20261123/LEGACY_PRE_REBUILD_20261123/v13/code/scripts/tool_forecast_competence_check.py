#!/usr/bin/env python3
"""Does the SHADOW tool forecast know, before the effect, when a call lies outside the world it was fitted on?

Each forecast now carries `competence` (v13/toolforecast.Checkpoint.competence): mean cosine distance of the call's
context tap to its 5 nearest training contexts, with a threshold calibrated on the calibration partition only
(scripts/install_tool_forecast.py build-competence). This check draws a fresh plan (states used by no round and not
by the earlier live check), runs it through the same live path as scripts/tool_forecast_live_check.py and scores the
pre-effect flag per unique context state:
  calc   in-world start values 1..999  vs  out-of-range 1000..9999
  note   unused round-8 vocabulary notes  vs  free sentences outside that vocabulary
Gates (fixed in preregistration.json before the run), per world: AUROC(distance; out = positive) >= .90, in-world
flagged as out-of-domain <= 10 %, out-of-world flagged >= 80 %. Report only: forecast/control ratio of flagged vs
unflagged calls. No authority: nothing reads the flag.
"""
import argparse
import json
from pathlib import Path
import sys

import numpy as np

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))
sys.path.insert(0, str(APP / 'scripts'))
from v13 import toolforecast as F
import tool_forecast_live_check as live

SEED = 20261016
N = 30
GATES = {'auroc_min': .90, 'in_world_flag_max': .10, 'out_of_world_flag_min': .80}
WORLDS = {'calc_counter': ('calc_in_world', 'calc_out_of_range'), 'note_edit': ('note_in_world', 'note_free')}
# Thirty one-line notes written for this check, outside the round-8 vocabulary and the live check's FREE list.
FREE = ('Pick up the dry cleaning before six.', 'Ask Lena about the spare key.', 'Defrost the freezer this weekend.',
        'Order new ink for the printer.', 'Call grandma on her birthday.', 'Cancel the gym membership.',
        'Bring the blue folder to the meeting.', 'Plant the garlic in October.', 'Feed the neighbours cat on Tuesday.',
        'Sort the receipts for the tax return.', 'Replace the smoke alarm battery.', 'Measure the window for curtains.',
        'Return the library books by Friday.', 'Charge the camera for the trip.', 'Write a thank-you card to Omar.',
        'Clean the gutters before winter.', 'Pay the parking fine online.', 'Find a recipe for lentil soup.',
        'Oil the bike chain.', 'Print the boarding passes.', 'Ask the landlord about the heating.',
        'Pack sunscreen and a hat.', 'Update the address at the bank.', 'Practise the speech twice.',
        'Bake a cake for the school fair.', 'Book the car for its inspection.', 'Label the moving boxes.',
        'Test the new router settings.', 'Buy stamps and envelopes.', 'Water the orchid once a week.')


def plan(restored):
    restored = Path(restored)
    earlier = json.loads((APP / 'specs/tool_forecast/live-plan.json').read_text())['plan']
    used = {e['value'] for p in ('round5-raw/r5world/world.json', 'round7-fresh-raw/world/world.json')
            for e in json.loads((restored / p).read_text())['episodes']} | set(earlier['calc_in_world'])
    seen = {e['content'] for e in json.loads((restored / 'round8-note-tool-raw/world/world.json').read_text())['episodes']}
    if set(FREE) & (F.NOTE_WORLD | set(live.FREE)) or len(set(FREE)) != N:
        raise ValueError('free notes must be new and outside the vocabulary')
    rng = np.random.default_rng(SEED)
    return {'calc_in_world': sorted(rng.choice([v for v in range(1, 1000) if v not in used], N, replace=False).tolist()),
            'calc_out_of_range': sorted(rng.choice([v for v in range(1000, 10000) if v not in set(earlier['calc_out_of_range'])],
                                                   N, replace=False).tolist()),
            'note_in_world': sorted(rng.choice(sorted(F.NOTE_WORLD - seen - set(earlier['note_in_world'])), N, replace=False).tolist()),
            'note_free': list(FREE)}


# Round 2 (v2 signal: last-token OR token-mean kNN test): thirty more new notes.
FREE2 = ('Swap the light bulb in the hall.', 'Ask Pavel for the drill bits.', 'Cancel the magazine subscription.',
         'Book the dentist for the twins.', 'Pickle the cucumbers.', 'Send the photos to Aunt Rosa.',
         'Patch the bicycle tyre.', 'Write a shopping list for the barbecue.', 'Ask the school about the trip form.',
         'Clean the bathroom grout.', 'Hand in the library card.', 'Order a cake for Friday.',
         'Turn off the water before the holiday.', 'Learn the chorus of the song.', 'Return the parcel to the shop.',
         'Mop the kitchen floor.', 'Update the phone software.', 'Buy a gift card for Sam.',
         'Wash the car on Sunday.', 'Plant tulips by the fence.', 'Check the bus times for Monday.',
         'Paint the bird house.', 'Pay the electricity bill.', 'Bring the ladder from the shed.',
         'Fix the squeaky door.', 'Sort the old magazines.', 'Ask Ivan about the football match.',
         'Clear the inbox before Friday.', 'Hem the new trousers.', 'Cook rice for the week.')
SEED2 = 20261019


def plan2(restored):
    """Fresh plan for the v2 signal: every state of the live, competence-1 and learning-1/2 plans excluded."""
    import tool_forecast_learning_check as lc
    restored = Path(restored)
    earlier = [json.loads((APP / 'specs/tool_forecast/live-plan.json').read_text())['plan'], plan(restored)]
    l1, l2 = lc.plan(restored, 1), lc.plan(restored, 2)
    calc_in = {v for p in earlier for v in p['calc_in_world']} | set(l1['calc_in_test']) | set(l2['calc_in_test'])
    calc_out = ({v for p in earlier for v in p['calc_out_of_range']} | set(l1['calc_shift_exp'] + l1['calc_shift_test'])
                | set(l2['calc_shift_exp'] + l2['calc_shift_test']))
    notes = {v for p in earlier for v in p['note_in_world']} | set(l1['note_in_test']) | set(l2['note_in_test'])
    used = {e['value'] for p in ('round5-raw/r5world/world.json', 'round7-fresh-raw/world/world.json')
            for e in json.loads((restored / p).read_text())['episodes']} | calc_in
    seen = {e['content'] for e in json.loads((restored / 'round8-note-tool-raw/world/world.json').read_text())['episodes']} | notes
    older = set(live.FREE) | set(FREE) | set(lc.FREE_EXP + lc.FREE_TEST + lc.FREE_EXP2 + lc.FREE_TEST2)
    if set(FREE2) & (F.NOTE_WORLD | older) or len(set(FREE2)) != N:
        raise ValueError('free notes must be new and outside the vocabulary')
    rng = np.random.default_rng(SEED2)
    return {'calc_in_world': sorted(rng.choice([v for v in range(1, 1000) if v not in used], N, replace=False).tolist()),
            'calc_out_of_range': sorted(rng.choice([v for v in range(1000, 10000) if v not in calc_out], N, replace=False).tolist()),
            'note_in_world': sorted(rng.choice(sorted(F.NOTE_WORLD - seen), N, replace=False).tolist()),
            'note_free': list(FREE2)}


def auroc(neg, pos):
    """P(distance of an out-of-world state > an in-world one), ties count half."""
    neg, pos = np.asarray(neg), np.asarray(pos)
    return float(((pos[:, None] > neg[None, :]).sum() + .5 * (pos[:, None] == neg[None, :]).sum()) / (len(pos) * len(neg)))


def analyze(rows, field='distance'):
    """Per world: one competence value per (arm, state); a state's calls share its pre-effect tap."""
    out = {}
    for world, (inside, outside) in WORLDS.items():
        states = {}
        for r in rows:
            if r['arm'] in (inside, outside):
                c = r['competence']
                states.setdefault((r['arm'], r['state']), c)
        d = {arm: [c[field] for (a, _), c in states.items() if a == arm] for arm in (inside, outside)}
        flag = {arm: float(np.mean([not c['in_domain'] for (a, _), c in states.items() if a == arm])) for arm in (inside, outside)}
        ratios = {k: [r['ratio_to_best_control'] for r in rows if r['arm'] in (inside, outside) and r['status'] == 'SCORED'
                      and (not r['competence']['in_domain']) == k] for k in (False, True)}
        res = {'states': {arm: len(v) for arm, v in d.items()}, 'auroc': round(auroc(d[inside], d[outside]), 4),
               'in_world_flag_rate': round(flag[inside], 4), 'out_of_world_flag_rate': round(flag[outside], 4),
               'distance_median': {arm: round(float(np.median(v)), 6) for arm, v in d.items()},
               'threshold': next(iter(states.values()))['threshold'],
               'report_only_ratio_geo_mean': {('flagged' if k else 'unflagged'): (round(float(np.exp(np.mean(np.log(v)))), 4) if v else None)
                                              for k, v in ratios.items()}}
        res['pass'] = (res['auroc'] >= GATES['auroc_min'] and res['in_world_flag_rate'] <= GATES['in_world_flag_max']
                       and res['out_of_world_flag_rate'] >= GATES['out_of_world_flag_min'])
        out[world] = res
    return {'worlds': out, 'gates': GATES,
            'verdict': 'COMPETENCE_SIGNAL_CONFIRMED' if all(v['pass'] for v in out.values()) else 'COMPETENCE_SIGNAL_NOT_CONFIRMED'}


def main():
    a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    a.add_argument('command', choices=('plan', 'run'))
    a.add_argument('--restored', required=True, help='restored round-5/7/8 evidence')
    a.add_argument('--encoder-home', help='home whose data/tool_forecast/encoder.json passed parity (run)')
    a.add_argument('--out', help='fresh output folder (run)')
    a.add_argument('--round', type=int, choices=(1, 2), default=2, help='1 = preregistered 8b15627 (last-token signal); 2 = v2 signal')
    args = a.parse_args()
    p = plan(args.restored) if args.round == 1 else plan2(args.restored)
    if args.command == 'plan':
        print(json.dumps(p, indent=1))
        return 0
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / 'plan.json').write_text(json.dumps({'plan': p}, indent=1) + '\n')
    live.run(argparse.Namespace(plan=str(out / 'plan.json'), restored=None, out=str(out / 'live'), encoder_home=args.encoder_home))
    rows = json.loads((out / 'live' / 'rows.json').read_text())
    report = analyze(rows, 'distance' if args.round == 1 else 'score') | {'schema': 'v13-tool-forecast-competence-check-v1', 'round': args.round, 'plan_counts': {k: len(v) for k, v in p.items()},
                              'live_verdict': json.loads((out / 'live' / 'report.json').read_text())['verdict'],
                              'claim_limit': 'Pre-effect domain flag of a SHADOW forecast on two closed worlds; Linux cloud, not the Redmi; '
                                             'nothing reads the flag.'}
    (out / 'report.json').write_text(json.dumps(report, indent=1) + '\n')
    print(json.dumps({k: report[k] for k in ('verdict',)} | {w: {k: v[k] for k in ('auroc', 'in_world_flag_rate', 'out_of_world_flag_rate', 'pass')}
                                                             for w, v in report['worlds'].items()}, indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main())
