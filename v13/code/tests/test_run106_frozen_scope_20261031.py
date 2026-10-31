"""Original historical candidate is executable only at its exact frozen source.

These tests do not replace the RED current-source historical test suites.
They prove both the original positive baseline and current fail-closed scope.
"""
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from scripts import source_handoff_candidate as handoff
from scripts import native_firing_runtime_candidate as firing
from v13.common import APP


CASES = (
    (handoff, 'SOURCE_HANDOFF_FROZEN_BASELINE_V1',
     'Runtime is neither exact frozen baseline nor complete reviewed candidate'),
    (firing, 'NATIVE_FIRING_RUNTIME_BASELINE_V1',
     'Live sources differ from complete baseline/candidate'),
)


class Run106FrozenScope(unittest.TestCase):
    def frozen(self, module, root):
        src = APP / module.SNAPSHOT
        dest = root / module.SNAPSHOT
        dest.mkdir(parents=True)
        shutil.copyfile(src / 'manifest.json', dest / 'manifest.json')
        manifest = json.loads((dest / 'manifest.json').read_text())
        for name in module.NAMES:
            frozen = src / Path(name).name
            raw = frozen.read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(), manifest['files'][name])
            (dest / Path(name).name).write_bytes(raw)
            live = root / name
            live.parent.mkdir(parents=True, exist_ok=True)
            live.write_bytes(raw)
        return manifest, dest

    def test_original_frozen_baselines_still_accept_exact_source(self):
        for module, schema, _ in CASES:
            with self.subTest(module=module.__name__), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                manifest, _ = self.frozen(module, root)
                self.assertEqual(manifest['schema'], schema)
                self.assertEqual(set(manifest['files']), set(module.NAMES))
                original, candidate = module.sources(root)
                self.assertEqual(set(original), set(module.NAMES))
                self.assertEqual(set(candidate), set(module.NAMES))
                self.assertTrue(any(original[k] != candidate[k] for k in module.NAMES))
                for name in module.NAMES:
                    self.assertEqual(hashlib.sha256(original[name].encode()).hexdigest(),
                                     manifest['files'][name])

    def test_frozen_manifest_tampering_refuses_before_candidate(self):
        for module, _, _ in CASES:
            with self.subTest(module=module.__name__), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                _, dest = self.frozen(module, root)
                file = dest / Path(module.NAMES[0]).name
                file.write_bytes(file.read_bytes() + b'\n# tampered')
                with self.assertRaisesRegex(ValueError, 'baseline.*digest changed'):
                    module.sources(root)

    def test_current_live_source_refuses_historical_candidate(self):
        for module, _, message in CASES:
            with self.subTest(module=module.__name__):
                with self.assertRaisesRegex(ValueError, message):
                    module.sources(APP)

    def test_no_model_or_authority_is_needed_to_check_scope(self):
        self.assertTrue((APP / 'scripts/install_selftest.py').is_file())
        self.assertTrue((APP / 'specs/gate-graph.json').is_file())
        from v13 import gates
        self.assertEqual(gates.evaluate()['STEP2_EXIT']['status'],
                         'EVIDENCE_NOT_PASSING')


if __name__ == '__main__':
    unittest.main()
