"""Exploratory posthoc full-task diagnostic for frozen seed61 original raw.

NOT a preregistered score, gate, native rerun, or replacement of score_pair.
Strict name+finish claim extraction can undercount paraphrases; mark uncertain.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import zipfile

ARMS = ('A_C3_ONLY', 'B_B1_ONLY', 'C_B2_ONLY', 'D_DISTINCT_BOTH',
        'E_SHARED_DUAL_COLD', 'F_NATIVE_AUTO')


def sooner_claim(output, fixture):
    """Conservative named 'finishes sooner/first' extraction; no inference from arithmetic."""
    names = (fixture['a'], fixture['b'])
    found = set()
    negated = False
    for name in names:
        n = re.escape(name)
        patterns = (
            rf'(?i)\b{n}\b[^.!?\n]{{0,75}}?\b(?:finish(?:es)?|would\s+finish|will\s+finish|complet(?:es?|ion))\b[^.!?\n]{{0,35}}?\b(?:sooner|first|earlier|fastest)\b',
            rf'(?i)\b{n}\b[^.!?\n]{{0,75}}?\b(?:is|would\s+be)\b[^.!?\n]{{0,35}}?\b(?:faster|quicker)\b',
            rf'(?i)\b(?:sooner|first|earlier|fastest)\b[^.!?\n]{{0,40}}?\b{n}\b',
        )
        for pattern in patterns:
            for match in re.finditer(pattern, output):
                if re.search(r"(?i)\b(?:not|never|nicht|kein\w*|no)\b|n.t", match.group(0)):
                    negated = True
                else:
                    found.add(name)
    if negated:
        return 'AMBIGUOUS'
    if len(found) != 1:
        return 'AMBIGUOUS' if found else 'NO_EXPLICIT_CLAIM'
    expected = fixture['a'] if fixture['a_days'] < fixture['b_days'] else fixture['b']
    return 'CORRECT' if next(iter(found)) == expected else 'INCORRECT'


def audit(path, expected_sha256):
    path = Path(path)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != expected_sha256:
        raise ValueError('ORIGINAL_ZIP_SHA256_CHANGED')
    with zipfile.ZipFile(path) as z:
        if z.testzip() is not None:
            raise ValueError('ZIP_CRC_ERROR')
        report = json.loads(z.read('pilot/report.json'))
        if report['schema'] != 'v13.c2_body.isolated_postclose.seed61.v1' or report['seed'] != 61:
            raise ValueError('WRONG_ORIGINAL_COHORT')
        if len(report['rows']) != 24 or tuple(report['arms']) != ARMS:
            raise ValueError('ROW_OR_ARM_IDENTITY_CHANGED')
        out = []
        for row in report['rows']:
            i, arm = row['index'], row['arm']
            fixture = report['fixtures'][i//6]
            raw = json.loads(z.read(f'pilot/raw/{i:02d}_{arm}.json'))
            if raw['flags'] != row['flags'] or raw['score'] != row['score'] or raw['final_output'] != row['final_output']:
                raise ValueError('RAW_REPORT_SOURCE_CHANGED')
            if raw['raw_audit']['source_errors'] != [] or not all(raw['raw_audit']['checks'].values()):
                raise ValueError('SOURCE_AUDIT_RED')
            label = sooner_claim(row['final_output'], fixture)
            out.append({'index': i, 'arm': arm, 'fixture': fixture['project'],
                        'registered_remainder_score_out_of_2': row['score']['correct'],
                        'sooner_claim_exploratory': label,
                        'full_task_exploratory': row['score']['correct']==2 and label=='CORRECT'})
        by_arm = {}
        for arm in ARMS:
            subset = [r for r in out if r['arm']==arm]
            by_arm[arm] = {'registered_remainders_out_of_8': sum(x['registered_remainder_score_out_of_2'] for x in subset),
                           'sooner_correct_out_of_4': sum(x['sooner_claim_exploratory']=='CORRECT' for x in subset),
                           'sooner_wrong_out_of_4': sum(x['sooner_claim_exploratory']=='INCORRECT' for x in subset),
                           'sooner_ambiguous_or_absent_out_of_4': sum(x['sooner_claim_exploratory'] in ('AMBIGUOUS','NO_EXPLICIT_CLAIM') for x in subset),
                           'exploratory_full_task_out_of_4': sum(x['full_task_exploratory'] for x in subset)}
        return {'schema': 'v13.seed61.fulltask.posthoc.exploratory.v1',
                'original_zip_sha256': digest, 'original_inner_manifest_present': 'SHA256SUMS' in z.namelist(),
                'original_status': report['status'], 'rows': out, 'by_arm': by_arm,
                'not_preregistered': True, 'not_a_gate': True, 'not_native_rerun': True,
                'age0_record_only': True, 'step2_gate_promoted': False,
                'b3_promoted': False, 'body_jepa_available': False,
                'jepa_weight': 0, 'redmi_measured': False, 'whole_system_complete': False,
                'claim_limit': 'Exploratory lexical named-sooner diagnostic; undercounts paraphrases and cannot replace frozen scorer.'}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--zip', type=Path, required=True)
    p.add_argument('--sha256', required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    if a.out.exists():
        raise FileExistsError('FRESH_EXPLORATORY_OUTPUT_REQUIRED')
    result = audit(a.zip, a.sha256)
    a.out.write_text(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2)+'\n')
    print(json.dumps({'by_arm': result['by_arm'], 'not_a_gate': True}, sort_keys=True))


if __name__ == '__main__':
    main()