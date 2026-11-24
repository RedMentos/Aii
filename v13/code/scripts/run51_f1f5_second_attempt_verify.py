#!/usr/bin/env python3
"""Independent original Run51 F1/F5 second-attempt native source replay."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re

from scripts.run47_jef_c3_typed_receiver_verify import (
    MODELS, RUNNER_SHA, NEGATIVE, canonical, parse, sha)

FIXTURE_SHA = '160128b2f5df2a5798ae7ec62687e6be5a8e61f6c6b2dad43f1ad253ee592ecc'
PROJECTS = ('Cypress', 'Lark', 'Delta')


def require(ok, code):
    if not ok:
        raise ValueError('RUN51_REPLAY_' + code)


def exact_score(answer, amount, project):
    if type(answer) is not str or len(answer) > 4096:
        return 0
    nums = re.findall(r'(?<![A-Za-z0-9])\d+(?:[.,]\d+)?(?![A-Za-z0-9])', answer)
    named = re.findall(r'\bProject\s+([A-Za-z][A-Za-z0-9_-]*)\b', answer, re.I)
    return int(nums == [str(amount)] and all(n.lower() == project.lower() for n in named))


def replay(report_path, fixture_path):
    raw = Path(fixture_path).read_bytes()
    require(sha(raw) == FIXTURE_SHA, 'FIXTURE_SHA')
    fixture = parse(raw)
    require(fixture.get('schema') == 'v13.run51.f1f5_second_attempt_seed467.v1'
            and fixture.get('seed') == 467
            and [f.get('id') for f in fixture.get('fixtures', [])] == list(PROJECTS), 'FIXTURE')
    report = parse(Path(report_path).read_bytes())
    require(report.get('schema') == 'v13.run51.f1f5_second_attempt_native_result.v1'
            and report.get('fixture_sha256') == FIXTURE_SHA
            and report.get('seed') == 467 and report.get('registered') is True
            and report.get('negative_gates') == NEGATIVE, 'REGISTRATION')
    binding = report.get('binding', {})
    require(binding.get('model_sha256') == MODELS and
            binding.get('runner_sha256') == RUNNER_SHA, 'NATIVE_BINDING')
    rows = report.get('rows')
    require(type(rows) is list and len(rows) <= 3
            and [r.get('fixture') for r in rows] == list(PROJECTS[:len(rows)]), 'ROW_ORDER')
    manifests = report.get('row_sha256')
    require(type(manifests) is dict and set(manifests) == {r['fixture'] for r in rows}, 'ROW_MANIFEST')
    correct = 0
    reasons = []
    for row in rows:
        f = next(f for f in fixture['fixtures'] if f['id'] == row['fixture'])
        require(manifests[f['id']] == sha(canonical(row)), 'ROW_SHA')
        require(row.get('first_query_sha256') == sha(f['first_query'].encode())
                and row.get('correction_event_sha256') == sha(f['correction_event'].encode())
                and row.get('followup_sha256') == sha(f['followup'].encode())
                and row.get('oracle_visible_to_native_as_oracle') is False, 'SOURCES')
        if row.get('status') != 'RECORDED':
            require(row.get('score', {}).get('correct') == 0, 'RED_SCORE_ZERO')
            reasons.append(f['id'] + ':' + str(row.get('status')))
            continue
        for field, source in (('first_source_ref', f['first_query']),
                              ('correction_source_ref', f['correction_event']),
                              ('followup_source_ref', f['followup'])):
            ref = row.get(field)
            require(type(ref) is dict and ref.get('sha256') == sha(source.encode())
                    and ref.get('char_start') == 0 and ref.get('char_end') == len(source)
                    and ref.get('modality') == 'text', 'SOURCE_REF')
        require(row.get('baseline_decision') == 'CLARIFY'
                and row.get('baseline_has_messages') is False
                and row.get('baseline_model_calls') == 0
                and row.get('second_decision') == 'ADMITTED'
                and row.get('second_reason') == 'ONE_VERIFIED_CORRECTION'
                and row.get('native_model_calls') == 1, 'SECOND_ATTEMPT')
        m = row.get('memory_row', {})
        feedback = row.get('feedback_row', {})
        source = row.get('second_source', {})
        require(m.get('id') == row.get('memory_id') == source.get('memory_id')
                and m.get('kind') == 'fact' and m.get('scope') == 'session'
                and m.get('active') == 1
                and m.get('key_text') == f['key'] and m.get('value') == f['value']
                and source.get('topic') == f['key'] and source.get('value') == f['value']
                and feedback.get('event_id') == m.get('event_id')
                and feedback.get('source_id') == m.get('source_id')
                and feedback.get('kind') == 'fact' and feedback.get('value') == f['value']
                and feedback.get('permission') == 'record', 'F1_F5_ROWS')
        ref = source.get('source_ref', {})
        require(ref.get('source_id') == m['source_id']
                and ref.get('sha256') == sha(f['value'].encode())
                and ref.get('char_start') == 0
                and ref.get('char_end') == len(f['value'])
                and ref.get('modality') == 'text', 'VALUE_SOURCE')
        packets = row.get('f1f5_packets')
        require(type(packets) is list and len(packets) == 2, 'F1_F5_PACKET_COUNT')
        pmap = {p['kind']: p for p in packets}
        require(set(pmap) == {'MemoryRecord', 'HumanDecision'}, 'F1_F5_PACKET_KINDS')
        record, human = (parse(pmap[k]['payload']) for k in ('MemoryRecord', 'HumanDecision'))
        require(all(p['event_id'] == m['event_id'] for p in packets)
                and pmap['MemoryRecord']['generation_id'] == pmap['HumanDecision']['generation_id']
                and record.get('packet_id') == pmap['MemoryRecord']['id']
                and human.get('packet_id') == pmap['HumanDecision']['id']
                and record.get('producer_component') == 'F1_MEMORY'
                and human.get('producer_component') == 'F5_HUMAN_CONTROL'
                and record.get('memory_id') == m['id']
                and record.get('key') == f['key']
                and record.get('source_ref') == ref
                and human.get('source_ref') == ref
                and human.get('kind') == 'fact'
                and human.get('value') == f['value']
                and human.get('learning_permission') == 'record', 'F1_F5_PROVENANCE')
        prompt = row.get('native_prompt')
        require(type(prompt) is list and len(prompt) == 2
                and prompt[0].get('role') == 'system'
                and prompt[1] == {'role': 'user', 'content': f['followup']}
                and ('Verified user correction for this topic: ' + f['key'] + ' = ' + f['value']) in prompt[0]['content']
                and f['value'] not in prompt[1]['content']
                and row.get('native_prompt_sha256') == sha(canonical(prompt)), 'PROMPT')
        require(row.get('native_c3_final') is True
                and row.get('native_c3_metrics', {}).get('status') == 'FINAL'
                and row.get('processes_reaped') is True
                and type(row.get('process_releases')) is list
                and len(row['process_releases']) > 0
                and all(x.get('process_reaped') is True for x in row['process_releases']), 'NATIVE_FINAL_REAP')
        scored = exact_score(row.get('native_answer'), f['oracle_amount'], f['id'])
        require(row.get('score', {}).get('correct') == scored, 'NATIVE_SCORE')
        correct += scored
    structural = len(rows) == 3 and not reasons
    signal = structural and correct >= 2 and report.get('installed_binding_unchanged') is True
    if structural:
        require(report.get('second_attempt_signal') is signal and report.get('status') ==
                ('SOURCE_BACKED_SECOND_ATTEMPT_SIGNAL_ONLY' if signal else 'UTILITY_FAIL'), 'AGGREGATE')
    else:
        require(report.get('status') in ('STRUCTURAL_RED', 'RUNNING'), 'STRUCTURAL_STATUS')
    return {'schema': 'v13.run51.independent_replay.v1',
            'structural_valid': structural, 'second_attempt_signal': signal,
            'native_correct': correct, 'rows': len(rows), 'reasons': reasons,
            'negative_gates': NEGATIVE,
            'scope': 'LINUX_NATIVE_SOURCE_BACKED_SECOND_ATTEMPT_ONLY_NO_WEIGHT_LEARNING'}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--report', type=Path, required=True)
    p.add_argument('--fixture', type=Path, required=True)
    a = p.parse_args()
    result = replay(a.report, a.fixture)
    print(json.dumps(result, sort_keys=True), flush=True)
    if not result['second_attempt_signal']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()