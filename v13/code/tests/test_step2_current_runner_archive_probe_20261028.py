"""Linux runner/source archive byte proof tests: synthetic local HTTP only."""
import hashlib
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest

from scripts.step2_current_catalog_artifact_probe import git_blob_sha
from scripts.step2_current_runner_archive_probe import probe
from tests.test_step2_current_catalog_artifact_probe_20261028 import server_for


def archive(member='source/file.txt'):
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode='w:gz') as tf:
        data = b'closed archive fixture'
        info = tarfile.TarInfo(member)
        info.size = len(data)
        tf.addfile(info, io.BytesIO(data))
    return buffer.getvalue()


def catalog(port, source_bytes, binary_bytes):
    def spec(name, data):
        return {'url': f'http://127.0.0.1:{port}/{name}.tar.gz',
                'sha256': hashlib.sha256(data).hexdigest(),
                'size': len(data)}
    return {'runner': {'tag': 'test-runner-tag', 'source_revision': 'test-rev',
                       'source_url': spec('source', source_bytes)['url'],
                       'source_sha256': spec('source', source_bytes)['sha256'],
                       'source_size': len(source_bytes),
                       'linux_binaries': {'linux-x86_64': spec('binary', binary_bytes)}}}


class RunnerArchiveProbe(unittest.TestCase):
    def execute(self, source_bytes, binary_bytes, *, change=None, allow_http=True):
        with server_for({'/source.tar.gz': source_bytes,
                         '/binary.tar.gz': binary_bytes}) as port:
            cat = catalog(port, source_bytes, binary_bytes)
            if change:
                change(cat)
            raw = json.dumps(cat, sort_keys=True).encode()
            with tempfile.TemporaryDirectory() as td:
                root = Path(td)
                path = root / 'catalog.json'
                path.write_bytes(raw)
                try:
                    result = probe(root / 'home', root / 'report.json',
                                   git_blob_sha(raw), path,
                                   allow_local_http=allow_http,
                                   progress=lambda *_: None)
                except Exception:
                    self.assertFalse((root / 'report.json').exists())
                    raise
                self.assertTrue((root / 'report.json').exists())
                return result

    def test_exact_archives_verified_without_executable_or_native_proof(self):
        result = self.execute(archive('source/file.txt'),
                              archive('binary/llama-server'))
        self.assertEqual(len(result['archives']), 2)
        self.assertTrue(all(x['sha256_verified'] and x['tar_structure_verified']
                            for x in result['archives']))
        self.assertFalse(result['executable_hash_verified'])
        self.assertFalse(result['native_inference_performed'])
        self.assertFalse(result['step2_gate_promoted'])

    def test_corrupted_binary_hash_never_seals(self):
        def corrupt(cat):
            cat['runner']['linux_binaries']['linux-x86_64']['sha256'] = '0' * 64
        with self.assertRaises(Exception):
            self.execute(archive(), archive('binary/llama-server'), change=corrupt)

    def test_non_tar_binary_rejected(self):
        with self.assertRaises(ValueError):
            self.execute(archive(), b'not-a-tarball' * 40)

    def test_unsafe_tar_member_rejected_without_extraction(self):
        with self.assertRaises(ValueError):
            self.execute(archive('../escape'), archive('binary/llama-server'))

    def test_non_https_runner_source_rejected(self):
        with self.assertRaises(ValueError):
            self.execute(archive(), archive('binary/llama-server'),
                         allow_http=False)

    def test_catalog_blob_mismatch_refuses_before_download(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            path = root / 'catalog.json'
            path.write_text('{}')
            with self.assertRaises(ValueError):
                probe(root / 'home', root / 'report.json', '0' * 40, path)
            self.assertFalse((root / 'home').exists())


if __name__ == '__main__':
    unittest.main()
