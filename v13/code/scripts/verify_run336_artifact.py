#!/usr/bin/env python3
"""Independent ZIP/manifest/receipt guard for the isolated Run336 replay.

This audits a *downloaded* GitHub Actions artifact. It cannot reproduce native
optimizer execution or tensor values once the ephemeral GGUF files are gone.
"""
import argparse
import hashlib
import json
from pathlib import PurePosixPath
import zipfile

EXPECTED_HEAD = 'dfbe3c50a5e0f1b31e42d3ccb05fffa98c446195'
GATES = {'STEP2': 'UTILITY_FAIL', 'B3_L1': 'FAIL', 'Body_JEPA': 'UNAVAILABLE',
         'jepa_weight': 0, 'V13': 'INCOMPLETE'}
ARMS = {'A_ALL_NO_REPLAY': ('all', False), 'B_ANSWER_NO_REPLAY': ('answer', False),
        'C_ANSWER_REPLAY': ('answer', True)}

def check(condition, message):
    if not condition:
        raise ValueError(message)

def audit(path):
    archive_hash = hashlib.sha256(path.read_bytes()).hexdigest()
    with zipfile.ZipFile(path) as archive:
        infos = archive.infolist()
        names = [i.filename for i in infos if not i.is_dir()]
        check(len(names) == len(set(names)), 'duplicate archive name')
        for name in names:
            p = PurePosixPath(name)
            check(not p.is_absolute() and '..' not in p.parts and '\\' not in name,
                  'unsafe archive member path')
            check(not name.endswith(('.gguf', '.safetensors', '.npz', '.pt', '.bin')),
                  'model weights published in artifact')
        check('RUN334_SHA256SUMS.txt' in names, 'missing closed manifest')
        lines = archive.read('RUN334_SHA256SUMS.txt').decode('utf-8').splitlines()
        entries = {}
        for line in lines:
            check(len(line) >= 67 and line[64:66] == '  ', 'invalid manifest row')
            expected, raw_name = line[:64], line[66:]
            name = raw_name.removeprefix('./')
            check(len(expected) == 64 and all(c in '0123456789abcdef' for c in expected),
                  'invalid SHA256')
            check(name not in entries, 'duplicate manifest row')
            entries[name] = expected
        check(set(entries) == set(names) - {'RUN334_SHA256SUMS.txt'},
              'missing or extra raw artifact entry')
        for name, expected in entries.items():
            check(hashlib.sha256(archive.read(name)).hexdigest() == expected,
                  'raw SHA mismatch: ' + name)
        def txt(name):
            check(name in entries, 'missing receipt: ' + name)
            return archive.read(name).decode('utf-8')
        check(txt('RUN330_HEAD.txt').strip() == EXPECTED_HEAD, 'wrong exact head')
        for name in ('RUN330_MODEL_EXIT.txt', 'RUN330_COMPILE_EXIT.txt',
                     'RUN334_GGUF_IMPORT_EXIT.txt', 'RUN334_NATIVE_EXIT.txt',
                     'RUN334_AUDIT_EXIT.txt', 'RUN330_PRIVACY_EXIT.txt'):
            check(txt(name).strip() == '0', 'nonzero stage: ' + name)
        imported = txt('RUN334_GGUF_IMPORT_RAW.log')
        check('PINNED_B10964_GGUF_IMPORT_OK' in imported and
              '/llama.cpp-b10964/gguf-py/gguf/__init__.py' in imported,
              'official GGUF reader import not established')
        report = json.loads(txt('run334eval/RUN334_REPORT.json'))
        check(report.get('status') == 'COMPLETE_NATIVE_THREE_ARM_DIAGNOSTIC'
              and report.get('evidence_level') == 'LINUX_NATIVE_C3_FRESH_COHORT_TRAIN_EVAL',
              'incomplete native experiment')
        check(report.get('gates') == GATES and report.get('model_activated') is False
              and report.get('weights_published') is False, 'negative gate drift')
        check(set(report.get('arms', {})) == set(ARMS), 'missing native arm')
        summary = {}
        for name, (mode, replay) in ARMS.items():
            row = report['arms'][name]
            check(row.get('loss_mode') == mode and row.get('replay') is replay
                  and row.get('native_training_executed') is True
                  and row.get('status') == 'COMPLETE_NATIVE_DIAGNOSTIC'
                  and row.get('weights_published') is False
                  and row.get('weights_retained') is False,
                  'arm mode, optimizer or publication mismatch: ' + name)
            check(len(row.get('checkpoint_receipts', [])) == 2
                  and len(row.get('epochs', [])) == 2, 'incomplete epochs: ' + name)
            check(row.get('tensor_audit', {}).get('changes', {}).get('unchanged_nonselected') == 144,
                  'unselected weights changed: ' + name)
            summary[name] = {'selection': row['selection_report']['selection'],
                             'epochs': [e['evaluation']['summary'] for e in row['epochs']]}
        independent = json.loads(txt('RUN334_INDEPENDENT_AUDIT.json'))
        check(independent.get('status') == 'PASS_SOURCE_ONLY_REPORT_AUDIT_NOT_NATIVE_REEXECUTION'
              and independent.get('gates') == GATES,
              'independent raw-score audit did not pass')
    return {'status': 'PASS_RAW_ARTIFACT_INTEGRITY_NOT_NATIVE_REEXECUTION',
            'zip_sha256': archive_hash, 'manifest_entries': len(entries),
            'exact_head': EXPECTED_HEAD, 'arms': summary, 'gates': GATES,
            'claim_limit': 'Only stored report/raw integrity; original native tensor execution not reproduced'}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('artifact', type=__import__('pathlib').Path)
    args = parser.parse_args()
    try:
        result = audit(args.artifact)
    except (OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile) as exc:
        result = {'status': 'FAIL_CLOSED', 'error': str(exc)[:350], 'gates': GATES}
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result['status'].startswith('PASS_') else 2)

if __name__ == '__main__':
    main()