"""Isolated staging tests; actual V13 end-to-end suite is separate."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

MODULE_PATH = Path(__file__).resolve().parents[1] / 'scripts/stage_integrated_candidate.py'
spec = importlib.util.spec_from_file_location('stage_candidate', MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class StageTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.code = self.root / 'code'
        (self.code / 'scripts').mkdir(parents=True)
        (self.code / 'v13').mkdir()
        (self.code / 'v13/runtime.py').write_text('ORIGINAL')
        (self.code / 'specs').mkdir()
        (self.code / 'specs/test.json').write_text('{}')

    def builder(self, body):
        (self.code / module.BUILDER).write_text('def build_sources(code_dir):\n' + body)

    def test_stages_replacement_without_mutating_source(self):
        self.builder("    return {'v13/runtime.py': b'INTEGRATED'}\n")
        out = self.root / 'candidate'
        result = module.stage(self.code, out)
        self.assertEqual((out / 'v13/runtime.py').read_text(), 'INTEGRATED')
        self.assertEqual((self.code / 'v13/runtime.py').read_text(), 'ORIGINAL')
        self.assertEqual(result['status'], 'SHADOW_REVIEW_ONLY')
        self.assertTrue((out / 'specs/test.json').exists())
        with self.assertRaises(FileExistsError):
            module.stage(self.code, out)

    def test_pin_failure_never_publishes_candidate(self):
        self.builder("    raise ValueError('pin mismatch')\n")
        out = self.root / 'candidate'
        with self.assertRaisesRegex(ValueError, 'pin mismatch'):
            module.stage(self.code, out)
        self.assertFalse(out.exists())

    def test_rejects_traversal_before_copy(self):
        self.builder("    return {'../outside.py': b'bad'}\n")
        with self.assertRaisesRegex(ValueError, 'unsafe'):
            module.stage(self.code, self.root / 'candidate')
        self.assertFalse((self.root / 'outside.py').exists())


if __name__ == '__main__':
    unittest.main()
