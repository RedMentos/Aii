"""Regression: real native model-launch flags change with Redmi performance knobs.

No native model is started in CI. A separate real Android cold/warm benchmark
must measure latency, battery pressure and model quality before changing defaults.
"""
from pathlib import Path
import tempfile
import unittest

from v13.config import DEFAULTS, validate
from v13.runners import LlamaRunner


class NativeBatchKnobTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        (self.home / "bin").mkdir()

    def test_native_batch_is_explicit_and_default_preserves_baseline(self):
        self.assertEqual(DEFAULTS["native_batch_tokens"], 128)
        self.assertEqual(validate(dict(DEFAULTS))["native_batch_tokens"], 128)
        for n in (64, 128, 256, 384, 512):
            cfg = dict(DEFAULTS, native_batch_tokens=n)
            self.assertEqual(validate(cfg)["native_batch_tokens"], n)
        for n in (63, 513, -1, True, 256.5):
            with self.assertRaises(ValueError):
                validate(dict(DEFAULTS, native_batch_tokens=n))

    def test_warm_runner_stamp_changes_when_launch_flags_change(self):
        cfg = dict(DEFAULTS)
        runner = LlamaRunner(self.home, "B1_DETAIL", self.home / "models/body.gguf", cfg)
        before = runner._lifecycle_stamp()
        self.assertEqual(before, runner._lifecycle_stamp())
        for key, value in [
            ("threads", 6),
            ("context_tokens", 4096),
            ("native_batch_tokens", 256),
            ("native_cache_ram_mb", 256),
            ("native_ctx_checkpoints", 8),
        ]:
            old = cfg[key]
            cfg[key] = value
            self.assertNotEqual(before, runner._lifecycle_stamp(), key)
            cfg[key] = old
            self.assertEqual(before, runner._lifecycle_stamp(), key)

    def test_runner_keeps_existing_source_and_role_identity(self):
        cfg = dict(DEFAULTS, native_batch_tokens=256)
        a = LlamaRunner(self.home, "C3_LANGUAGE", self.home / "models/language.gguf", cfg)
        b = LlamaRunner(self.home, "B2_GIST", self.home / "models/gist.gguf", cfg)
        self.assertNotEqual(a._lifecycle_stamp(), b._lifecycle_stamp())
        self.assertEqual(a.role, "C3_LANGUAGE")
        self.assertEqual(b.role, "B2_GIST")


if __name__ == "__main__":
    unittest.main()
