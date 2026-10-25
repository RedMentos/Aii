"""Run368: AG12 unseen tasks must not enter distillation as wrapped text.

Real Runtime/Store, deterministic registered suite, local fake teacher only.
No model, network or changed holdout seed/hash.
"""
import tempfile
import unittest
from pathlib import Path

from v13.runtime import Runtime
from v13.agi import hub


class EmbeddedHoldoutRun368(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.r = Runtime(Path(self.tmp.name))
        self.r.sleep.cycle.set_policy("enabled", "off")
        self.g = hub(self.r)
        self.unseen = next(i for i in self.g.eval.suite["items"] if i["split"] == "unseen" and i["family"] == "arith_mul")
        self.seen = next(i for i in self.g.eval.suite["items"] if i["split"] == "seen")

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def test_wrapped_holdout_cannot_bypass_exact_prompt_guard(self):
        prompt = self.unseen["prompt"]
        for candidate in (
            "User asks:\n" + prompt + "\nAssistant should explain the answer.",
            "Instruction: " + prompt.upper() + "  \n Answer follows.",
            "Training pair: {question: '" + prompt + "', answer: '" + self.unseen["answer"] + "'}",
        ):
            with self.subTest(candidate=candidate):
                with self.assertRaises(ValueError):
                    self.g.eval.guard_training([candidate])
        with self.assertRaises(ValueError):
            self.g.eval.guard_training([prompt])
        self.assertTrue(self.g.eval.guard_training([self.seen["prompt"], "Write a short poem about numbers."]))

    def _teacher_trace(self, answer="safe", reasoning=None, rejected=None):
        teacher = self.g.teacher
        teacher.register("run368_fake_local", lambda prompt: {
            "answer": answer,
            "reasoning": reasoning or "",
            "model": "local-test-double",
        }, kind="local")
        rid = teacher.request("Ordinary safe prompt unrelated to the evaluation suite", own_answer=rejected)
        teacher.fulfil(rid, "run368_fake_local")
        return teacher

    def test_teacher_answer_field_cannot_launder_holdout(self):
        teacher = self._teacher_trace(answer="Quoted task: " + self.unseen["prompt"])
        with self.assertRaises(ValueError):
            teacher.dataset()

    def test_teacher_reasoning_field_cannot_launder_holdout(self):
        teacher = self._teacher_trace(answer="safe answer", reasoning="Worked example: " + self.unseen["prompt"])
        with self.assertRaises(ValueError):
            teacher.dataset()

    def test_teacher_rejected_field_cannot_launder_holdout(self):
        teacher = self._teacher_trace(answer="safe answer", rejected="Earlier guess for " + self.unseen["prompt"])
        with self.assertRaises(ValueError):
            teacher.dataset()

    def test_safe_teacher_trace_remains_usable(self):
        teacher = self._teacher_trace(answer="A grounded safe reference", reasoning="Simple safe explanation", rejected="old safe guess")
        dataset = teacher.dataset()
        self.assertEqual(len(dataset), 1)
        self.assertEqual(dataset[0]["authority"], "REFERENCE_NOT_FACT")
        self.assertEqual(dataset[0]["target"], "A grounded safe reference")


if __name__ == "__main__":
    unittest.main()
