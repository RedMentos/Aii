"""Run637 prospective dependency/evidence close regressions, no model needed."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[3]
WORKFLOW = ROOT / '.github/workflows/run637-c3-deployed-native.yml'


class Run637NativePrereqs(unittest.TestCase):
    def test_transformers5_official_template_requires_pinned_jinja2(self):
        w = WORKFLOW.read_text()
        self.assertIn("'transformers==5.0.0'", w)
        self.assertIn("'jinja2==3.1.6'", w)
        self.assertIn("'chat_template.jinja'", w)

    def test_evidence_close_and_enforce_expand_bash_k_correctly(self):
        w = WORKFLOW.read_text()
        self.assertIn('RUN637_${k}_EXIT.txt', w)
        self.assertNotIn('RUN637_$k_EXIT.txt', w)
        self.assertIn('RUN637_SHA256SUMS.txt', w)
        self.assertIn('sha256sum', w)

    def test_original_native_bindings_are_unchanged(self):
        w = WORKFLOW.read_text()
        self.assertIn('12701530582', w)
        self.assertIn('3674e88f71855b46a1de59ca50642ec07c39bb3d6c86bd7e8a49eb1a031d8599', w)
        self.assertIn('3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d', w)
        self.assertIn('79e312188dc1d75c28201771f106e91de470b5cebdd838d31bb4db25eecf5d39', w)


if __name__ == '__main__':
    unittest.main()
