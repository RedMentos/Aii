#!/usr/bin/env python3
"""Read-only LP3 native host preflight; never launches a model or claims ownership.

Reports current *local* prerequisites for the already preregistered LP3 pilot.
A green local asset check is NOT authorization to run concurrently with an
unseen Claude/other host job, nor proof of RAM headroom or model performance.
"""
import argparse
import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path

REQUIRED_DEPS = ('torch', 'transformers', 'safetensors')
FIXTURES = ('lp2_assignment_objective.py', 'lora_bench.py')


def literal(path, name):
    """Extract frozen literal constants without importing project/model code."""
    tree = ast.parse(Path(path).read_text(encoding='utf-8'))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == name for target in node.targets
        ):
            return ast.literal_eval(node.value)
    raise ValueError(f'missing registered constant {name}')


def file_sha256(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def local_cgroup_limit():
    for p in ('/sys/fs/cgroup/memory.max', '/sys/fs/cgroup/memory/memory.limit_in_bytes'):
        try:
            value = Path(p).read_text().strip()
            if value != 'max':
                return int(value)
        except (OSError, ValueError):
            continue
    return None


def is_lp3_native_argv(argv):
    # Only an actual argv path, not a shell string or a readiness --candidate
    # argument, counts as a running native candidate process.
    names = [Path(arg).name for arg in argv if arg]
    return ('lp3_memory_key_candidate.py' in names and
            'lp3_native_readiness.py' not in names and
            not any(a in ('-c', '--command') for a in argv[:3]))


def active_lp3_processes():
    """Conservative local-only detection; no signals, no ownership inference."""
    result = []
    for proc in Path('/proc').iterdir():
        if not proc.name.isdecimal() or int(proc.name) == os.getpid():
            continue
        try:
            args = [(v.decode('utf-8', 'replace')) for v in
                    (proc / 'cmdline').read_bytes()[:8192].split(b'\x00') if v]
        except (OSError, PermissionError):
            continue
        if is_lp3_native_argv(args):
            result.append(int(proc.name))
    return sorted(result)


def inspect(master, candidate, fixture_root=None, *, modules=None, process_scan=None,
            memory_limit=None):
    master, candidate = Path(master), Path(candidate)
    fixture_root = Path(fixture_root) if fixture_root else candidate.parent
    missing = []
    assets = {}
    asset_symlinks = []
    expected_weight = None
    try:
        expected_weight = literal(candidate, 'PINNED_MASTER_SHA256')
        names = literal(candidate, 'HF_ASSETS')
        revision = literal(candidate, 'PINNED_HF_REVISION')
        if not isinstance(expected_weight, str) or len(expected_weight) != 64 or not isinstance(names, tuple):
            raise ValueError('invalid registered constants')
    except (OSError, SyntaxError, ValueError, TypeError) as exc:
        return {'status': 'BLOCKED', 'reason': 'CANDIDATE_SOURCE_UNREADABLE',
                'error_type': type(exc).__name__, 'native_executed': False,
                'phone_measured': False, 'owner_confirmed': False}
    for name in names:
        path = master / name
        if not path.is_file() or path.stat().st_size == 0:
            missing.append('asset:' + name)
            continue
        # HF snapshots normally link to the revision's blobs/ store. Follow
        # regular-file symlinks, as the registered runner does, and hash bytes.
        if path.is_symlink():
            asset_symlinks.append(name)
        assets[name] = file_sha256(path)
    if assets.get('model.safetensors') is not None and assets['model.safetensors'] != expected_weight:
        missing.append('asset:master_sha256_mismatch')
    fixtures = {}
    for name in FIXTURES:
        path = fixture_root / name
        if not path.is_file() or path.stat().st_size == 0:
            missing.append('fixture:' + name)
        else:
            fixtures[name] = file_sha256(path)
    if modules is None:
        modules = {name: importlib.util.find_spec(name) is not None for name in REQUIRED_DEPS}
    for name in REQUIRED_DEPS:
        if not modules.get(name, False):
            missing.append('python_module:' + name)
    jobs = process_scan() if process_scan is not None else active_lp3_processes()
    if jobs:
        missing.append('local_lp3_process_active')
    return {'status': 'BLOCKED' if missing else 'LOCAL_ASSETS_READY_OWNER_UNVERIFIED',
            'missing': sorted(missing), 'snapshot_revision': revision,
            'pinned_master_sha256': expected_weight,
            'asset_hashes': assets, 'asset_symlinks_followed': asset_symlinks,
            'fixture_hashes': fixtures,
            'cgroup_memory_limit_bytes': local_cgroup_limit() if memory_limit is None else memory_limit,
            'local_lp3_process_count': len(jobs), 'native_executed': False,
            'phone_measured': False, 'owner_confirmed': False,
            'claim_limit': 'Local read-only preflight only; no global job-owner or RAM-fit proof.'}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--master', type=Path, required=True)
    ap.add_argument('--candidate', type=Path, default=Path(__file__).with_name('lp3_memory_key_candidate.py'))
    ap.add_argument('--fixture-root', type=Path)
    a = ap.parse_args()
    report = inspect(a.master, a.candidate, a.fixture_root)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report['status'] == 'LOCAL_ASSETS_READY_OWNER_UNVERIFIED' else 2


if __name__ == '__main__':
    raise SystemExit(main())
