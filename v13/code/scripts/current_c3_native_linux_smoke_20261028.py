"""Pinned current-catalog C3 native Linux smoke (isolated; no production swap).

Downloads only immutable official C3 GGUF and llama.cpp binary tar. Emits metadata
and public fixed-prompt raw evidence, NEVER weights. Linux-only, no gate promotion.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import shutil
import subprocess
import tarfile
import time
from urllib.parse import urlsplit

from scripts.step2_current_catalog_artifact_probe import git_blob_sha
from v13.common import APP, file_hash
from v13.models import download_file

CATALOG_BLOB = '7af05962af41d0bc3f7dd18ef01d4eba55eabf99'
MANAGER_BLOB = 'bd035cf8029850cce00b179edf533e53bf24358a'
MODEL_SHA = '3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d'
RUNNER_SHA = '9abf88aea48a55d0f80edb1ee20220b186848cca0b4e919d71518cfd7ca67443'
MODEL_BYTES = 219312832
RUNNER_BYTES = 16825086
PROMPT = 'Hello.'
N_TOKENS = 12


def _catalog():
    raw = (APP / 'specs/models.json').read_bytes()
    if git_blob_sha(raw) != CATALOG_BLOB:
        raise ValueError('Pinned catalog Git blob changed')
    if git_blob_sha((APP / 'v13/models.py').read_bytes()) != MANAGER_BLOB:
        raise ValueError('Pinned ModelManager source changed')
    catalog = json.loads(raw)
    model = catalog['models']['language']
    file = model['files'][0]
    binary = catalog['runner']['linux_binaries']['linux-x86_64']
    if (model['model_id'] != 'LiquidAI/LFM2.5-350M-GGUF' or
            model['revision'] != '657e078c94084481950a2d555a941481f715536b' or
            model['license_id'] != 'LFM Open License 1.0' or
            file['size'] != MODEL_BYTES or file['sha256'] != MODEL_SHA or
            binary['size'] != RUNNER_BYTES or binary['sha256'] != RUNNER_SHA or
            catalog['runner']['tag'] != 'b10964'):
        raise ValueError('Current C3/runner artifact identity drift')
    if (urlsplit(file['url']).hostname != 'huggingface.co' or
            urlsplit(binary['url']).hostname != 'github.com' or
            urlsplit(file['url']).scheme != 'https' or
            urlsplit(binary['url']).scheme != 'https'):
        raise ValueError('Nonofficial model/runner URL')
    return model, file, binary


def _extract_runner(archive_path, destination):
    """Reject unsafe tar entries; Python's data filter confines symlinks."""
    destination = Path(destination)
    if destination.exists():
        raise FileExistsError('Fresh runner extraction directory required')
    with tarfile.open(archive_path, 'r:gz') as tar:
        members = tar.getmembers()
        if not members:
            raise ValueError('Empty runner tar')
        for m in members:
            p = PurePosixPath(m.name)
            if p.is_absolute() or '..' in p.parts or m.isdev() or m.isfifo():
                raise ValueError('Unsafe runner tar member')
        destination.mkdir(parents=True)
        tar.extractall(destination, filter='data')
    cli = [p for p in destination.rglob('llama-cli')
           if p.is_file() and os.access(p, os.X_OK)]
    if len(cli) != 1:
        raise ValueError('Expected one executable llama-cli in pinned archive')
    return cli[0]


def run(scratch_home, evidence_dir):
    if platform.system() != 'Linux' or platform.machine() not in ('x86_64', 'amd64'):
        raise ValueError('Linux x86_64 native-only experiment')
    scratch_home, evidence_dir = Path(scratch_home), Path(evidence_dir)
    if scratch_home.exists() or evidence_dir.exists():
        raise FileExistsError('Fresh scratch and evidence directories required')
    if shutil.disk_usage(scratch_home.parent).free < 2 * 1024**3:
        raise OSError('Native scratch disk reserve under 2 GiB')
    model_meta, model_spec, runner_spec = _catalog()
    scratch_home.mkdir(parents=True)
    evidence_dir.mkdir(parents=True)
    model = download_file(model_spec, scratch_home / 'C3.gguf', progress=print)
    runner_tar = download_file(runner_spec, scratch_home / 'runner.tar.gz', progress=print)
    if (model.stat().st_size != MODEL_BYTES or file_hash(model) != MODEL_SHA or
            runner_tar.stat().st_size != RUNNER_BYTES or file_hash(runner_tar) != RUNNER_SHA or
            model.open('rb').read(4) != b'GGUF'):
        raise ValueError('Native artifacts differ from pinned bytes')
    cli = _extract_runner(runner_tar, scratch_home / 'runner')
    binary_sha = file_hash(cli)
    libdirs = sorted({str(p.parent) for p in (scratch_home / 'runner').rglob('*.so*')
                      if p.is_file()})
    env = os.environ.copy()
    env['LD_LIBRARY_PATH'] = ':'.join([str(cli.parent), *libdirs,
                                      env.get('LD_LIBRARY_PATH', '')])
    env['OMP_NUM_THREADS'] = '2'
    cmd = [str(cli), '-m', str(model), '-p', PROMPT, '-n', str(N_TOKENS),
           '-c', '256', '-t', '2', '--temp', '0']
    started = time.monotonic()
    try:
        proc = subprocess.run(cmd, input='', capture_output=True, text=True,
                              timeout=180, env=env, check=False)
        elapsed = time.monotonic() - started
        stdout, stderr, code = proc.stdout, proc.stderr, proc.returncode
    except subprocess.TimeoutExpired as exc:
        elapsed = time.monotonic() - started
        stdout = (exc.stdout or b'').decode('utf-8', errors='replace') if isinstance(exc.stdout, bytes) else (exc.stdout or '')
        stderr = (exc.stderr or b'').decode('utf-8', errors='replace') if isinstance(exc.stderr, bytes) else (exc.stderr or '')
        code = 124
    (evidence_dir / 'NATIVE_STDOUT_RAW.log').write_text(stdout, encoding='utf-8')
    (evidence_dir / 'NATIVE_STDERR_RAW.log').write_text(stderr, encoding='utf-8')
    report = {
        'schema': 'v13.current_catalog.c3_native_linux_smoke.v1',
        'evidence_kind': 'LINUX_NATIVE_C3_ONLY',
        'platform': platform.platform(),
        'catalog_git_blob': CATALOG_BLOB,
        'model_manager_git_blob': MANAGER_BLOB,
        'model_id': model_meta['model_id'],
        'model_revision': model_meta['revision'],
        'license_id': model_meta['license_id'],
        'model_sha256': file_hash(model),
        'runner_tar_sha256': file_hash(runner_tar),
        'actual_llama_cli_sha256': binary_sha,
        'prompt_sha256': hashlib.sha256(PROMPT.encode()).hexdigest(),
        'max_tokens': N_TOKENS,
        'native_exit_code': code,
        'native_elapsed_s': round(elapsed, 3),
        'stdout_sha256': hashlib.sha256(stdout.encode()).hexdigest(),
        'stderr_sha256': hashlib.sha256(stderr.encode()).hexdigest(),
        'stdout_chars': len(stdout),
        'stderr_chars': len(stderr),
        'native_execution_performed': True,
        'native_smoke_pass': code == 0 and bool(stdout.strip()) and stdout.strip() != PROMPT,
        'c2_jef_executed': False,
        'b1_b2_executed': False,
        'redmi_measured': False,
        'step2_gate_promoted': False,
        'jepa_weight': 0,
        'age_authority': 0,
        'whole_system_complete': False,
    }
    (evidence_dir / 'REPORT.json').write_text(
        json.dumps(report, sort_keys=True, indent=2, allow_nan=False) + '\n',
        encoding='utf-8')
    if not report['native_smoke_pass']:
        raise RuntimeError('Current C3 Linux native smoke failed; raw preserved')
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scratch-home', required=True, type=Path)
    parser.add_argument('--evidence-dir', required=True, type=Path)
    args = parser.parse_args(argv)
    report = run(args.scratch_home, args.evidence_dir)
    print(json.dumps({'native_smoke_pass': report['native_smoke_pass'],
                      'evidence_kind': report['evidence_kind'],
                      'native_elapsed_s': report['native_elapsed_s']},
                     sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
