"""Synthetic contract checks for source-bound T8 evaluation."""
import unittest
from unittest.mock import patch
from v13 import online_world_store_evaluation as subject


class Store:
    def rows(self, *args, **kwargs):
        raise AssertionError("Only the producer should query SQL")


def records(n):
    return [{"action_id": "action-%03d" % i, "s": [0., 0., 0., 1.],
             "a": "simple", "y": [0.1, 1., 0.1]} for i in range(n)]


class SourceBoundTests(unittest.TestCase):
    def test_rejects_non_store_and_bad_limit(self):
        with self.assertRaises(ValueError):
            subject.evaluate_store_disjoint(None)
        with self.assertRaises(ValueError):
            subject.evaluate_store_disjoint(Store(), limit=True)

    def test_rejects_duplicate_source_ids(self):
        rows = records(16)
        rows[-1]["action_id"] = rows[0]["action_id"]
        with patch.object(subject.world_model, "transitions", return_value=rows):
            with self.assertRaises(ValueError):
                subject.evaluate_store_retention(Store())

    def test_only_admitted_producer_reaches_retention(self):
        rows = records(16)
        with patch.object(subject.world_model, "transitions", return_value=rows) as producer:
            with patch.object(subject, "evaluate_retention", return_value={"status": "TEST"}) as evaluator:
                out = subject.evaluate_store_retention(Store(), limit=16)
        producer.assert_called_once()
        self.assertEqual(producer.call_args.kwargs["limit"], 16)
        cohorts = evaluator.call_args.args
        self.assertEqual([len(x) for x in cohorts], [4, 4, 4, 4])
        self.assertEqual(len({r["action_id"] for cohort in cohorts for r in cohort}), 16)
        self.assertEqual(out["producer"], "world_model.transitions")

    def test_short_stream_never_trains(self):
        with patch.object(subject.world_model, "transitions", return_value=records(5)):
            self.assertEqual(subject.evaluate_store_retention(Store())["status"], "INSUFFICIENT_COMMITTED_T8")

    def test_disjoint_split_producer_bound(self):
        with patch.object(subject.world_model, "transitions", return_value=records(64)):
            with patch.object(subject, "evaluate_disjoint", return_value={"status": "TEST"}) as evaluator:
                result = subject.evaluate_store_disjoint(Store())
        train, held = evaluator.call_args.args
        self.assertTrue(train and held)
        self.assertFalse(set(r["action_id"] for r in train) & set(r["action_id"] for r in held))
        self.assertEqual(result["evidence"], "OFFLINE_STORE_BOUND_NOT_ANDROID")


if __name__ == "__main__":
    unittest.main()
