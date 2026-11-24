#!/usr/bin/env python3
"""Actual pinned Linux llama-server --version activation, not model inference.

Reuses the original catalog SHA and the production installer, extractor and
activation logic. Two invocations (checkout / extracted phone source) share
one verified archive cache but use independent temporary homes.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

from v13.bootstrap import install_llama_runner
from v13.common import file_hash
from v13.models import catalog, download_file, platform_tag


def verify(work, label):
    work = Path(work)
    work.mkdir(parents=True, exist_ok=True)
    if label not in ('checkout', 'extracted'):
        raise ValueError('Unknown source label')
    tag = platform_tag()
    if tag != 'linux-x86_64':
        raise ValueError('This proof is Linux x86_64 only, not Redmi')
    runner = catalog()['runner']
    if runner['tag'] != 'b10964':
        raise ValueError('Pinned runner cohort changed')
    spec = runner['linux_binaries'][tag]
    archive = work / 'pinned-llama-bin.tar.gz'
    download_file(spec, archive, print)
    if archive.stat().st_size != spec['size'] or file_hash(archive) != spec['sha256']:
        raise ValueError('Original pinned archive mismatch')
    home = work / label
    if home.exists():
        raise ValueError('Refusing to overwrite prior independent proof home')
    for rel in ('bin', 'config', 'tmp', 'legacy'):
        (home / rel).mkdir(parents=True)
    # Exact cached pinned tar, copied to the production download destination.
    shutil.copyfile(archive, home / 'tmp/llama-bin.tar.gz')
    old = home / 'legacy/llama-server'
    old.write_text('#!/bin/sh\necho old-fixture\nexit 0\n')
    old.chmod(0o700)
    old_hash = file_hash(old)
    binary = home / 'bin/llama-server'
    binary.symlink_to(old)
    manifest = home / 'config/runner.json'
    manifest.write_text('{"tag":"old","binary_sha256":"old"}')
    install_llama_runner(home)
    if not binary.is_symlink():
        raise ValueError('Expected activated native symlink')
    candidate = binary.resolve(strict=True)
    if not candidate.is_relative_to(home / 'bin') or '.llama-b10964-' not in str(candidate):
        raise ValueError('Native candidate was not isolated from prior target')
    if file_hash(old) != old_hash:
        raise ValueError('Old runner mutated during activation')
    state = json.loads(manifest.read_text())
    if state['tag'] != runner['tag'] or state['platform'] != tag:
        raise ValueError('Wrong runner tag/platform')
    if state['binary_sha256'] != file_hash(candidate):
        raise ValueError('Live native binary hash differs from committed manifest')
    if state.get('phone_runner_proof', 'missing') is not None:
        raise ValueError('Linux-only proof must not mark phone runner')
    version = subprocess.run([str(binary), '--version'], capture_output=True,
                             text=True, timeout=15)
    if version.returncode:
        raise ValueError('Native live --version failed after promotion')
    version_text = (version.stdout + version.stderr).strip()
    if not version_text or state['version'] != version_text:
        raise ValueError('Native version receipt mismatch')
    stage_before = sorted(p.name for p in (home / 'bin').glob('.llama-b10964-*'))
    manifest_before = manifest.read_bytes()
    target_before = candidate
    install_llama_runner(home)
    if binary.resolve(strict=True) != target_before or manifest.read_bytes() != manifest_before:
        raise ValueError('Identical second install was not no-op')
    if sorted(p.name for p in (home / 'bin').glob('.llama-b10964-*')) != stage_before:
        raise ValueError('Second install created another candidate')
    if len(stage_before) != 1:
        raise ValueError('Expected exactly one isolated staging directory')
    return {
        'schema': 'v13.run109.pinned_native_version.linux.v1',
        'runner_tag': runner['tag'], 'platform': tag,
        'archive_sha256': file_hash(archive), 'archive_size': archive.stat().st_size,
        'binary_sha256': state['binary_sha256'], 'version': version_text,
        'old_runner_preserved': True, 'manifest_hash_bound': True,
        'native_version_executed': True, 'native_inference_executed': False,
        'model_downloaded': False, 'redmi_measured': False,
        'second_install_noop': True, 'staging_directories': len(stage_before),
        'step2_promoted': False, 'b3_promoted': False,
        'body_jepa_promoted': False, 'age_promoted': False,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--label', choices=('checkout', 'extracted'), required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    report = verify(args.work, args.label)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, sort_keys=True, indent=2) + '\n')
    print(json.dumps(report, sort_keys=True))


if __name__ == '__main__':
    main()
