"""Seed61 software-only adversarial controls. Stubbed imports are not native proof."""
import importlib.util
from pathlib import Path
import re
import sys
import tempfile
import types
import unittest
from unittest.mock import patch


def load_candidate():
    names = ["v13", "v13.cognition", "v13.config", "v13.models", "v13.proofs",
             "v13.runtime", "scripts", "scripts.c2_body_controlled_utility_seed53_20261030"]
    prior = {n: sys.modules.get(n) for n in names}
    def put(name, **attrs):
        mod = types.ModuleType(name)
        for k, v in attrs.items():
            setattr(mod, k, v)
        sys.modules[name] = mod
    put("v13")
    put("v13.cognition", scaffold_route=lambda s: (
        "both" if re.search(r"vergleich|compare|abwäg|trade.?off", s.lower()) else
        "detail" if re.search(r"code|python|berechn|calculate|budget|mathe|debug|fehler|\d\s*[+*/=]", s.lower()) else
        "gist" if re.search(r"zusammenfass|summary|summarize|überblick|plan", s.lower()) else "simple"))
    put("v13.config", initialize=lambda _: {}, save_config=lambda *a: None)
    put("v13.models", ModelManager=object, model_key=lambda *a: "body")
    put("v13.proofs", audit_event=lambda *a: {})
    put("v13.runtime", Runtime=object)
    put("scripts")
    put("scripts.c2_body_controlled_utility_seed53_20261030",
        score_pair=lambda *a: {}, valid_control_evidence=lambda *a, **k: True,
        BODY_MODEL="body.gguf", GIST_MODEL="gist.gguf", LANGUAGE_MODEL="language.gguf")
    path = Path(__file__).resolve().parents[1] / "scripts" / "c2_isolated_postclose_seed61_20261030.py"
    spec = importlib.util.spec_from_file_location("seed61_isolated_test_subject", path)
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    finally:
        for n, value in prior.items():
            if value is None:
                sys.modules.pop(n, None)
            else:
                sys.modules[n] = value
    return mod


m = load_candidate()


def sample(route="detail", source="OPERATOR_ROUTE_OVERRIDE", role="B1_DETAIL", offers=()):
    info = {"source": source}
    if source != "OPERATOR_ROUTE_OVERRIDE":
        info["native_control_metrics"] = {"memory": {"pid": 123}}
    return {"checks": {"source_refs_valid": True, "output_valid": True},
            "source_errors": [], "offers": [{"role": x, "native_metrics": {"memory": {"pid": 17 if x == "B1_DETAIL" else 18}}} for x in offers],
            "output": "source-bound native answer",
            "output_metadata": {"route": info, "c2_packet": {"route": route},
                                "runner": {"role": role, "actual_model": m.role_model(role, False), "memory": {"pid": 18 if role == "B2_GIST" else 17}},
                                "model_generated": True}}


def release(role, reaped=True, pid=None):
    return {"role": role, "process_reaped": reaped, "before": {"pid": (18 if role == "B2_GIST" else 17) if pid is None else pid}}


class IsolatedPostcloseSoftware(unittest.TestCase):
    def test_preregistered_fixtures_and_simple_scaffold(self):
        self.assertEqual(m.SEED, 61)
        self.assertTrue(m.validate_fixtures())
        self.assertEqual(m.fixture_hash(), m.FIXTURE_SHA256)
        self.assertEqual(sum(map(len, m.ARM_ORDER)), 24)
        self.assertEqual(len({f['project'] for f in m.FIXTURES}), 4)

    def test_source_leak_or_scaffold_change_rejected(self):
        f = dict(m.FIXTURES[0]); f['b_cost'] = f['budget'] - f['a_cost']
        with patch.object(m, 'FIXTURES', (f, *m.FIXTURES[1:])):
            with patch.object(m, 'FIXTURE_SHA256', m.fixture_hash()):
                with self.assertRaisesRegex(ValueError, 'ANSWER_LEAKED_IN_PROMPT'):
                    m.validate_fixtures()
        f = dict(m.FIXTURES[0]); f['project'] = 'Compare'
        with patch.object(m, 'FIXTURES', (f, *m.FIXTURES[1:])):
            with patch.object(m, 'FIXTURE_SHA256', m.fixture_hash()):
                with self.assertRaisesRegex(ValueError, 'SCAFFOLD_NOT_SIMPLE'):
                    m.validate_fixtures()

    def test_b1_final_only_accepts_postclose_release(self):
        a = sample()
        f = m.row_evidence(a, 'B_B1_ONLY', [], [release('B1_DETAIL')])
        self.assertTrue(f['valid_native'])
        self.assertTrue(f['observer_isolated'] and f['postclose_release_valid'])
        self.assertEqual(f['preclose_release_roles'], [])
        self.assertEqual(f['postclose_release_roles'], ['B1_DETAIL'])
        self.assertFalse(m.row_evidence(a, 'B_B1_ONLY', [], [])['valid_native'])

    def test_b2_final_only_postclose_release(self):
        a = sample('gist', role='B2_GIST')
        f = m.row_evidence(a, 'C_B2_ONLY', [], [release('B2_GIST')])
        self.assertTrue(f['valid_native'])
        self.assertEqual(f['runner_model'], 'gist.gguf')
        a['output_metadata']['runner']['actual_model'] = 'body.gguf'
        self.assertFalse(m.row_evidence(a, 'C_B2_ONLY', [], [release('B2_GIST')])['valid_native'])

    def test_background_observer_contamination_rejected(self):
        a = sample(offers=('B1_DETAIL', 'B2_GIST'))
        f = m.row_evidence(a, 'B_B1_ONLY', [release('B1_DETAIL')],
                           [release('B1_DETAIL'), release('B2_GIST')])
        self.assertFalse(f['valid_native'])
        self.assertFalse(f['observer_isolated'])
        self.assertFalse(f['postclose_release_valid'])

    def test_forged_role_receipt_wrong_pid_rejected(self):
        a = sample()
        self.assertFalse(m.row_evidence(a, 'B_B1_ONLY', [],
                         [release('B1_DETAIL', pid=999)])['valid_native'])
        self.assertTrue(m.row_evidence(a, 'B_B1_ONLY', [],
                        [release('B1_DETAIL')])['final_pid_reaped'])

    def test_unreaped_final_process_rejected(self):
        a = sample()
        f = m.row_evidence(a, 'B_B1_ONLY', [], [release('B1_DETAIL', False)])
        self.assertFalse(f['valid_native'])
        self.assertFalse(f['postclose_release_valid'])

    def test_both_allows_multiple_releases_same_expected_role(self):
        a = sample('both', role='B1_DETAIL', offers=('B1_DETAIL', 'B2_GIST'))
        pre = [release('B1_DETAIL'), release('B2_GIST')]
        post = pre + [release('B1_DETAIL')]
        f = m.row_evidence(a, 'D_DISTINCT_BOTH', pre, post)
        self.assertTrue(f['valid_native'])
        self.assertFalse(m.row_evidence(a, 'D_DISTINCT_BOTH', pre, pre[:-1])['valid_native'])

    def test_native_gist_selected_and_reaped_after_close(self):
        a = sample('gist', source='NATIVE_C2_ADVISORY', role='B2_GIST', offers=('B2_GIST',))
        kw = dict(native_context={'query_ref': {'source_id': 'synthetic'}},
                  native_alive=True, native_reaped=True, native_pid=123,
                  source_exact=True, session='s', event_id='e', source_text='synthetic')
        f = m.row_evidence(a, 'F_NATIVE_AUTO', [], [release('B2_GIST')], **kw)
        self.assertTrue(f['valid_native'])
        self.assertTrue(f['native_c2_invocation'] and f['native_c2_selected'])
        self.assertFalse(m.row_evidence(a, 'F_NATIVE_AUTO', [], [], **kw)['valid_native'])
        self.assertFalse(m.row_evidence(a, 'F_NATIVE_AUTO', [], [release('B2_GIST')],
                                        **{**kw, 'native_pid': 999})['valid_native'])

    def test_missing_source_errors_rejected(self):
        a = sample(); a.pop('source_errors')
        self.assertFalse(m.row_evidence(a, 'B_B1_ONLY', [], [release('B1_DETAIL')])['valid_native'])

    def test_signal_no_gate_and_invalid_totals(self):
        t = {k: 0 for k in m.ARMS}; t['D_DISTINCT_BOTH'] = 3
        self.assertTrue(m.pilot_signals(t, True, 0)['distinct_vs_single_shared'])
        self.assertFalse(m.pilot_signals(t, False, 0)['distinct_vs_single_shared'])
        t['F_NATIVE_AUTO'] = 5
        self.assertTrue(m.pilot_signals(t, True, 1)['native_auto_vs_forced'])
        self.assertFalse(m.pilot_signals({**t, 'F_NATIVE_AUTO': True}, True, 1)['native_auto_vs_forced'])

    def test_native_workflow_raw_validator_heredoc_and_python_syntax(self):
        import ast
        workflow = (Path(__file__).resolve().parents[3] / '.github' / 'workflows' /
                    'v13-c2-isolated-seed61-native-20261030.yml')
        if not workflow.exists():
            self.skipTest('GitHub workflow not in isolated source fixture')
        content = workflow.read_text()
        self.assertEqual(content.count("<<'PY'\n"), 1)
        after = content.split("<<'PY'\n", 1)[1]
        self.assertIn('\n          PY\n', after, 'Shell heredoc must close at run-block indentation')
        block = after.split('\n          PY\n', 1)[0]
        lines = block.splitlines()
        self.assertTrue(all(line.startswith('          ') for line in lines))
        ast.parse('\n'.join(line[10:] for line in lines))

    def test_existing_output_refused(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(FileExistsError):
                m.run(Path(d), Path(d))


if __name__ == '__main__':
    unittest.main()