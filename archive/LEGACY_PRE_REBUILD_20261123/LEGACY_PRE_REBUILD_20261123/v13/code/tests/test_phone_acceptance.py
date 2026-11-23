"""Collector tests use labelled synthetic sensors, never native model claims."""
import importlib.util
import json
from pathlib import Path
import signal
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('phone_acceptance', Path(__file__).resolve().parents[1] / 'scripts/phone_acceptance.py')
collector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(collector)


def sample(t, power=None, rss=100, start_ticks=1000, temperature=None):
    return {'monotonic_s': t, 'subprocess_tree_rss_sum_bytes': rss,
            'subprocess_tree': [{'pid': 23, 'start_ticks': start_ticks, 'rss_bytes': rss, 'command': 'fixture'}],
            'batteries': [{'path': 'fixture/battery', 'discharge_power_w': power, 'temperature_c': temperature}],
            'thermal_zones': [], 'kv_cache_bytes': None}


class PhoneCollector(unittest.TestCase):
    def test_nonfinite_and_invalid_sensor_values_are_missing(self):
        for value in ('nan', 'inf', '-inf', None, 'denied'):
            self.assertIsNone(collector.number(value))
        self.assertEqual(collector.number('2.5'), 2.5)

    def test_sysfs_units_and_unknown_charging_are_not_energy(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            battery = root / 'class/power_supply/battery'
            battery.mkdir(parents=True)
            fields = {'type': 'Battery', 'status': 'Discharging', 'current_now': '-2000000', 'voltage_now': '4000000', 'temp': '350'}
            for key, value in fields.items():
                (battery / key).write_text(value)
            row = collector.battery_sysfs(root)[0]
            self.assertEqual(row['discharge_power_w'], 8)
            self.assertEqual(row['temperature_c'], 35)
            self.assertIsNone(row['energy_microwatt_hour'])
            (battery / 'status').write_text('Charging')
            self.assertIsNone(collector.battery_sysfs(root)[0]['discharge_power_w'])
            (battery / 'status').write_text('Discharging')
            (battery / 'power_now').write_text('5000000')
            self.assertEqual(collector.battery_sysfs(root)[0]['discharge_power_w'], 5)
            (battery / 'power_now').write_text('500000000')
            self.assertIsNone(collector.battery_sysfs(root)[0]['discharge_power_w'])

    def test_thermal_abi_and_outlier_rejection(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            zone = root / 'class/thermal/thermal_zone0'
            zone.mkdir(parents=True)
            (zone / 'temp').write_text('42000')
            (zone / 'type').write_text('fixture')
            self.assertEqual(collector.thermal_sysfs(root)[0]['temperature_c'], 42)
            (zone / 'temp').write_text('4200000')
            self.assertEqual(collector.thermal_sysfs(root), [])

    def test_energy_does_not_bridge_missing_charging_or_large_time_gaps(self):
        state = collector.Summary(2)
        for row in (sample(0, 4), sample(2, 6), sample(4, None), sample(6, 8), sample(20, 8), sample(22, 4)):
            state.add(row)
        result = state.report()
        self.assertEqual(result['energy_intervals'], 2)
        self.assertEqual(result['energy_observed_seconds'], 4)
        self.assertEqual(result['battery_discharge_energy_joules_observed_intervals'], 22)
        self.assertIsNone(result['kv_cache_bytes'])

    def test_multiple_batteries_never_double_count_energy(self):
        state = collector.Summary(2)
        for t in (0, 2):
            row = sample(t, 5)
            row['batteries'] *= 2
            state.add(row)
        self.assertIsNone(state.report()['battery_discharge_energy_joules_observed_intervals'])

    def test_pid_reuse_keeps_separate_lifetimes_and_unknown_samples_stay_null(self):
        state = collector.Summary(2)
        state.add(sample(0, rss=100))
        state.add(sample(2, rss=120))
        state.add(sample(4, rss=300, start_ticks=2000))
        rows = state.report()['process_lifetimes']
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]['observed_rss_delta_bytes'], 20)
        self.assertEqual(rows[0]['endpoint_rss_delta_bytes_per_second'], 10)
        self.assertIsNone(rows[1]['observed_rss_delta_bytes'])
        self.assertIsNone(rows[1]['endpoint_rss_delta_bytes_per_second'])

    def test_optional_termux_never_runs_on_linux_and_preserves_unknown_units(self):
        with patch.object(collector.subprocess, 'run') as run:
            self.assertEqual(collector.termux_battery(True, False)['status'], 'DISABLED')
            run.assert_not_called()
            run.return_value.returncode = 0
            run.return_value.stdout = '{"current":123,"fixture_only":true}'
            result = collector.termux_battery(True, True, '/fixture/command')
            self.assertEqual(result['raw']['current'], 123)
            self.assertNotIn('energy_joules', result)

    def test_signal_checkpoint_resume_keeps_raw_and_rejects_tampering(self):
        with tempfile.TemporaryDirectory() as td:
            home = Path(td) / 'home'
            home.mkdir()
            out = Path(td) / 'proof'
            archive = Path(td) / 'archive'
            args = ['--installed-home', str(home), '--out', str(out), '--archive-dir', str(archive), '--sensors-only', '--duration-seconds', '1', '--sample-seconds', '.25']
            def interrupt(*args, **kwargs):
                signal.raise_signal(signal.SIGTERM)
                return sample(0)
            # Fixed identity prevents parallel source edits affecting synthetic test.
            with patch.object(collector, 'source_identity', return_value={'fixture': 'synthetic'}), patch.object(collector, 'measure', side_effect=interrupt):
                self.assertEqual(collector.main(args), 130)
            first = json.loads((out / 'summary.json').read_text())
            self.assertEqual(first['status'], 'INTERRUPTED')
            self.assertFalse(first['gates']['native_sustained_batches'])
            self.assertFalse(first['gates']['native_kv_growth_measured'])
            self.assertEqual((out / 'samples-000.jsonl').read_bytes(), (archive / 'samples-000.jsonl').read_bytes())
            resume = ['--installed-home', str(home), '--resume', str(out), '--archive-dir', str(archive), '--sensors-only', '--duration-seconds', '1', '--sample-seconds', '.25']
            with patch.object(collector, 'source_identity', return_value={'fixture': 'synthetic'}):
                self.assertEqual(collector.main(resume), 0)
                report = json.loads((out / 'summary.json').read_text())
                self.assertEqual(len(report['invocations']), 2)
                self.assertEqual(report['invocations'][0], first['invocations'][0])
                self.assertFalse(report['hardware_epoch_complete'])
                (out / 'samples-000.jsonl').write_text('tampered')
                # Completed run immutability is itself enforced before tamper check.
                report['status'] = 'INTERRUPTED'
                (out / 'summary.json').write_text(json.dumps(report))
                with self.assertRaises(SystemExit):
                    collector.main(resume)

    def test_invalid_budgets_never_start_collection(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / 'proof'
            for flag, value in (('--duration-seconds', 'nan'), ('--cycles-per-batch', '3'), ('--batches', '33'), ('--sample-seconds', '.1')):
                with self.assertRaises(SystemExit):
                    collector.main(['--installed-home', td, '--out', str(out), flag, value])
                self.assertFalse(out.exists())


if __name__ == '__main__':
    unittest.main()
