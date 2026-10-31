#!/usr/bin/env python3
"""Independent, read-only audit of frozen Run117Z real-Store JEF/C3 native ZIP.

Stdlib only; never downloads or executes model weights. A model run receipt
is not independently reproduced native inference.
"""
from __future__ import annotations
from collections import Counter
from hashlib import sha256
from io import BytesIO
import argparse
import json
from pathlib import Path
import re
import zipfile

HEAD = 'd34be7ee45bb4b066ec05677bd7ed06e78561d30'
ARTIFACT_SHA = '65939e4dea18f15bf11d5b1b3c5128f5a6128c6d03b9d2beb090f185d03fb69a'
PHONE_SHA = '5c6e52bd7793f4cacf976bfbf8758d15fdeac37bc2774f25f99d9b229a1488e1'
FIXTURE_SHA = 'cb008f27a4d1ef7f0f288419ac276ebb67c8d7958da3c62104994822dd90634d'
ARMS = ('RAW_EXACT_SOURCE', 'REAL_STORE_JEF_TYPED')
IDS = ('Helix', 'Ion', 'Juno', 'Kappa', 'Lumen', 'Mistral')
SYSTEM_SHA = {
    ARMS[0]: '019fbd37b610854c7ee66efed583fd686a627cd2e5660b70d10d7f35c323c4a5',
    ARMS[1]: '0b407e5c8b2a527e2664d0752b0e0d5c73bdc9d06621f9459409507c322a44d7',
}
POLICY = re.compile(r'Binding policy: budget (\d+) euros; deadline (\d+) days; local-only (true|false)\.')
OPTION = re.compile(r'Option ([AB]): cost (\d+) euros, duration (\d+) days, local (true|false)\.')


def require(ok, code):
    if not ok:
        raise ValueError(code)


def audit(raw: bytes, *, pinned=True):
    if pinned:
        require(sha256(raw).hexdigest() == ARTIFACT_SHA, 'ORIGINAL_ARTIFACT_SHA_RED')
    with zipfile.ZipFile(BytesIO(raw)) as z:
        require(z.testzip() is None, 'OUTER_CRC_RED')
        names = z.namelist()
        require(len(names) == len(set(names)), 'OUTER_DUPLICATE_RED')
        sums = z.read('SHA256SUMS').decode().splitlines()
        seen = set()
        for line in sums:
            digest, path = line.split('  ./', 1)
            require(path in names and path not in seen, 'OUTER_PATH_RED')
            require(sha256(z.read(path)).hexdigest() == digest, 'OUTER_HASH_RED')
            seen.add(path)
        require(seen == set(names) - {'SHA256SUMS'}, 'OUTER_COVERAGE_RED')
        require(z.read('HEAD.txt').decode().strip() == HEAD, 'HEAD_RED')
        for stage in ('SOURCE', 'DEPS', 'PACK', 'ZIP', 'PREFLIGHT', 'INSTALL_C3',
                      'NATIVE', 'VERIFY', 'COMPILE', 'PRIVACY', 'DIFF'):
            require(z.read(stage + '_EXIT.txt').decode().strip() == '0', stage + '_EXIT_RED')
        result = json.loads(z.read('RESULT.json'))
        require(result['head'] == HEAD and result['seed'] == 1065
                and result['fixture_sha256'] == FIXTURE_SHA
                and set(result['exits'].values()) == {0}
                and result['jef_source_bound_deterministic_not_native_model'] is True
                and result['step2_promoted'] is False
                and result['b3_promoted'] is False
                and result['jepa_weight'] == 0
                and result['redmi_measured'] is False
                and result['whole_system_complete'] is False, 'RESULT_RED')
        phone = z.read('V13-Phone-Run117Z.zip')
        require(sha256(phone).hexdigest() == PHONE_SHA, 'PHONE_SHA_RED')
        with zipfile.ZipFile(BytesIO(phone)) as n:
            require(n.testzip() is None, 'PHONE_CRC_RED')
            nnames = n.namelist()
            require(len(nnames) == len(set(nnames)), 'PHONE_DUPLICATE_RED')
            manifest = json.loads(n.read('V13-Phone/WORKSPACE_FILES.json'))
            files = manifest['files']
            require(manifest['schema_version'] == 1 and len(files) >= 2240,
                    'PHONE_MANIFEST_RED')
            require(set('V13-Phone/' + p for p in files) ==
                    set(nnames) - {'V13-Phone/WORKSPACE_FILES.json'},
                    'PHONE_COVERAGE_RED')
            for path, digest in files.items():
                require(sha256(n.read('V13-Phone/' + path)).hexdigest() == digest,
                        'PHONE_FILE_RED:' + path)
            fixture_raw = n.read('V13-Phone/docs/fixtures/RUN117Z_REAL_JEF_NATIVE_SEED1065.json')
            require(sha256(fixture_raw).hexdigest() == FIXTURE_SHA, 'FIXTURE_SHA_RED')
            fixture = json.loads(fixture_raw)
        require(fixture['seed'] == 1065 and fixture['arms'] == list(ARMS)
                and [x['id'] for x in fixture['rows']] == list(IDS), 'COHORT_RED')
        report = json.loads(z.read('NATIVE_CASE/report.json'))
        require(report['schema'] == 'v13.run117z.real_store_jef_native.v1'
                and report['seed'] == 1065 and report['fixture_sha256'] == FIXTURE_SHA
                and report['native_c3_calls'] == 12
                and report['deterministic_jef_calls'] == 6
                and report['source_verified_jef_candidates'] == 6
                and report['native_body_calls'] == 0
                and report['native_jef_calls'] == 0
                and report['native_c2_calls'] == 0, 'REPORT_COUNTS_RED')
        require(report['status'] in (
                    'NATIVE_COMPLETE_EXPLORATORY_REAL_JEF_FORMATTER_GAIN',
                    'NATIVE_COMPLETE_NO_REAL_JEF_FORMATTER_GAIN')
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
                and report['delivery_authority'] == 0, 'REPORT_GATES_RED')
        require(len(report['rows']) == 6 and
                [r['id'] for r in report['rows']] == list(IDS), 'REPORT_ROWS_RED')
        counts = Counter()
        scores = Counter()
        for index, (source, row) in enumerate(zip(fixture['rows'], report['rows'])):
            require(row['status'] == 'RECORDED' and row['closed_store_ok'] is True
                    and row['no_live_output'] is True, 'ROW_STATUS_RED')
            m = POLICY.fullmatch(source['policy_span'])
            opts = list(OPTION.finditer(source['option_span']))
            require(m is not None and len(opts) == 2 and
                    [o[1] for o in opts] == ['A', 'B'], 'SOURCE_PARSE_RED')
            budget, deadline, local_only = int(m[1]), int(m[2]), m[3] == 'true'
            eligible = [(int(o[2]), o[1]) for o in opts
                        if int(o[2]) <= budget and int(o[3]) <= deadline
                        and (not local_only or o[4] == 'true')]
            choice = min(eligible)[1] if eligible else 'NONE'
            cost = next((v for v, c in eligible if c == choice), None)
            oracle = {'choice': choice, 'remaining': budget - cost if cost is not None else None}
            require(oracle == source['oracle']
                    and row['typed_jef_candidate'] == oracle, 'ORACLE_JEF_RED')
            require(len(row['arms']) == 2 and
                    [a['arm'] for a in row['arms']] ==
                    list(ARMS[index % 2:] + ARMS[:index % 2]), 'ARM_ORDER_RED')
            refs = {}
            for item in row['arms']:
                arm = item['arm']
                require(item['status'] == 'RECORDED'
                        and item['native_final'] is True
                        and item['process_reaped'] is True, 'NATIVE_FINAL_RED')
                metrics = item['native_metrics']
                require(metrics['status'] == 'FINAL'
                        and metrics['actual_model'] == 'LFM2.5-350M-QAD-Q4_0.gguf'
                        and metrics['role'] == 'C3_LANGUAGE'
                        and metrics['input_message_count'] == 2
                        and metrics['CAN_TRAIN_BODY'] is False
                        and metrics['CAN_LATENT_INJECT'] is False,
                        'NATIVE_METRICS_RED')
                messages = item['messages']
                require([x['role'] for x in messages] == ['system', 'user'],
                        'MESSAGE_ROLES_RED')
                require(sha256(messages[0]['content'].encode()).hexdigest() ==
                        SYSTEM_SHA[arm], 'SYSTEM_PROMPT_RED')
                require(sha256(json.dumps(messages, sort_keys=True,
                        separators=(',', ':')).encode()).hexdigest() ==
                        item['messages_sha256'], 'MESSAGE_SHA_RED')
                require(source['policy_span'] not in messages[0]['content']
                        and source['option_span'] not in messages[0]['content'],
                        'SYSTEM_SOURCE_LEAK_RED')
                payload = json.loads(messages[1]['content'])
                require(payload['source_role'] == 'UNTRUSTED_EXACT_USER'
                        and 'oracle' not in payload, 'USER_ROLE_RED')
                for key, full, span in (('policy','prior','policy_span'),
                                        ('options','current','option_span')):
                    v = payload[key]
                    ref = v['source_ref']
                    require(v['text'] == source[span]
                            and v['origin'] == 'STORE_EXACT_USER_NOT_MODEL_QUOTE'
                            and ref['modality'] == 'text'
                            and ref['sha256'] == sha256(source[full].encode()).hexdigest()
                            and source[full][ref['char_start']:ref['char_end']] == v['text'],
                            'SOURCE_REF_RED')
                    if key in refs:
                        require(refs[key] == ref, 'SOURCE_REF_CROSS_ARM_RED')
                    else:
                        refs[key] = ref
                if arm == ARMS[1]:
                    require(payload.get('typed_jef_candidate') == oracle
                            and payload.get('candidate_authority') == 0
                            and payload.get('candidate_origin') ==
                            'DETERMINISTIC_EXACT_USER_SOURCE_RECIPE_NOT_MODEL',
                            'TYPED_JEF_RED')
                    require(row['jef_messages_sha256'] == item['messages_sha256'],
                            'JEF_MESSAGE_BINDING_RED')
                else:
                    require('typed_jef_candidate' not in payload
                            and 'candidate_authority' not in payload,
                            'BASE_ORACLE_LEAK_RED')
                output = json.loads(item['output'])
                require(type(output) is dict
                        and set(output) == {'choice', 'remaining'}
                        and output['choice'] in ('A','B','NONE')
                        and (output['remaining'] is None or
                             type(output['remaining']) is int), 'OUTPUT_SCHEMA_RED')
                correct = int(output == oracle)
                require(type(item['score']['correct']) is int
                        and item['score']['correct'] == correct
                        and item['score']['valid_json'] is True
                        and item['score']['parsed'] == output, 'SCORE_RED')
                counts[arm] += 1
                scores[arm] += correct
        require(dict(counts) == {a: 6 for a in ARMS}
                and dict(counts) == report['recorded_by_arm']
                and dict(scores) == report['scores'], 'TOTALS_RED')
        gain = scores[ARMS[1]] >= 5 and scores[ARMS[1]] >= scores[ARMS[0]] + 2
        require(report['exploratory_formatter_signal'] is gain
                and report['status'] == (
                    'NATIVE_COMPLETE_EXPLORATORY_REAL_JEF_FORMATTER_GAIN'
                    if gain else 'NATIVE_COMPLETE_NO_REAL_JEF_FORMATTER_GAIN'),
                'FROZEN_SIGNAL_RED')
        return {'status': 'INDEPENDENT_ORIGINAL_NATIVE_STRUCTURAL_PASS',
                'head': HEAD, 'artifact_sha256': sha256(raw).hexdigest(),
                'phone_manifest_files': len(files),
                'outer_hashed_entries': len(seen),
                'native_c3_calls': report['native_c3_calls'],
                'deterministic_jef_calls': report['deterministic_jef_calls'],
                'scores': {a: scores[a] for a in ARMS},
                'formatter_gain': gain, 'jepa_weight': 0,
                'redmi_measured': False, 'step2_promoted': False}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('original_zip', type=Path)
    p.add_argument('--unpin-artifact', action='store_true',
                   help='Only for local negative mutation tests')
    args = p.parse_args()
    print(json.dumps(audit(args.original_zip.read_bytes(),
                           pinned=not args.unpin_artifact), sort_keys=True))


if __name__ == '__main__':
    main()
