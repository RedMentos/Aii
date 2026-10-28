"""Current-catalog B1/B2/C3 GGUF byte verification. NO native inference or gate promotion.

Uses the canonical ModelManager downloader and exact immutable catalog blob.
Model files remain in an isolated local scratch home; never upload the weights.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
from urllib.parse import urlsplit

from v13.models import ModelManager
from v13.common import APP, dumps, file_hash

ROLES = ('body', 'gist', 'language')
MAX_TOTAL_BYTES = 2_000_000_000
MIN_DISK_RESERVE = 512 * 1024 * 1024


def git_blob_sha(data):
    return hashlib.sha1(b'blob ' + str(len(data)).encode('ascii') + b'\0' + data).hexdigest()


def probe(home, report_path, expected_catalog_blob, catalog_path=None,
          *, allow_local_http=False, progress=print):
    home, report_path = Path(home), Path(report_path)
    catalog_path = Path(catalog_path or (APP / 'specs/models.json'))
    raw = catalog_path.read_bytes()
    if git_blob_sha(raw) != expected_catalog_blob:
        raise ValueError('Catalog Git blob differs from externally pinned revision')
    catalog = json.loads(raw)
    specs = catalog['models']
    total = 0
    expected = {}
    for role in ROLES:
        spec = specs[role]
        if not spec.get('license_id') or not spec.get('license_url'):
            raise ValueError('Missing upstream license metadata')
        if len(spec['files']) != 1:
            raise ValueError('Artifact-only probe requires one GGUF per role')
        f = spec['files'][0]
        digest = f['sha256']
        if (type(digest) is not str or len(digest) != 64 or
                any(c not in '0123456789abcdef' for c in digest)):
            raise ValueError('Invalid model SHA256 pin')
        if type(f['size']) is not int or f['size'] <= 4:
            raise ValueError('Invalid model byte count')
        u = urlsplit(f['url'])
        if u.scheme != 'https' and not (allow_local_http and
                u.scheme == 'http' and u.hostname in ('127.0.0.1', 'localhost')):
            raise ValueError('Non-HTTPS model source')
        if not f['url'].endswith('/' + f['upstream_path']):
            raise ValueError('Model URL and declared filename disagree')
        expected[role] = (spec, f)
        total += f['size']
    if expected['body'][1]['sha256'] == expected['gist'][1]['sha256']:
        raise ValueError('B1/B2 files not distinct')
    if total > MAX_TOTAL_BYTES:
        raise ValueError('Catalog artifact budget exceeded')
    if home.exists() or report_path.exists():
        raise FileExistsError('Scratch home/report must be new; refuse overwrite')
    report_path.parent.mkdir(parents=True, exist_ok=True)
    if shutil.disk_usage(report_path.parent).free < total + MIN_DISK_RESERVE:
        raise OSError('Insufficient scratch disk budget')
    home.mkdir(parents=True)
    manager = ModelManager(home)
    for role in ROLES:
        progress('download+SHA256 role=' + role)
        manager.install(role, progress=progress)
    verification = manager.verify(deep=True)
    output = []
    for role in ROLES:
        spec, f = expected[role]
        state = manager.installed[role]
        result = verification[role]
        if not result['ok'] or not result['hash_checked']:
            raise ValueError('Installed artifact SHA256 failed: ' + role)
        if (state['exact_revision'] != spec['revision'] or
                state['model_id'] != spec['model_id'] or
                state['license_id'] != spec['license_id']):
            raise ValueError('Installed model identity drift: ' + role)
        entry = state['files'][f['local_name']]
        p = home / entry['path']
        if (entry['sha256'] != f['sha256'] or entry['size'] != f['size'] or
                p.stat().st_size != f['size'] or file_hash(p) != f['sha256']):
            raise ValueError('Downloaded bytes differ from pinned file: ' + role)
        with p.open('rb') as stream:
            if stream.read(4) != b'GGUF':
                raise ValueError('Downloaded model is not GGUF: ' + role)
        output.append({'role': role, 'model_id': spec['model_id'],
                       'revision': spec['revision'], 'sha256': f['sha256'],
                       'size': f['size'], 'license_id': spec['license_id'],
                       'gguf_magic_verified': True, 'sha256_verified': True})
    report = {'schema': 'v13.step2.current_catalog_artifact_probe.v1',
              'evidence_kind': 'LINUX_ARTIFACT_BYTES_ONLY',
              'catalog_git_blob_sha': expected_catalog_blob,
              'roles': output, 'total_model_bytes': total,
              'native_inference_performed': False, 'redmi_proof': False,
              'step2_gate_promoted': False, 'jepa_weight': 0}
    data = dumps(report)
    with report_path.open('xb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    return report


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--scratch-home', required=True)
    p.add_argument('--report', required=True)
    p.add_argument('--expected-catalog-blob', required=True)
    a = p.parse_args()
    report = probe(a.scratch_home, a.report, a.expected_catalog_blob)
    print('ARTIFACT_SHA_VERIFIED_ONLY roles=' + str(len(report['roles'])))


if __name__ == '__main__':
    main()
