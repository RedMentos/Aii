import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock
from v13 import gates
from scripts import measure_suite


class StrictGateVerdictTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.patch = mock.patch.object(gates, "APP", self.root)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.file = self.root / "evidence.json"

    def verdict(self, actual, expected, op="=="):
        self.file.write_text(json.dumps({"x": actual}))
        return gates.verdicts({"verdict": [{"file": "evidence.json", "path": "x", "op": op, "value": expected}]})

    def test_true_not_numeric_one(self):
        self.assertEqual(len(self.verdict(1, True)), 1)

    def test_false_not_numeric_zero(self):
        self.assertEqual(len(self.verdict(0, False)), 1)

    def test_exact_boolean_passes(self):
        self.assertEqual(self.verdict(True, True), [])
        self.assertEqual(self.verdict(False, False), [])

    def test_boolean_cannot_pass_numeric_threshold(self):
        self.assertEqual(len(self.verdict(True, 0.9, ">=")), 1)
        self.assertEqual(len(self.verdict(False, 0.0, "<=")), 1)

    def test_nonfinite_fails_closed(self):
        self.assertEqual(len(self.verdict(float("inf"), 0.9, ">=")), 1)
        self.assertEqual(len(self.verdict(float("nan"), 0.9, ">=")), 1)
        self.assertEqual(len(self.verdict(float("inf"), float("inf"))), 1)

    def test_finite_numeric_comparison_allows_int_float(self):
        self.assertEqual(self.verdict(1, 0.9, ">="), [])
        self.assertEqual(self.verdict(0, 0.1, "<="), [])

    def test_equality_rejects_type_coercion(self):
        self.assertEqual(len(self.verdict("1", 1)), 1)
        self.assertEqual(len(self.verdict(1, 1.0)), 1)

    def test_unknown_operator_fails(self):
        self.assertEqual(len(self.verdict(2, 1, "!=")), 1)

    def test_missing_evidence_fails(self):
        self.assertEqual(len(gates.verdicts({"verdict": [
            {"file": "missing.json", "path": "x", "op": "==", "value": True}]})), 1)


class StrictBenchmarkClassificationTests(unittest.TestCase):
    def setUp(self):
        self.b = {"implemented": True, "tests": [], "artifacts": [
            "../bench-results/phantom/native.json"], "needs": "none"}

    def test_phantom_artifact_path_not_measured(self):
        self.assertEqual(measure_suite.classify(self.b, {}), "TESTED")

    def test_existing_artifact_without_verdict_not_measured(self):
        with tempfile.TemporaryDirectory() as d:
            file = Path(d) / "native.json"
            file.write_text('{"pass":true}')
            self.assertEqual(measure_suite.classify(self.b | {"artifacts": [str(file)]}, {}), "TESTED")

    def test_explicit_verdict_requires_real_passing_value(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "proof.json").write_text('{"passed":true}')
            verdict = [{"file": "proof.json", "path": "passed", "op": "==", "value": True}]
            with mock.patch.object(gates, "APP", root):
                self.assertEqual(measure_suite.classify(self.b | {"verdict": verdict}, {}), "MEASURED")
                (root / "proof.json").write_text('{"passed":1}')
                self.assertEqual(measure_suite.classify(self.b | {"verdict": verdict}, {}), "MEASURED_FAILING")

    def test_existing_precedence_unchanged(self):
        self.assertEqual(measure_suite.classify(self.b | {"implemented": False}, {}), "NOT_IMPLEMENTED")
        self.assertEqual(measure_suite.classify(self.b | {"needs": "redmi"}, {}), "NEEDS_REDMI")
        self.assertEqual(measure_suite.classify(self.b | {"tests": ["t"]}, {"t": {"ok": False}}), "TEST_FAIL")


if __name__ == "__main__":
    unittest.main()
