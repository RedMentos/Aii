"""Run372 RED-first: punctuation and wrong-typed JSON answers must abstain."""
import tempfile
import unittest
from pathlib import Path

from v13.runtime import Runtime
from v13.agi import hub
from v13.agi import solver as sv


class FakeRunner:
    def __init__(self, text, prob=0.99):
        self.text = text
        self.last_metrics = {"token_confidence": {"field_min_prob": prob}}

    def generate(self, *args, **kwargs):
        yield self.text


class FakePool:
    def __init__(self, runner):
        self.runner = runner

    def get(self, role):
        return self.runner


class InvalidAnswerRun372(unittest.TestCase):
    def test_structurally_empty_answers_abstain(self):
        for raw in (
            '{"answer": ","}',
            '{"answer": "  !?  "}',
            '{"answer": "★"}',
            '{"answer": ",',
            ",",
            "?!",
        ):
            with self.subTest(raw=raw):
                self.assertEqual(sv.extract(raw), "")

    def test_non_string_json_answer_field_cannot_be_coerced(self):
        for raw in ('{"answer": null}', '{"answer": true}', '{"answer": 42}', '{"answer": ["42"]}'):
            with self.subTest(raw=raw):
                self.assertEqual(sv.extract(raw), "")

    def test_valid_answers_and_legacy_truncated_string_still_work(self):
        for raw, expected in (
            ('{"answer":"42"}', "42"),
            ('{"answer":" -4 "}', "-4"),
            ('{"answer":"apple"}', "apple"),
            ('{"answer":"Δ"}', "Δ"),
            ('{"answer":"elppa', "elppa"),
            ("42\nbecause", "42"),
        ):
            with self.subTest(raw=raw):
                self.assertEqual(sv.extract(raw), expected)

    def test_invalid_answer_zeroes_even_high_native_confidence(self):
        bad = sv.BodySolver(FakePool(FakeRunner('{"answer":","}')), ("C3_LANGUAGE",))
        result = bad.ask("C3_LANGUAGE", {"prompt": "Compute 2 + 2"})
        self.assertEqual(result["answer"], "")
        self.assertEqual(result["confidence"], 0.0)
        self.assertEqual(result["confidence_source"], "invalid_answer")
        good = sv.BodySolver(FakePool(FakeRunner('{"answer":"4"}', 0.8)), ("C3_LANGUAGE",))
        result = good.ask("C3_LANGUAGE", {"prompt": "Compute 2 + 2"})
        self.assertEqual((result["answer"], result["confidence"]), ("4", 0.8))
        self.assertEqual(result["confidence_source"], "field_min_prob")

    def test_actual_sqlite_generality_run_keeps_invalid_answer_uncertain(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = Runtime(Path(tmp))
            try:
                r.sleep.cycle.set_policy("enabled", "off")
                growth = hub(r)
                solver = sv.BodySolver(FakePool(FakeRunner('{"answer":","}')), ("C3_LANGUAGE",))
                before = r.store.one("SELECT COUNT(*) n FROM events")["n"]
                out = growth.eval.run(lambda view: solver.ask("C3_LANGUAGE", view), solver_name="run372_invalid")
                self.assertEqual(out["status"], "DONE")
                self.assertEqual(out["summary"]["overall"], 0.0)
                self.assertEqual(out["summary"]["calibration"]["ece"], 0.0)
                self.assertEqual(r.store.one("SELECT COUNT(*) n FROM events")["n"], before)
            finally:
                r.close()


if __name__ == "__main__":
    unittest.main()
