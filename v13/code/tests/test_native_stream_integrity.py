"""Native stream termination regression: synthetic HTTP only, no phone proof."""
import io
import threading
import time
import unittest
from unittest.mock import patch

from v13.common import Unavailable
from v13.runners import LlamaRunner


class _Response:
    status = 200
    def __init__(self, frames):
        self.frames = iter(frames)
    def readline(self):
        return next(self.frames, b"")
    def read(self, n=None):
        return b""


class _Connection:
    def __init__(self, response):
        self.response = response
    def request(self, *args, **kwargs):
        pass
    def getresponse(self):
        return self.response
    def close(self):
        pass


class NativeStreamIntegrityTests(unittest.TestCase):
    def _run(self, frames):
        runner = LlamaRunner.__new__(LlamaRunner)
        runner.role = "C3_LANGUAGE"
        runner.purpose = "generate"
        runner.cfg = {"answer_tokens": 8, "temperature": 0.1, "c3_sampling": "default"}
        runner.proc = None
        runner.port = 12345
        runner.key = "test-only"
        runner._audit_enabled = False
        runner.last_metrics = {}
        runner.stage_times = {}
        runner.phase = "prefill"
        runner.phase_started = time.monotonic()
        runner.model = type("Model", (), {"name": "fake"})()
        runner.load = lambda cancel, deadline: None
        runner._prompt = lambda messages, cancel, deadline, cap: ("prompt", 3, False)
        response = _Response(frames)
        with patch("v13.runners.http.client.HTTPConnection", return_value=_Connection(response)), \
             patch("v13.runners.process_memory", return_value={}):
            return list(runner._generate([{"role": "user", "content": "hello"}],
                                         threading.Event(), time.monotonic() + 5))

    def test_clean_native_stop_is_accepted(self):
        self.assertEqual(self._run([b'data: {"content":"ok","tokens":[1]}\n',
                                    b'data: {"stop":true,"content":"","tokens":[]}\n']), ["ok"])

    def test_eof_after_partial_output_is_not_final(self):
        with self.assertRaisesRegex(Unavailable, "without completion marker"):
            self._run([b'data: {"content":"partial","tokens":[1]}\n'])

    def test_truthy_nonboolean_stop_is_not_accepted(self):
        with self.assertRaisesRegex(Unavailable, "without completion marker"):
            self._run([b'data: {"stop":"false","content":"partial","tokens":[1]}\n'])

    def test_empty_eof_is_not_final(self):
        with self.assertRaisesRegex(Unavailable, "without completion marker"):
            self._run([])


if __name__ == "__main__":
    unittest.main()
