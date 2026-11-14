"""End-to-end synthetic regression for the observer fair-share candidate.

This intentionally tests the Runtime turn path, not just fair_deadline().
No native runner, model weights or Redmi measurement is implied.
"""
import json
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from v13.runtime import Runtime
from v13.operator import Operator
from v13 import effort


@pytest.mark.parametrize("schedule,first,second", [
    ("A_THEN_B_SEQUENTIAL", "B1_DETAIL", "B2_GIST"),
    ("B_THEN_A_SEQUENTIAL", "B2_GIST", "B1_DETAIL"),
])
def test_failed_first_body_still_attempts_second_and_answers(schedule, first, second):
    with tempfile.TemporaryDirectory() as directory:
        runtime = Runtime(Path(directory))
        try:
            runtime.sleep.cycle.set_policy("enabled", "off")
            Operator(runtime).run(":route both")
            Operator(runtime).run(":observers " + schedule)
            effort.set_mode(runtime.store, "max")
            runtime.learner.output_delta = Mock(return_value=None)
            calls = []
            def offer(role, event, version, deadline, peer=None, **kwargs):
                calls.append((role, deadline, time.monotonic()))
                if role == first:
                    raise TimeoutError("simulated first body budget exhausted")
                return {
                    "role": role, "packet_id": "pkt_" + role,
                    "offer": {"summary": "source-bound test offer", "needs_reentry": False, "quotes": []},
                    "evidence_refs": [],
                }
            runtime.cognition.offer = offer
            runtime.cognition.communicate = Mock(return_value=None)
            def generate(messages, cancel, deadline, *args, **kwargs):
                yield "Visible response."
            runtime.pool.get = Mock(return_value=SimpleNamespace(
                role="C3_LANGUAGE", last_metrics={"test_seam": True}, generate=generate
            ))
            runtime.submit("Compare two alternatives carefully")
            until = time.monotonic() + 15
            while not runtime.idle() and time.monotonic() < until:
                time.sleep(.01)
            assert runtime.idle(), "Runtime did not complete its turn"
            answer = runtime.last_answer()
            assert answer is not None
            metadata = json.loads(answer["metadata"])
            assert metadata["observer_schedule"]["schedule"] == schedule
            roles = [role for role, _, _ in calls]
            assert roles[:2] == [first, second], roles
            assert calls[0][1] < calls[1][1], "first body must not consume second deadline"
            assert answer["status"] == "FINAL"
            assert "Visible response." in answer["text"]
        finally:
            runtime.close()


@pytest.mark.parametrize("schedule,first,second", [
    ("A_THEN_B_SEQUENTIAL", "B1_DETAIL", "B2_GIST"),
    ("B_THEN_A_SEQUENTIAL", "B2_GIST", "B1_DETAIL"),
])
def test_successful_first_body_passes_peer_message_to_second(schedule, first, second):
    """Fair time slicing must not silently sever B1/B2 communication."""
    with tempfile.TemporaryDirectory() as directory:
        runtime = Runtime(Path(directory))
        try:
            runtime.sleep.cycle.set_policy("enabled", "off")
            Operator(runtime).run(":route both")
            Operator(runtime).run(":observers " + schedule)
            effort.set_mode(runtime.store, "max")
            runtime.learner.output_delta = Mock(return_value=None)
            received = []
            peer_message = {"origin": first, "message": "synthetic peer signal"}

            def offer(role, event, version, deadline, peer=None, **kwargs):
                received.append((role, peer))
                return {
                    "role": role, "packet_id": "pkt_" + role,
                    "offer": {"summary": "synthetic offer", "needs_reentry": False, "quotes": []},
                    "evidence_refs": [],
                }

            def communicate(packet, target, **kwargs):
                if packet["role"] == first and target == second:
                    return peer_message
                return None

            runtime.cognition.offer = offer
            runtime.cognition.communicate = Mock(side_effect=communicate)
            runtime.pool.get = Mock(return_value=SimpleNamespace(
                role="C3_LANGUAGE", last_metrics={"test_seam": True},
                generate=lambda *args, **kwargs: iter(["Synthetic answer."]),
            ))
            runtime.submit("Compare two alternatives carefully")
            until = time.monotonic() + 15
            while not runtime.idle() and time.monotonic() < until:
                time.sleep(.01)
            assert runtime.idle()
            assert [role for role, _ in received][:2] == [first, second]
            assert received[0][1] is None
            assert received[1][1] == peer_message
            assert runtime.last_answer()["status"] == "FINAL"
        finally:
            runtime.close()
