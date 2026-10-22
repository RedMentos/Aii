#!/usr/bin/env python3
"""Can the SHADOW tool forecast keep learning from its own scored calls without forgetting its measured world?

Phase A (experience): live calls outside the fitted world (calc counters 1000..9999, free one-line notes) run through
the same path as scripts/tool_forecast_live_check.py; each scored call joins the experience buffer.
Learn: `:toolforecast learn` (v13/toolforecast.learn: anchored ridge per action, lambda on the newest quarter of the
experience, retention gate on the install retention taps). The measured checkpoint is never changed.
Phase B (test, fresh states): the same shifted kinds of call plus fresh in-world calls; every forecast now carries
the measured and the adapted prediction, both scored against the observed outcome.
Gates (fixed in preregistration.json before the run), per world:
  learn passed (at least one adapted action),
  shifted test: adapted mean MSE < .90 x measured for more than half of the actions,
  in-world test: adapted mean MSE <= 1.02 x measured for every action.
CONTINUAL_LEARNING_CONFIRMED only if both worlds pass. No authority: nothing reads either forecast.
"""
import argparse
import json
from pathlib import Path
import shutil
import sys
import time

import numpy as np

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))
sys.path.insert(0, str(APP / 'scripts'))
from v13 import toolforecast as F
from v13.agi import hub
from v13.runtime import Runtime
import tool_forecast_competence_check as cc
import tool_forecast_live_check as live

SEED = 20261017
GATES = {'shift_gain_max_ratio': .90, 'in_world_max_ratio': 1.02}
WORLDS = {'calc_counter': ('calc_shift_test', 'calc_in_test'), 'note_edit': ('note_shift_test', 'note_in_test')}
EXP_ARMS = ('calc_shift_exp', 'note_shift_exp')
# Fifty one-line notes written for this check; none in the round-8 vocabulary or an earlier check's list.
FREE_EXP = ('Repaint the garden fence in May.', 'Ask Priya for the cake recipe.', 'Renew the car insurance.',
            'Collect the parcel from the kiosk.', 'Swap the winter tyres.', 'Sharpen the kitchen knives.',
            'Send the invoice to the client.', 'Try the new bakery on Elm Street.', 'Fix the dripping tap in the bathroom.',
            'Call the vet about the vaccination.', 'Buy a birthday present for Tom.', 'Read the contract before signing.',
            'Hang the picture in the hallway.', 'Plan the route for the hike.', 'Empty the dishwasher.',
            'Look up train times to Leeds.', 'Wash the curtains.', 'Reply to the survey from school.',
            'Change the password for the router.', 'Recycle the old batteries.', 'Fill in the visa form.',
            'Bring a jacket for the boat trip.', 'Polish the black shoes.', 'Restring the old guitar.',
            'Prune the apple tree.', 'Scan the signed lease.', 'Top up the bus card.', 'Check the smoke in the chimney.',
            'Practise the piano scales.', 'Order a new phone case.')
FREE_TEST = ('Clear the snow from the steps.', 'Write the minutes of the meeting.', 'Sew the button back on the coat.',
             'Ask Jonah to feed the fish.', 'Glue the broken mug.', 'Tune the bike brakes.', 'Bake bread for Sunday.',
             'Air out the guest room.', 'Note the meter reading.', 'Find the warranty for the fridge.',
             'Tidy the garage shelves.', 'Ring the hotel about late arrival.', 'Mend the hole in the sock.',
             'Pick strawberries at the farm.', 'Rinse the paint brushes.', 'Download the concert tickets.',
             'Weigh the suitcase before leaving.', 'Return the borrowed ladder.', 'Wipe the kitchen windows.',
             'Learn ten words of Italian.')


# Round 2 (region mode, complementary memory): fifty more new notes.
FREE_EXP2 = ('Defrost the chicken for dinner.', 'Ask Marta to return the umbrella.', 'Renew the fishing licence.',
             'Clean the oven racks.', 'Phone the garage about the noise.', 'Buy seeds for the window box.',
             'Write a review of the hotel.', 'Move the meeting to Thursday.', 'Check the expiry date of the milk.',
             'Fold the laundry before lunch.', 'Text Ben the address.', 'Bring cupcakes to the office.',
             'Sweep the balcony.', 'Rename the holiday photo folder.', 'Return the rental skis.',
             'Book a haircut for Saturday.', 'Collect the keys from Anna.', 'Unsubscribe from the newsletter.',
             'Charge the electric toothbrush.', 'Ask the bakery about gluten free bread.', 'Fix the wobbly chair leg.',
             'Make a list for the camping trip.', 'Drop the coats at the charity shop.', 'Set an alarm for the early train.',
             'Thaw the peas for the soup.', 'Find the passport photos.', 'Call the council about the bin.',
             'Brush the dog after the walk.', 'Back up the work laptop.', 'Pay back Lucy for the tickets.')
FREE_TEST2 = ('Buy a frame for the poster.', 'Test the garden hose for leaks.', 'Clean the fish tank filter.',
              'Ask Olga about the night shift.', 'Wrap the gift for the wedding.', 'Measure the sofa for the new room.',
              'Ring the pharmacy about the order.', 'Iron the shirt for the interview.', 'Paint the door handle.',
              'Count the chairs for the party.', 'Store the summer clothes.', 'Visit the market on the square.',
              'Order the textbook for the course.', 'Repair the zip on the backpack.', 'Fill the car with petrol.',
              'Water the herbs on the sill.', 'Send flowers to the hospital.', 'Delete the old voicemails.',
              'Bake cookies with the kids.', 'Rake the leaves in the yard.')
ROUNDS = {1: {'seed': SEED, 'mode': 'one weight, no replay (code at f4a3c82)', 'exp': FREE_EXP, 'test': FREE_TEST},
          2: {'seed': 20261018, 'mode': 'region', 'exp': FREE_EXP2, 'test': FREE_TEST2}}


def plan(restored, round_=1):
    restored = Path(restored)
    earlier = [json.loads((APP / 'specs/tool_forecast/live-plan.json').read_text())['plan'], cc.plan(restored)]
    if round_ == 2:
        p1 = plan(restored, 1)
        earlier.append({'calc_in_world': p1['calc_in_test'], 'calc_out_of_range': p1['calc_shift_exp'] + p1['calc_shift_test'],
                        'note_in_world': p1['note_in_test']})
    cfg = ROUNDS[round_]
    used_in = {e['value'] for p in ('round5-raw/r5world/world.json', 'round7-fresh-raw/world/world.json')
               for e in json.loads((restored / p).read_text())['episodes']} | {v for p in earlier for v in p['calc_in_world']}
    used_out = {v for p in earlier for v in p['calc_out_of_range']}
    seen = {e['content'] for e in json.loads((restored / 'round8-note-tool-raw/world/world.json').read_text())['episodes']}
    seen |= {v for p in earlier for v in p['note_in_world']}
    free = set(cfg['exp']) | set(cfg['test'])
    older = set(live.FREE) | set(cc.FREE) | (set(FREE_EXP) | set(FREE_TEST) if round_ == 2 else set())
    if len(free) != len(cfg['exp']) + len(cfg['test']) or free & (F.NOTE_WORLD | older):
        raise ValueError('free notes must be new and outside the vocabulary')
    rng = np.random.default_rng(cfg['seed'])
    out = rng.choice([v for v in range(1000, 10000) if v not in used_out], 70, replace=False).tolist()
    return {'calc_shift_exp': sorted(out[:40]), 'calc_shift_test': sorted(out[40:]),
            'calc_in_test': sorted(rng.choice([v for v in range(1, 1000) if v not in used_in], 30, replace=False).tolist()),
            'note_shift_exp': list(cfg['exp']), 'note_shift_test': list(cfg['test']),
            'note_in_test': sorted(rng.choice(sorted(F.NOTE_WORLD - seen), 20, replace=False).tolist())}


def analyze(rows, learn_report):
    out = {}
    for world, (shift, inside) in WORLDS.items():
        res = {'learn': {k: learn_report[world].get(k) for k in ('pass', 'reason', 'experience_rows', 'adapted_actions')}}
        for arm in (shift, inside):
            per = {}
            for r in rows:
                if r['arm'] == arm and r['status'] == 'SCORED':
                    a = per.setdefault(r['action'], {'measured': [], 'adapted': [], 'copy': [], 'mean_delta': []})
                    a['measured'].append(r['mse']['forecast'])
                    a['adapted'].append(r['mse'].get('adapted', r['mse']['forecast']))
                    a['copy'].append(r['mse']['copy'])
                    a['mean_delta'].append(r['mse']['mean_delta'])
            res[arm] = {act: {k: float(np.mean(v)) for k, v in m.items()} | {'n': len(m['measured'])} for act, m in per.items()}
            for v in res[arm].values():
                v['adapted_vs_measured'] = round(v['adapted'] / v['measured'], 4)
                v['adapted_to_best_control'] = round(v['adapted'] / min(v['copy'], v['mean_delta']), 4)
                v['measured_to_best_control'] = round(v['measured'] / min(v['copy'], v['mean_delta']), 4)
        gains = [v['adapted_vs_measured'] < GATES['shift_gain_max_ratio'] for v in res[shift].values()]
        res['shift_actions_improved'] = sum(gains)
        res['pass'] = bool(res['learn']['pass'] and res[shift] and res[inside] and sum(gains) > len(gains) / 2
                           and all(v['adapted_vs_measured'] <= GATES['in_world_max_ratio'] for v in res[inside].values()))
        out[world] = res
    return {'worlds': out, 'gates': GATES,
            'verdict': 'CONTINUAL_LEARNING_CONFIRMED' if all(v['pass'] for v in out.values()) else 'CONTINUAL_LEARNING_NOT_CONFIRMED'}


def run(args):
    if getattr(args, 'plan', None):   # fixed plan file (phone): specs/tool_forecast/learning-plan.json, region mode
        doc = json.loads(Path(args.plan).read_text())
        p, args.round = doc['plan'], doc['round']
    else:
        p = plan(args.restored, args.round)
    out = Path(args.out)
    home = out / 'home'
    if home.exists():
        raise SystemExit('fresh output folder required')
    (home / 'data' / 'tool_forecast').mkdir(parents=True)
    (out / 'plan.json').write_text(json.dumps({'plan': p}, indent=1) + '\n')
    shutil.copyfile(Path(args.encoder_home) / 'data' / 'tool_forecast' / 'encoder.json', home / 'data' / 'tool_forecast' / 'encoder.json')
    r = Runtime(home)
    rows, t0 = [], time.monotonic()
    try:
        r.sleep.cycle.set_policy('enabled', 'off')
        g = hub(r)
        tf = F.for_runtime(r)
        tf.set_mode('SHADOW')
        g.tools.enable('calc')
        g.tools.enable('sandbox_note')
        live.run_arms(r, g, tf, p, EXP_ARMS, rows)
        learned = tf.learn(mode='region' if args.round == 2 else 'mixed')
        (out / 'learn.json').write_text(json.dumps(learned, indent=1) + '\n')
        live.run_arms(r, g, tf, p, ('calc_shift_test', 'calc_in_test', 'note_shift_test', 'note_in_test'), rows)
        report = analyze([x for x in rows if x['arm'] not in EXP_ARMS], learned) | {
            'schema': 'v13-tool-forecast-learning-check-v1', 'round': args.round, 'utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            'plan_counts': {k: len(v) for k, v in p.items()},
            'statuses': {s: sum(x['status'] == s for x in rows) for s in sorted({x['status'] for x in rows})},
            'experience_phase_ratio_to_best_control': live.verdict([x for x in rows if x['arm'] in EXP_ARMS]),
            'encoder': {k: json.loads((home / 'data/tool_forecast/encoder.json').read_text())[k] for k in ('tool_sha256', 'model_sha256')},
            'runtime_report': tf.report(), 'minutes': round((time.monotonic() - t0) / 60, 1),
            'claim_limit': 'Closed-form adapted residual next to the measured candidate, two closed worlds, Linux cloud, not the Redmi; '
                           'SHADOW only, nothing reads either forecast.'}
    finally:
        r.close()
    (out / 'rows.json').write_text(json.dumps(rows, indent=0) + '\n')
    (out / 'report.json').write_text(json.dumps(report, indent=1) + '\n')
    print(json.dumps({'verdict': report['verdict']} | {w: {k: v[k] for k in ('pass', 'shift_actions_improved', 'learn')}
                                                       for w, v in report['worlds'].items()}, indent=1))
    return 0


def main():
    a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    a.add_argument('command', choices=('plan', 'run'))
    a.add_argument('--restored', help='restored round-5/7/8 evidence (to draw the plan)')
    a.add_argument('--plan', help='fixed plan file instead (run), e.g. specs/tool_forecast/learning-plan.json')
    a.add_argument('--encoder-home', help='home whose encoder.json passed parity and carries retention taps (run)')
    a.add_argument('--out')
    a.add_argument('--round', type=int, choices=(1, 2), default=2, help='1 = preregistered f4a3c82 (one weight, no replay); 2 = region mode')
    args = a.parse_args()
    if not (args.restored or (args.plan and args.command == 'run')):
        a.error('--restored (or --plan for run) required')
    if args.command == 'plan':
        print(json.dumps(plan(args.restored, args.round), indent=1))
        return 0
    return run(args)


if __name__ == '__main__':
    sys.exit(main())
