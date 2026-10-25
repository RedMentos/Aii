"""Run170: source-bound read-only audit of pinned Run169 CI metadata.

Integrity/consistency only; not a replay, answer-quality proof, JEPA or Redmi.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import zipfile

ARCHIVE_SHA = '16c41e05a4cba14bc520759bab13543e123e2cf7ee4b6f10752306c3c2aed760'
MODEL_SHA = 'bb741ebb106d543e9de114b843a3d3d73d51c74b5801e69da2abde821a0cb3e1'
PATCH_SHA = 'fb07c373c7770d298ed6c8145950166cb4b924ac9166bff7c141b4eafc69f89f'
PROMPT_SHA = 'f744b15218f8448879ae4339cf158e463e114b2026e6967fa9e3e7197f3ac64f'
GATES = {'STEP2':'UTILITY_FAIL','B3_L1':'FAIL','Body_JEPA':'UNAVAILABLE',
         'jepa_weight':0,'DS2_H2':'FAIL','V13':'INCOMPLETE'}
NAMES = ['blk.0.attn_norm.weight','blk.0.ffn_norm.weight',
         'blk.1.attn_norm.weight','blk.1.ffn_norm.weight']
HEX = re.compile(r'[0-9a-f]{64}\\Z')


def check(ok, reason):
    if not ok:
        raise ValueError('RUN170_REFUSED:' + reason)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def pairs_unique(rows):
    out = {}
    for k, v in rows:
        check(k not in out, 'duplicate_json_key')
        out[k] = v
    return out


def load(path):
    path = Path(path)
    check(path.is_file() and not path.is_symlink(), 'archive_type')
    check(0 < path.stat().st_size <= 1000000, 'archive_size')
    check(digest(path.read_bytes()) == ARCHIVE_SHA, 'archive_sha')
    with zipfile.ZipFile(path) as z:
        entries = z.infolist()
        check(len(entries) == 1 and entries[0].filename == 'metadata-summary.json', 'archive_members')
        check(entries[0].file_size < 100000 and entries[0].compress_size > 0, 'entry_size')
        check(z.testzip() is None, 'archive_crc')
        raw = z.read(entries[0])
    data = json.loads(raw, object_pairs_hook=pairs_unique,
                      parse_constant=lambda _: check(False, 'nonfinite_json'))
    return data, digest(raw)


def verify(d):
    check(type(d) is dict and d.get('schema') == 'V13_RUN169_REAL_PINNED_B1_PRIVATE_NATIVE_RECEIVER_V1', 'schema')
    check(d.get('evidence_class') == 'LINUX_NATIVE_B1_PRIVATE_RECEIVER_NO_JEPA_OR_UTILITY', 'class')
    check(d.get('source_revision') == '6767265158422fb8a19c62ceb45f16f05363615b', 'revision')
    check(d.get('full_source_sha256') == MODEL_SHA and d.get('full_source_bytes') == 695755488, 'model')
    check(d.get('gates') == GATES and d.get('native_training') is False and d.get('redmi') is False, 'root_gates')
    check(d.get('tensor_count') == 148 and d.get('fp32_count') == 55, 'tensor_counts')
    a = d.get('external_audit', {})
    check(a.get('schema') == 'V13_RUN163_FP32_EXPORT_AUDIT_V1', 'audit_schema')
    check(a.get('model_sha256') == MODEL_SHA and a.get('selected_count') == 4, 'audit_source')
    check(a.get('selected_bytes_exact') is True and a.get('selected_source_spans_nonoverlap') is True, 'audit_bytes')
    check(a.get('gates') == GATES and a.get('body_training_authority') == 0 and a.get('gate') == 'UNVERIFIED', 'audit_gates')
    check(d.get('private_master_sha256') == a.get('master_sha256'), 'master_binding')
    tensors = d.get('selected_tensors', [])
    check(type(tensors) is list and len(tensors) == 4, 'selected_count')
    spans = []
    for i, t in enumerate(tensors):
        check(t.get('name') == NAMES[i] and t.get('dtype') == 'float32' and
              t.get('shape') == [2048] and t.get('bytes') == 8192, 'selected_type')
        start = t.get('offset_in_gguf')
        check(type(start) is int and start >= 0 and HEX.fullmatch(str(t.get('sha256'))), 'selected_span')
        spans.append((start, start + 8192))
    check(all(x[1] <= y[0] for x, y in zip(spans, spans[1:])) and
          spans[-1][1] <= d['full_source_bytes'], 'span_overlap_or_bounds')
    m = d.get('synthetic_micro', {})
    check(m.get('schema') == 'V13_RUN166_FP32_MASTER_MICRO_V1' and
          m.get('synthetic_objective') == 'QUADRATIC_W0_PLUS_0P01_NOT_JEPA', 'micro_objective')
    check(m.get('registered_model_sha256') == MODEL_SHA and
          m.get('source_master_sha256') == d['private_master_sha256'], 'micro_source')
    check(m.get('gates') == GATES and m.get('body_training_authority') == 0 and
          m.get('jepa_weight') == 0 and m.get('gate') == 'UNVERIFIED', 'micro_gates')
    check(type(m.get('applied_update_l2')) in (int, float) and
          0 < m['applied_update_l2'] <= .20001, 'micro_norm')
    check(m.get('selected_tensors') == 4 and len(m.get('per_tensor', [])) == 4, 'micro_count')
    r = d.get('private_native_receiver', {})
    check(r.get('schema') == 'V13_RUN169_NATIVE_PRIVATE_B1_RECEIVER_V1' and
          r.get('evidence_class') == 'NATIVE_RECEIVER_ONLY_NO_JEPA_OR_UTILITY', 'receiver_schema')
    check(r.get('model_sha256') == MODEL_SHA and r.get('private_restored_sha256') == MODEL_SHA and
          r.get('private_patch_sha256') == PATCH_SHA, 'receiver_model')
    check(r.get('prompt_set_sha256') == PROMPT_SHA and r.get('gates') == GATES and
          r.get('jepa_weight') == 0 and r.get('body_training_authority') == 0, 'receiver_gates')
    check(r.get('native_model_loads_sequential') is True and
          r.get('native_runner_unloaded') is True, 'receiver_lifecycle')
    rows = r.get('rows')
    check(type(rows) is list and len(rows) == 6, 'rows_count')
    for i, row in enumerate(rows):
        check(row.get('model') == ('baseline' if i < 3 else 'private_patched') and
              type(row.get('prompt_index')) is int and row['prompt_index'] == i % 3, 'row_order')
        check(type(row.get('response_chars')) is int and 0 < row['response_chars'] <= 4096 and
              HEX.fullmatch(str(row.get('response_sha256'))), 'row_digest')
    pairs = r.get('pairs')
    check(type(pairs) is list and len(pairs) == 3, 'pair_count')
    for i, pair in enumerate(pairs):
        check(type(pair.get('prompt_index')) is int and pair['prompt_index'] == i and
              type(pair.get('same_output_hash')) is bool and
              pair['same_output_hash'] == (rows[i]['response_sha256'] == rows[i + 3]['response_sha256']), 'pair_truth')
    return {'schema':'V13_RUN170_RUN169_METADATA_AUDIT_V1','paired_identical':sum(x['same_output_hash'] for x in pairs),
            'paired_total':3,'native_replay':False,'predictive_jepa_proven':False,
            'semantic_utility_proven':False,'redmi':False,'gates':GATES,
            'limitations':['metadata-only, no independent native replay or response adjudication',
                           'synthetic quadratic norm update, not predictive JEPA']}


def adversarial_tests(doc):
    import copy
    cases = [
        lambda x: x['gates'].__setitem__('STEP2', 'PASS'),
        lambda x: x.__setitem__('native_training', True),
        lambda x: x.__setitem__('redmi', True),
        lambda x: x.__setitem__('full_source_sha256', '0'*64),
        lambda x: x['external_audit'].__setitem__('selected_bytes_exact', False),
        lambda x: x['selected_tensors'][1].__setitem__('offset_in_gguf', x['selected_tensors'][0]['offset_in_gguf']),
        lambda x: x['synthetic_micro'].__setitem__('synthetic_objective', 'JEPA'),
        lambda x: x['private_native_receiver']['pairs'][0].__setitem__('same_output_hash', False),
        lambda x: x['private_native_receiver']['rows'][3].__setitem__('response_sha256', '0'*64),
        lambda x: x['private_native_receiver'].__setitem__('prompt_set_sha256', '0'*64),
    ]
    for i, mutate in enumerate(cases):
        changed = copy.deepcopy(doc)
        mutate(changed)
        try:
            verify(changed)
        except ValueError:
            continue
        raise AssertionError('adversarial_mutation_accepted:' + str(i))
    return len(cases)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('archive')
    p.add_argument('--selftest', action='store_true')
    args = p.parse_args()
    doc, meta_sha = load(args.archive)
    result = verify(doc)
    result.update(archive_sha256=ARCHIVE_SHA, metadata_sha256=meta_sha)
    if args.selftest:
        result['adversarial_mutations_refused'] = adversarial_tests(doc)
    print(json.dumps(result, sort_keys=True, indent=2))
