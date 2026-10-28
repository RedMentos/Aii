"""Software-only local HTTP fixture tests; never download public model weights."""
from contextlib import contextmanager
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from scripts.step2_current_catalog_artifact_probe import git_blob_sha, probe


@contextmanager
def server_for(payloads):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_GET(self):
            body = payloads.get(self.path)
            if body is None:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_port
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def fixture(port):
    payloads = {role: b'GGUF' + role.encode() * 100
                for role in ('body', 'gist', 'language')}
    models = {}
    for role, data in payloads.items():
        filename = role + '.gguf'
        models[role] = {
            'model_id': 'local-test/' + role, 'revision': role + '-revision',
            'license_id': 'test-license', 'license_url': 'https://example.org/license',
            'quant_format': 'Q4_0', 'main_file': filename,
            'files': [{'local_name': filename, 'upstream_path': filename,
                       'size': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
                       'url': f'http://127.0.0.1:{port}/{filename}'}],
        }
    catalog = {'schema_version': '1.0', 'models': models}
    raw = json.dumps(catalog, sort_keys=True).encode()
    return catalog, raw, {'/' + k + '.gguf': v for k, v in payloads.items()}


class CurrentCatalogArtifactProbe(unittest.TestCase):
    def test_local_fixture_bytes_verified_without_inference(self):
        with server_for({'/body.gguf': b'GGUF' + b'body' * 100,
                         '/gist.gguf': b'GGUF' + b'gist' * 100,
                         '/language.gguf': b'GGUF' + b'language' * 100}) as port:
            catalog, raw, _ = fixture(port)
            with tempfile.TemporaryDirectory() as td:
                root = Path(td)
                path = root / 'catalog.json'
                path.write_bytes(raw)
                with patch('v13.models.catalog', return_value=catalog):
                    result = probe(root / 'home', root / 'evidence' / 'report.json',
                                   git_blob_sha(raw), path, allow_local_http=True,
                                   progress=lambda *_: None)
                self.assertEqual(len(result['roles']), 3)
                self.assertFalse(result['native_inference_performed'])
                self.assertFalse(result['step2_gate_promoted'])
                self.assertEqual(result['jepa_weight'], 0)
                self.assertTrue(all(x['gguf_magic_verified'] and x['sha256_verified']
                                    for x in result['roles']))
                self.assertTrue((root / 'evidence/report.json').exists())

    def test_wrong_catalog_blob_refuses_before_download(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            path = root / 'catalog.json'
            path.write_bytes(b'{}')
            with self.assertRaises(ValueError):
                probe(root / 'home', root / 'report.json', '0' * 40, path)
            self.assertFalse((root / 'home').exists())

    def test_http_source_rejected_outside_explicit_test_mode(self):
        catalog, raw, _ = fixture(12345)
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            path = root / 'catalog.json'
            path.write_bytes(raw)
            with self.assertRaises(ValueError):
                probe(root / 'home', root / 'report.json', git_blob_sha(raw), path)
            self.assertFalse((root / 'home').exists())

    def test_existing_home_cannot_be_overwritten(self):
        catalog, raw, _ = fixture(12345)
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            path = root / 'catalog.json'
            path.write_bytes(raw)
            (root / 'home').mkdir()
            with self.assertRaises(FileExistsError):
                probe(root / 'home', root / 'report.json', git_blob_sha(raw), path,
                      allow_local_http=True)
            self.assertFalse((root / 'report.json').exists())

    def test_wrong_download_sha_never_seals_report(self):
        payloads = {'/body.gguf': b'GGUF' + b'body' * 100,
                    '/gist.gguf': b'GGUF' + b'gist' * 100,
                    '/language.gguf': b'GGUF' + b'language' * 100}
        with server_for(payloads) as port:
            catalog, _, _ = fixture(port)
            catalog['models']['gist']['files'][0]['sha256'] = '0' * 64
            raw = json.dumps(catalog, sort_keys=True).encode()
            with tempfile.TemporaryDirectory() as td:
                root = Path(td)
                path = root / 'catalog.json'
                path.write_bytes(raw)
                with patch('v13.models.catalog', return_value=catalog):
                    with self.assertRaises(Exception):
                        probe(root / 'home', root / 'report.json', git_blob_sha(raw),
                              path, allow_local_http=True, progress=lambda *_: None)
                self.assertFalse((root / 'report.json').exists())


if __name__ == '__main__':
    unittest.main()
