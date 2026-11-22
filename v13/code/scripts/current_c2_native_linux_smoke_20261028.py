"""Pinned C2 Needle3 Linux native control-call smoke, strictly review-only.

No JEF authority, external tools, Age promotion, or Redmi claim. Exact catalog
model/binary/schema bytes; file-backed bounded raw logs and fail-closed JSON.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import resource
import shutil
import signal
import subprocess
import time
from urllib.parse import urlsplit

from scripts.step2_current_catalog_artifact_probe import git_blob_sha
from v13.common import APP, file_hash
from v13.models import download_file

CATALOG_BLOB = '7af05962af41d0bc3f7dd18ef01d4eba55eabf99'
TOOLS_BLOB = '954a3f468f10195fbce12d27f68585ee7edee2c9'
MODEL_SHA = 'c9d915eca282ed42d1a09b143b592adb4cc6744ffe2d294adf5cfc5548170c38'
BINARY_SHA = '5eb163c5ed33bd914c103ef8eba2134c7bb2d97bafafdd69f410a4a3100e8c37'
MODEL_BYTES = 35335380
BINARY_BYTES = 1246880
PROMPT = 'Budget 120 Euro. Berechne die Hälfte.'
ROUTES = frozenset(('simple', 'detail', 'gist', 'both'))
MAX_RAW = 1024 * 1024


def _catalog():
    raw = (APP / 'specs/models.json').read_bytes()
    if git_blob_sha(raw) != CATALOG_BLOB:
        raise ValueError('Current catalog Git blob drift')
    if git_blob_sha((APP / 'specs/control_tools.json').read_bytes()) != TOOLS_BLOB:
        raise ValueError('C2 select_processing tool schema drift')
    c = json.loads(raw)
    spec = c['models']['needle']
    model = spec['files'][0]
    candidates = [x for x in spec['platforms']['linux-x86_64']
                  if x['local_name'] == 'needle']
    if (spec['model_id'] != 'Cactus-Compute/needle3' or
            spec['revision'] != 'b274efcb211a9eef48c9a88da4b43bd569696a39' or
            spec['license_id'] != 'Apache-2.0' or len(spec['files']) != 1 or
            model['sha256'] != MODEL_SHA or model['size'] != MODEL_BYTES or
            len(candidates) != 1):
        raise ValueError('C2 model/catalog pin drift')
    binary = candidates[0]
    if binary['sha256'] != BINARY_SHA or binary['size'] != BINARY_BYTES:
        raise ValueError('C2 native CLI pin drift')
    for artifact in (model, binary):
        u = urlsplit(artifact['url'])
        if u.scheme != 'https' or u.hostname != 'huggingface.co':
            raise ValueError('Untrusted C2 artifact URL')
    return model, binary


def _unique_pairs(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError('Duplicate native JSON key: ' + key)
        out[key] = value
    return out


def _nonfinite(value):
    raise ValueError('Nonfinite native JSON: ' + value)


def _route(args):
    if isinstance(args, str):
        try:
            args = json.loads(args, object_pairs_hook=_unique_pairs,
                              parse_constant=_nonfinite)
        except (ValueError, TypeError):
            return None
    return args.get('route') if isinstance(args, dict) and args.get('route') in ROUTES else None


def _valid_control(raw):
    try:
        data = json.loads(raw.decode('utf-8'), object_pairs_hook=_unique_pairs,
                          parse_constant=_nonfinite)
    except (UnicodeError, ValueError):
        return False, None
    if type(data) is not dict or type(data.get('function_calls')) is not list:
        return False, None
    calls = data['function_calls']
    if not calls or any(type(c) is not dict or c.get('name') != 'select_processing'
                        for c in calls):
        return False, None
    routes = [_route(c.get('arguments')) for c in calls]
    if any(route is None for route in routes):
        return False, None
    return True, routes[0]


def _limit_raw():
    resource.setrlimit(resource.RLIMIT_FSIZE, (MAX_RAW, MAX_RAW))


def _native_one(binary, model, tools, evidence_dir, env, timeout=90):
    evidence_dir = Path(evidence_dir)
    stdout_path = evidence_dir / 'C2_STDOUT_RAW.log'
    stderr_path = evidence_dir / 'C2_STDERR_RAW.log'
    cmd = [str(binary), '--model', str(model), '--tools', str(tools),
           '--prompt', PROMPT, '--max', '160', '--depth', '8', '--threads', '2']
    start = time.monotonic()
    timed_out = False
    with stdout_path.open('xb') as out, stderr_path.open('xb') as err:
        try:
            p = subprocess.run(cmd, stdin=subprocess.DEVNULL, stdout=out,
                               stderr=err, env=env, timeout=timeout,
                               check=False, preexec_fn=_limit_raw)
            code = p.returncode
        except subprocess.TimeoutExpired:
            timed_out = True
            code = 124
    stdout, stderr = stdout_path.read_bytes(), stderr_path.read_bytes()
    capped = (code == -signal.SIGXFSZ or len(stdout) >= MAX_RAW
              or len(stderr) >= MAX_RAW)
    valid, route = _valid_control(stdout) if code == 0 and not capped else (False, None)
    return {
        'native_exit_code': code,
        'native_elapsed_s': round(time.monotonic() - start, 3),
        'native_timed_out': timed_out,
        'raw_output_cap_bytes_per_stream': MAX_RAW,
        'raw_capture_complete': not capped,
        'raw_output_capped': capped,
        'stdout_bytes': len(stdout),
        'stderr_bytes': len(stderr),
        'stdout_sha256': hashlib.sha256(stdout).hexdigest(),
        'stderr_sha256': hashlib.sha256(stderr).hexdigest(),
        'valid_control_call': valid,
        'proposed_route': route,
        'native_control_pass': code == 0 and not timed_out and not capped and valid,
    }


def run(scratch, evidence_dir):
    if platform.system() != 'Linux' or platform.machine() not in ('x86_64', 'amd64'):
        raise ValueError('C2 native Linux x86_64 only')
    scratch, evidence_dir = Path(scratch), Path(evidence_dir)
    if scratch.exists() or evidence_dir.exists():
        raise FileExistsError('Fresh scratch/evidence required')
    if shutil.disk_usage(scratch.parent).free < 512 * 1024**2:
        raise OSError('Insufficient scratch reserve for C2')
    model_spec, binary_spec = _catalog()
    scratch.mkdir(parents=True)
    evidence_dir.mkdir(parents=True)
    model = download_file(model_spec, scratch / 'needle3.cact', progress=print)
    binary = download_file(binary_spec, scratch / 'needle', progress=print)
    if (model.stat().st_size != MODEL_BYTES or file_hash(model) != MODEL_SHA or
            binary.stat().st_size != BINARY_BYTES or file_hash(binary) != BINARY_SHA):
        raise ValueError('C2 downloaded bytes differ from pinned catalog')
    binary.chmod(binary.stat().st_mode | 0o100)
    env = os.environ.copy()
    env.update(NEEDLE_TELEMETRY='0', DO_NOT_TRACK='1', OMP_NUM_THREADS='2')
    outcome = _native_one(binary, model, APP / 'specs/control_tools.json',
                          evidence_dir, env)
    report = {
        'schema': 'v13.current_catalog.c2_needle_native_linux_smoke.v1',
        'evidence_kind': 'LINUX_NATIVE_C2_CONTROL_CALL_ONLY',
        'catalog_git_blob': CATALOG_BLOB,
        'tools_git_blob': TOOLS_BLOB,
        'model_id': 'Cactus-Compute/needle3',
        'model_revision': 'b274efcb211a9eef48c9a88da4b43bd569696a39',
        'license_id': 'Apache-2.0',
        'model_sha256': file_hash(model),
        'binary_sha256': file_hash(binary),
        'prompt_sha256': hashlib.sha256(PROMPT.encode()).hexdigest(),
        **outcome,
        'external_tools_executed': False,
        'b1_b2_c3_executed': False,
        'jef_end_to_end_executed': False,
        'redmi_measured': False,
        'step2_gate_promoted': False,
        'jepa_weight': 0,
        'age_authority': 0,
        'whole_system_complete': False,
    }
    (evidence_dir / 'REPORT.json').write_text(
        json.dumps(report, sort_keys=True, indent=2, allow_nan=False) + '\n',
        encoding='utf-8')
    if not report['native_control_pass']:
        raise RuntimeError('Pinned C2 native control smoke RED; raw retained')
    return report


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--scratch-home', type=Path, required=True)
    p.add_argument('--evidence-dir', type=Path, required=True)
    args = p.parse_args(argv)
    report = run(args.scratch_home, args.evidence_dir)
    print(json.dumps({'native_control_pass': report['native_control_pass'],
                      'evidence_kind': report['evidence_kind']}, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
