"""Exercise post-answer observer policy in the actual composed Stage."""
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

CODE = Path(__file__).resolve().parents[1]


class PostcommitStage(unittest.TestCase):
    def test_composed_runtime_exercises_postcommit_policy(self):
        path = CODE / 'scripts/stage_integrated_candidate.py'
        spec = importlib.util.spec_from_file_location('postcommit_composition', path)
        stager = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(stager)
        with tempfile.TemporaryDirectory(prefix='v13-observer-stage-') as tmp:
            dest = Path(tmp) / 'candidate'
            stager.stage(CODE, dest)
            (dest / 'tests').mkdir(exist_ok=True)
            name = 'test_postcommit_observer_20261116.py'
            shutil.copyfile(CODE / 'tests' / name, dest / 'tests' / name)
            env = dict(os.environ, PYTHONPATH=str(dest), PYTHONDONTWRITEBYTECODE='1',
                       V13_TEST_POSTCOMMIT_STAGE='1')
            cases = [
                'test_one_foreground_offer_only_retries_the_missing_body',
                'test_failed_postcommit_body_does_not_starve_other',
                'test_user_one_body_effort_never_starts_other_body',
                'test_new_yellow_resource_limit_applies_after_first_attempt',
                'test_on_demand_stays_without_postcommit_calls',
                'test_timeout_reflex_defers_only_the_authorized_body',
                'test_latewatch_respects_user_one_body_effort',
            ]
            command = [sys.executable, '-m', 'pytest', '-q',
                       *['tests/' + name + '::RuntimePostcommit::' + item for item in cases]]
            run = subprocess.run(command, cwd=dest, env=env, capture_output=True,
                                 text=True, timeout=120)
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)


if __name__ == '__main__':
    unittest.main()
