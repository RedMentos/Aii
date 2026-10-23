"""The phone proof must reject partial lifecycle evidence and actually hit kill phases."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

APP = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('train_runner_proof', APP/'scripts/train_runner_proof.py')
proof = importlib.util.module_from_spec(spec)
spec.loader.exec_module(proof)


class IntegrationAcceptance(unittest.TestCase):
    def full(self):
        return {'proof_status': 'LEARNING_LIFECYCLE_PASS',
                'checks': dict.fromkeys(proof.INTEGRATION_CHECKS, True)}

    def test_complete_pass_only(self):
        self.assertTrue(proof.integration_pass(self.full(), 0))
        for status in ('LEARNING_LIFECYCLE_PARTIAL', 'LEARNING_INTERRUPTED', None):
            report = self.full(); report['proof_status'] = status
            self.assertFalse(proof.integration_pass(report, 0))

    def test_each_required_check_must_be_present_and_true(self):
        for key in proof.INTEGRATION_CHECKS:
            for value in (False, None, 1, 'true'):
                report = self.full(); report['checks'][key] = value
                self.assertFalse(proof.integration_pass(report, 0), (key, value))
            report = self.full(); del report['checks'][key]
            self.assertFalse(proof.integration_pass(report, 0), key)

    def test_selected_passes_cannot_hide_failed_actual_routes(self):
        report = self.full(); report['checks']['actual_learned_route_use'] = False
        # These are exactly the selected checks that the previous proof accepted.
        self.assertTrue(all(report['checks'][k] for k in (
            'shadow_does_not_commit', 'explicit_activation', 'restart_uses_head', 'integrity', 'rollback')))
        self.assertFalse(proof.integration_pass(report, 0))

    def test_exit_error_and_new_failed_checks_refuse(self):
        self.assertFalse(proof.integration_pass(self.full(), 2))
        report = self.full(); report['error'] = 'interrupted'
        self.assertFalse(proof.integration_pass(report, 0))
        report = self.full(); report['checks']['future_required_guard'] = False
        self.assertFalse(proof.integration_pass(report, 0))
        for value in (None, {}, {'checks': []}):
            self.assertFalse(proof.integration_pass(value, 0))


class ObservedKills(unittest.TestCase):
    def test_real_worker_killed_inside_each_phase(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d); x, y = proof.data(4, n_per=3)
            req = proof.request(base, x, y, dict(proof.CFG, learning_steps=2))
            for phase in ('forward', 'backward', 'checkpoint'):
                folder = base/phase
                result = proof.phase_kill(folder, req, phase, timeout=15)
                self.assertTrue(result['pass'], result)
                self.assertEqual(result['observed']['phase'], phase)
                self.assertFalse((folder/'metrics.json').exists())
                if phase == 'checkpoint':
                    self.assertGreater((folder/'candidate.npz').stat().st_size, 0)
                    with self.assertRaises(Exception):
                        proof.load(folder)

    def test_stale_phase_marker_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d); (base/'phase_reached.json').write_text('{}')
            with self.assertRaisesRegex(ValueError, 'fresh'):
                proof.phase_kill(base, base/'unused', 'forward')

    def test_existing_final_report_is_preserved(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/'train-runner-proof.json'; p.write_text('{"old":true}')
            with self.assertRaises(SystemExit):
                proof.main(['--out', d, '--skip-integration'])
            self.assertEqual(p.read_text(), '{"old":true}')


if __name__ == '__main__':
    unittest.main()
