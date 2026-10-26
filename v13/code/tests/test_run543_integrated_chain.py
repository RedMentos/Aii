"""Run543 exact reviewed historical integration replay, no permissive source fallback."""
from pathlib import Path
import shutil
import tempfile
import unittest

from scripts import integrated_candidates as integrated
from scripts import native_firing_runtime_candidate as firing
from scripts import source_handoff_candidate as handoff


ROOT = Path(__file__).resolve().parents[1]
FILES = ('v13/runners.py', 'v13/memory_server.py', 'v13/runtime.py',
         'v13/store.py', 'v13/bodyview.py', 'v13/cognition.py')
SNAPSHOTS = (
    'docs/proofs/continuation-20261011/source-handoff-baseline',
    'docs/proofs/continuation-20261011/native-firing-runtime-baseline',
)


class ExactIntegratedChain(unittest.TestCase):
    def test_current_live_sources_match_complete_frozen_reviewed_chain(self):
        expected = integrated.integrated_sources(ROOT)
        self.assertEqual(set(expected), set(integrated.NAMES))
        for name, value in expected.items():
            self.assertEqual((ROOT / name).read_text(), value, name)
        baseline, changed = handoff.sources(ROOT)
        self.assertEqual((ROOT / 'v13/runtime.py').read_text(), changed['v13/runtime.py'])
        self.assertNotEqual(baseline['v13/runtime.py'], changed['v13/runtime.py'])
        original, candidate = firing.sources(ROOT)
        self.assertEqual((ROOT / 'v13/store.py').read_text(), candidate['v13/store.py'])
        self.assertNotEqual(original['v13/store.py'], candidate['v13/store.py'])

    def test_one_byte_runtime_or_store_drift_still_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for name in FILES:
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / name, target)
            for name in SNAPSHOTS:
                shutil.copytree(ROOT / name, root / name)
            # First verify the exact copied live sources are admitted.
            handoff.sources(root)
            firing.sources(root)
            runtime = root / 'v13/runtime.py'
            original = runtime.read_bytes()
            runtime.write_bytes(original + b'\n# unauthorized source drift\n')
            with self.assertRaisesRegex(ValueError, "Runtime is neither exact"):
                handoff.sources(root)
            runtime.write_bytes(original)
            store = root / 'v13/store.py'
            original = store.read_bytes()
            store.write_bytes(original + b'\n# unauthorized source drift\n')
            with self.assertRaisesRegex(ValueError, "Live sources differ"):
                firing.sources(root)


if __name__ == "__main__":
    unittest.main()
