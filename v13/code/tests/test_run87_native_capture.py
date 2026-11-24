"""Run87 native wrapper SOFTWARE MOCK tests; no model is loaded."""
import unittest

try:
    from scripts import run87_b1b2_budget_native as native
    from scripts import jef_b1b2_budget_fixture_877 as f
    from v13.common import dumps
except ImportError:
    native = f = dumps = None


class FakeRunner:
    last_metrics = {"status": "FINAL", "actual_model": "FAKE_SOFTWARE_ONLY"}
    def __init__(self):
        self.calls = []
    def generate(self, messages, *args, **kwargs):
        self.calls.append((messages, args, kwargs))
        return iter(['{"summary":"synthetic","quotes":[],"uncertainty":"none","needs_reentry":false}'])


@unittest.skipUnless(native is not None, "full isolated runtime dependencies required")
class Run87NativeCaptureSoftwareTests(unittest.TestCase):
    def test_01_capture_exact_native_schema_and_budget(self):
        real = FakeRunner();captures = {}
        wrapped = native.CapturedNativeBody(real, captures, "B1_DETAIL:current")
        messages = [{"role": "system", "content": "test"},
                    {"role": "user", "content": "synthetic source"}]
        schema = {"properties": {"summary": {"maxLength": 48}}}
        output = "".join(wrapped.generate(messages, object(), 100.0, 96, schema))
        self.assertIn('"summary":"synthetic"', output)
        self.assertEqual(len(real.calls), 1)
        self.assertEqual(real.calls[0][0], messages)
        self.assertEqual(real.calls[0][1][2:], (96, schema))
        capture = captures["B1_DETAIL:current"]
        self.assertEqual(capture["observer_tokens"], 96)
        self.assertEqual(capture["summary_max_chars"], 48)
        self.assertEqual(capture["messages_sha256"], f.sha(dumps(messages).encode()))
        self.assertEqual(capture["schema_sha256"], f.sha(dumps(schema).encode()))
        self.assertEqual(wrapped.last_metrics, real.last_metrics)

    def test_02_long_budget_and_role_separation(self):
        real = FakeRunner();captures = {}
        messages = [{"role": "user", "content": "synthetic"}]
        for role, tokens in (("B1_DETAIL", 96), ("B2_GIST", 160)):
            schema = {"properties": {"summary": {"maxLength": f.summary_cap(tokens)}}}
            wrapped = native.CapturedNativeBody(real, captures, role)
            list(wrapped.generate(messages, None, 100.0, tokens, schema))
        self.assertEqual(captures["B1_DETAIL"]["summary_max_chars"], 48)
        self.assertEqual(captures["B2_GIST"]["summary_max_chars"], 84)
        self.assertEqual(len(real.calls), 2)

    def test_03_signature_and_noninteger_budget_rejected(self):
        wrapped = native.CapturedNativeBody(FakeRunner(), {}, "B1_DETAIL")
        with self.assertRaisesRegex(ValueError, "SIGNATURE_RED"):
            wrapped.generate([], None, 10.0, 96)
        with self.assertRaisesRegex(ValueError, "SCHEMA_OR_TOKENS_RED"):
            wrapped.generate([], None, 10.0, True, {})
        with self.assertRaisesRegex(ValueError, "SCHEMA_OR_TOKENS_RED"):
            wrapped.generate([], None, 10.0, 96, None)

    def test_04_reaped_helper_requires_all_processes_closed(self):
        self.assertFalse(native.reaped([]))
        self.assertFalse(native.reaped([{"before": 1, "process_reaped": False}]))
        self.assertFalse(native.reaped([{"before": None, "process_reaped": True}]))
        self.assertTrue(native.reaped([{"before": 1, "process_reaped": True}]))
        self.assertFalse(native.reaped([{"before": 1, "process_reaped": True},
                                        {"before": 2, "process_reaped": False}]))

if __name__ == "__main__":
    unittest.main()
