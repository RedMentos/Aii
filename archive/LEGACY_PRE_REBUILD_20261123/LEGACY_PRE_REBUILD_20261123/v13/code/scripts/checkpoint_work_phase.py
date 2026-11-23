#!/usr/bin/env python3
"""Development phase checkpoint, independent of chat context or STEP2 progress.

This is not a runtime capability or a background-chat scheduler. It packages
the existing project and optionally saves the five existing versioned items.
An uncertain remote outcome is recorded before the call and is never retried.
"""
import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import zipfile

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))
from v13.common import atomic_write

CANON = 'docs/canon/V13_v10.16.1_WORK_HANDOFF_SINGLE_SOURCE_B3_HARDENED.md'
CANON_SHA = '3423906b01b24443fcef733fb5c7ef47296963df63e603d8f843c99d544877ee'


def validate_results(plan, results):
    if len(results) != len(plan['uploads']):
        raise ValueError('Incomplete write receipt; no retry')
    for expected, result in zip(plan['uploads'], results):
        if (result.get('status') != 'succeeded'
                or result.get('local_metadata_applied') is not True
                or result.get('library_file_id') != expected['library_file_id']
                or type(result.get('current_version_number')) is not int
                or result['current_version_number'] <= expected['expected_current_version']):
            raise ValueError('Failed/uncertain write or identity mismatch; no retry')
    return dict(uploads=[dict(item, expected_current_version=result['current_version_number'])
                         for item, result in zip(plan['uploads'], results)])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phase', required=True)
    parser.add_argument('--full-zip', required=True)
    parser.add_argument('--phone-zip', required=True)
    parser.add_argument('--receipt', required=True)
    parser.add_argument('--upload-helper')
    parser.add_argument('--upload-plan')
    args = parser.parse_args()
    if bool(args.upload_helper) != bool(args.upload_plan):
        parser.error('Helper and exact versioned plan required together')
    if not 1 <= len(args.phase) <= 128 or any(ord(c) < 32 for c in args.phase):
        parser.error('Bounded printable phase name required')
    full, phone, receipt = [Path(value).resolve() for value in
                            (args.full_zip, args.phone_zip, args.receipt)]
    if len({full, phone, receipt}) != 3 or any(path.is_relative_to(APP) for path in (full, phone, receipt)):
        parser.error('Distinct archive/receipt paths outside the source required')
    receipt.parent.mkdir(parents=True, exist_ok=True)
    lock = receipt.with_suffix(receipt.suffix + '.lock').open('a+')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    prior = json.loads(receipt.read_text()) if receipt.exists() else None
    if prior and prior.get('status') not in {'SAVED', 'LOCAL_SAVED'}:
        parser.error('Previous write uncertain; inspect its receipt before another write')
    plan = json.loads(Path(args.upload_plan).read_text()) if args.upload_plan else None
    if plan:
        if prior and prior.get('next_upload_plan'):
            plan = prior['next_upload_plan']
        required = {str(APP / name) for name in
                    ('BUILD_STATE.json', 'docs/completion-ledger.json', 'docs/USER_DECISIONS_AND_OPEN_QUESTIONS.md')}
        required.update((str(full), str(phone)))
        if (len(plan.get('uploads', [])) != 5
                or {item['local_path'] for item in plan['uploads']} != required
                or any(item.get('purpose') != 'replace_library_file'
                       or not item.get('library_file_id')
                       or type(item.get('expected_current_version')) is not int
                       for item in plan['uploads'])):
            parser.error('Exactly five existing identities/paths and integer guards required')
    if hashlib.sha256((APP / CANON).read_bytes()).hexdigest() != CANON_SHA:
        raise ValueError('Immutable SSOT changed')
    state_path = APP / 'BUILD_STATE.json'
    state = json.loads(state_path.read_text())
    if state.get('canonical_architecture_complete') or state.get('user_full_scope_complete'):
        raise ValueError('This unfinished project cannot be checkpointed as complete')
    stamp = datetime.now(timezone.utc).isoformat()
    state.update(checkpoint_time_utc=stamp, checkpoint_kind=args.phase)
    for path in (state_path, APP / 'docs/BUILD_STATE.json'):
        atomic_write(path, json.dumps(state, ensure_ascii=False, indent=2) + '\n')
    next_steps = '\n'.join('- ' + step for step in state.get('resume_next', []))
    active = json.dumps(state.get('active_test_sessions', {}), ensure_ascii=False, indent=2)
    text = ('# Weiterarbeit am gespeicherten Stand\n\n'
            f'Checkpoint: {stamp}\nPhase: `{args.phase}`\n\n'
            'Die SSOT bleibt unverändert. Dieser Stand ist nicht die fertige Gesamtarchitektur.\n'
            'Vor Änderungen BUILD_STATE.json lesen; dann nur die betroffenen Quellen und Proofs öffnen.\n'
            'Vorhandene funktionierende Teile und fehlgeschlagene Ergebnisse erhalten.\n\n'
            '## Nächste Arbeit\n\n' + next_steps + '\n\n'
            '## Aktive/abgeschlossene Teilpfade\n\n```json\n' + active + '\n```\n\n'
            'Native Caches sind regenerierbar; Daten/Proofs sind im vollständigen Source-Checkpoint.\n'
            'Der eingefrorene Acceptance-Quellstand liegt in docs/proofs/acceptance-frozen-source-20261009.tar.gz.\n'
            'Acceptance nur mit identischen Quellen, Harness, Modellen, Runnern, Einstellungen und Gerät fortsetzen.\n'
            'Nach einer fertigen Entwicklungsphase checkpoint_work_phase.py ausführen. Das kann keinen Chatlauf\n'
            'nach einem App-/Backend-Abbruch automatisch neu starten; es sichert den Wiederaufnahmepunkt.\n')
    atomic_write(APP / 'docs/CONTINUE.md', text)
    packed = []
    for path, flags in ((phone, ['--phone-install']), (full, [])):
        raw = subprocess.check_output([sys.executable, str(APP / 'scripts/package_source.py'),
                                       *flags, '--out', str(path)], text=True)
        packed.append(json.loads(raw))
    with zipfile.ZipFile(full) as archive:
        saved_state = archive.read('V13-Phone/BUILD_STATE.json')
        if saved_state != state_path.read_bytes():
            raise ValueError('BUILD_STATE changed during capture; do not publish inconsistent state')
    record = {'status': 'LOCAL_SAVED', 'phase': args.phase, 'time_utc': stamp,
              'archives': packed, 'build_state_sha256': hashlib.sha256(saved_state).hexdigest(),
              'canonical_architecture_complete': False}
    atomic_write(receipt, json.dumps(record, indent=2) + '\n')
    if plan:
        record['status'] = 'WRITE_OUTCOME_UNCERTAIN'
        atomic_write(receipt, json.dumps(record, indent=2) + '\n')
        result = subprocess.run([sys.executable, args.upload_helper], input=json.dumps(plan),
                                text=True, capture_output=True)
        atomic_write(receipt.with_suffix('.writeback.json'), result.stdout)
        if result.returncode:
            raise RuntimeError('Save failed/uncertain; inspect receipt, no automatic retry')
        record['next_upload_plan'] = validate_results(plan, json.loads(result.stdout)['results'])
        record['status'] = 'SAVED'
        atomic_write(receipt, json.dumps(record, indent=2) + '\n')
    print(json.dumps({'status': record['status'], 'phase': args.phase,
                      'archive_sha256': packed[1]['sha256']}), flush=True)
    lock.close()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
