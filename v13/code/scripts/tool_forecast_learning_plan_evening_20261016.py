"""Generate a 610-row plan with fresh shifted cases and fixed retention repeats.

Only reads checkpoint metadata and historical plans; does not load models or
execute tools. The seed and 50 free notes are fixed before any new outcome.
"""
import argparse
import hashlib
import json
from pathlib import Path
import tempfile

import numpy as np

from scripts import action_jepa_round8_note_tool as r8
from scripts import tool_forecast_competence_check as competence
from scripts import tool_forecast_learning_check as learning
from scripts.tool_forecast_learning_integrity_candidate import expected_grid
from v13 import toolforecast as forecast

APP = Path(__file__).resolve().parents[1]
SEED = 20261021
FREE_EXP = ('Inspect the seal around the attic hatch.', 'Ask Rina to lend the folding stool.', 'Clean the cobwebs behind the radiator.', 'Replace the cracked lid on the lunch box.', 'Check the pressure in the spare tyre.', 'Label the jars of homemade chutney.', 'Leave the library pass beside the keys.', 'Measure the curtain rail in the study.', 'Book a chimney sweep for November.', 'Bring spare gloves to the allotment.', 'Polish the brass bell on the door.', 'Find the missing piece of the jigsaw.', 'Ask Pavel to water the fern.', 'Rinse the salt from the walking boots.', 'Mend the torn lining in the jacket.', 'Put the garden tools under cover.', 'Collect the repaired watch from town.', 'Make room for the new filing cabinet.', 'Take the empty ink cartridges for recycling.', 'Check the weather before hanging the washing.', 'Set aside coins for the car park.', 'Send the measurements to the carpenter.', 'Wash the cushions from the porch bench.', 'Ask Saira to bring the spare easel.', 'Order a replacement hinge for the cupboard.', 'Clear the gravel from the drain cover.', 'Photocopy the timetable for the noticeboard.', 'Wind the old clock in the hallway.', 'Move the flour into an airtight tin.', 'Save a seat for the visiting lecturer.')
FREE_TEST = ('Replace the worn lace in the hiking shoe.', 'Ask Mateo to check the shed lock.', 'Clean the magnifying glass before the workshop.', 'Bring the borrowed music stand on Wednesday.', 'Store the fragile ornaments in padded boxes.', 'Measure the hallway before ordering the runner.', 'Put the rain gauge back in the garden.', 'Return the spare paint to the storeroom.', 'Print the new rota for the reception desk.', 'Check the zip on the tent bag.', 'Bring a blank notebook to the induction.', 'Ask Leila where the display boards belong.', 'Remove the dead leaves from the hanging basket.', 'Replace the cracked tile beside the sink.', 'Wash the mud from the wheelbarrow.', 'Collect the reserved book after the lecture.', 'Send the photograph to the frame maker.', 'Tighten the bolt on the coat rack.', 'Leave the picnic cutlery by the door.', 'Store the clean towels on the upper shelf.')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def text_sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def generate():
    sources = {}

    def read_plan(relative):
        path = APP / relative
        sources[relative] = sha(path)
        return json.loads(path.read_text())['plan']

    bound_texts = {}
    for world in ('calc_counter', 'note_edit'):
        relative = 'specs/tool_forecast/' + world + '/candidate.npz'
        sources[relative] = sha(APP / relative)
        with np.load(APP / relative, allow_pickle=False) as archive:
            metadata = json.loads(str(archive['metadata']))
        bindings = metadata['bindings']
        bound_texts[world] = {entry['sha256'] for key, entry in bindings.items() if key.startswith('text-')}
        if any(key[5:] != entry['sha256'] for key, entry in bindings.items() if key.startswith('text-')):
            raise ValueError('Text binding identity mismatch')

    # Recover contexts from bound hashes; no tap values or outcomes are read.
    round7 = {value for value in range(1, 1000)
              if text_sha(forecast.CALC_STATE.format(n=value)) in bound_texts['calc_counter']}
    round8 = {note for note in forecast.NOTE_WORLD
              if text_sha(forecast.NOTE_STATE.format(c=note)) in bound_texts['note_edit']}
    round5 = set(np.random.default_rng(20261012).choice(np.arange(1, 1000), 400, replace=False).tolist())
    draw7 = set(np.random.default_rng(20261013).choice(
        [value for value in range(1, 1000) if value not in round5], 400, replace=False).tolist())
    contents = r8.contents()
    draw8 = {contents[index] for index in np.random.default_rng(20261014).choice(len(contents), 400, replace=False)}
    if len(round7) != 400 or round7 != draw7 or len(round8) != 400 or round8 != draw8:
        raise ValueError('Recovered contexts do not match original deterministic worlds')

    # Minimal temporary context documents are only inputs to pure plan functions;
    # they are not represented as recovered original world files/transactions.
    with tempfile.TemporaryDirectory() as temporary:
        restored = Path(temporary)
        for relative, key, values in (
                ('round5-raw/r5world/world.json', 'value', sorted(round5)),
                ('round7-fresh-raw/world/world.json', 'value', sorted(round7)),
                ('round8-note-tool-raw/world/world.json', 'content', sorted(round8))):
            path = restored / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps({'episodes': [{key: value} for value in values]}))
        historical = {'live': read_plan('specs/tool_forecast/live-plan.json'),
                      'competence1_reconstructed': competence.plan(restored),
                      'learning1_reconstructed': learning.plan(restored, 1),
                      'learning2_reconstructed': learning.plan(restored, 2),
                      'competence2_reconstructed': competence.plan2(restored)}
    saved_learning = read_plan('specs/tool_forecast/learning-plan.json')
    saved_competence = read_plan('docs/proofs/continuation-20261013/tool-forecast-competence-v2/plan.json')
    if historical['learning2_reconstructed'] != saved_learning:
        raise ValueError('Reconstructed learning2 differs from saved fixed plan')
    if historical['competence2_reconstructed'] != saved_competence:
        raise ValueError('Reconstructed competence2 differs from saved plan')

    # Include every additional saved learning/live/competence plan, if any.
    extra_paths = set((APP / 'specs/tool_forecast').glob('*plan*.json'))
    extra_paths.update((APP / 'docs/proofs').rglob('plan.json'))
    extra_paths.update((APP / 'docs/proofs').rglob('preregistration.json'))
    for path in sorted(extra_paths):
        relative = path.relative_to(APP).as_posix()
        if path.name == 'learning-plan-20261016-evening.json' or not ('tool-forecast' in relative or 'tool_forecast' in relative):
            continue
        document = json.loads(path.read_text())
        if isinstance(document, dict) and isinstance(document.get('plan'), dict):
            historical[relative] = document['plan']
            sources[relative] = sha(path)

    used_calc = round5 | round7
    used_notes = set(round8)
    for plan in historical.values():
        for arm, values in plan.items():
            if arm.startswith('calc_'):
                used_calc.update(value for value in values if type(value) is int)
            elif arm.startswith('note_'):
                used_notes.update(values)
    old_free = set(learning.live.FREE) | set(competence.FREE) | set(competence.FREE2)
    old_free.update(learning.FREE_EXP + learning.FREE_TEST + learning.FREE_EXP2 + learning.FREE_TEST2)
    free = set(FREE_EXP + FREE_TEST)
    if (len(FREE_EXP) != 30 or len(FREE_TEST) != 20 or len(free) != 50
            or free & (old_free | used_notes | forecast.NOTE_WORLD)):
        raise ValueError('Fresh free notes collide with historical notes/vocabulary')
    rng = np.random.default_rng(SEED)
    shifted = rng.choice([value for value in range(1000, 10000) if value not in used_calc], 70, replace=False).tolist()
    unseen_inside = [value for value in range(1, 1000) if value not in used_calc]
    previous = read_plan('specs/tool_forecast/learning-plan-20261016.json')
    # Finite original world has fewer than30 unused input states. Keep all
    # counts and numerical gates; repeat the prior fixed retention controls,
    # explicitly not a fresh retention/generalization claim. No outcome read.
    inside = list(previous['calc_in_test'])
    notes = list(previous['note_in_test'])
    plan = {'calc_shift_exp': sorted(shifted[:40]), 'calc_shift_test': sorted(shifted[40:]),
            'calc_in_test': inside, 'note_shift_exp': list(FREE_EXP),
            'note_shift_test': list(FREE_TEST), 'note_in_test': notes}
    new_calc = set(shifted + inside)
    new_notes = set(notes) | free
    input_hashes = ({text_sha(forecast.CALC_STATE.format(n=value)) for value in new_calc}
                    | {text_sha(forecast.NOTE_STATE.format(c=note)) for note in new_notes})
    bound_union = set.union(*bound_texts.values())
    if set(shifted) & used_calc or free & used_notes or input_hashes & bound_union:
        raise ValueError('Fresh context overlaps an excluded state or bound source text')
    document = {'schema': 'v13-tool-forecast-learning-plan-v1', 'round': 2, 'mode': 'region',
                'seed': SEED, 'source': 'scripts/tool_forecast_learning_plan_evening_20261016.py',
                'gates': dict(learning.GATES), 'plan': plan,
                'retention_controls': 'Exact repeat of20261016 fixed in-world arms; fewer than30 unseen arithmetic states remain',
                'fresh_scope': '70 shifted arithmetic states and50 free notes only',
                'claim_limit': 'Fresh shifted cases versus enumerated history, repeated fixed in-world retention controls; '
                               'not a fresh retention cohort, proof of absence from pretraining, or general-world transfer.'}
    if len(expected_grid(document)) != 610:
        raise ValueError('Fresh fixed grid must contain exactly610 rows')
    for relative in ('scripts/tool_forecast_learning_plan_evening_20261016.py', 'scripts/tool_forecast_learning_check.py',
                     'scripts/tool_forecast_competence_check.py', 'scripts/tool_forecast_live_check.py',
                     'scripts/action_jepa_round5_tools.py', 'scripts/action_jepa_round7_fresh.py',
                     'scripts/action_jepa_round8_note_tool.py', 'v13/toolforecast.py'):
        sources[relative] = sha(APP / relative)
    provenance = {'schema': 'V13_FRESH_LEARNING_PLAN_EXCLUSIONS_20261016_V1', 'sources': sources,
                  'numpy_version': np.__version__, 'seed': SEED, 'historical_plans': historical,
                  'recovered_world_contexts': {'round5': sorted(round5), 'round7': sorted(round7), 'round8': sorted(round8)},
                  'reconstruction': {'round5': '400 states; NumPy default_rng seed20261012, round5 generator',
                     'round7': '400 states; seed20261013 excluding round5; exact match to checkpoint source-text hashes',
                     'round8': '400 states; seed20261014 from contents(); exact match to checkpoint source-text hashes',
                     'learning2_matches_saved_plan': True, 'competence2_matches_saved_plan': True},
                  'excluded_calc_states': sorted(used_calc), 'excluded_notes': sorted(used_notes | old_free),
                  'checks': {'new_calc_states': len(shifted), 'new_note_states': len(free),
                     'repeated_calc_retention_states': len(inside), 'repeated_note_retention_states': len(notes),
                     'unseen_in_world_calc_states_available': len(unseen_inside),
                     'new_free_notes': 50, 'fresh_shifted_calc_overlap': [], 'fresh_free_note_overlap': [],
                     'bound_source_input_hash_overlap': [], 'expected_rows': 610,
                     'phase_a_rows': 250, 'phase_b_rows': 360},
                  'outcomes_observed': False, 'native_models_launched': False,
                  'claim_limit': document['claim_limit']}
    return document, provenance


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--provenance', type=Path, required=True)
    args = parser.parse_args()
    document, provenance = generate()
    # Exclusive creation preserves an already frozen plan on repeated attempts.
    with args.out.open('x') as stream:
        stream.write(json.dumps(document, indent=2) + '\n')
    provenance['plan_sha256'] = sha(args.out)
    with args.provenance.open('x') as stream:
        stream.write(json.dumps(provenance, indent=2) + '\n')
    print(json.dumps({'plan_sha256': provenance['plan_sha256'], 'expected_rows': 610,
                      'checks': provenance['checks']}))


if __name__ == '__main__':
    main()
