"""Regression: native admission must never erase protected B1/B2 peer evidence."""
import json
import threading
import time
import unittest
from unittest.mock import patch

from v13.runners import LlamaRunner


class NativeProtectedAdmissionTests(unittest.TestCase):
    def test_body_peer_handoff_survives_unmet_soft_target(self):
        runner = object.__new__(LlamaRunner)
        runner.role = "B1_DETAIL"
        runner.cfg = {"context_tokens": 2048}
        runner._prompt_admission = None
        messages = [
            {"role": "system", "content": "Pinned B1 rules"},
            {"role": "user", "content": "EXACT_SOURCE_PEER_MESSAGE"},
            {"role": "assistant", "content": "B2_PEER_REENTRY"},
        ]
        seen = []
        def fake_json(method, path, payload, deadline):
            if path == "/apply-template":
                seen.append(payload["messages"])
                return {"prompt": json.dumps(payload["messages"])}
            if path == "/tokenize":
                return {"tokens": list(range(300))}
            raise AssertionError(path)
        runner._json = fake_json
        with patch("v13.native_prompt_admission.soft_limit", return_value=96):
            prompt, count, truncated = runner._prompt(
                messages, threading.Event(), time.monotonic() + 5, 16
            )
        self.assertEqual(count, 300)
        self.assertFalse(truncated)
        self.assertEqual(seen[-1], messages)
        self.assertIn("B2_PEER_REENTRY", prompt)
        self.assertEqual(
            runner._prompt_admission["status"],
            "PROTECTED_CONTEXT_EXCEEDS_TIME_TARGET",
        )
        self.assertEqual(runner._prompt_admission["removed_layers"], [])
        self.assertFalse(runner._prompt_admission["source_text_rewritten"])


if __name__ == "__main__":
    unittest.main()
