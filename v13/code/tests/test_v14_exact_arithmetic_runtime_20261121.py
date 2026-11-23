from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import subprocess
import sys


CODE = Path(__file__).resolve().parents[1]
STAGER = CODE / "scripts" / "stage_integrated_candidate.py"


def _stage(code_dir: Path, destination: Path):
    spec = importlib.util.spec_from_file_location("v14_core_runtime_stager", STAGER)
    if spec is None or spec.loader is None:
        raise RuntimeError("V14 staged Runtime builder unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.stage(code_dir, destination)


def test_exact_arithmetic_is_date_safe_and_reaches_runtime_c5_broker_world(tmp_path):
    destination = tmp_path / "candidate"
    manifest = _stage(CODE, destination)
    assert manifest["status"] == "SHADOW_REVIEW_ONLY"
    assert manifest["arithmetic_overlay"]["status"] == "SHADOW_REVIEW_ONLY"
    assert {"v13/arithmetic_reflex.py", "v13/runtime.py"} <= set(manifest["replaced_files"])

    script = r'''
import json
import time
from pathlib import Path
from unittest.mock import Mock

from v13.arithmetic_reflex import exact_arithmetic
from v13.broker import decide, egress_type
from v13.output_policy import match
from v13.runtime import Runtime

# Narrow two-integer arithmetic, with date-shaped subtraction/division held
# unless the user explicitly asks to calculate.
assert exact_arithmetic("2+2") == "4"
assert exact_arithmetic("Was ist 2+2?") == "4"
assert exact_arithmetic("Wie viel ist 2+2?") == "4"
assert exact_arithmetic("compute 2026-11") == "2015"
assert exact_arithmetic("calculate 11-21") == "-10"
assert exact_arithmetic("What is 2026-11?") is None
assert exact_arithmetic("Was ist 2026/11?") is None
assert exact_arithmetic("11-21") is None
assert exact_arithmetic("What is 11-21?") is None
assert exact_arithmetic("Was ist 11-21?") is None
assert exact_arithmetic("7-12") is None
assert exact_arithmetic("What is 7-12?") is None
assert exact_arithmetic("calculate 7-12") == "-5"
assert exact_arithmetic("compute 11-21") == "-10"
assert exact_arithmetic("berechne 11-21") == "-10"
assert exact_arithmetic("8/4") == "2"
# 7-12 is ambiguous without an explicit math cue (covered above).
assert exact_arithmetic("2/0") is None
assert exact_arithmetic("2+2+2") is None

def wait(runtime):
    until = time.monotonic() + 10
    while not runtime.idle() and time.monotonic() < until:
        time.sleep(0.005)
    assert runtime.idle(), "Runtime did not finish the bounded test turn"
    return runtime.last_answer()

def packet(runtime, event_id, kind):
    row = runtime.store.one(
        "SELECT payload FROM packets WHERE event_id=? AND kind=? ORDER BY rowid DESC LIMIT 1",
        (event_id, kind),
    )
    return json.loads(row["payload"]) if row else None

runtime = Runtime(Path(__import__("sys").argv[1]))
try:
    runtime.sleep.cycle.set_policy("enabled", "off")
    assert match(runtime.store, "2+2") is None

    # Arithmetic must use the current source and typed C5/Broker authority,
    # not route, perceive, retrieve, invoke B1/B2/C3 or load a model.
    runtime._route = Mock(side_effect=AssertionError("arithmetic entered normal routing"))
    runtime.pool.get = Mock(side_effect=AssertionError("arithmetic loaded a native model"))
    runtime.cognition.percept = Mock(side_effect=AssertionError("arithmetic re-entered perception"))
    runtime.cognition.offer = Mock(side_effect=AssertionError("arithmetic invoked B1/B2"))
    runtime.memory.recall = Mock(side_effect=AssertionError("arithmetic invoked optional recall"))
    runtime.learner.retrieve = Mock(side_effect=AssertionError("arithmetic invoked semantic retrieval"))
    # ModelManager.revision is read-only manifest metadata used by the
    # post-turn World/Self snapshot; it does not load a native model. The
    # actual native-load boundary is RunnerPool.get, asserted below.

    event_id = runtime.submit("2+2")
    answer = wait(runtime)
    assert answer["event_id"] == event_id
    assert answer["status"] == "FINAL"
    assert answer["text"] == "4"

    metadata = json.loads(answer["metadata"])
    assert metadata["model_generated"] is False
    assert metadata["output_authority"] == "LOCAL_EXACT_ARITHMETIC"
    assert metadata["direct_source_copy"] is False
    assert metadata["arithmetic_reflex"]["result"] == "4"
    event_packet = json.loads(runtime.store.one("SELECT packet FROM events WHERE id=?", (event_id,))["packet"])
    assert metadata["arithmetic_reflex"]["source_ref"] == event_packet["source_ref"]

    selection = packet(runtime, event_id, "ActionSelection")
    assert selection["selected"]["action_id"] == "LOCAL_EXACT_ARITHMETIC"
    assert selection["selected"]["action_type"] == "TEXT_REPORT"
    assert selection["selected"]["permission_class"] == "local_text_only"

    broker = packet(runtime, event_id, "OutputBrokerDecision")
    assert broker["authority"] == "LOCAL_EXACT_ARITHMETIC"
    assert broker["egress_type"] == "TEXT_REPORT"
    assert broker["rewrites"] == 0

    egress = packet(runtime, event_id, "EgressCheck")
    assert egress["action_type"] == "TEXT_REPORT"
    assert egress["ok"] is True

    action = runtime.store.one("SELECT status,outcome FROM actions WHERE event_id=?", (event_id,))
    outcome = json.loads(action["outcome"])
    assert action["status"] == "FINAL"
    assert outcome["role"] == "LOCAL_EXACT_ARITHMETIC"
    assert outcome["model_generated"] is False

    assert packet(runtime, event_id, "PerceptPacket")["modality"] == "text"
    assert packet(runtime, event_id, "ExperienceRecord")["outcome"] == "FINAL"
    assert packet(runtime, event_id, "OutputPolicyDecision") is None
    assert runtime.store.one(
        "SELECT COUNT(*) AS n FROM packets WHERE event_id=? AND kind IN ('QueryPacket','OfferPacket')",
        (event_id,),
    )["n"] == 0
    assert runtime.store.integrity(True) == []

    runtime._route.assert_not_called()
    runtime.pool.get.assert_not_called()
    runtime.cognition.percept.assert_not_called()
    runtime.cognition.offer.assert_not_called()
    runtime.memory.recall.assert_not_called()
    runtime.learner.retrieve.assert_not_called()
finally:
    runtime.close()

assert decide(["MODEL_ANSWER", "LOCAL_EXACT_ARITHMETIC"])["selected"] == "LOCAL_EXACT_ARITHMETIC"
assert decide(["APPROVED_FIXED_RULE", "LOCAL_EXACT_ARITHMETIC"])["selected"] == "APPROVED_FIXED_RULE"
assert decide(["EXPLICIT_EXACT_COPY", "LOCAL_EXACT_ARITHMETIC"])["selected"] == "EXPLICIT_EXACT_COPY"
assert egress_type("LOCAL_EXACT_ARITHMETIC") == "TEXT_REPORT"
assert egress_type("EXPLICIT_EXACT_COPY") == "EXACT_RENDER"
print("PASS: staged exact arithmetic is date-safe, source-bound and connected through Runtime/C5/F4/Broker/C6")
'''
    env = dict(os.environ)
    env["PYTHONPATH"] = str(destination)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run(
        [sys.executable, "-c", script, str(tmp_path / "private-home")],
        cwd=destination,
        env=env,
        text=True,
        capture_output=True,
        timeout=45,
    )
    assert result.returncode == 0, result.stdout + "\n" + result.stderr
    assert "PASS: staged exact arithmetic" in result.stdout


def test_experience_record_survives_optional_world_observer_failures(tmp_path):
    destination = tmp_path / "candidate"
    manifest = _stage(CODE, destination)
    assert manifest["status"] == "SHADOW_REVIEW_ONLY"
    assert "v13/runtime.py" in manifest["replaced_files"]

    script = r'''
import json
import time
from pathlib import Path
from unittest.mock import Mock
from v13.runtime import Runtime

def wait(runtime):
    until = time.monotonic() + 10
    while not runtime.idle() and time.monotonic() < until:
        time.sleep(0.005)
    assert runtime.idle(), "Runtime did not finish the bounded test turn"
    return runtime.last_answer()

def packet(runtime, event_id, kind):
    row = runtime.store.one(
        "SELECT payload FROM packets WHERE event_id=? AND kind=? ORDER BY rowid DESC LIMIT 1",
        (event_id, kind),
    )
    return json.loads(row["payload"]) if row else None

runtime = Runtime(Path(__import__("sys").argv[1]))
try:
    runtime.sleep.cycle.set_policy("enabled", "off")
    runtime.world.observe = Mock(side_effect=RuntimeError("injected World failure"))
    runtime.world.self_state = Mock(side_effect=RuntimeError("injected Self failure"))

    event_id = runtime.submit("2+2")
    answer = wait(runtime)
    assert answer["event_id"] == event_id
    assert answer["status"] == "FINAL"
    assert answer["text"] == "4"

    experience = packet(runtime, event_id, "ExperienceRecord")
    assert experience is not None
    assert experience["outcome"] == "FINAL"
    assert runtime.world.observe.call_count == 1
    assert runtime.world.self_state.call_count == 1

    rows = runtime.store.rows(
        "SELECT kind,metrics FROM telemetry WHERE event_id=? AND kind IN (?,?) ORDER BY id",
        (event_id, "world_observe_unavailable", "world_self_state_unavailable"),
    )
    failures = {row["kind"]: json.loads(row["metrics"]) for row in rows}
    assert failures["world_observe_unavailable"]["stage"] == "observe"
    assert failures["world_self_state_unavailable"]["stage"] == "observe"
    assert runtime.store.integrity(True) == []
finally:
    runtime.close()

print("PASS: optional World/Self failures are logged without suppressing the durable ExperienceRecord")
'''
    env = dict(os.environ)
    env["PYTHONPATH"] = str(destination)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run(
        [sys.executable, "-c", script, str(tmp_path / "private-home")],
        cwd=destination,
        env=env,
        text=True,
        capture_output=True,
        timeout=45,
    )
    assert result.returncode == 0, result.stdout + "\n" + result.stderr
    assert "PASS: optional World/Self failures" in result.stdout
