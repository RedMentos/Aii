#!/usr/bin/env python3
"""Export a fixed three-case native diagnostic; no inference or gate promotion."""
import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('private_pilot_geometry', HERE / 'generate_fixtures.py')
G = importlib.util.module_from_spec(spec)
spec.loader.exec_module(G)

SCHEMA = 'V13_STEP2_PRIVATE_DIAGNOSTIC_PILOT_V1'
ACTIONS = ('A', 'B', 'NONE')
SELECTION_RULE = ('From the fixed seed-20261016 full cohort, keep complementary fixtures only; '
                  'solve their declared source constraints without native outcomes; choose the '
                  'lexicographically smallest fixture id for each geometry action in order A,B,NONE.')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def select_pilot(full_doc):
    if G.canonical(full_doc) != G.canonical(G.generate()):
        raise ValueError('Pilot must be selected from the untouched fixed full cohort')
    by_action = {action: [] for action in ACTIONS}
    for fixture in full_doc['fixtures']:
        if fixture['kind'] != 'complementary':
            continue
        values = G.facts(source['text'] for source in fixture['sources'])
        if any(len(values[field]) != 1 for field in G.REQUIRED):
            raise ValueError('Ambiguous complementary fixture geometry')
        rules = {field: next(iter(values[field])) for field in G.REQUIRED}
        solved = G.solve(fixture['public'], rules)
        if solved != fixture['oracle']:
            raise ValueError('Geometry answer differs from fixed fixture oracle')
        by_action[solved['action']].append(fixture)
    selected = [min(by_action[action], key=lambda f: f['id']) for action in ACTIONS]
    return {'schema': SCHEMA, 'status': 'DIAGNOSTIC_FIXTURES_ONLY_NOT_REGISTERED',
            'scope': 'THREE_COMPLEMENTARY_CASE_DIAGNOSTIC_NOT_FULL_STEP2',
            'selection_rule': SELECTION_RULE, 'geometry_action_order': list(ACTIONS),
            'selected_ids': [f['id'] for f in selected], 'fixtures': copy.deepcopy(selected),
            'full_fixture_document_sha256': G.digest(G.canonical(full_doc)),
            'full_fixture_count': len(full_doc['fixtures']), 'full_benchmark_rows': 234,
            'pilot_max_rows': 18, 'pilot_max_native_calls': 42, 'native_runs': 0,
            'historical_step2_utility': 'UTILITY_FAIL_UNCHANGED', 'gate_promotion': False,
            'numeric_utility_gate': 'NO_UTILITY_PROMOTION_FOR_DIAGNOSTIC_PILOT'}


def export(full_path, out):
    full_path, out = Path(full_path), Path(out)
    full_doc = json.loads(full_path.read_text())
    pilot = select_pilot(full_doc)
    out.mkdir(parents=True, exist_ok=False)
    fixture_path = out / 'pilot-fixtures.json'
    fixture_path.write_text(json.dumps(pilot, indent=2, sort_keys=True, allow_nan=False) + '\n')
    manifest = {'schema': SCHEMA + '_SELECTION_MANIFEST', 'status': 'SELECTED_BEFORE_NATIVE_OUTCOMES',
        'scope': pilot['scope'], 'selection_rule': SELECTION_RULE,
        'selected_geometry': [{'fixture': f['id'], 'action': f['oracle']['action'],
                               'kind': f['kind']} for f in pilot['fixtures']],
        'source_sha256': {'generate_fixtures.py': sha(HERE / 'generate_fixtures.py'),
                          'prepare_pilot.py': sha(__file__), 'full-fixtures.json': sha(full_path),
                          'pilot-fixtures.json': sha(fixture_path)},
        'full_fixture_document_sha256': pilot['full_fixture_document_sha256'],
        'pilot_fixture_document_sha256': G.digest(G.canonical(pilot)),
        'pilot_max_rows': 18, 'pilot_max_native_calls': 42,
        'full_benchmark_unchanged': True, 'native_runs': 0, 'cohort_registration': False,
        'gate_promotion': False, 'historical_step2_utility': 'UTILITY_FAIL_UNCHANGED'}
    (out / 'pilot-selection-manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--full-fixtures', type=Path, default=HERE / 'generated/fixtures.json')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    result = export(args.full_fixtures, args.out)
    print(G.canonical(result))
