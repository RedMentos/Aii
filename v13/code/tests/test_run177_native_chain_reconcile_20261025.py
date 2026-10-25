"""Run177 reviewed B2 native tap identity must be in integrated candidate chain.

Software/source-hash only. No native model, B3 authority or Redmi.
"""
import hashlib
from pathlib import Path
import unittest

from scripts import integrated_candidates as chain


EXPECTED_RUNNERS_SHA256 = '18db214f930953a5f781aa8aaa2b4425e048fd8bacf7848793c112a4e06af798'


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


class Run177NativeChainReconcile(unittest.TestCase):
    def test_integrated_chain_is_byte_exact_live_for_all_four_files(self):
        expected=chain.integrated_sources()
        live={name:(chain.ROOT/name).read_text() for name in chain.NAMES}
        self.assertEqual(set(expected),set(live))
        self.assertEqual({name:digest(text) for name,text in expected.items()},
                         {name:digest(text) for name,text in live.items()})
        self.assertEqual(digest(expected['v13/runners.py']),EXPECTED_RUNNERS_SHA256)
        self.assertEqual(chain.overlay(chain._baseline(chain.ROOT)),live)

    def test_b2_native_identity_preserved_without_changing_c3(self):
        t=chain.integrated_sources()['v13/runners.py']
        self.assertIn("self.role in ('C3_LANGUAGE','B2_GIST') else 2048",t)
        self.assertIn("'qwen35.result_norm.final.v1' if self.role=='B2_GIST'",t)
        self.assertIn("'lfm2.result_norm.final.v1'",t)
        self.assertIn('Pinned role-specific final token-state readout',t)

    def test_reapplying_run177_transform_must_fail_on_duplicate_anchors(self):
        t=chain.integrated_sources()
        with self.assertRaises(ValueError):
            chain.run177_b2_tap_identity(t)


if __name__=='__main__':
    unittest.main()
