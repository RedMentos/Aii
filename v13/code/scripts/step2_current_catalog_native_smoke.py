"""Bounded, serial, exact-byte Linux llama-cli smoke. NOT STEP2 utility or Redmi."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import time

from v13.common import dumps, file_hash
from v13.models import ModelManager
from scripts.step2_current_catalog_artifact_probe import probe as model_probe
from scripts.native_smoke_io_20261028 import run_one_turn
from scripts.step2_current_runner_archive_probe import probe as runner_probe

ROLES = ('B1_DETAIL', 'B2_GIST', 'C3_LANGUAGE')
PROMPT = 'Hello.'
SEED = 27
TOKENS = 4
CONTEXT = 512
THREADS = 2
MIN_MEMORY_BYTES = 4 * 1024 ** 3
MIN_FREE_DISK = 3 * 1024 ** 3


def cgroup_memory_limit(path='/sys/fs/cgroup/memory.max'):
    try:
        raw = Path(path).read_text().strip()
        if raw == 'max':
            return None
        return int(raw)
    except (OSError, ValueError):
        return None


def preflight(root):
    limit = cgroup_memory_limit()
    if limit is not None and limit < MIN_MEMORY_BYTES:
        raise RuntimeError('Linux cgroup memory budget below 4 GiB')
    if shutil.disk_usage(Path(root).parent).free < MIN_FREE_DISK:
        raise RuntimeError('Linux scratch disk budget below 3 GiB')
    if Path(root).exists():
        raise FileExistsError('Smoke scratch root must be new')


def locate_cli(verified_archive, extraction_root):
    extraction_root = Path(extraction_root)
    if extraction_root.exists():
        raise FileExistsError('Runner extraction directory must be new')
    extraction_root.mkdir(parents=True)
    with tarfile.open(verified_archive, 'r:gz') as tf:
        for member in tf.getmembers():
            from pathlib import PurePosixPath
            p = PurePosixPath(member.name)
            if p.is_absolute() or '..' in p.parts:
                raise ValueError('Unsafe runner tar member')
        tf.extractall(extraction_root, filter='data')
    candidates = [p for p in extraction_root.rglob('llama-cli') if p.is_file()]
    if len(candidates) != 1:
        raise RuntimeError('Expected one pinned llama-cli executable')
    cli = candidates[0]
    cli.chmod(cli.stat().st_mode | 0o100)
    return cli


def command(cli, model):
    return [str(cli), '-m', str(model), '-p', PROMPT, '-n', str(TOKENS),
            '-c', str(CONTEXT), '-t', str(THREADS), '--seed', str(SEED),
            '--temp', '0', '--single-turn']


def _write_new(path, content):
    with Path(path).open('xb') as stream:
        stream.write(content if isinstance(content, bytes) else content.encode('utf-8'))
        stream.flush()
        os.fsync(stream.fileno())


def _run(argv, timeout, env):
    start = time.monotonic()
    try:
        result = subprocess.run(argv, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, env=env, timeout=timeout,
                                check=False)
        return {'returncode': result.returncode, 'timeout': False,
                'stdout': result.stdout, 'stderr': result.stderr,
                'elapsed_seconds': round(time.monotonic() - start, 3)}
    except subprocess.TimeoutExpired as exc:
        return {'returncode': None, 'timeout': True,
                'stdout': exc.stdout or b'', 'stderr': exc.stderr or b'',
                'elapsed_seconds': round(time.monotonic() - start, 3)}


def smoke(scratch_root, evidence_dir, expected_catalog_blob, progress=print):
    scratch_root, evidence_dir = Path(scratch_root), Path(evidence_dir)
    evidence_dir.mkdir(parents=True, exist_ok=True)
    preflight(scratch_root)
    scratch_root.mkdir(parents=True)
    models_home = scratch_root / 'models-home'
    runner_home = scratch_root / 'runner-home'
    model_report = model_probe(models_home, evidence_dir / 'MODEL_BYTES.json',
                               expected_catalog_blob, progress=progress)
    runner_report = runner_probe(runner_home, evidence_dir / 'RUNNER_ARCHIVES.json',
                                 expected_catalog_blob, progress=progress)
    cli = locate_cli(runner_home / 'binary.tar.gz', scratch_root / 'runner-extracted')
    library_dirs = {str(cli.parent)}
    for p in (scratch_root / 'runner-extracted').rglob('*'):
        if p.is_file() and ('.so' in p.name):
            library_dirs.add(str(p.parent))
    env = os.environ.copy()
    env['LD_LIBRARY_PATH'] = os.pathsep.join(sorted(library_dirs)) + (
        os.pathsep + env['LD_LIBRARY_PATH'] if env.get('LD_LIBRARY_PATH') else '')
    env['OMP_NUM_THREADS'] = str(THREADS)
    version = _run([str(cli), '--version'], 30, env)
    _write_new(evidence_dir / 'VERSION.stdout', version['stdout'])
    _write_new(evidence_dir / 'VERSION.stderr', version['stderr'])
    _write_new(evidence_dir / 'VERSION.json', dumps({
        'returncode': version['returncode'], 'timeout': version['timeout'],
        'elapsed_seconds': version['elapsed_seconds']}))
    if version['timeout'] or version['returncode'] != 0:
        raise RuntimeError('Pinned llama-cli --version failed')
    manager = ModelManager(models_home)
    records = []
    for role in ROLES:
        model = manager.path_for(role)
        result = run_one_turn(command(cli, model), evidence_dir, role, env)
        prefix = role
        stdout = (evidence_dir / (prefix + '_STDOUT_RAW.log')).read_bytes()
        stderr = (evidence_dir / (prefix + '_STDERR_RAW.log')).read_bytes()
        # Preserve the older evidence names while also retaining exact raw files.
        _write_new(evidence_dir / (prefix + '.stdout'), stdout)
        _write_new(evidence_dir / (prefix + '.stderr'), stderr)
        entry = {'role': role, 'model_sha256': file_hash(model),
                 'runner_cli_sha256': file_hash(cli),
                 'returncode': result['native_exit_code'],
                 'timeout': result['native_timed_out'],
                 'elapsed_seconds': result['native_elapsed_s'],
                 'stdout_sha256': result['stdout_sha256'],
                 'stderr_sha256': result['stderr_sha256'],
                 'stdout_nonempty': bool(stdout.strip()),
                 'stdout_bytes': result['stdout_bytes'],
                 'stderr_bytes': result['stderr_bytes'],
                 'raw_capture_complete': result['raw_capture_complete'],
                 'raw_output_capped': result['raw_output_capped'],
                 'generation_marker_seen': result['generation_marker_seen'],
                 'native_smoke_pass': result['native_smoke_pass']}
        _write_new(evidence_dir / (prefix + '.json'), dumps(entry))
        records.append(entry)
        if not result['native_smoke_pass']:
            raise RuntimeError('Linux native smoke failed for ' + role)
    report = {'schema': 'v13.step2.current_catalog_linux_native_smoke.v1',
              'evidence_kind': 'LINUX_NATIVE_SMOKE_ONLY',
              'catalog_git_blob_sha': expected_catalog_blob,
              'model_artifact_report_sha256': file_hash(evidence_dir / 'MODEL_BYTES.json'),
              'runner_archive_report_sha256': file_hash(evidence_dir / 'RUNNER_ARCHIVES.json'),
              'runner_cli_sha256': file_hash(cli),
              'seed': SEED, 'tokens': TOKENS, 'context': CONTEXT,
              'threads': THREADS, 'prompt': PROMPT,
              'cgroup_memory_limit_bytes': cgroup_memory_limit(),
              'roles': records, 'native_linux_load_decode': True,
              'step2_semantic_utility_proven': False, 'redmi_proof': False,
              'step2_gate_promoted': False, 'jepa_weight': 0}
    _write_new(evidence_dir / 'SMOKE_REPORT.json', dumps(report))
    return report


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--scratch-root', required=True)
    p.add_argument('--evidence-dir', required=True)
    p.add_argument('--expected-catalog-blob', required=True)
    a = p.parse_args()
    result = smoke(a.scratch_root, a.evidence_dir, a.expected_catalog_blob)
    print('LINUX_NATIVE_SMOKE_ONLY roles=' + str(len(result['roles'])))


if __name__ == '__main__':
    main()
