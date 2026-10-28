"""Pinned distinct B1/B2 GGUF native Linux smoke, strictly serial and review-only.

No shared-weight substitute, no model upload, no C2/JEF, no STEP2 gate.
Run only after separate current-C3 native job has completed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import time
from urllib.parse import urlsplit

from scripts import current_c3_native_linux_smoke_20261028 as c3
from scripts.step2_current_catalog_artifact_probe import git_blob_sha
from v13.common import APP, file_hash
from v13.models import download_file

MODELS = {
    'B1_DETAIL': {
        'key': 'body', 'model_id': 'LiquidAI/LFM2.5-1.2B-Instruct-GGUF',
        'revision': '6767265158422fb8a19c62ceb45f16f05363615b',
        'license_id': 'LFM Open License 1.0', 'size': 695755488,
        'sha256': 'bb741ebb106d543e9de114b843a3d3d73d51c74b5801e69da2abde821a0cb3e1',
    },
    'B2_GIST': {
        'key': 'gist', 'model_id': 'ggml-org/Qwen3.5-0.8B-GGUF',
        'revision': '8fea620810c4afa23dd6443f999a48574c1611a3',
        'license_id': 'Apache-2.0', 'size': 563036064,
        'sha256': '57d1997790d1744fba5b40a7317df71ea5e2acee28c47e78f0cce39c0703f8cf',
    },
}
PROMPT = 'Hello.'
N_TOKENS = 12


def _catalog():
    raw = (APP / 'specs/models.json').read_bytes()
    if (git_blob_sha(raw) != c3.CATALOG_BLOB or
            git_blob_sha((APP / 'v13/models.py').read_bytes()) != c3.MANAGER_BLOB):
        raise ValueError('Current model catalog/manager source drift')
    catalog = json.loads(raw)
    if (catalog['runner']['tag'] != 'b10964' or
            catalog['runner']['linux_binaries']['linux-x86_64']['sha256'] != c3.RUNNER_SHA):
        raise ValueError('Runner identity drift')
    entries = []
    for role, pin in MODELS.items():
        spec = catalog['models'][pin['key']]
        if (spec['model_id'] != pin['model_id'] or
                spec['revision'] != pin['revision'] or
                spec['license_id'] != pin['license_id'] or len(spec['files']) != 1):
            raise ValueError('Model identity drift: ' + role)
        file = spec['files'][0]
        if (file['sha256'] != pin['sha256'] or file['size'] != pin['size'] or
                urlsplit(file['url']).scheme != 'https' or
                urlsplit(file['url']).hostname != 'huggingface.co'):
            raise ValueError('Model file pin drift: ' + role)
        entries.append((role, pin, file))
    if entries[0][2]['sha256'] == entries[1][2]['sha256']:
        raise ValueError('B1/B2 must be distinct GGUF weights')
    runner = catalog['runner']['linux_binaries']['linux-x86_64']
    if (runner['size'] != c3.RUNNER_BYTES or
            urlsplit(runner['url']).hostname != 'github.com' or
            urlsplit(runner['url']).scheme != 'https'):
        raise ValueError('Runner URL/size drift')
    return entries, runner


def _native_one(cli, model, role, evidence_dir, env):
    cmd = [str(cli), '-m', str(model), '-p', PROMPT, '-n', str(N_TOKENS),
           '-c', '256', '-t', '2', '--temp', '0']
    started = time.monotonic()
    try:
        proc = subprocess.run(cmd, input='', capture_output=True, text=True,
                              timeout=180, env=env, check=False)
        stdout, stderr, code = proc.stdout, proc.stderr, proc.returncode
    except subprocess.TimeoutExpired as exc:
        stdout = (exc.stdout or b'').decode('utf-8', errors='replace') if isinstance(exc.stdout, bytes) else (exc.stdout or '')
        stderr = (exc.stderr or b'').decode('utf-8', errors='replace') if isinstance(exc.stderr, bytes) else (exc.stderr or '')
        code = 124
    elapsed = time.monotonic() - started
    (evidence_dir / (role + '_STDOUT_RAW.log')).write_text(stdout, encoding='utf-8')
    (evidence_dir / (role + '_STDERR_RAW.log')).write_text(stderr, encoding='utf-8')
    return {
        'role': role,
        'native_exit_code': code,
        'native_elapsed_s': round(elapsed, 3),
        'stdout_sha256': hashlib.sha256(stdout.encode()).hexdigest(),
        'stderr_sha256': hashlib.sha256(stderr.encode()).hexdigest(),
        'stdout_chars': len(stdout),
        'stderr_chars': len(stderr),
        'native_smoke_pass': code == 0 and bool(stdout.strip()) and stdout.strip() != PROMPT,
    }


def run(scratch_home, evidence_dir):
    if platform.system() != 'Linux' or platform.machine() not in ('x86_64', 'amd64'):
        raise ValueError('Linux x86_64 native-only experiment')
    scratch_home, evidence_dir = Path(scratch_home), Path(evidence_dir)
    if scratch_home.exists() or evidence_dir.exists():
        raise FileExistsError('Fresh scratch/evidence directories required')
    if shutil.disk_usage(scratch_home.parent).free < 3 * 1024**3:
        raise OSError('Insufficient 3GiB scratch disk reserve')
    entries, runner_spec = _catalog()
    scratch_home.mkdir(parents=True)
    evidence_dir.mkdir(parents=True)
    paths = {}
    for role, pin, spec in entries:
        p = download_file(spec, scratch_home / (role + '.gguf'), progress=print)
        if p.stat().st_size != pin['size'] or file_hash(p) != pin['sha256']:
            raise ValueError('Model bytes differ: ' + role)
        with p.open('rb') as stream:
            if stream.read(4) != b'GGUF':
                raise ValueError('Invalid GGUF magic: ' + role)
        paths[role] = p
    tar = download_file(runner_spec, scratch_home / 'runner.tar.gz', progress=print)
    if tar.stat().st_size != c3.RUNNER_BYTES or file_hash(tar) != c3.RUNNER_SHA:
        raise ValueError('Runner tar bytes differ')
    cli = c3._extract_runner(tar, scratch_home / 'runner')
    binary_sha = file_hash(cli)
    libdirs = sorted({str(p.parent) for p in (scratch_home / 'runner').rglob('*.so*')
                      if p.is_file()})
    env = os.environ.copy()
    env['LD_LIBRARY_PATH'] = ':'.join([str(cli.parent), *libdirs,
                                      env.get('LD_LIBRARY_PATH', '')])
    env['OMP_NUM_THREADS'] = '2'
    outcomes = []
    for role, pin, spec in entries:  # strictly serial; process returns before next
        result = _native_one(cli, paths[role], role, evidence_dir, env)
        result.update({
            'model_id': pin['model_id'],
            'model_revision': pin['revision'],
            'license_id': pin['license_id'],
            'model_sha256': file_hash(paths[role]),
            'model_size': paths[role].stat().st_size,
        })
        if result['model_sha256'] != pin['sha256']:
            result['native_smoke_pass'] = False
        outcomes.append(result)
    report = {
        'schema': 'v13.current_catalog.b1b2_native_linux_smoke.v1',
        'evidence_kind': 'LINUX_NATIVE_DISTINCT_B1_B2_SERIAL_SMOKE',
        'catalog_git_blob': c3.CATALOG_BLOB,
        'model_manager_git_blob': c3.MANAGER_BLOB,
        'runner_tar_sha256': file_hash(tar),
        'actual_llama_cli_sha256': binary_sha,
        'prompt_sha256': hashlib.sha256(PROMPT.encode()).hexdigest(),
        'max_tokens_per_role': N_TOKENS,
        'roles': outcomes,
        'models_distinct': outcomes[0]['model_sha256'] != outcomes[1]['model_sha256'],
        'serial_execution': True,
        'native_all_pass': all(x['native_smoke_pass'] for x in outcomes),
        'c2_jef_executed': False,
        'c3_executed': False,
        'redmi_measured': False,
        'step2_gate_promoted': False,
        'jepa_weight': 0,
        'age_authority': 0,
        'whole_system_complete': False,
    }
    (evidence_dir / 'REPORT.json').write_text(
        json.dumps(report, sort_keys=True, indent=2, allow_nan=False) + '\n',
        encoding='utf-8')
    if not report['native_all_pass'] or not report['models_distinct']:
        raise RuntimeError('Native B1/B2 Linux smoke RED; raw retained')
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scratch-home', type=Path, required=True)
    parser.add_argument('--evidence-dir', type=Path, required=True)
    args = parser.parse_args(argv)
    report = run(args.scratch_home, args.evidence_dir)
    print(json.dumps({'native_all_pass': report['native_all_pass'],
                      'evidence_kind': report['evidence_kind']}, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
