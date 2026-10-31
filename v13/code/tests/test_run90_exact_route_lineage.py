"""Exact Run12J source lineage: acceptance without arbitrary-hash bypass."""
import hashlib
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from scripts import integrated_candidates, source_handoff_candidate, native_firing_runtime_candidate

ROOT=Path(__file__).resolve().parents[1]


class ExactRouteLineage(TestCase):
    def test_current_integrated_source_matches_byte_exactly(self):
        expected=integrated_candidates.integrated_sources(ROOT)
        self.assertEqual(set(expected),set(integrated_candidates.NAMES))
        for name, text in expected.items():
            self.assertEqual((ROOT/name).read_bytes(),text.encode('utf-8'),name)

    def test_strict_candidate_sources_accept_exact_reviewed_chain(self):
        for candidate in (source_handoff_candidate,native_firing_runtime_candidate):
            baseline,changed=candidate.sources(ROOT)
            self.assertEqual(set(baseline),set(candidate.NAMES))
            self.assertEqual(set(changed),set(candidate.NAMES))

    def test_security_patch_exactly_once(self):
        expected=integrated_candidates.integrated_sources(ROOT)['v13/runtime.py']
        self.assertEqual(expected.count("from .control_calibration_worker import observation"),1)
        self.assertEqual(expected.count("and calls[0].get('name')=='select_processing'"),1)
        self.assertNotIn("for v in obj.values():yield from routes(v)",expected)

    def test_one_byte_runtime_tamper_refused_by_both(self):
        original=Path.read_text
        runtime=(ROOT/'v13/runtime.py').resolve()
        def altered(path,*args,**kwargs):
            value=original(path,*args,**kwargs)
            if path.resolve()==runtime:return value+'\n# unauthorized change\n'
            return value
        with patch.object(Path,'read_text',altered):
            for candidate in (source_handoff_candidate,native_firing_runtime_candidate):
                with self.subTest(candidate=candidate.__name__):
                    with self.assertRaisesRegex(ValueError,'Runtime is neither|Live sources differ'):
                        candidate.sources(ROOT)

    def test_probe_never_changes_live_runtime(self):
        names=integrated_candidates.NAMES
        before={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in names}
        integrated_candidates.integrated_sources(ROOT)
        source_handoff_candidate.sources(ROOT)
        native_firing_runtime_candidate.sources(ROOT)
        after={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in names}
        self.assertEqual(before,after)


if __name__=='__main__':
    import unittest
    unittest.main()
