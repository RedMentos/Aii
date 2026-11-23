"""Run43: source-pinned original TP/s27 post-hoc software replay; NO native.

Original Linux-native evidence remains immutable. Only prior user source text
and current question enter the Run42 selector; oracle is scored afterwards.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from scripts import run42_b2_eligibility_source_shadow as shadow
from scripts import run39_b2_rule_span_candidate as spans
from tests.test_run40_b2_store_history_readonly import Store

ORIGINAL_HEAD = 'fa76c7599fc066b7cb2d58b133a649bd9604ded9'
ORIGINAL_RAW_SHA256 = '3c4e9aada921da8a35b43b69f720757369777d4ab8242e30f7067314f758e1d9'
ORIGINAL_ZIP_SHA256 = '965bf4ef904cf96c759e1324b74c23662b03f1aa1c5c4698be71e9f5bb9db635'
SCHEMA = 'v13.run43.tp27.source_tool.posthoc.v1'


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def verified_artifact(root):
    root = Path(root).resolve()
    manifest = (root / 'SHA256SUMS.txt').read_text().splitlines()
    if len(manifest) != 29:
        raise ValueError('RUN43_ORIGINAL_MANIFEST_COUNT')
    seen = set()
    for line in manifest:
        want, name = line.split(maxsplit=1)
        name = name.lstrip('*').removeprefix('./')
        path = root / name
        if (name in seen or not path.resolve().is_relative_to(root) or
                path.is_symlink() or not path.is_file() or _sha(path.read_bytes()) != want):
            raise ValueError('RUN43_ORIGINAL_RAW_TAMPER')
        seen.add(name)
    if (root / 'HEAD.txt').read_text().strip() != ORIGINAL_HEAD:
        raise ValueError('RUN43_ORIGINAL_HEAD')
    raw = (root / 'step2_TP_s27.json').read_bytes()
    if _sha(raw) != ORIGINAL_RAW_SHA256:
        raise ValueError('RUN43_ORIGINAL_SOURCE_SHA')
    receipt = json.loads((root / 'RECEIPT.json').read_bytes())
    if (receipt['raw_source_sha256'] != ORIGINAL_RAW_SHA256 or
            receipt['native_status'] != 'UTILITY_FAIL' or
            receipt['tool_status'] != 'TOOL_UTILITY_FAIL' or
            receipt['canonical_gate_pass'] is not False or
            receipt['jepa_weight'] != 0 or
            receipt['native_rows'] != 70 or receipt['tool_rows'] != 70):
        raise ValueError('RUN43_ORIGINAL_NEGATIVE_GATE')
    return json.loads(raw)


def predict_fixture(fixture, preparation):
    """Never reads fixture oracle; use only original source-ref-verified history."""
    texts = fixture['history']
    events = preparation['prior_events']
    if len(texts) != 3 or len(events) != 3:
        raise ValueError('RUN43_HISTORY_SHAPE')
    for text, event in zip(texts, events):
        ref = event['source_ref']
        if (ref['char_start'] != 0 or ref['char_end'] != len(text) or
                _sha(text.encode()) != ref['sha256']):
            raise ValueError('RUN43_HISTORY_SOURCE_TAMPER')
    s = Store()
    for text in texts:
        event = s.event(text)
        s.offer(event)
    current = s.event(fixture['current'])
    result = shadow.evaluate(s, current, 's', 'g', 'm')
    item = result['decision']
    if (result['authority'] != 'SHADOW_NO_AUTHORITY' or
            result['canonical_gate_pass'] is not False or
            result['native_executed'] is not False):
        raise ValueError('RUN43_SHADOW_AUTHORITY')
    return {
        'fixture_id': fixture['id'], 'status': result['status'],
        'action': item['action'] if item else None,
        'remaining': [o['remaining'] for o in item['options']] if item else None,
        'eligible': [o['eligible'] for o in item['options']] if item else None,
        'selected_source_hashes': [r['sha256'] for r in result['source_refs']],
        'first240_cues': sum(bool(rx.search(texts[0][:240])) for rx in spans.CUES.values()),
        'canonical_gate_pass': False, 'jepa_weight': 0,
    }


def replay(native):
    preparations = {p['fixture']: p for p in native['preparations']}
    fixtures = [f for f in native['fixtures'] if f['type'] in ('SPLIT', 'RULE')]
    if len(fixtures) != 6 or len({f['id'] for f in fixtures}) != 6:
        raise ValueError('RUN43_FIXTURE_COHORT')
    # Prediction is closed before consulting any oracle field.
    predictions = [predict_fixture(f, preparations[f['id']]) for f in fixtures]
    for pred, fixture in zip(predictions, fixtures):
        refs = preparations[fixture['id']]['prior_events']
        # RULE fixtures put option clauses in the current turn; SPLIT uses the earlier sheet.
        from v13.agi import eligibility
        current_options = (eligibility.fixed_option('A', fixture['current']) is not None and
                           eligibility.fixed_option('B', fixture['current']) is not None)
        option_sha = _sha(fixture['current'].encode()) if current_options else refs[2]['source_ref']['sha256']
        expected = [refs[0]['source_ref']['sha256'], option_sha]
        if pred['selected_source_hashes'] and pred['selected_source_hashes'] != expected:
            raise ValueError('RUN43_SELECTED_SOURCE_MISMATCH')
        if pred['remaining'] is not None and len(pred['remaining']) != 2:
            raise ValueError('RUN43_OPTION_COUNT')
    counts = {'fixtures': len(fixtures), 'actions_exact': 0,
              'remaining_fields_exact': 0, 'eligibility_fields_exact': 0,
              'first240_all_three_cues': 0}
    for pred, fixture in zip(predictions, fixtures):
        oracle = fixture['oracle']
        counts['actions_exact'] += int(pred['action'] == oracle['action'])
        counts['first240_all_three_cues'] += int(pred['first240_cues'] == 3)
        if pred['remaining'] is not None:
            counts['remaining_fields_exact'] += sum(a == b['remaining'] for a, b in zip(pred['remaining'], oracle['options']))
        if pred['eligible'] is not None:
            counts['eligibility_fields_exact'] += sum(a == b['eligible'] for a, b in zip(pred['eligible'], oracle['options']))
    return {'schema': SCHEMA, 'scope': 'POST_HOC_RECONSTRUCTED_SQLITE_SOFTWARE_ONLY',
            'original_native_head': ORIGINAL_HEAD, 'original_native_zip_sha256': ORIGINAL_ZIP_SHA256,
            'original_native_source_sha256': ORIGINAL_RAW_SHA256,
            'original_native_status': 'UTILITY_FAIL', 'original_tool_status': 'TOOL_UTILITY_FAIL',
            'counts': counts, 'predictions': predictions,
            'claim_limits': ['No native B2/C3 inference in this replay.',
                             'The six original fixtures are known; this is post-hoc, not a new held-out cohort.',
                             'Original TP/s27 gates remain negative; no user-facing action authority.'],
            'canonical_gate_pass': False, 'phone_measured': False,
            'jepa_weight': 0, 'whole_system_complete': False}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--original-extracted', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args(argv)
    report = replay(verified_artifact(a.original_extracted))
    if a.out.exists():
        raise ValueError('RUN43_OUTPUT_EXISTS')
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(',', ':'))+'\n')
    print(json.dumps({'status': report['scope'], 'counts': report['counts']}, sort_keys=True))


if __name__ == '__main__':
    main()
