"""World-JEPA SHADOW reader/refit synchronization; software-only, no native learning."""
import threading
import unittest
from unittest.mock import patch

import numpy as np

from v13 import world_jepa as wj
from v13 import world_jepa_shadow_checkpoint as checkpoint


class WorldJEPAReaderSnapshot(unittest.TestCase):
    def setUp(self):
        self.X = np.array([[0., 1.], [1., 0.], [.3, .7], [.7, .3]])
        self.A = np.array([[1., 0.], [0., 1.], [1., 0.], [0., 1.]])
        self.X2 = self.X[:, ::-1].copy()

    def fitted(self):
        return wj.WorldJEPA(seed=11, ensemble=1).fit(
            self.X, self.A, self.X2, steps=0)

    def _interleave(self, reader, block):
        entered = threading.Event()
        release = threading.Event()
        writer_started = threading.Event()
        writer_done = threading.Event()
        errors = []
        model = self.fitted()
        old_mu = model.mu.copy()

        def blocked(*args, **kwargs):
            entered.set()
            if not release.wait(5):
                raise TimeoutError("reader barrier was not released")
            return block(*args, **kwargs)

        def read_job():
            try:
                reader(model, blocked)
            except BaseException as exc:
                errors.append(("reader", repr(exc)))

        def write_job():
            try:
                writer_started.set()
                model.fit(self.X + 7, self.A, self.X2 + 7, steps=0)
            except BaseException as exc:
                errors.append(("writer", repr(exc)))
            finally:
                writer_done.set()

        t1 = threading.Thread(target=read_job, name="world-reader", daemon=True)
        t2 = threading.Thread(target=write_job, name="world-writer", daemon=True)
        try:
            t1.start()
            self.assertTrue(entered.wait(3), "reader never reached protected read")
            t2.start()
            self.assertTrue(writer_started.wait(3), "writer never started")
            # Training may happen outside the lock, but the complete refit
            # cannot become visible while the reader is inside its read.
            self.assertFalse(writer_done.wait(.2), "refit published during read")
        finally:
            release.set()
            t1.join(6)
            if t2.ident is not None:
                t2.join(6)
        self.assertFalse(t1.is_alive())
        self.assertFalse(t2.is_alive())
        self.assertEqual(errors, [])
        np.testing.assert_allclose(model.mu, old_mu + 7, rtol=0, atol=1e-12)

    def test_confidence_read_is_not_mixed_with_refit(self):
        original = wj.encode

        def reader(model, blocked):
            def pause_first(enc, x):
                if threading.current_thread().name == "world-reader":
                    return blocked(enc, x)
                return original(enc, x)

            with patch.object(wj, "encode", side_effect=pause_first):
                conf, labels = model.confidence(self.X, self.A)
                self.assertEqual(len(conf), 4)
                self.assertEqual(len(labels), 4)

        self._interleave(reader, original)

    def test_checkpoint_export_is_not_mixed_with_refit(self):
        original = checkpoint._pin
        source = "a" * 64

        def reader(model, blocked):
            def pause_pin(value):
                if threading.current_thread().name == "world-reader":
                    return blocked(value)
                return original(value)

            with patch.object(checkpoint, "_pin", side_effect=pause_pin):
                meta, arrays = checkpoint._extract(model, source)
                self.assertEqual(meta["source_sha256"], source)
                np.testing.assert_array_equal(arrays["mu"], self.X.mean(0))

        self._interleave(reader, original)


if __name__ == "__main__":
    unittest.main()
