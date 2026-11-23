"""Pinned llama.cpp source and Linux runner archive byte probe; NO execution."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import tarfile
from urllib.parse import urlsplit

from v13.common import APP, dumps, file_hash
from v13.models import download_file
from scripts.step2_current_catalog_artifact_probe import git_blob_sha

MAX_TOTAL_BYTES = 100_000_000
DISK_RESERVE = 128 * 1024 * 1024


def _safe_archive(path):
    try:
        with tarfile.open(path, 'r:gz') as archive:
            names = archive.getmembers()
            if not names or not any(m.isfile() for m in names):
                raise ValueError('Runner/source archive empty')
            for member in names:
                p = PurePosixPath(member.name)
                if p.is_absolute() or '..' in p.parts:
                    raise ValueError('Runner/source archive contains unsafe member')
            return len(names)
    except (tarfile.TarError, EOFError) as exc:
        raise ValueError('Invalid runner/source tar.gz archive') from exc


def probe(home, report_path, expected_catalog_blob, catalog_path=None,
          *, platform='linux-x86_64', allow_local_http=False, progress=print):
    home, report_path = Path(home), Path(report_path)
    raw = Path(catalog_path or (APP / 'specs/models.json')).read_bytes()
    if git_blob_sha(raw) != expected_catalog_blob:
        raise ValueError('Runner catalog Git blob differs from external pin')
    runner = json.loads(raw)['runner']
    if platform not in ('linux-x86_64', 'linux-arm64'):
        raise ValueError('Linux artifact-only runner platform required')
    binary = runner['linux_binaries'][platform]
    source = {'url': runner['source_url'], 'sha256': runner['source_sha256'],
              'size': runner['source_size']}
    items = [('source', source), ('binary', binary)]
    total = 0
    for label, spec in items:
        digest = spec['sha256']
        if (type(digest) is not str or len(digest) != 64 or
                any(c not in '0123456789abcdef' for c in digest)):
            raise ValueError('Runner archive SHA256 pin invalid: ' + label)
        if type(spec['size']) is not int or spec['size'] <= 4:
            raise ValueError('Runner archive byte count invalid: ' + label)
        u = urlsplit(spec['url'])
        if u.scheme != 'https' and not (allow_local_http and
                u.scheme == 'http' and u.hostname in ('127.0.0.1', 'localhost')):
            raise ValueError('Runner archive source must use HTTPS')
        if not u.path.endswith('.tar.gz'):
            raise ValueError('Runner archive URL suffix invalid')
        total += spec['size']
    if total > MAX_TOTAL_BYTES:
        raise ValueError('Runner archive byte budget exceeded')
    if home.exists() or report_path.exists():
        raise FileExistsError('Runner scratch home/report must be new')
    report_path.parent.mkdir(parents=True, exist_ok=True)
    if shutil.disk_usage(report_path.parent).free < total + DISK_RESERVE:
        raise OSError('Insufficient runner archive scratch disk')
    home.mkdir(parents=True)
    records = []
    for label, spec in items:
        dest = home / (label + '.tar.gz')
        progress('download+SHA256 runner archive=' + label)
        download_file(spec, dest, progress=progress)
        if dest.stat().st_size != spec['size'] or file_hash(dest) != spec['sha256']:
            raise ValueError('Runner archive SHA256 differs: ' + label)
        count = _safe_archive(dest)
        records.append({'kind': label, 'sha256': spec['sha256'],
                        'size': spec['size'], 'tar_members': count,
                        'sha256_verified': True, 'tar_structure_verified': True})
    report = {'schema': 'v13.step2.current_runner_archive_probe.v1',
              'evidence_kind': 'LINUX_RUNNER_ARCHIVE_BYTES_ONLY',
              'catalog_git_blob_sha': expected_catalog_blob,
              'runner_tag': runner['tag'],
              'runner_source_revision': runner['source_revision'],
              'platform': platform, 'archives': records,
              'total_archive_bytes': total,
              'executable_hash_verified': False, 'native_inference_performed': False,
              'redmi_proof': False, 'step2_gate_promoted': False, 'jepa_weight': 0}
    with report_path.open('xb') as stream:
        stream.write(dumps(report).encode('utf-8'))
        stream.flush()
        os.fsync(stream.fileno())
    return report


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--scratch-home', required=True)
    p.add_argument('--report', required=True)
    p.add_argument('--expected-catalog-blob', required=True)
    p.add_argument('--platform', default='linux-x86_64',
                   choices=('linux-x86_64', 'linux-arm64'))
    a = p.parse_args()
    report = probe(a.scratch_home, a.report, a.expected_catalog_blob,
                   platform=a.platform)
    print('RUNNER_ARCHIVE_SHA_VERIFIED_ONLY count=' + str(len(report['archives'])))


if __name__ == '__main__':
    main()
