"""V14 regression: exact arithmetic uses the existing source-bound C5 policy path."""
from __future__ import annotations

import hashlib
import json
import threading
import time
from unittest.mock import Mock, patch

from v13.config import initialize
from v13.exact_arithmetic import evidence
from v13.output_policy import match
from v13.runtime import Runtime
from v13.store import Store


class FakeStore:
    def __init__(self):
        self.mutex = threading.RLock()
        self.sources = []

    def generation(self):
        return {"rule_version": 1}

    def one(self, sql, params):
        return {"rules": "[]"}

    def source(self, text, kind):
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        ref = {
            "source_id": f"source-{len(self.sources) + 1}",
            "sha256": digest,
            "char_start": 0,
            "char_end": len(text),
            "modality": "text",
        }
        self.sources.append((text, kind, ref))
        return ref


def test_exact_binary_integer_evidence_and_negative_controls():
    cases = {
        "2+2": "4",
        "What is 2+2?": "4",
        "Wie viel ist -2 + 7?": "5",
        "calculate -12 * 3": "-36",
        "berechne 4×6": "24",
        "12 - 20": "-8",
        "2--3": "5",
        "0*123": "0",
    }
    for prompt, answer in cases.items():
        result = evidence(prompt)
        assert result is not None, prompt
        assert result["result"] == answer
        assert result["model_generated"] is False
        assert result["authority"] == "DETERMINISTIC_EVIDENCE_ONLY"

    for prompt in (
        "2+2 and explain",
        "1+2+3",
        "2026-11",
        "2026 - 11",
        "What is 2026-11?",
        "11-21",
        "12-24",
        "please run 2+2",
        "1/0",
        "2**100",
        "9.5+2",
        "2+2=5",
        "2+2\nother",
        "1; delete files",
        "",
        None,
        True,
    ):
        assert evidence(prompt) is None, repr(prompt)


def test_policy_returns_exact_source_bound_query_and_answer():
    store = FakeStore()
    policy = match(store, "2+2")
    assert policy["kind"] == "SYSTEM_DETERMINISTIC_ARITHMETIC"
    assert policy["rule_id"] == "fixed_builtin_exact_integer_arithmetic_v1"
    assert policy["rule_version"] == "builtin-1"
    assert policy["answer"] == "4"
    assert policy["model_generated"] is False
    assert policy["output_authority"] == "APPROVED_FIXED_RULE"
    assert [item[1] for item in store.sources] == [
        "SYSTEM_DETERMINISTIC_QUERY",
        "SYSTEM_DETERMINISTIC_ANSWER",
    ]
    assert store.sources[0][0] == "2+2"
    assert store.sources[1][0] == "4"


def test_operator_fixed_answer_keeps_precedence_over_builtin_arithmetic():
    store = FakeStore()
    fixed = {
        "entry": {
            "rule_id": "fixed_0123456789abcdef0123456789abcdef",
            "query_ref": {"source_id": "human-query"},
            "answer_ref": {"source_id": "human-answer"},
        },
        "query": "2+2",
        "answer": "operator answer",
    }
    with patch("v13.output_policy.validate_rules", return_value=[fixed]):
        policy = match(store, "2+2")
    assert policy["answer"] == "operator answer"
    assert policy["rule_id"] == fixed["entry"]["rule_id"]
    assert store.sources == []


def test_real_store_persists_resolvable_arithmetic_sources(tmp_path):
    home = tmp_path / "runtime"
    initialize(home)
    store = Store(home)
    try:
        policy = match(store, "2+2")
        assert policy["answer"] == "4"
        assert store.read_source(policy["query_ref"]) == "2+2"
        assert store.read_source(policy["answer_ref"]) == "4"
        rows = store.rows(
            "SELECT kind FROM sources WHERE kind LIKE 'SYSTEM_DETERMINISTIC_%'"
        )
        assert {row["kind"] for row in rows} == {
            "SYSTEM_DETERMINISTIC_QUERY",
            "SYSTEM_DETERMINISTIC_ANSWER",
        }
        assert store.integrity(True) == []
    finally:
        store.close()


def _wait(runtime):
    until = time.monotonic() + 5
    while not runtime.idle() and time.monotonic() < until:
        time.sleep(0.005)
    assert runtime.idle()
    return runtime.last_answer()


def _native_spies(runtime):
    spies = []
    for obj, attr in (
        (runtime.pool, "get"),
        (runtime.needle, "embed"),
        (runtime.needle, "control"),
        (runtime.cognition, "percept"),
        (runtime.cognition, "offer"),
        (runtime.memory, "recall"),
        (runtime.learner, "decide"),
        (runtime.learner, "output_delta"),
        (runtime.learner, "world_predict"),
    ):
        spy = Mock(side_effect=AssertionError("unexpected native path: " + attr))
        setattr(obj, attr, spy)
        spies.append(spy)
    return spies


def test_real_runtime_arithmetic_turn_is_correct_source_bound_and_model_free(tmp_path):
    runtime = Runtime(tmp_path)
    try:
        spies = _native_spies(runtime)
        event_id = runtime.submit("2+2")
        row = _wait(runtime)
        assert row["status"] == "FINAL"
        assert row["text"] == "4"
        metadata = json.loads(row["metadata"])
        assert metadata["model_generated"] is False
        assert metadata["output_authority"] == "APPROVED_FIXED_RULE"
        assert metadata["exact_policy_matched"] is True
        assert "C3_DECODE" in metadata["skipped_native_stages"]
        assert all(spy.call_count == 0 for spy in spies)

        decision = runtime.store.one(
            "SELECT payload FROM packets WHERE event_id=? AND kind='OutputPolicyDecision'",
            (event_id,),
        )
        assert decision is not None
        payload = json.loads(decision["payload"])
        assert payload["rule_id"] == "fixed_builtin_exact_integer_arithmetic_v1"
        assert runtime.store.read_source(payload["query_ref"]) == "2+2"
        assert runtime.store.read_source(payload["answer_ref"]) == "4"
        for kind in (
            "PerceptPacket",
            "JEFBroadcastPacket",
            "CorollaryCopy",
            "ActionOutcome",
            "PredictionOutcome",
            "ExperienceRecord",
        ):
            assert runtime.store.one(
                "SELECT id FROM packets WHERE event_id=? AND kind=?",
                (event_id, kind),
            ), kind
        assert runtime.store.one(
            "SELECT state FROM accepted_turns WHERE event_id=?",
            (event_id,),
        )["state"] == "DONE"
        assert runtime.store.integrity(True) == []
    finally:
        runtime.close()


def test_multi_step_arithmetic_remains_eligible_for_normal_reasoning():
    store = FakeStore()
    for prompt in ("2+2 and explain", "1+2+3", "please run 2+2"):
        assert match(store, prompt) is None
    assert store.sources == []
