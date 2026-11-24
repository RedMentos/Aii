#!/usr/bin/env python3
"""Run117AK independent read-only audit of original Run117AH native ZIP.

No model import, network access, source mutation, or fresh native inference.
An intact partial original remains RED; reported model scores are recomputed.
"""
from __future__ import annotations

from collections import Counter
from hashlib import sha256
from io import BytesIO
import argparse
import json
import zipfile

HEAD = '35e3bee123166b7761b6335adc423c8f73654c2b'
FIXTURE_SHA = 'cff778da793fbab2d456143b5d8290176b1097cc0e4d867eabbd9fbc2e05f67a'
IDS = ('Auric', 'Beryl', 'Cobalt', 'Daphne', 'Elder', 'Fable')
ROLES = ('B1_DETAIL', 'B2_GIST')
MODELS = {
    'B1_DETAIL': 'LFM2.5-1.2B-Instruct-QAD-Q4_0.gguf',
    'B2_GIST': 'Qwen3.5-0.8B-Q4_0.gguf',
}
STAGES = ('SOURCE', 'DEPS', 'PACK', 'ZIP', 'PREFLIGHT', 'INSTALL_C3',
          'INSTALL_BODIES', 'NATIVE', 'VERIFY', 'COMPILE', 'PRIVACY', 'DIFF')
COMPLETE = 'NATIVE_COMPLETE_BODY_ID_DIAGNOSTIC'


def require(condition, code):
    if not condition:
        raise ValueError(code)


def _unique(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'DUPLICATE_JSON_KEY_RED')
        result[key] = value
    return result


def _reject_constant(_):
    raise ValueError('NONFINITE_JSON_RED')


def _json(raw):
    return json.loads(raw, object_pairs_hook=_unique,
                      parse_constant=_reject_constant)


def _hash(raw):
    return sha256(raw).hexdigest()


def _sums(z):
    names = z.namelist()
    require(len(names) == len(set(names)), 'OUTER_DUPLICATE_ENTRY_RED')
    require(z.testzip() is None, 'OUTER_CRC_RED')
    seen = set()
    for line in z.read('SHA256SUMS').decode().splitlines():
        parts = line.split('  ./', 1)
        require(len(parts) == 2, 'OUTER_SUM_FORMAT_RED')
        digest, name = parts
        require(name in names and name not in seen,
                'OUTER_SUM_ENTRY_RED')
        require(_hash(z.read(name)) == digest, 'OUTER_SUM_HASH_RED')
        seen.add(name)
    require(seen == set(names) - {'SHA256SUMS'},
            'OUTER_SUM_COVERAGE_RED')
    return len(seen)


def _full_ref(ref, text):
    require(type(ref) is dict
            and ref.get('modality') == 'text'
            and ref.get('sha256') == _hash(text.encode())
            and type(ref.get('char_start')) is int
            and type(ref.get('char_end')) is int
            and ref['char_start'] == 0
            and ref['char_end'] == len(text)
            and type(ref.get('source_id')) is str,
            'FULL_SOURCE_REF_RED')


def _span(span, source, full_ref):
    require(type(span) is dict
            and span.get('origin') == 'STORE_EXACT_USER_NOT_MODEL_QUOTE',
            'SPAN_ORIGIN_RED')
    ref = span.get('source_ref')
    require(type(ref) is dict, 'SPAN_REF_SHAPE_RED')
    start, end = ref.get('char_start'), ref.get('char_end')
    require(type(start) is int and type(end) is int
            and 0 <= start < end <= len(source)
            and {k:v for k,v in ref.items()
                 if k not in ('char_start', 'char_end')} ==
            {k:v for k,v in full_ref.items()
             if k not in ('char_start', 'char_end')}
            and span.get('text') == source[start:end],
            'SPAN_SOURCE_BINDING_RED')


def _packet(evidence, kind):
    require(type(evidence) is dict
            and evidence.get('kind') == kind
            and type(evidence.get('raw')) is str
            and _hash(evidence['raw'].encode()) ==
            evidence.get('sha256'), 'RAW_PACKET_HASH_OR_KIND_RED')
    packet = _json(evidence['raw'])
    require(type(packet) is dict
            and packet.get('schema_version') == '1.0'
            and type(packet.get('packet_id')) is str
            and type(packet.get('event_id')) is str
            and type(packet.get('provenance')) is list,
            'PACKET_BASE_RED')
    return packet


def _native(item, role):
    # Baseline _observe records FINAL in native_metrics but does not expose
    # a separate native_final key; ID selections expose both.
    require(item.get('role') == role
            and item.get('process_reaped') is True
            and (item.get('native_final') is True
                 if 'native_final' in item else True),
            'NATIVE_ROLE_FINAL_REAP_RED')
    metrics = item.get('native_metrics')
    require(type(metrics) is dict
            and metrics.get('status') == 'FINAL'
            and metrics.get('actual_model') == MODELS[role]
            and metrics.get('role') == role,
            'NATIVE_MODEL_METRICS_RED')


def _selection(item, role, source, source_ref, expected):
    """Independently score persisted raw model ID, never trust reported bool."""
    _native(item, role)
    require(item.get('status') == 'RECORDED'
            and item.get('source_ref') == source_ref,
            'SELECTION_ITEM_SOURCE_RED')
    packet = _packet(item.get('packet_evidence'), 'BodySourceIdSelection')
    require(packet.get('role') == role
            and packet.get('source_ref') == source_ref
            and packet.get('provenance') == [source_ref]
            and packet.get('packet_id') == item.get('packet_id')
            and packet.get('model_hypothesis_not_fact') is True
            and packet.get('source_semantic_truth_authority') is False
            and packet.get('output_committed') is False
            and packet.get('delivery_authority') == 0
            and packet.get('learning_authority') == 0,
            'SELECTION_PACKET_AUTHORITY_RED')
    candidates = packet.get('candidates')
    require(type(candidates) is list and len(candidates) == 2,
            'SELECTION_CANDIDATES_RED')
    ids = []
    for candidate in candidates:
        require(type(candidate) is dict
                and type(candidate.get('span_id')) is str,
                'SELECTION_ID_SHAPE_RED')
        ids.append(candidate['span_id'])
        _span({k:v for k,v in candidate.items() if k != 'span_id'},
              source, source_ref)
    require(len(set(ids)) == 2, 'SELECTION_DUPLICATE_ID_RED')
    selected = packet.get('selected_id')
    require(selected in set(ids) | {'NONE'}, 'SELECTION_UNKNOWN_ID_RED')
    raw = item.get('raw_output')
    require(type(raw) is str
            and _hash(raw.encode()) == packet.get('raw_output_sha256')
            and len(raw.encode()) == packet.get('raw_output_bytes'),
            'SELECTION_OUTPUT_SHA_RED')
    parsed = _json(raw)
    require(type(parsed) is dict and set(parsed) == {'span_id'}
            and parsed['span_id'] == selected,
            'SELECTION_OUTPUT_JSON_RED')
    chosen = next((c for c in candidates if c['span_id'] == selected), None)
    expected_span = (None if chosen is None else
                     {k:v for k,v in chosen.items() if k != 'span_id'})
    require(packet.get('selected_span') == expected_span,
            'SELECTION_SELECTED_SPAN_RED')
    correct = bool(chosen is not None and chosen['text'] == expected)
    require(packet.get('selection_correct_shadow') is correct
            and item.get('model_id_correct') is correct,
            'SELECTION_REPORTED_SCORE_RED')
    status = ('SHADOW_ABSTAIN_RECORDED' if selected == 'NONE'
              else 'SHADOW_SOURCE_ID_SELECTED' if correct
              else 'SHADOW_WRONG_SOURCE_ID_RECORDED')
    require(item.get('component_status') == status,
            'SELECTION_COMPONENT_STATUS_RED')
    return int(correct)


def _offer(item, role, source_ref):
    _native(item, role)
    require(item.get('status') == 'RECORDED'
            and item.get('source_ref') == source_ref,
            'OFFER_ITEM_SOURCE_RED')
    offer = _packet(item.get('packet_evidence'), 'OfferPacket')
    query = _packet(item.get('query_evidence'), 'QueryPacket')
    require(offer.get('role') == role
            and offer.get('packet_id') == item.get('packet_id')
            and query.get('target_role') == role
            and query.get('packet_id') == item.get('query_packet_id')
            and source_ref in offer.get('provenance', [])
            and source_ref in query.get('provenance', []),
            'OFFER_QUERY_PROVENANCE_RED')


def _phone(z):
    raw = z.read('V13-Phone-Run117AH.zip')
    with zipfile.ZipFile(BytesIO(raw)) as n:
        require(n.testzip() is None, 'PHONE_CRC_RED')
        names = n.namelist()
        require(len(names) == len(set(names)), 'PHONE_DUPLICATE_RED')
        manifest = _json(n.read('V13-Phone/WORKSPACE_FILES.json'))
        files = manifest['files']
        require(manifest['schema_version'] == 1 and len(files) >= 2200,
                'PHONE_MANIFEST_RED')
        require(set('V13-Phone/' + path for path in files) ==
                set(names) - {'V13-Phone/WORKSPACE_FILES.json'},
                'PHONE_COVERAGE_RED')
        for path, digest in files.items():
            require(_hash(n.read('V13-Phone/' + path)) == digest,
                    'PHONE_HASH_RED:' + path)
        fixture_raw = n.read(
            'V13-Phone/docs/fixtures/RUN117AH_BODY_SOURCE_ID_SEED1069.json')
        require(_hash(fixture_raw) == FIXTURE_SHA,
                'PHONE_FIXTURE_SHA_RED')
        fixture = _json(fixture_raw)
        require(fixture['seed'] == 1069
                and fixture['roles'] == list(ROLES)
                and [r['id'] for r in fixture['rows']] == list(IDS),
                'PHONE_FIXTURE_COHORT_RED')
        return fixture, len(files)


def audit(raw: bytes, *, expected_sha: str):
    require(type(raw) is bytes and _hash(raw) == expected_sha,
            'ORIGINAL_ARTIFACT_SHA_RED')
    with zipfile.ZipFile(BytesIO(raw)) as z:
        outer_count = _sums(z)
        require(z.read('HEAD.txt').decode().strip() == HEAD,
                'ORIGINAL_HEAD_RED')
        exits = {name:int(z.read(name + '_EXIT.txt').decode().strip())
                 for name in STAGES}
        result = _json(z.read('RESULT.json'))
        require(result['head'] == HEAD and result['seed'] == 1069
                and result['fixture_sha256'] == FIXTURE_SHA
                and result['exits'] == exits
                and result['step2_promoted'] is False
                and result['b3_promoted'] is False
                and result['jepa_weight'] == 0
                and result['redmi_measured'] is False
                and result['whole_system_complete'] is False,
                'WORKFLOW_RECEIPT_RED')
        # A failed install/pack/native attempt may have no original report.
        # Preserve its RED rather than pretending it was a scored cohort.
        if ('V13-Phone-Run117AH.zip' not in z.namelist()
                or 'NATIVE_CASE/report.json' not in z.namelist()):
            require(set(exits.values()) != {0},
                    'GREEN_RECEIPT_MISSING_ORIGINAL_ARTIFACT_RED')
            return {
                'status': 'INDEPENDENT_ORIGINAL_NATIVE_NOT_RUN_RED_PRESERVED',
                'head': HEAD, 'artifact_sha256': _hash(raw),
                'outer_hashed_entries': outer_count,
                'original_exits': exits,
                'native_c3_proven': False, 'native_jef_proven': False,
                'native_c2_proven': False, 'step2_promoted': False,
                'jepa_weight': 0, 'redmi_measured': False,
            }
        fixture, phone_files = _phone(z)
        report = _json(z.read('NATIVE_CASE/report.json'))
        require(report['schema'] ==
                'v13.run117ah.body_source_id_native_seed1069.v1'
                and report['seed'] == 1069
                and report['fixture_sha256'] == FIXTURE_SHA
                and report['native_c3_calls'] == 0
                and report['native_jef_calls'] == 0
                and report['native_c2_calls'] == 0
                and report['age0'] == 'RECORD_ONLY'
                and report['step2_exit'] == 'EVIDENCE_NOT_PASSING'
                and report['b3'] == 'NO_PROMOTION'
                and report['body_jepa'] == 'UNAVAILABLE'
                and report['jepa_weight'] == 0
                and report['redmi_measured'] is False
                and report['whole_system_complete'] is False
                and report['output_committed'] is False
                and report['tool_dispatches'] == 0
                and report['delivery_authority'] == 0
                and report['learning_authority'] == 0
                and len(report['rows']) <= 6
                and 0 <= report['native_body_calls'] <= 30,
                'NATIVE_REPORT_NEGATIVE_GATES_RED')
        scores = Counter()
        pairs = 0
        ready = 0
        recorded = Counter()
        for i, row in enumerate(report['rows']):
            frozen = fixture['rows'][i]
            require(row['id'] == frozen['id'], 'ROW_ORDER_RED')
            if (row.get('prior_source_text') != frozen['prior']
                    or row.get('current_source_text') != frozen['current']
                    or row.get('no_live_output') is not True
                    or row.get('closed_store_ok') is not True):
                require(report['status'] != COMPLETE,
                        'COMPLETE_ROW_SOURCE_OR_CLOSED_STORE_RED')
                # Partial native attempt: retain RED; do not score a row
                # whose original source/closed-Store evidence is missing.
                continue
            prior = row['prior_source_ref']
            current = row['current_source_ref']
            _full_ref(prior, frozen['prior'])
            _full_ref(current, frozen['current'])
            require(len(row.get('offers', [])) <= 3
                    and len(row.get('id_selections', [])) <= 2,
                    'ROW_ITEM_COUNT_RED')
            for item in row['offers']:
                role = item['role']
                require(role in ROLES, 'OFFER_ROLE_RED')
                ref = prior if item['phase'] == 'prior' else current
                if item['status'] == 'RECORDED':
                    _offer(item, role, ref)
                    recorded['offers'] += 1
            role_scores = {}
            for item in row['id_selections']:
                role = item['role']
                require(role in ROLES, 'SELECTION_ROLE_RED')
                ref, source, expected = (
                    (prior, frozen['prior'], frozen['policy_span'])
                    if role == 'B2_GIST' else
                    (current, frozen['current'], frozen['option_span']))
                if item['status'] == 'RECORDED':
                    correct = _selection(item, role, source, ref, expected)
                    scores[role] += correct
                    role_scores[role] = correct
                    recorded['id_selections'] += 1
            pair = int(len(role_scores) == 2 and all(role_scores.values()))
            if 'id_pair_correct' in row:
                require(row['id_pair_correct'] is bool(pair),
                        'ROW_PAIR_SCORE_RED')
            else:
                require(report['status'] != COMPLETE,
                        'COMPLETE_ROW_PAIR_MISSING_RED')
            pairs += pair
            ready += int(row.get('baseline_quote_ready') is True)
        complete = (report['status'] == COMPLETE
                    and set(exits.values()) == {0}
                    and report['native_body_calls'] == 30
                    and len(report['rows']) == 6
                    and recorded == Counter({'offers':18,'id_selections':12})
                    and all(row['status'] == 'RECORDED'
                            and len(row['offers']) == 3
                            and len(row['id_selections']) == 2
                            for row in report['rows']))
        if complete:
            require(report['baseline_quote_ready_count'] == ready
                    and report['model_id_pair_correct_count'] == pairs
                    and report['model_id_by_role_correct'] ==
                    {role:scores[role] for role in ROLES},
                    'NATIVE_AGGREGATE_SCORE_RED')
        return {
            'status': ('INDEPENDENT_ORIGINAL_NATIVE_STRUCTURAL_PASS'
                       if complete else 'INDEPENDENT_ORIGINAL_NATIVE_RED_PRESERVED'),
            'head': HEAD, 'artifact_sha256': _hash(raw),
            'outer_hashed_entries': outer_count,
            'phone_manifest_files': phone_files,
            'native_body_calls': report['native_body_calls'],
            'recorded': dict(recorded),
            'model_id_by_role_correct': {role:scores[role] for role in ROLES},
            'model_id_pair_correct_count': pairs,
            'baseline_quote_ready_count': ready,
            'original_status': report['status'],
            'original_exits': exits,
            'native_c3_proven': False, 'native_jef_proven': False,
            'native_c2_proven': False, 'step2_promoted': False,
            'jepa_weight': 0, 'redmi_measured': False,
        }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('original_zip')
    parser.add_argument('--expected-sha', required=True)
    args = parser.parse_args()
    from pathlib import Path
    print(json.dumps(audit(Path(args.original_zip).read_bytes(),
                           expected_sha=args.expected_sha), sort_keys=True))


if __name__ == '__main__':
    main()
