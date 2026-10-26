"""Run428 source-identity negative-control audit pure tests."""
import unittest
from scripts import run428_native_control_audit as A


def source_row(b1="same", b2="same"):
    return {"consumer_messages": [
        {"role": "user", "content": A.canonical({
            "analysts": [
                {"role": "B1_DETAIL", "summary": b1},
                {"role": "B2_GIST", "summary": b2}
            ]})}
    ]}


def sample(source_marker="same", answer="A", utility=0.5):
    source = {f: source_row(source_marker) for f in A.FIXTURES}
    tool = {f: {"consumer_messages_sha256": A.digest(
                A.canonical(source[f]["consumer_messages"])),
                "answer": answer, "score": {"utility": utility}}
            for f in A.FIXTURES}
    return source, tool


class Run428NativeControls(unittest.TestCase):
    def test_clean_same_task_negative_control(self):
        a, x = sample()
        b, y = sample()
        r = A.compare_rows(
            {"O": {(f, "b1_only"): a[f] for f in A.FIXTURES},
             "P": {(f, "b1_only"): b[f] for f in A.FIXTURES}},
            {"O": {(f, "b1_only"): x[f] for f in A.FIXTURES},
             "P": {(f, "b1_only"): y[f] for f in A.FIXTURES}},
            "P", "O", "b1_only")
        self.assertEqual(r["same_consumer_inputs"], 6)
        self.assertEqual(r["same_b1_offers"], 6)
        self.assertEqual(r["same_answers"], 6)
        self.assertEqual(r["nonzero_utility_deltas"], 0)

    def test_changed_b1_offer_and_answer_detected(self):
        a, x = sample()
        b, y = sample()
        f = A.FIXTURES[0]
        b[f] = source_row("different")
        y[f] = {"consumer_messages_sha256": A.digest(A.canonical(b[f]["consumer_messages"])),
                "answer": "B", "score": {"utility": 0.9}}
        r = A.compare_rows(
            {"O": {(k, "b1_only"): a[k] for k in A.FIXTURES},
             "P": {(k, "b1_only"): b[k] for k in A.FIXTURES}},
            {"O": {(k, "b1_only"): x[k] for k in A.FIXTURES},
             "P": {(k, "b1_only"): y[k] for k in A.FIXTURES}},
            "P", "O", "b1_only")
        self.assertEqual(r["same_consumer_inputs"], 5)
        self.assertEqual(r["same_b1_offers"], 5)
        self.assertEqual(r["same_answers"], 5)
        self.assertEqual(r["nonzero_utility_deltas"], 1)
        self.assertAlmostEqual(r["mean_utility_delta"], 0.4 / 6)

    def test_nonfinite_utility_refused(self):
        a, x = sample()
        b, y = sample(utility=float("nan"))
        with self.assertRaisesRegex(ValueError, "INVALID_UTILITY"):
            A.compare_rows(
                {"O": {(f, "b1_only"): a[f] for f in A.FIXTURES},
                 "P": {(f, "b1_only"): b[f] for f in A.FIXTURES}},
                {"O": {(f, "b1_only"): x[f] for f in A.FIXTURES},
                 "P": {(f, "b1_only"): y[f] for f in A.FIXTURES}},
                "P", "O", "b1_only")

    def test_unsafe_paths_refused(self):
        for path in ("../escape", "/root/file", "dir/../file", "dir//file",
                     "C:/evil", "dir\\evil"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                A.safe_name(path)


if __name__ == "__main__":
    unittest.main()
