"""Isolated resume-integrity guard for frozen 16-case SourceHandoff ablation.

This is a review candidate, NOT patched into the active/source-frozen runner.
It rejects forged gate flags or inconsistent row hashes, summaries and finished
statuses before any new native inference is attempted. No model dependency.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ARMS = ('baseline','state_off','semantics_only','full_candidate')
FIXTURES = ('Mira','Lumen','Nacre','Tessera')
ROW_STATES = frozenset(('RECORDED','STRUCTURAL_FAIL','ERROR','INTERRUPTED'))
REPORT_STATES = frozenset(('RUNNING','INTERRUPTED','ARTIFACT_CHANGED','RECORDED_DIAGNOSIS','STRUCTURAL_FAIL'))
GATE_FIELDS = ('canonical_gate_pass','learned_semantic_utility_proven','phone_measured')
NATIVE_CHECKS = ('real_B2_final','real_C3_final','current_event_bound','corrupt_prior_not_delivered')


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',',':'), allow_nan=False)


def row_sha(row):
    return hashlib.sha256(_canonical(row).encode('utf-8')).hexdigest()


def expected_summary(rows):
    report={}
    for arm in ARMS:
        chosen=[r for r in rows if r['arm']==arm]
        report[arm]={'rows':len(chosen),
                     'mean_strict_utility':sum(r['score']['utility'] for r in chosen)/len(chosen) if chosen else None,
                     'exact_decisions':sum(bool(r['score']['exact']) for r in chosen),
                     'rows_with_prior_quote':sum(bool(r.get('delivered_prior_quotes')) for r in chosen),
                     'structural_failures':sum(r['status']!='RECORDED' for r in chosen)}
    return report


def validate_resume(report, registration_sha):
    if not isinstance(report,dict) or report.get('schema')!='SOURCE_HANDOFF_ABLATION_V1':
        raise ValueError('Unexpected report schema')
    if report.get('preregistration_sha256')!=registration_sha:
        raise ValueError('Resume preregistration changed')
    if any(report.get(field) is not False for field in GATE_FIELDS):
        raise ValueError('Unproven quality/phone/canonical gate changed')
    if report.get('status') not in REPORT_STATES:
        raise ValueError('Unknown report lifecycle state')
    rows=report.get('rows'); hashes=report.get('row_sha256')
    if not isinstance(rows,list) or not isinstance(hashes,dict):
        raise ValueError('Malformed row ledger')
    valid={(fixture,arm) for fixture in FIXTURES for arm in ARMS}
    keys=[]
    for row in rows:
        if not isinstance(row,dict) or row.get('status') not in ROW_STATES:
            raise ValueError('Invalid row lifecycle state')
        if not isinstance(row.get('score'),dict):
            raise ValueError('Row has no score')
        score=row['score']
        if type(score.get('utility')) not in (float,int) or not 0<=score['utility']<=1 or type(score.get('exact')) is not bool:
            raise ValueError('Malformed utility score')
        keys.append((row.get('fixture'),row.get('arm')))
    if len(keys)!=len(set(keys)) or any(k not in valid for k in keys):
        raise ValueError('Resume row keys invalid')
    # The frozen runner emits a deterministic fixture-major/arm-minor prefix.
    # Accepting a future row early silently marks that arm done on restart.
    canonical_order = [(fixture, arm) for fixture in FIXTURES for arm in ARMS]
    if keys != canonical_order[:len(keys)]:
        raise ValueError('Resume rows are not a contiguous preregistered prefix')
    for row in rows:
        if row['status'] != 'RECORDED':
            continue  # Preserve diagnostics from failed/interrupted native calls.
        checks = row.get('checks')
        if (row.get('oracle_visible_to_native') is not False
            or row.get('processes_reaped') is not True
            or not isinstance(checks, dict)
            or any(checks.get(k) is not True for k in NATIVE_CHECKS)
            or not isinstance(row.get('offer'), dict)
            or not isinstance(row['offer'].get('native_metrics'), dict)
            or row['offer']['native_metrics'].get('status') != 'FINAL'
            or not isinstance(row.get('consumer_metrics'), dict)
            or row['consumer_metrics'].get('status') != 'FINAL'):
            raise ValueError('RECORDED row lacks independently required native evidence')
    expected={r['fixture']+'/'+r['arm']:row_sha(r) for r in rows}
    if hashes!=expected:
        raise ValueError('Resume recorded row bytes/ledger changed')
    if len(rows)>len(valid):
        raise ValueError('Too many rows')
    if (report.get('summary') != expected_summary(rows)
            if rows else report.get('summary') is not None):
        raise ValueError('Resume summary does not match immutable rows')
    if report['status']=='RECORDED_DIAGNOSIS':
        if len(rows)!=len(valid) or set(keys)!=valid or any(r['status']!='RECORDED' for r in rows):
            raise ValueError('Cannot mark incomplete/failed rows as recorded diagnosis')
        if report.get('installed_artifacts_unchanged') is not True:
            raise ValueError('Final result lacks unchanged artifacts binding')
    if report['status']=='INTERRUPTED' and (not rows or rows[-1]['status']!='INTERRUPTED'):
        raise ValueError('Interrupted report lacks interrupted last row')
    return set(keys)


def audit_files(registration_path, report_path):
    """Privacy-minimal, read-only preflight for an existing native cohort.

    This does not run models, reconstruct missing rows, or promote utility.
    The preregistration hash is over the exact on-disk JSON bytes, just as in
    the frozen runner. Caller must separately verify current source/model binds.
    """
    registration_path, report_path = Path(registration_path), Path(report_path)
    for path in (registration_path, report_path):
        if path.is_symlink() or not path.is_file():
            raise ValueError('Existing regular prerequisite file required')
        if path.stat().st_size > (64 << 20):
            raise ValueError('Oversize preregistration/report refused')
    original = registration_path.read_bytes()
    registration = json.loads(original)
    if (not isinstance(registration, dict)
        or registration.get('schema') != 'SOURCE_HANDOFF_ABLATION_PREREGISTRATION_V1'
        or registration.get('arm_order') != list(ARMS)
        or not isinstance(registration.get('fixtures'), list)
        or len(registration['fixtures']) != len(FIXTURES)
        or any(not isinstance(row, dict) for row in registration['fixtures'])
        or [row.get('id') for row in registration['fixtures']] != list(FIXTURES)):
        raise ValueError('Unexpected fixed native ablation preregistration')
    expected_hash = hashlib.sha256(original).hexdigest()
    report = json.loads(report_path.read_bytes())
    done = validate_resume(report, expected_hash)
    return {'status':'RESUME_LEDGER_VALID_NOT_UTILITY_PASS',
            'rows':len(done),'expected_rows':len(FIXTURES)*len(ARMS),
            'remaining_rows':len(FIXTURES)*len(ARMS)-len(done),
            'preregistration_sha256':expected_hash,
            'original_report_state':report['status'],
            'native_models_launched':False,
            'source_and_model_binding_verified':False,
            'phone_measured':False,
            'canonical_gate_pass':False}


def main():
    parser = argparse.ArgumentParser(description='Read-only SourceHandoff resume integrity preflight, not a model run')
    parser.add_argument('--preregistration',type=Path,required=True)
    parser.add_argument('--report',type=Path,required=True)
    args = parser.parse_args()
    try:
        result = audit_files(args.preregistration,args.report)
    except (ValueError, OSError, TypeError, KeyError, json.JSONDecodeError) as error:
        # No raw report/answer/statement content in diagnostic output.
        print(json.dumps({'status':'RESUME_LEDGER_REJECTED',
                          'error_type':type(error).__name__}),file=sys.stderr)
        return 2
    print(json.dumps(result,sort_keys=True))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
