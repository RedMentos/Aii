#!/usr/bin/env python3
"""Read-only original-artifact auditor for frozen Run117W seed1063.

No model execution, no production gates, no network access. Accepts a GitHub
Actions original artifact ZIP and independently recomputes strict scores.
"""
from __future__ import annotations
import argparse
from collections import Counter
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import re
import zipfile

HEAD = '978be6017a49365aa401c848a429913e88ef7b75'
ARTIFACT_SHA = 'aa4330b3609778a9910265bd7df71723b4ea432f0342e27bc07b6ee044059cde'
FIXTURE_SHA = '2b62fd13c81201c23574fa42ad87176f5d25f755b534a76f4386c9ec9c608ed9'
PHONE_SHA = 'cee53009b20e8f36cc82d51d201136849431ffcc1d14dbecb35d43aaf4f642dd'
ARMS = ('BASE_SOURCE_SYSTEM', 'EXPLICIT_ARITHMETIC_SYSTEM', 'TYPED_JEF_FORMATTER')
SYSTEM_SHA = {
    'BASE_SOURCE_SYSTEM': '019fbd37b610854c7ee66efed583fd686a627cd2e5660b70d10d7f35c323c4a5',
    'EXPLICIT_ARITHMETIC_SYSTEM': 'cc7514b47c33af0ab93c9e3319d112330516e8a196b27050fc6546f24ff914ba',
    'TYPED_JEF_FORMATTER': 'd977fbab2e9eb4cf8e183adaccdf8a631f17254d822708e681a7048c4b087d4f',
}
IDS = ('Arbor', 'Brisa', 'Cyra', 'Doran', 'Elyra', 'Fenix')
POLICY = re.compile(r'Binding policy: budget (\d+) euros; deadline (\d+) days; local-only (true|false)\.')
OPTION = re.compile(r'Option ([AB]): cost (\d+) euros, duration (\d+) days, local (true|false)\.')


def require(ok, code):
    if not ok:
        raise ValueError(code)


def jload(raw):
    return json.loads(raw)


def audit(raw: bytes, *, pinned=True):
    if pinned:
        require(sha256(raw).hexdigest() == ARTIFACT_SHA, 'ORIGINAL_ARTIFACT_SHA_RED')
    with zipfile.ZipFile(BytesIO(raw)) as outer:
        require(outer.testzip() is None, 'OUTER_CRC_RED')
        names = outer.namelist()
        require(len(names) == len(set(names)), 'OUTER_DUPLICATE_ENTRY_RED')
        sums = outer.read('SHA256SUMS').decode().splitlines()
        checked = set()
        for line in sums:
            digest, path = line.split('  ./', 1)
            require(path in names and path not in checked, 'OUTER_SUMS_PATH_RED')
            require(sha256(outer.read(path)).hexdigest() == digest, 'OUTER_SUMS_HASH_RED')
            checked.add(path)
        require(checked == set(names) - {'SHA256SUMS'}, 'OUTER_SUMS_COVERAGE_RED')
        require(outer.read('HEAD.txt').decode().strip() == HEAD, 'HEAD_RED')
        for name in ('SOURCE', 'DEPS', 'PACK', 'ZIP', 'PREFLIGHT', 'INSTALL_C3',
                     'NATIVE', 'VERIFY', 'COMPILE', 'PRIVACY', 'DIFF'):
            require(outer.read(name + '_EXIT.txt').decode().strip() == '0', name + '_EXIT_RED')
        result = jload(outer.read('RESULT.json'))
        require(result['head'] == HEAD and result['seed'] == 1063
                and result['fixture_sha256'] == FIXTURE_SHA, 'RESULT_BINDING_RED')
        require(set(result['exits'].values()) == {0}, 'RESULT_EXIT_RED')
        require(result['typed_jef_is_precomputed_not_native'] is True
                and result['jepa_weight'] == 0
                and result['redmi_measured'] is False
                and result['whole_system_complete'] is False
                and result['step2_promoted'] is False
                and result['b3_promoted'] is False, 'RESULT_GATE_RED')
        phone = outer.read('V13-Phone-Run117W.zip')
        require(sha256(phone).hexdigest() == PHONE_SHA, 'PHONE_SHA_RED')
        with zipfile.ZipFile(BytesIO(phone)) as nested:
            require(nested.testzip() is None, 'PHONE_CRC_RED')
            nnames = nested.namelist()
            require(len(nnames) == len(set(nnames)), 'PHONE_DUPLICATE_RED')
            manifest = jload(nested.read('V13-Phone/WORKSPACE_FILES.json'))
            files = manifest['files']
            require(manifest['schema_version'] == 1 and len(files) >= 2200,
                    'PHONE_MANIFEST_SCHEMA_RED')
            require(set('V13-Phone/' + p for p in files) ==
                    set(nnames) - {'V13-Phone/WORKSPACE_FILES.json'},
                    'PHONE_MANIFEST_COVERAGE_RED')
            for path, digest in files.items():
                require(sha256(nested.read('V13-Phone/' + path)).hexdigest() == digest,
                        'PHONE_MANIFEST_HASH_RED:' + path)
            fixture_raw = nested.read('V13-Phone/docs/fixtures/RUN117W_C3_ARITHMETIC_SEED1063.json')
            require(sha256(fixture_raw).hexdigest() == FIXTURE_SHA, 'FIXTURE_SHA_RED')
            fixture = jload(fixture_raw)
        require(fixture['seed'] == 1063 and fixture['arms'] == list(ARMS)
                and [x['id'] for x in fixture['rows']] == list(IDS), 'COHORT_RED')
        report = jload(outer.read('NATIVE_CASE/report.json'))
        require(report['seed'] == 1063 and report['fixture_sha256'] == FIXTURE_SHA
                and report['schema'] == 'v13.run117w.c3_arithmetic_native.v1'
                and report['native_c3_calls'] == 18
                and report['native_body_calls'] == 0
                and report['native_jef_calls'] == 0
                and report['native_c2_calls'] == 0, 'REPORT_SCOPE_RED')
        require(report['status'] == 'NATIVE_COMPLETE_NO_ARITHMETIC_GAIN'
                and report['exploratory_arithmetic_signal'] is False
                and report['age0'] == 'RECORD_ONLY'
                and report['step2_exit'] == 'EVIDENCE_NOT_PASSING'
                and report['b3'] == 'NO_PROMOTION'
                and report['body_jepa'] == 'UNAVAILABLE'
                and report['world_jepa'] == 'SHADOW'
                and report['jepa_weight'] == 0
                and report['redmi_measured'] is False
                and report['whole_system_complete'] is False
                and report['output_committed'] is False
                and report['tool_dispatches'] == 0
                and report['learning_authority'] == 0
                and report['delivery_authority'] == 0
                and report['typed_candidate_precomputed'] is True, 'REPORT_GATE_RED')
        require(len(report['rows']) == 6 and
                [x['id'] for x in report['rows']] == list(IDS), 'REPORT_ROWS_RED')
        scores = Counter()
        seen = Counter()
        for source, row in zip(fixture['rows'], report['rows']):
            require(row['status'] == 'RECORDED' and row['closed_store_ok'] is True
                    and row['no_live_output'] is True, 'ROW_STATUS_RED')
            p = POLICY.fullmatch(source['policy_span'])
            options = list(OPTION.finditer(source['option_span']))
            require(p is not None and len(options) == 2, 'SOURCE_PARSE_RED')
            budget, deadline, local_only = int(p[1]), int(p[2]), p[3] == 'true'
            eligible = [(int(o[2]), o[1]) for o in options
                        if int(o[2]) <= budget and int(o[3]) <= deadline
                        and (not local_only or o[4] == 'true')]
            choice = min(eligible)[1] if eligible else 'NONE'
            cost = next((cost for cost, name in eligible if name == choice), None)
            oracle = {'choice': choice, 'remaining': budget - cost if cost is not None else None}
            require(oracle == source['oracle'], 'FIXTURE_ORACLE_RED')
            require(len(row['arms']) == 3 and
                    set(x['arm'] for x in row['arms']) == set(ARMS), 'ARM_COVERAGE_RED')
            index = IDS.index(row['id'])
            require([a['arm'] for a in row['arms']] ==
                    list(ARMS[index % 3:] + ARMS[:index % 3]), 'ARM_ORDER_RED')
            refs = {}
            for item in row['arms']:
                arm = item['arm']
                require(item['status'] == 'RECORDED' and item['native_final'] is True
                        and item['process_reaped'] is True, 'NATIVE_FINAL_RED')
                metric = item['native_metrics']
                require(metric['status'] == 'FINAL'
                        and metric['actual_model'] == 'LFM2.5-350M-QAD-Q4_0.gguf'
                        and metric['role'] == 'C3_LANGUAGE'
                        and metric['input_message_count'] == 2
                        and metric['CAN_TRAIN_BODY'] is False
                        and metric['CAN_LATENT_INJECT'] is False, 'NATIVE_METRIC_RED')
                messages = item['messages']
                require(len(messages) == 2 and [m['role'] for m in messages] ==
                        ['system', 'user'], 'MESSAGE_ROLES_RED')
                system = messages[0]['content']
                require(sha256(system.encode()).hexdigest() == SYSTEM_SHA[arm],
                        'SYSTEM_PROMPT_RED')
                require(sha256(json.dumps(messages, sort_keys=True,
                        separators=(',', ':')).encode()).hexdigest() ==
                        item['messages_sha256'], 'MESSAGE_SHA_RED')
                require(source['policy_span'] not in system
                        and source['option_span'] not in system, 'SOURCE_SYSTEM_LEAK_RED')
                payload = jload(messages[1]['content'])
                require(payload['schema'] == 'v13.run117w.two_source_spans.v1'
                        and payload['source_role'] == 'UNTRUSTED_EXACT_USER', 'PAYLOAD_ROLE_RED')
                for key, full, span in (('policy', 'prior', 'policy_span'),
                                        ('options', 'current', 'option_span')):
                    v = payload[key]
                    ref = v['source_ref']
                    require(v['text'] == source[span]
                            and v['origin'] == 'STORE_EXACT_USER_NOT_MODEL_QUOTE'
                            and ref['modality'] == 'text'
                            and ref['sha256'] == sha256(source[full].encode()).hexdigest()
                            and source[full][ref['char_start']:ref['char_end']] == v['text']
                            and isinstance(ref['source_id'], str)
                            and ref['source_id'].startswith('src_'), 'SOURCE_REF_RED')
                    if key in refs:
                        require(ref == refs[key], 'SOURCE_REF_CROSS_ARM_RED')
                    else:
                        refs[key] = ref
                if arm == 'TYPED_JEF_FORMATTER':
                    require(payload.get('typed_jef_candidate') == oracle
                            and payload.get('candidate_authority') == 0
                            and payload.get('candidate_origin') ==
                            'DETERMINISTIC_SOURCE_RECIPE_NOT_NATIVE_JEF',
                            'TYPED_CONTROL_RED')
                else:
                    require('typed_jef_candidate' not in payload
                            and 'candidate_origin' not in payload, 'ORACLE_LEAK_RED')
                output = jload(item['output'])
                require(set(output) == {'choice', 'remaining'}
                        and output['choice'] in ('A', 'B', 'NONE')
                        and (output['remaining'] is None or
                             type(output['remaining']) is int), 'OUTPUT_SCHEMA_RED')
                correct = int(output == oracle)
                require(type(item['score']['correct']) is int
                        and item['score']['correct'] == correct
                        and item['score']['valid_json'] is True
                        and item['score']['parsed'] == output, 'SCORE_RECALC_RED')
                seen[arm] += 1
                scores[arm] += correct
        require(dict(seen) == {arm: 6 for arm in ARMS}, 'COUNT_RED')
        require(dict(scores) == report['scores']
                and dict(seen) == report['recorded_by_arm'], 'TOTALS_RED')
        require([scores[a] for a in ARMS] == [0, 0, 6], 'FROZEN_RESULT_RED')
        return {'status': 'INDEPENDENT_ORIGINAL_ARTIFACT_PASS',
                'artifact_sha256': sha256(raw).hexdigest(),
                'head': HEAD, 'phone_manifest_files': len(files),
                'outer_hashed_entries': len(checked),
                'native_c3_calls': report['native_c3_calls'],
                'scores': {a: scores[a] for a in ARMS},
                'step2_promoted': False, 'jepa_weight': 0,
                'redmi_measured': False}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('original_zip', type=Path)
    parser.add_argument('--unpin-artifact', action='store_true',
                        help='For local negative mutation tests only')
    args = parser.parse_args()
    print(json.dumps(audit(args.original_zip.read_bytes(), pinned=not args.unpin_artifact),
                     sort_keys=True))


if __name__ == '__main__':
    main()