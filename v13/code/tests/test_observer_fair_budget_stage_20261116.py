"""Run observer fairness through the real final-stage builder, without models."""
import hashlib
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

CODE = Path(__file__).resolve().parents[1]
HELPER = CODE / 'scripts/integrated_observer_fair_budget_candidate_20261116.py'


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ObserverStageTests(unittest.TestCase):
    def test_exact_anchors_are_idempotent_and_reject_tampering(self):
        module = load(HELPER, 'observer_layer')
        result = module.apply_sources(CODE, {'v13/upstream_example.py': b'unchanged'})
        self.assertEqual(result['v13/upstream_example.py'], b'unchanged')
        second = module.apply_sources(CODE, result)
        self.assertEqual(second, result)
        tampered = dict(result)
        tampered['v13/runtime.py'] = b'tampered runtime bytes'
        with self.assertRaisesRegex(ValueError, 'anchor changed'):
            module.apply_sources(CODE, tampered)

    def test_existing_native_success_variant_is_recognized(self):
        module = load(HELPER, 'observer_existing_success')
        result = module.apply_sources(CODE, {})
        budget = result['v13/native_turn_budget.py']
        self.assertEqual(budget.count(b'data=row.get("metadata")'), 1)
        self.assertIn(b'native["generated_tokens"] > 0', budget)

    def test_existing_cognition_fair_slice_is_recognized_without_rewrite(self):
        module = load(HELPER, 'observer_existing_cognition')
        original = (CODE / 'v13/cognition.py').read_bytes()
        result = module.apply_sources(CODE, {})
        cognition = result['v13/cognition.py']
        self.assertEqual(cognition, original)
        for marker in (b'observer_deadline=deadline', b'minimum_role_slice_s',
                       b'native_body_budgeted_for_c3', b'preanswer_seconds_available',
                       b'native_body_deferred_for_c3'):
            self.assertIn(marker, cognition)
        self.assertEqual(cognition.count(b'observer_deadline=deadline'), 1)

    def test_final_composed_runtime_and_native_success_contract(self):
        module = load(HELPER, 'observer_pins')
        before = {name: hashlib.sha256((CODE/name).read_bytes()).hexdigest() for name in module.PINS}
        stage = load(CODE/'scripts/stage_integrated_candidate.py', 'observer_stage')
        with tempfile.TemporaryDirectory(prefix='v13-observer-stage-') as folder:
            destination = Path(folder)/'stage'
            stage.stage(CODE, destination)
            result = subprocess.run([sys.executable, "-m", "pytest", "-q",
                str(CODE/'tests/observer_fair_budget_disposable_cases_20261116.py'),
                str(CODE/'tests/test_same_turn_body_delivery_qa.py')],
                cwd=destination, env=dict(os.environ, PYTHONPATH=str(destination), PYTHONDONTWRITEBYTECODE='1'),
                capture_output=True, text=True, timeout=60)
            self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
        self.assertEqual(before, {name: hashlib.sha256((CODE/name).read_bytes()).hexdigest() for name in before})


if __name__ == '__main__':
    unittest.main()
