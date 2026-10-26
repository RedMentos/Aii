"""Run357 source-only lineage adversarial tests; no model/native/Redmi claims."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import current_source_lineage_run357 as L
from scripts import integrated_candidates as chain


class CurrentSourceLineageRun357(unittest.TestCase):
    def test_frozen_chain_and_current_reviewed_files_are_both_exact(self):
        result=L.verify()
        self.assertTrue(result['historical_chain_exact'])
        self.assertTrue(result['current_reviewed_sources_exact'])
        self.assertEqual(set(result['scope']),set(L.NAMES))

    def test_one_byte_current_store_tamper_is_not_accepted(self):
        original=Path.read_bytes
        target=L.ROOT/'v13/store.py'
        def altered(path):
            data=original(path)
            return data+b'\n# tampered' if path==target else data
        with patch.object(Path,'read_bytes',altered):
            with self.assertRaisesRegex(ValueError,'Current reviewed source digest changed: v13/store.py'):
                L.verify()

    def test_manifest_hash_edit_is_not_auto_repaired(self):
        d=json.loads(L.MANIFEST.read_text())
        d['current_sha256']['v13/runtime.py']='0'*64
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/'lineage.json';p.write_text(json.dumps(d))
            with self.assertRaisesRegex(ValueError,'Current reviewed source digest changed: v13/runtime.py'):
                L.verify(manifest_path=p)
            self.assertEqual(json.loads(p.read_text())['current_sha256']['v13/runtime.py'],'0'*64)

    def test_historical_chain_edit_rejected_even_if_live_is_unchanged(self):
        original=L.historical_sources()
        changed=dict(original);changed['v13/runners.py']+='\n# altered historical chain'
        with patch.object(L,'historical_sources',return_value=changed):
            with self.assertRaisesRegex(ValueError,'Historical integrated chain digest changed: v13/runners.py'):
                L.verify()

    def test_current_integrated_chain_edit_rejected_even_if_live_is_unchanged(self):
        original=chain.integrated_sources()
        changed=dict(original);changed['v13/store.py']+='\n# altered current chain'
        with patch.object(chain,'integrated_sources',return_value=changed):
            with self.assertRaisesRegex(ValueError,'Current integrated chain digest changed: v13/store.py'):
                L.verify()

    def test_frozen_and_current_replays_remain_distinct(self):
        historical=L.historical_sources()
        reviewed=chain.integrated_sources()
        manifest=json.loads(L.MANIFEST.read_text())
        import hashlib
        sha=lambda value: hashlib.sha256(value.encode('utf-8')).hexdigest()
        self.assertEqual({n:sha(historical[n]) for n in L.NAMES},manifest['historical_sha256'])
        self.assertEqual({n:sha(reviewed[n]) for n in L.NAMES},manifest['current_sha256'])
        self.assertNotEqual(historical['v13/runtime.py'],reviewed['v13/runtime.py'])
        self.assertNotEqual(historical['v13/store.py'],reviewed['v13/store.py'])

    def test_later_reviewed_runtime_and_store_are_not_misrepresented_as_run177_bytes(self):
        d=json.loads(L.MANIFEST.read_text())
        for name in ('v13/runners.py','v13/memory_server.py'):
            self.assertEqual(d['historical_sha256'][name],d['current_sha256'][name])
        for name in ('v13/runtime.py','v13/store.py'):
            self.assertNotEqual(d['historical_sha256'][name],d['current_sha256'][name])


if __name__=='__main__':
    unittest.main()
