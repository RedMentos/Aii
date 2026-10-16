#!/usr/bin/env python3
"""Independent post-closure evidence/learner replay; never performs inference.

Only run after the coordinator signals the cohort has completed. All replay
writes are confined to a fresh temporary home under this proof directory.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import time

HERE = Path(__file__).resolve().parent
APP = next(parent for parent in HERE.parents if (parent / 'v13/toolforecast.py').is_file())
EXPECTED_PLAN_SHA256 = '653cc8cad377a1942e839073f93af164a2a2e60d0bc3719078092e65f948633b'
EXPECTED_PREREG_SHA256 = 'c3c696a26843cfb93f906d1ddab2109098076894e48b9254bc434b2b011661e6'
sys.path.insert(0, str(APP))
sys.path.insert(0, str(APP / 'scripts'))


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cohort', required=True)
    parser.add_argument('--confirm-closed', action='store_true', required=True)
    args = parser.parse_args()
    cohort = Path(args.cohort).resolve()
    require(cohort.is_dir(), 'Closed cohort directory missing')
    report = read(cohort / 'report.json')
    require(report.get('status') in ('CONTINUAL_LEARNING_CONFIRMED', 'CONTINUAL_LEARNING_NOT_CONFIRMED'),
            'Cohort is not closed with a learning verdict')
    require(report.get('completed_calls') == 610 and report.get('source_binding_verified_after') is True
            and report.get('native_binding_verified_after') is True
            and report.get('phase_a_snapshot_verified_after') is True, 'Full closed cohort checks missing')
    # These imports and all numerical operations happen only after closure checks.
    import numpy as np
    from scripts import tool_forecast_bound_learning_candidate as bound
    from scripts import tool_forecast_learning_check as learning
    from scripts import tool_forecast_learning_integrity_candidate as integrity
    from v13 import toolforecast as F

    prereg = read(cohort / 'preregistration.json')
    prereg_sha = sha(cohort / 'preregistration.json')
    require(prereg_sha == report['preregistration_sha256'] == EXPECTED_PREREG_SHA256, 'Preregistration digest mismatch')
    require(prereg['plan_sha256'] == EXPECTED_PLAN_SHA256, 'Evening plan identity mismatch')
    require(bound.numerical_runtime_binding() == prereg['numerical_runtime'], 'Numerical runtime differs')
    bound.verify_sources(prereg, APP)
    require(prereg['gates'] == learning.GATES and prereg['rule'] == F.LEARN_RULE, 'Learner/gates differ')
    require(sha(prereg['plan_path']) == prereg['plan_sha256'], 'Plan file changed')
    require(read(prereg['plan_path']) == prereg['plan'], 'Plan content changed')
    rows = [json.loads(line) for line in (cohort / 'rows.jsonl').read_text().splitlines()]
    require(rows == read(cohort / 'rows.json'), 'JSON and JSONL rows differ')
    require(len(rows) == 610, 'Journal does not contain exactly610 rows')
    require([row.get('ordinal') for row in rows] == list(range(610)), 'Journal ordinal mismatch')
    require(all(row.get('preregistration_sha256') == prereg_sha for row in rows), 'Journal preregistration mismatch')
    require(sha(cohort / 'rows.jsonl') == report['rows_sha256'], 'Journal digest mismatch')
    grid = integrity.expected_grid(prereg['plan'])
    require([(r['arm'], r['action'], r['state']) for r in rows] == grid, 'Journal differs from exact planned order')
    learned = read(cohort / 'learn.json')
    checked = integrity.analyze_checked(rows, learned, prereg['plan'])
    require(checked['integrity']['pass'] and checked['analysis_ran'], 'Strict complete-grid verification failed')
    require(checked == read(cohort / 'analysis.json') == report['analysis'], 'Independent strict analysis differs')
    snapshot = report['phase_a_experience']
    learning.verify_experience_snapshot(cohort, snapshot, learned)
    directory = cohort / snapshot['directory']
    encoder_file = cohort / 'encoder.json'
    enc = read(encoder_file)
    require(enc == read(cohort / 'home/data/tool_forecast/encoder.json'), 'Closed encoder copies differ')
    tracked = [cohort / name for name in ('report.json', 'preregistration.json', 'rows.jsonl', 'rows.json',
                                        'learn.json', 'analysis.json', 'encoder.json')]
    tracked += [directory / 'manifest.json']
    manifest = read(APP / 'specs/tool-forecast.json')
    results = {}
    absent_original_paths = []
    for world, item in snapshot['manifest']['worlds'].items():
        tracked += [directory / item['file'], Path(enc['retention'][world]['path'])]
        for adaptation_path in F.adapted_paths(cohort / 'home', world):
            if adaptation_path.exists():
                tracked.append(adaptation_path)
            else:
                absent_original_paths.append(adaptation_path)
        final_experience = F.Experience(cohort / 'home').path(world)
        tracked.append(final_experience)
        family = 'calc' if world == 'calc_counter' else 'note'
        phase_a = [row for row in rows if row['arm'] == family + '_shift_exp']
        all_world = [row for row in rows if row['arm'].startswith(family + '_')]
        with np.load(directory / item['file'], allow_pickle=False) as saved:
            ids = saved['id'].tolist()
            require(ids == item['forecast_ids'] == [row['forecast_id'] for row in phase_a], 'PhaseA ordered ID mismatch')
            require(len(ids) == item['rows'] == (160 if family == 'calc' else 90), 'PhaseA row denominator mismatch')
            require(all(len(saved[key]) == len(ids) for key in ('x', 'y', 'xm', 'action')), 'PhaseA shape mismatch')
            require(json.loads(str(saved['binding'])) == item['binding'], 'PhaseA binding mismatch')
            actions = manifest['worlds'][world]['actions']
            require(saved['action'].tolist() == [actions.index(row['action']) for row in phase_a], 'PhaseA action identity mismatch')
        with np.load(final_experience, allow_pickle=False) as saved:
            require(saved['id'].tolist() == [row['forecast_id'] for row in all_world], 'Final experience ordered IDs differ')
            require(all(len(saved[key]) == len(all_world) for key in ('x', 'y', 'xm', 'action')), 'Final experience shapes differ')
        ck = F.Checkpoint(world, manifest['worlds'][world], APP)
        require(item['binding'] == F.experience_binding(ck, enc), 'Experience checkpoint/encoder binding differs')
        require(learned[world]['binding'] == F.adaptation_binding(ck, enc, 'region'), 'Adaptation binding differs')
        ret = enc['retention'][world]
        require(sha(ret['path']) == ret['sha256'], 'Retention bytes differ')
        results[world] = {'phase_a_rows': len(phase_a), 'final_experience_rows': len(all_world),
                          'phase_a_ids_match': True, 'final_experience_ids_match': True,
                          'phase_a_sha256': item['sha256'], 'retention_sha256': ret['sha256']}
    before = {str(path): sha(path) for path in tracked}
    # Copy the phaseA inputs and retention tensors before replay. Absolute model
    # paths remain inert metadata; F.learn never opens a model or launches a tap.
    with tempfile.TemporaryDirectory(prefix='replay-', dir=HERE) as temporary:
        replay_home = Path(temporary) / 'home'
        data = replay_home / 'data/tool_forecast'
        (data / 'experience').mkdir(parents=True)
        copied_enc = json.loads(json.dumps(enc))
        for world, item in snapshot['manifest']['worlds'].items():
            shutil.copyfile(directory / item['file'], data / 'experience' / (world + '.npz'))
            target = data / ('retention-' + world + '.npz')
            shutil.copyfile(enc['retention'][world]['path'], target)
            require(sha(target) == enc['retention'][world]['sha256'], 'Copied retention differs')
            copied_enc['retention'][world]['path'] = str(target)
        (data / 'encoder.json').write_text(json.dumps(copied_enc, indent=1) + '\n')
        for world in sorted(results):
            ck = F.Checkpoint(world, manifest['worlds'][world], APP)
            replayed = F.learn(replay_home, ck, copied_enc, mode='region')
            require(replayed == learned[world], 'Full replay learn report differs: ' + world)
            original_npz, original_json = F.adapted_paths(cohort / 'home', world)
            replay_npz, replay_json = F.adapted_paths(replay_home, world)
            if replayed['pass']:
                require(sha(original_npz) == sha(replay_npz) == learned[world]['adapted_sha256'], 'Replay adapted bytes differ')
                require(read(original_json) == read(replay_json) == learned[world], 'Adapted report differs')
                with np.load(original_npz, allow_pickle=False) as old, np.load(replay_npz, allow_pickle=False) as new:
                    require(old.files == new.files and all(np.array_equal(old[key], new[key]) for key in old.files),
                            'Replay adapted arrays differ')
                results[world] |= {'full_learn_report_exact': True, 'adapted_arrays_exact': True,
                                   'adapted_npz_sha256_exact': sha(replay_npz), 'adapted_report_exact': True}
            else:
                require(not any(p.exists() for p in (original_npz, original_json, replay_npz, replay_json)),
                        'Failed fresh learner unexpectedly wrote adaptation files')
                results[world] |= {'full_learn_report_exact': True, 'no_adaptation_expected_or_written': True}
    require(before == {str(path): sha(path) for path in tracked}, 'Original cohort inputs changed during replay')
    require(not any(path.exists() for path in absent_original_paths), 'Originally absent adaptation files appeared')
    bound.verify_sources(prereg, APP)
    output = {'schema': 'V13_INDEPENDENT_CLOSED_LEARNER_REPLAY_20261016_V1', 'status': 'PASS',
              'utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'cohort': str(cohort),
              'preregistration_sha256': prereg_sha, 'plan_sha256': prereg['plan_sha256'],
              'verified_journal_rows': len(rows), 'unique_call_ids': len({r['call'] for r in rows}),
              'unique_forecast_ids': len({r['forecast_id'] for r in rows}), 'exact_planned_order': True,
              'strict_integrity_pass': True, 'strict_analysis_exact': True, 'numerical_runtime_exact': True,
              'source_binding_exact': True, 'source_inputs_unchanged': True, 'native_inference_performed': False,
              'original_cohort_hashes': before, 'worlds': results,
              'original_learning_verdict': checked['verdict'], 'canonical_gate_pass': False, 'phone_measured': False,
              'scope': 'Independent deterministic replay of the same closed PhaseA learner inputs and complete610-case analysis; no new utility/generalization/device evidence.'}
    path = HERE / 'report.json'
    with path.open('x') as stream:
        json.dump(output, stream, indent=1, allow_nan=False)
        stream.write('\n')
    print(json.dumps({'status': output['status'], 'rows': len(rows), 'worlds': sorted(results), 'report': str(path)}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
