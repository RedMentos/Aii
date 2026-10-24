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

# Independent registration from the verified PR #50 tree (0b465235), NOT
# values supplied by the candidate under inspection. Git blob SHA-1 binds
# the exact source bytes at that commit; SHA-256 binds the HF weight bytes.
# These must only change with a newly reviewed and preregistered cohort.
REGISTERED_MASTER_SHA256 = '1c9c77a4471a7f590f85240f74ed1fc26df7fbde88c3006724e2f93ca993ea4e'
REGISTERED_HF_REVISION = '55e5a53e8637c4522a0577040fe68682db3fbbb6'
REGISTERED_HF_ASSETS = ('model.safetensors', 'config.json', 'generation_config.json',
                        'tokenizer.json', 'tokenizer_config.json', 'chat_template.jinja', 'LICENSE')
REGISTERED_SOURCE_GIT_BLOBS = {
    'lp3_memory_key_candidate.py': '4006a461b82df58dbdf4fe98886207686ca30c42',
    'lp2_assignment_objective.py': '7cc55996bd9016a05614d6f11b91fd33d1605f2e',
    'lora_bench.py': '8a7b725bb450a21775cc1c0ab98dedba5d123278',
}


def git_blob_sha1(path):
    """Git's exact blob object identity for a regular source file."""
    data = Path(path).read_bytes()
    return hashlib.sha1(b'blob ' + str(len(data)).encode('ascii') + b'\0' + data).hexdigest()


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
    try:
        candidate_weight = literal(candidate, 'PINNED_MASTER_SHA256')
        candidate_names = literal(candidate, 'HF_ASSETS')
        candidate_revision = literal(candidate, 'PINNED_HF_REVISION')
        if (not isinstance(candidate_weight, str) or len(candidate_weight) != 64 or
                not isinstance(candidate_names, tuple) or not isinstance(candidate_revision, str)):
            raise ValueError('invalid registered constants')
        candidate_blob = git_blob_sha1(candidate)
    except (OSError, SyntaxError, ValueError, TypeError) as exc:
        return {'status': 'BLOCKED', 'reason': 'CANDIDATE_SOURCE_UNREADABLE',
                'error_type': type(exc).__name__, 'native_executed': False,
                'phone_measured': False, 'owner_confirmed': False}
    if (candidate_weight != REGISTERED_MASTER_SHA256 or
            candidate_names != REGISTERED_HF_ASSETS or
            candidate_revision != REGISTERED_HF_REVISION):
        missing.append('candidate:registered_constants_mismatch')
    if candidate_blob != REGISTERED_SOURCE_GIT_BLOBS['lp3_memory_key_candidate.py']:
        missing.append('candidate:registered_source_mismatch')
    # Never let a candidate reduce the asset set or redirect reads outside the
    # frozen seven-file cohort. HF symlinks into the blob store are supported.
    for name in REGISTERED_HF_ASSETS:
        path = master / name
        try:
            if not path.is_file() or path.stat().st_size == 0:
                missing.append('asset:' + name)
                continue
            if path.is_symlink():
                asset_symlinks.append(name)
            assets[name] = file_sha256(path)
        except (OSError, PermissionError):
            missing.append('asset:' + name + ':unreadable')
    if assets.get('model.safetensors') is not None and assets['model.safetensors'] != REGISTERED_MASTER_SHA256:
        missing.append('asset:master_sha256_mismatch')
    fixtures = {}
    source_blobs = {'lp3_memory_key_candidate.py': candidate_blob}
    for name in FIXTURES:
        path = fixture_root / name
        try:
            if not path.is_file() or path.stat().st_size == 0:
                missing.append('fixture:' + name)
                continue
            fixtures[name] = file_sha256(path)
            source_blobs[name] = git_blob_sha1(path)
            if source_blobs[name] != REGISTERED_SOURCE_GIT_BLOBS[name]:
                missing.append('fixture:' + name + ':registered_source_mismatch')
        except (OSError, PermissionError):
            missing.append('fixture:' + name + ':unreadable')
    if modules is None:
        modules = {name: importlib.util.find_spec(name) is not None for name in REQUIRED_DEPS}
    for name in REQUIRED_DEPS:
        if not modules.get(name, False):
            missing.append('python_module:' + name)
    jobs = process_scan() if process_scan is not None else active_lp3_processes()
    if jobs:
        missing.append('local_lp3_process_active')
    return {'status': 'BLOCKED' if missing else 'LOCAL_ASSETS_READY_OWNER_UNVERIFIED',
            'missing': sorted(missing), 'snapshot_revision': REGISTERED_HF_REVISION,
            'pinned_master_sha256': REGISTERED_MASTER_SHA256,
            'candidate_source_git_blob': candidate_blob,
            'registered_source_git_blobs': source_blobs,
            'registered_source_blobs_match': source_blobs == REGISTERED_SOURCE_GIT_BLOBS,
            'asset_hashes': assets, 'asset_symlinks_followed': asset_symlinks,
            'fixture_hashes': fixtures,
            'cgroup_memory_limit_bytes': local_cgroup_limit() if memory_limit is None else memory_limit,
            'local_lp3_process_count': len(jobs), 'native_executed': False,
            'phone_measured': False, 'owner_confirmed': False,
            'claim_limit': 'Exact registered local source/weight checks only; no independent upstream nonweight authenticity, global job-owner, or RAM-fit proof.'}


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
