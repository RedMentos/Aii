"""World-JEPA SHADOW overlapping-fit ordering; deterministic software barriers only."""
import threading
import unittest
from unittest.mock import patch

import numpy as np

from v13 import world_jepa as wj


class WorldJEPAConcurrentFitOrder(unittest.TestCase):
    def setUp(self):
        self.x = np.array([[0., 1.], [1., 0.], [.3, .7], [.7, .3]])
        self.a = np.array([[1., 0.], [0., 1.], [1., 0.], [0., 1.]])
        self.x2 = self.x[:, ::-1].copy()

    def fitted(self):
        return wj.WorldJEPA(seed=11, ensemble=1).fit(
            self.x, self.a, self.x2, steps=0)

    def interleave(self, *, distinct_instances=False, newer_fails=False):
        model = self.fitted()
        newer = self.fitted() if distinct_instances else model
        committed_mu = model.mu.copy()
        old_started = threading.Event()
        release_old = threading.Event()
        errors = []
        original_init = wj._init
        original_grads = wj.loss_grads

        def gated_init(*args, **kwargs):
            if threading.current_thread().name == "older-fit":
                old_started.set()
                if not release_old.wait(5):
                    raise TimeoutError("Older fit was not released")
            return original_init(*args, **kwargs)

        def gated_grads(*args, **kwargs):
            if newer_fails and threading.current_thread().name == "newer-fit":
                raise RuntimeError("Injected newer training failure")
            return original_grads(*args, **kwargs)

        def older_job():
            try:
                model.fit(self.x + 1, self.a, self.x2 + 1, steps=0)
            except BaseException as exc:
                errors.append(("older", exc))

        def newer_job():
            try:
                newer.fit(self.x + 7, self.a, self.x2 + 7,
                          steps=1 if newer_fails else 0)
            except BaseException as exc:
                errors.append(("newer", exc))

        old_thread = threading.Thread(target=older_job, name="older-fit", daemon=True)
        new_thread = threading.Thread(target=newer_job, name="newer-fit", daemon=True)
        with patch.object(wj, "_init", side_effect=gated_init), \
             patch.object(wj, "loss_grads", side_effect=gated_grads):
            try:
                old_thread.start()
                self.assertTrue(old_started.wait(3), "Older fit did not enter training")
                new_thread.start()
                new_thread.join(5)
                self.assertFalse(new_thread.is_alive(), "Newer fit did not finish")
            finally:
                release_old.set()
                old_thread.join(5)
                new_thread.join(5)
        self.assertFalse(old_thread.is_alive(), "Older fit leaked a thread")
        self.assertFalse(new_thread.is_alive(), "Newer fit leaked a thread")
        return model, newer, committed_mu, errors

    def test_older_completion_cannot_overwrite_newer_committed_fit(self):
        model, newer, _, errors = self.interleave()
        self.assertIs(model, newer)
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0][0], "older")
        self.assertIsInstance(errors[0][1], RuntimeError)
        np.testing.assert_array_equal(model.mu, self.x.mean(0) + 7)

    def test_different_instances_have_independent_fit_generations(self):
        model, newer, _, errors = self.interleave(distinct_instances=True)
        self.assertEqual(errors, [])
        np.testing.assert_array_equal(model.mu, self.x.mean(0) + 1)
        np.testing.assert_array_equal(newer.mu, self.x.mean(0) + 7)

    def test_failed_newer_fit_preserves_prior_commit_and_vetoes_older(self):
        model, newer, committed_mu, errors = self.interleave(newer_fails=True)
        self.assertIs(model, newer)
        self.assertEqual({label for label, _ in errors}, {"older", "newer"})
        self.assertTrue(all(isinstance(exc, RuntimeError) for _, exc in errors))
        np.testing.assert_array_equal(model.mu, committed_mu)


if __name__ == "__main__":
    unittest.main()
