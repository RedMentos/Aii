"""Strict restart support for the existing acceptance collector.

Completed failures stay failures. Resuming never changes the stage denominator,
accepts a different source/native build, or turns protocol checks into inference.
"""
import fcntl
import json
from pathlib import Path
import shutil

from v13.common import file_hash

VERSION = 2


def process_identity(pid):
    """Linux/Termux PID + kernel start tick; a recycled PID is not the old worker."""
    try:
        stat = Path('/proc') / str(pid) / 'stat'
        fields = stat.read_text().rsplit(')', 1)[1].split()
        return {'pid': pid, 'start_tick': fields[19]}
    except FileNotFoundError:
        return None


def installed_identity(home):
    home = Path(home).resolve()
    manifest = home / 'config/models.json'
    installed = json.loads(manifest.read_text())
    files = {}
    for model in installed.values():
        for item in model.get('files', {}).values():
            path = (home / item['path']).resolve()
            if not path.is_relative_to(home) or not path.is_file():
                raise ValueError('Installed model file missing or outside home')
            digest = file_hash(path)
            if digest != item['sha256'] or path.stat().st_size != item['size']:
                raise ValueError('Installed model hash/size mismatch: ' + path.name)
            files[str(path.relative_to(home))] = digest
    # NeedleRunner uses the same installed worker for native E (embedding)
    # and C (control) operations; bootstrap does not build a second executable.
    for name in ('llama-server', 'needle-worker'):
        path = home / 'bin' / name
        if not path.is_file():
            raise ValueError('Installed runner missing: ' + name)
        files['bin/' + name] = file_hash(path)
    for path in sorted((home / 'bin').rglob('*.so*')):
        if path.is_file():
            files[str(path.relative_to(home))] = file_hash(path)
    return {'models_manifest_sha256': file_hash(manifest), 'files': files,
            'settings_sha256': file_hash(home / 'config/settings.json')}


def acquire_lock(out):
    lock = (Path(out) / 'collector.lock').open('a+')
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BaseException:
        lock.close()
        raise
    return lock


def validate_resume(report, out, binding, stage_spec):
    if report.get('checkpoint_version') != VERSION:
        raise ValueError('Legacy collector has no resume binding; keep it as historical evidence')
    if report.get('resume_binding') != binding or report.get('stage_spec') != stage_spec:
        raise ValueError('Source, native installation, device or complete stage plan changed')
    rows = report.get('stages')
    if not isinstance(rows, list) or len(rows) > len(stage_spec):
        raise ValueError('Malformed completed stage sequence')
    for index, row in enumerate(rows):
        name = stage_spec[index]['name']
        if row.get('name') != name or row.get('status') not in {'PASS', 'FAIL', 'RUNNING', 'INTERRUPTED'}:
            raise ValueError('Stage sequence/status differs from fixed plan')
        if row['status'] in {'RUNNING', 'INTERRUPTED'}:
            if index != len(rows) - 1:
                raise ValueError('Incomplete stage must be the final recorded stage')
            previous_process = row.get('process_identity')
            if previous_process and process_identity(previous_process['pid']) == previous_process:
                raise ValueError('Previous native stage process is still alive; resume refused')
            continue
        actual_files = {p.name: file_hash(p) for p in Path(out).glob(name + '.*') if p.is_file()}
        if row.get('checkpoint_files') != actual_files:
            raise ValueError('Completed artifact/log/feature bytes changed: ' + name)
        if row['status'] == 'PASS':
            artifact = Path(out) / (name + '.json')
            if not artifact.is_file() or file_hash(artifact) != row.get('artifact_sha256') or row.get('exit_code') != 0:
                raise ValueError('Completed PASS lacks exact successful native artifact: ' + name)
            data = json.loads(artifact.read_text())
            actual = data.get('proof_status') if name == 'learning' else data.get('all_passed') if name == 'cancel-restart' else data.get('status')
            if actual != stage_spec[index]['expected'] or row.get('observed_status') != actual:
                raise ValueError('Completed PASS disagrees with actual stage status: ' + name)
    return len(rows) - (bool(rows) and rows[-1]['status'] in {'RUNNING', 'INTERRUPTED'})


def preserve_interrupted(report, out):
    if not report['stages'] or report['stages'][-1]['status'] not in {'RUNNING', 'INTERRUPTED'}:
        return
    row = report['stages'][-1]
    attempts = report.setdefault('interrupted_attempts', [])
    folder = Path(out) / 'interrupted-attempts' / (row['name'] + '-' + str(len(attempts)))
    folder.mkdir(parents=True, exist_ok=False)
    files = {}
    for source in Path(out).glob(row['name'] + '.*'):
        if source.is_file():
            shutil.copyfile(source, folder / source.name)
            files[source.name] = file_hash(source)
    attempts.append({'row': dict(row), 'directory': str(folder.relative_to(out)), 'files': files})
    report['stages'].pop()
