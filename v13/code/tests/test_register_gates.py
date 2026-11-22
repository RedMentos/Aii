import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock
from v13.common import APP
from v13 import gates, register
from v13.runtime import Runtime

sys.path.insert(0, str(APP/'scripts'))
import build_knob_register  # noqa: E402
import measure_suite  # noqa: E402

class Register(unittest.TestCase):
    def test_parser_reads_knobs_tags_and_age0_bars(self):
        text = '\n'.join(['## 51. Boundary', 'A1.context_shift_gain = 0.35', 'SKILL.shadow_cycles = 10 [BOOT]', 'A1.segment_size [BOOT/TUNE]',
                          'not.a.knob(x) = 1', '## 78. Age 0', 'ATTENTION', '  focus gain      ████░░  0.40', '## 79. Later', 'Z9.ignored = 1'])
        ks = {k['id']: k for k in build_knob_register.parse(text)}
        self.assertEqual(ks['A1.context_shift_gain']['value'], .35); self.assertEqual(ks['SKILL.shadow_cycles']['tags'], ['BOOT'])
        self.assertIsNone(ks['A1.segment_size']['value']); self.assertEqual(ks['A1.segment_size']['tags'], ['BOOT', 'TUNE'])
        self.assertEqual(ks['AGE0.ATTENTION.focus_gain']['value'], .4); self.assertNotIn('Z9.ignored', ks)

    def test_map_targets_exist_and_match_blueprint(self):
        ids = {k['id'] for k in register.blueprint()['knobs']}
        for kid, loc in register.mapping().items():
            self.assertIn(kid, ids); register.resolve(loc)
        s = register.summary()
        self.assertEqual((s['drift'], s['map_broken']), (0, 0)); self.assertGreaterEqual(s['match'], 60)
        self.assertEqual(s['match']+s['drift']+s['documented_deviation']+s['declared_only']+s['map_broken'], s['blueprint_knobs'])

    def test_kinds_never_infer_probability_and_drift_is_reported(self):
        rows = [r for r in register.entries() if r['source'] == 'BLUEPRINT']
        self.assertFalse([r for r in rows if r['kind_inferred'] and r['kind'] == 'PROBABILITY'])
        self.assertEqual(register.kind_of({'id': 'X.cut_threshold', 'value': .3}), ('THRESHOLD', False))
        kid, loc = next(iter(register.mapping().items()))
        real = register.resolve
        with mock.patch.object(register, 'resolve', side_effect=lambda l: 123.0 if l == loc else real(l)):
            s = register.summary()
        self.assertEqual([d['id'] for d in s['drift_list']], [kid])

    def test_paths_cover_learnable_components(self):
        ps = register.paths(); self.assertTrue(ps)
        self.assertTrue(all(p['base_merge_authority'] == 0 for p in ps))

class Gates(unittest.TestCase):
    def test_graph_is_acyclic_and_deps_known(self):
        sp = gates.spec(); ev = gates.evaluate()
        for g, v in sp['gates'].items():
            for d in v['deps']: self.assertIn(d, sp['gates'])
        self.assertEqual(set(ev), set(sp['gates']))
        self.assertTrue(set(v['status'] for v in ev.values()) <= {'GREEN', 'BLOCKED_BY_DEP', 'EVIDENCE_NOT_PASSING', 'PARTIAL', 'OPEN'})

    def _fake(self, gs):
        base = gates.spec(); return mock.patch.object(gates, 'spec', return_value=base | {'gates': gs})

    def _app(self, app):return mock.patch.object(gates, 'APP', app)

    def test_mocks_never_count_as_real_data_and_verdicts_bind(self):
        full = {'code': ['v13/gates.py'], 'test': ['tests/test_register_gates.py'], 'persistence': None, 'telemetry': None, 'ablation': None,
                'limitations': ['docs/MEASUREMENT_SUITE.md'], 'title': 't'}
        with tempfile.TemporaryDirectory() as d:
            app = Path(d)/'code'
            for f in ('v13/gates.py', 'tests/test_register_gates.py', 'docs/MEASUREMENT_SUITE.md'): (app/f).parent.mkdir(parents=True, exist_ok=True); (app/f).write_text('')
            res = Path(d)/'bench-results/run/r.json'; res.parent.mkdir(parents=True); res.write_text(json.dumps({'a': {'ok': False}}))
            rel = '../bench-results/run/r.json'
            gs = {'A': full | {'deps': [], 'real_data': [rel]},
                  'B': full | {'deps': ['A'], 'real_data': ['tests/test_register_gates.py']},
                  'C': full | {'deps': ['A'], 'real_data': [rel], 'verdict': [{'file': rel, 'path': 'a.ok', 'op': '==', 'value': True}]},
                  'D': full | {'deps': ['B'], 'real_data': [rel]}}
            with self._fake(gs), self._app(app): ev = gates.evaluate()
            self.assertEqual(ev['A']['status'], 'GREEN'); self.assertEqual(ev['B']['status'], 'PARTIAL')
            self.assertEqual(ev['C']['status'], 'EVIDENCE_NOT_PASSING'); self.assertEqual(ev['D']['status'], 'BLOCKED_BY_DEP')
            self.assertEqual(ev['C']['verdict_failures'][0]['actual'], False)
            with self._fake({'X': full | {'deps': ['Y'], 'real_data': [rel]}, 'Y': full | {'deps': ['X'], 'real_data': [rel]}}), self._app(app):
                with self.assertRaises(ValueError): gates.evaluate()

class Suite(unittest.TestCase):
    def test_benchmark_map_points_at_real_tests_and_files(self):
        sp = json.loads((APP/'specs/benchmarks.json').read_text())
        self.assertEqual(len(sp['benchmarks']), 35); self.assertEqual(len(sp['ablations']), 11)
        for b in sp['benchmarks']:
            for t in b['tests']: self.assertTrue((APP/'tests'/(t+'.py')).exists(), t)
            if b['implemented']: self.assertTrue(b['tests'] or b['artifacts'], b['id'])
        for x in sp['ablations']: self.assertTrue(set(x['controls_available']) <= set(x['controls']), x['hypothesis'])

    def test_classify_never_promotes(self):
        ok = {'t': {'ok': True}}; bad = {'t': {'ok': False}}
        b = {'implemented': True, 'tests': ['t'], 'artifacts': [], 'needs': 'none'}
        self.assertEqual(measure_suite.classify(b | {'implemented': False}, ok), 'NOT_IMPLEMENTED')
        self.assertEqual(measure_suite.classify(b, bad), 'TEST_FAIL'); self.assertEqual(measure_suite.classify(b, ok), 'TESTED')
        self.assertEqual(measure_suite.classify(b | {'needs': 'redmi'}, ok), 'NEEDS_REDMI')
        self.assertEqual(measure_suite.classify(b | {'verdict': [{'file': 'missing.json', 'path': 'x', 'op': '==', 'value': 1}]}, ok), 'MEASURED_FAILING')

class Operator(unittest.TestCase):
    def test_register_and_gates_commands(self):
        with tempfile.TemporaryDirectory() as d:
            r = Runtime(Path(d)); r.sleep.cycle.set_policy('enabled', 'off')
            try:
                self.assertIn('coverage', register.operator_command(r, []))
                self.assertTrue(register.operator_command(r, ['A1']))
                self.assertIn('counts', gates.operator_command(r, ['summary']))
                self.assertIn('status', gates.operator_command(r, ['G0']))
                for cmd, args in ((register, ['a b']), (gates, ['nope'])):
                    with self.assertRaises(ValueError): cmd.operator_command(r, args)
                from v13.operator import Operator as Op
                self.assertIn('coverage', Op(r).run(':register'))
                self.assertIn('counts', Op(r).run(':gates'))
            finally: r.close()

if __name__ == '__main__':
    unittest.main()
