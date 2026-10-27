"""Independent PR666 review: a typed halt/ban arriving mid-fetch must stop quarantine writes."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from v13.runtime import Runtime
from v13 import modules_gate as M, prohibitions as P, userrules

H = M.HUMAN
URL = 'https://example.org/review-module.json'
PAYLOAD = json.dumps({
    'format': M.FORMAT, 'name': 'Synthetic review module', 'version': '1',
    'license': 'Apache-2.0', 'source': 'test fixture only',
    'items': [{'title': 'Test', 'text': 'The imaginary test planet has two moons.'}],
}).encode('utf-8')


class MidFetchRevocationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.runtime = Runtime(Path(self.temp.name))
        self.runtime.sleep.cycle.set_policy('enabled', 'off')
        self.store = self.runtime.store
        M.set_enabled(self.store, True, authority=H)
        self.mid = M.propose(self.store, URL, 'Synthetic', origin='USER')

    def tearDown(self):
        self.runtime.close()
        self.temp.cleanup()

    def assert_not_persisted(self):
        self.assertEqual(M.state(self.store)['mods'][self.mid]['state'], 'PROPOSED')
        self.assertFalse(M._file(self.store, self.mid).exists())

    def test_notaus_activated_inside_fetcher_refuses_before_quarantine(self):
        def fetcher(url):
            self.assertEqual(url, URL)
            P.halt(self.store, True, authority=H)
            return PAYLOAD
        with self.assertRaises(PermissionError):
            M.fetch(self.store, self.mid, authority=H, fetcher=fetcher)
        self.assert_not_persisted()

    def test_network_ban_added_inside_fetcher_refuses_before_quarantine(self):
        def fetcher(_):
            P.add(self.store, 'risk', 'NETWORK', authority=H)
            return PAYLOAD
        with self.assertRaises(PermissionError):
            M.fetch(self.store, self.mid, authority=H, fetcher=fetcher)
        self.assert_not_persisted()

    def test_user_rule_added_inside_fetcher_refuses_before_quarantine(self):
        def fetcher(_):
            userrules.add(self.store, 'Lade niemals Module aus dem Internet herunter', 'USER_TYPED')
            return PAYLOAD
        with self.assertRaises(PermissionError):
            M.fetch(self.store, self.mid, authority=H, fetcher=fetcher)
        self.assert_not_persisted()

    def test_uninterrupted_human_fetch_still_passes_data_only_gate(self):
        rec = M.fetch(self.store, self.mid, authority=H, fetcher=lambda _: PAYLOAD)
        self.assertEqual(rec['state'], 'SANDBOX_OK')
        self.assertEqual(rec['sha256'], hashlib.sha256(PAYLOAD).hexdigest())
        self.assertEqual(M._file(self.store, self.mid).read_bytes(), PAYLOAD)

    def test_preexisting_halt_still_blocks_before_fetcher(self):
        P.halt(self.store, True, authority=H)
        def never(_):
            self.fail('Fetch must not begin under Notaus')
        with self.assertRaises(PermissionError):
            M.fetch(self.store, self.mid, authority=H, fetcher=never)
        self.assert_not_persisted()


if __name__ == '__main__':
    unittest.main()
