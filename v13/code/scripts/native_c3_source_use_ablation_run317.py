"""Run317 frozen native C3 source-use A/B; independent of Run316 evidence.

Scoped change: English memory-header text during this diagnostic process only.
No Runtime/Store/Memory/ContextOS/Canon/model/seed or production prompt edits.
"""
import argparse
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import native_second_turn_probe_run315 as P
import native_c3_cohort_run316 as C
from v13 import prompts
from v13.common import atomic_write, dumps

BASELINE = 'Stored user corrections (with topic): '
CANDIDATE = ('Explicit user-provided correction for the named topic (not independently '
             'verified public information). If the question asks for that exact topic, '
             'report the stored correction as user-provided instead of treating missing '
             'public verification as a reason to withhold it. If no correction matches, '
             'say you do not know. ')
HEADER_SHA = {
    'A': 'a8a5e49e46b9e00c1f4638c92d175c694eb48e8053bcd71a537135d4ae93c5c1',
    'B': '6258c0c4848dc9f7a50edd08f6e27ffa76debe2aa0577ef56cf10c22383e14e8',
}
ORDER = (
    ('ASTER', 'A'), ('ASTER', 'B'),
    ('BERYL', 'B'), ('BERYL', 'A'),
    ('CEDAR', 'A'), ('CEDAR', 'B'),
    ('DELTA', 'B'), ('DELTA', 'A'),
    ('ECHO', 'A'), ('ECHO', 'B'),
)
CASE_BY_ID = {x['id']: x for x in C.CASES}
GATES = dict(P.GATES)


def sha_text(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def sha_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify_registration():
    if C.registry_sha() != C.COHORT_SHA256:
        raise ValueError('Run316 frozen registry drift')
    if tuple(CASE_BY_ID) != ('ASTER', 'BERYL', 'CEDAR', 'DELTA', 'ECHO'):
        raise ValueError('Run317 case identities drift')
    if prompts.TEXT['en']['memories'] != BASELINE:
        raise ValueError('Live English memory header differs from preregistered baseline')
    if sha_text(BASELINE) != HEADER_SHA['A'] or sha_text(CANDIDATE) != HEADER_SHA['B']:
        raise ValueError('Run317 frozen header bytes changed')


@contextmanager
def scoped_case(case, arm):
    """No global prompt change survives a case, even on exception."""
    original_question, original_code = P.QUESTION, P.CODE
    original_header = prompts.TEXT['en']['memories']
    try:
        P.QUESTION, P.CODE = case['question'], case['code']
        prompts.TEXT['en']['memories'] = BASELINE if arm == 'A' else CANDIDATE
        yield
    finally:
        P.QUESTION, P.CODE = original_question, original_code
        prompts.TEXT['en']['memories'] = original_header


def _raw_summary(result, case_id, arm, raw_sha):
    model = result.get('model') or {}
    native = result.get('native')
    integration = bool(result.get('integration_pass'))
    if native and model.get('sha256') != C.EXPECTED_C3_SHA256:
        integration = False
    return {
        'case_id': case_id, 'arm': arm, 'status': result.get('status'),
        'raw_sha256': raw_sha, 'native': native,
        'integration_pass': integration,
        'utility_pass': bool(integration and result.get('utility_pass')),
        'utility': result.get('utility') or {},
        'model_sha256': model.get('sha256'),
        'native_stages': len(result.get('stages') or []),
    }


def summarize(report):
    rows = report['cases']
    per_arm = {}
    for arm in ('A', 'B'):
        selected = [r for r in rows if r['arm'] == arm]
        counts = {
            'attempted': len(selected),
            'denominator': len(C.CASES),
            'integration': sum(bool(r['integration_pass']) for r in selected),
            'utility': sum(bool(r['utility_pass']) for r in selected),
            'second_exact': sum(bool(r['utility'].get('second_exact')) for r in selected),
            'improvement': sum(bool(r['utility'].get('observed_improvement')) for r in selected),
            'forget_nonretention': sum(bool(r['utility'].get('forget_output_nonretention')) for r in selected),
            'errors': sum(r['status'] == 'ERROR' for r in selected),
        }
        per_arm[arm] = counts
    paired = {}
    for metric in ('integration', 'utility', 'second_exact', 'improvement', 'forget_nonretention'):
        paired[metric + '_delta_B_minus_A'] = per_arm['B'][metric] - per_arm['A'][metric]
    report['metrics'] = {'arms': per_arm, 'paired_counts': paired}
    if len(rows) != len(ORDER):
        report['status'] = 'PARTIAL'
    elif all(x['integration_pass'] and x['native_stages'] == 3 for x in rows):
        report['status'] = 'COMPLETE'
    else:
        report['status'] = 'INTEGRATION_FAIL'
    report['evidence_capture_pass'] = report['status'] == 'COMPLETE'
    return report


def _verify_resume(report, out_dir, native):
    if (report.get('schema') != 'V13_RUN317_C3_SOURCE_USE_ABLATION_V1'
            or report.get('native') is not bool(native)
            or report.get('cohort_sha256') != C.COHORT_SHA256
            or report.get('header_sha256') != HEADER_SHA
            or report.get('case_arm_order') != [list(x) for x in ORDER]):
        raise ValueError('Run317 resume identity mismatch')
    if len(report.get('cases', [])) > len(ORDER):
        raise ValueError('Run317 resume excess cases')
    for idx, item in enumerate(report['cases']):
        case_id, arm = ORDER[idx]
        if (item.get('case_id'), item.get('arm')) != (case_id, arm):
            raise ValueError('Run317 resume case/arm order mismatch')
        raw = out_dir / ('RUN317_' + case_id + '_' + arm + '.json')
        if not raw.is_file() or sha_file(raw) != item.get('raw_sha256'):
            raise ValueError('Run317 resume raw bytes missing or changed')
        result = json.loads(raw.read_text())
        if item != _raw_summary(result, case_id, arm, sha_file(raw)):
            raise ValueError('Run317 aggregate differs from raw source of truth')
        if result.get('question') != CASE_BY_ID[case_id]['question']:
            raise ValueError('Run317 resume question mismatch')
        if result.get('synthetic_correction') != CASE_BY_ID[case_id]['code']:
            raise ValueError('Run317 resume correction mismatch')
    return report


def run(out_dir, models_from=None, native=True, timeout=140):
    verify_registration()
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    aggregate = out_dir / 'RUN317_ABLATION.json'
    if aggregate.exists():
        report = _verify_resume(json.loads(aggregate.read_text()), out_dir, native)
    else:
        report = {
            'schema': 'V13_RUN317_C3_SOURCE_USE_ABLATION_V1',
            'native': bool(native),
            'evidence_level': 'LINUX_NATIVE_C3' if native else 'FIXTURE_ONLY',
            'cohort_sha256': C.COHORT_SHA256,
            'header_sha256': dict(HEADER_SHA),
            'expected_c3_sha256': C.EXPECTED_C3_SHA256,
            'case_arm_order': [list(x) for x in ORDER],
            'cases': [], 'gates': dict(GATES),
            'claim_limit': 'Diagnostic 5 paired synthetic cases; scoped memory-header change, not production or weight learning',
        }

    def save():
        atomic_write(aggregate, (dumps(summarize(report)) + '\n').encode())

    save()
    try:
        for case_id, arm in ORDER[len(report['cases']):]:
            case = CASE_BY_ID[case_id]
            raw_path = out_dir / ('RUN317_' + case_id + '_' + arm + '.json')
            if raw_path.exists():
                raise ValueError('Run317 orphan raw case exists; refuse overwrite')
            with scoped_case(case, arm):
                try:
                    result = P.probe(out_dir / ('home-' + case_id + '-' + arm),
                                     models_from, raw_path, native=native, timeout=timeout)
                except Exception as exc:
                    if not raw_path.is_file():
                        atomic_write(raw_path, (dumps({
                            'status': 'ERROR', 'native': native,
                            'question': case['question'],
                            'synthetic_correction': case['code'],
                            'error': {'type': type(exc).__name__},
                        }) + '\n').encode())
                    result = json.loads(raw_path.read_text())
            summary = _raw_summary(result, case_id, arm, sha_file(raw_path))
            report['cases'].append(summary)
            save()
        return report
    finally:
        save()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out-dir', required=True)
    ap.add_argument('--models-from')
    ap.add_argument('--fixture', action='store_true')
    ap.add_argument('--timeout', type=int, default=140)
    args = ap.parse_args()
    report = run(args.out_dir, args.models_from, native=not args.fixture, timeout=args.timeout)
    print(dumps({'status': report['status'], 'native': report['native'],
                 'metrics': report['metrics']}))
    if not report['evidence_capture_pass']:
        raise SystemExit(2)


if __name__ == '__main__':
    main()
