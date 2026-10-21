"""Generate a fresh, hash-checked 610-row region-learning plan without outcomes.

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
SEED = 20261020
FREE_EXP = (
    'Patch the seam on the canvas bag.',
    'Schedule a tune-up for the lawn mower.',
    'Leave a spare charger at the studio.',
    'Store the dried lavender in a jar.',
    'Ask Daria which platform the train uses.',
    'Replace the missing drawer knob.',
    'Cut fresh labels for the seed trays.',
    'Photograph the serial number on the freezer.',
    'Reserve a locker at the swimming pool.',
    'Take the empty jars to the refill shop.',
    'Put a bookmark in the travel guide.',
    'Repair the clasp on the silver necklace.',
    'Turn the compost with the garden fork.',
    'Leave a towel beside the guest bed.',
    'Check whether the museum opens on Tuesdays.',
    'Post the signed consent form.',
    'Roll the sleeping mat before breakfast.',
    'Gather the fallen twigs for kindling.',
    'Bring the reusable cups to rehearsal.',
    'Transfer the herbs into larger pots.',
    'Rinse the dust from the picnic blanket.',
    'Find a quiet cafe near the station.',
    'Ask Noor to confirm the delivery window.',
    'Put fresh batteries in the wall clock.',
    'Measure the shelf above the washing machine.',
    'Add felt pads under the dining chairs.',
    'Wrap the spare cables with fabric ties.',
    'Sort the wool by colour.',
    'Book a space at the pottery workshop.',
    'Restock the first aid kit before camping.',
)
FREE_TEST = (
    'Fasten the loose strap on the camera case.',
    'Ask Elise where the folding tables are stored.',
    'Bring a thermos to the evening class.',
    'Clean the chalk from the blackboard.',
    'Save the receipt for the replacement kettle.',
    'Attach the new tag to the suitcase handle.',
    'Move the seedlings away from the cold window.',
    'Find the small screwdriver in the sewing box.',
    'Write the gate code inside the address book.',
    'Ask the violin teacher about autumn lessons.',
    'Place the spare key in the blue envelope.',
    'Wash the reusable filters for the coffee pot.',
    'Choose a waterproof cover for the bicycle seat.',
    'Return the empty gas cylinder to the supplier.',
    'Pin the trail map beside the kitchen calendar.',
    'Check the hinges on the greenhouse door.',
    'Take the old towels to the animal shelter.',
    'Pack a torch for the walk after sunset.',
    'Mark the borrowed tools with removable tape.',
    'Lay the damp wool jumper flat to dry.',
)


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
        if path.name == 'learning-plan-20261016.json' or not ('tool-forecast' in relative or 'tool_forecast' in relative):
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
    inside = sorted(rng.choice([value for value in range(1, 1000) if value not in used_calc], 30, replace=False).tolist())
    notes = sorted(rng.choice(sorted(forecast.NOTE_WORLD - used_notes), 20, replace=False).tolist())
    plan = {'calc_shift_exp': sorted(shifted[:40]), 'calc_shift_test': sorted(shifted[40:]),
            'calc_in_test': inside, 'note_shift_exp': list(FREE_EXP),
            'note_shift_test': list(FREE_TEST), 'note_in_test': notes}
    new_calc = set(shifted + inside)
    new_notes = set(notes) | free
    input_hashes = ({text_sha(forecast.CALC_STATE.format(n=value)) for value in new_calc}
                    | {text_sha(forecast.NOTE_STATE.format(c=note)) for note in new_notes})
    bound_union = set.union(*bound_texts.values())
    if new_calc & used_calc or new_notes & used_notes or input_hashes & bound_union:
        raise ValueError('Fresh context overlaps an excluded state or bound source text')
    document = {'schema': 'v13-tool-forecast-learning-plan-v1', 'round': 2, 'mode': 'region',
                'seed': SEED, 'source': 'scripts/tool_forecast_learning_plan_20261016.py',
                'gates': dict(learning.GATES), 'plan': plan,
                'claim_limit': 'Fresh versus enumerated historical context states and bound source texts only; '
                               'not proof of absence from model pretraining or general-world transfer.'}
    if len(expected_grid(document)) != 610:
        raise ValueError('Fresh fixed grid must contain exactly610 rows')
    for relative in ('scripts/tool_forecast_learning_plan_20261016.py', 'scripts/tool_forecast_learning_check.py',
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
                  'checks': {'new_calc_states': len(new_calc), 'new_note_states': len(new_notes),
                     'new_free_notes': 50, 'calc_state_overlap': [], 'note_state_overlap': [],
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
