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
    def test_current_runtime_is_already_composed_and_overlay_fails_closed(self):
        module = load(HELPER, 'observer_layer')
        from scripts import termux_runtime_recovery_candidate_20261112 as recovery
        runtime = (CODE / 'v13/runtime.py').read_bytes()
        self.assertTrue(recovery._observer_budget_is_composed(
            CODE, {'v13/runtime.py': runtime}))
        sources = {'v13/upstream_example.py': b'unchanged'}
        with self.assertRaisesRegex(ValueError, 'anchor changed'):
            module.apply_sources(CODE, sources)
        self.assertEqual(sources['v13/upstream_example.py'], b'unchanged')

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
