"""Android companion receipt -> C3 context integration.

The companion receipt is a signed dispatch/denial attestation only. It must
never be promoted to independent Android observation or a T8 transition.
"""
import json
import time
from pathlib import Path
from unittest.mock import Mock

import pytest

from v13.android_outcome_context import recent_companion_receipt_context
from v13.android_outcomes import ActionOutcome, persist_companion_outcome
from v13.common import dumps
from v13.operator import Operator
from v13.runtime import Runtime


def seed_receipt(runtime, *, session=None, status="COMPANION_ATTESTED_NOT_DEVICE_VERIFIED"):
    session = session or runtime.session
    source_event = runtime.store.event(session, "Open app com.example.test")
    runtime.store.message(
        session, source_event["event_id"], "user",
        "Open app com.example.test", status="FINAL",
    )
    runtime.store.message(
        session, source_event["event_id"], "assistant",
        "Waiting for the paired companion receipt.", status="FINAL",
    )
    token = source_event["event_id"].split("_", 1)[-1]
    denied = status == "COMPANION_USER_DENIED"
    failed = status == "COMPANION_DISPATCH_FAILED"
    receipt_status = "USER_DENIED" if denied else (
        "FAILED_TO_DISPATCH" if failed else "DISPATCHED_UNVERIFIED"
    )
    approval = "ANDROID_COMPANION_USER_DENIAL" if denied else "ANDROID_COMPANION_SIGNED_UI_CONFIRMATION"
    outcome = ActionOutcome(
        action_id="act_" + token,
        capability="launch_app",
        status=status,
        observed=False,
        evidence_level="COMPANION_RECEIPT_ONLY",
        timestamp=time.time(),
        details={
            "digest": token * 2,
            "receipt_schema": "v14.android-companion-receipt/1",
            "auth_scheme": "ECDSA_P256_SHA256_ANDROID_KEYSTORE",
            "receipt_nonce": token,
            "companion_local_consent_claim": not denied,
            "receipt_status": receipt_status,
            "local_approval_evidence": approval,
            "android_os_permission_status": "NOT_REQUIRED_FOR_LAUNCH_APP",
            "key_storage_status": "ANDROID_KEYSTORE_SOFTWARE_BACKED",
            "t8_authoritative": False,
            "world_learning_eligible": False,
            "event_id": source_event["event_id"],
            "source_ref": source_event["source_ref"],
        },
    )
    packet_value = persist_companion_outcome(runtime.store, outcome)
    return source_event, packet_value


class SyntheticRunner:
    def __init__(self, role, seen):
        self.role = role
        self.seen = seen
        self.last_metrics = {
            "role": role,
            "status": "FINAL",
            "generated_tokens": 9,
            "prompt_tokens": 40,
            "last_phase": "stream",
            "duration_s": 0.01,
            "synthetic": True,
        }

    def generate(self, messages, cancel, deadline, *args, **kwargs):
        if self.role == "C3_LANGUAGE":
            self.seen[self.role] = [dict(message) for message in messages]
            yield (
                "The paired companion reports that it dispatched the launch "
                "intent, but the app's foreground state was not independently verified."
            )
            return
        if self.role == "B1_DETAIL":
            payload = {
                "summary": "The current message asks whether the prior app launch completed.",
                "quotes": ["Did it open?"],
                "uncertainty": "medium",
                "needs_reentry": False,
            }
        elif self.role == "B2_GIST":
            payload = {
                "summary": "This is a follow-up about the result of a previous action.",
                "quotes": ["Did it open?"],
                "uncertainty": "medium",
                "needs_reentry": False,
            }
        else:
            raise AssertionError("unexpected role " + self.role)
        self.seen[self.role] = [dict(message) for message in messages]
        yield json.dumps(payload, ensure_ascii=False)


def wait_for_answer(runtime, timeout=15):
    until = time.monotonic() + timeout
    while not runtime.idle() and time.monotonic() < until:
        time.sleep(0.005)
    assert runtime.idle(), "synthetic Runtime turn did not settle"
    return runtime.last_answer()


def test_recent_companion_receipt_is_session_scoped_ttl_bounded_and_non_authoritative(tmp_path):
    runtime = Runtime(Path(tmp_path) / "private-home")
    try:
        source_event, packet_value = seed_receipt(runtime)
        created = runtime.store.one(
            "SELECT created FROM packets WHERE id=?", (packet_value["packet_id"],)
        )["created"]

        context = recent_companion_receipt_context(
            runtime.store, runtime.session, now=created + 1, ttl_seconds=300
        )
        assert context is not None
        assert context["status"] == "COMPANION_ATTESTED_NOT_DEVICE_VERIFIED"
        assert context["receipt_status"] == "DISPATCHED_UNVERIFIED"
        assert context["observed"] is False
        assert context["t8_authoritative"] is False
        assert context["world_learning_eligible"] is False
        assert context["trusted_transition_eligible"] is False
        assert source_event["source_ref"] in context["source_refs"]
        assert "not independently observed" in context["claim_boundary"].lower()
        assert "digest" not in context and "receipt_nonce" not in context

        assert recent_companion_receipt_context(
            runtime.store, runtime.session, now=created + 301, ttl_seconds=300
        ) is None

        other_session = runtime.store.new_session()
        seed_receipt(runtime, session=other_session)
        # The current session's latest receipt was made stale above; a receipt
        # belonging to another session must never be surfaced here.
        assert recent_companion_receipt_context(
            runtime.store, runtime.session, now=created + 301, ttl_seconds=300
        ) is None
    finally:
        runtime.close()


def test_tampered_authority_flags_fail_closed(tmp_path):
    runtime = Runtime(Path(tmp_path) / "private-home")
    try:
        _, packet_value = seed_receipt(runtime)
        row = runtime.store.one(
            "SELECT payload FROM packets WHERE id=?", (packet_value["packet_id"],)
        )
        tampered = json.loads(row["payload"])
        tampered["actual"]["world_learning_eligible"] = True
        with runtime.store.tx() as connection:
            connection.execute(
                "UPDATE packets SET payload=? WHERE id=?",
                (dumps(tampered), packet_value["packet_id"]),
            )
        assert recent_companion_receipt_context(
            runtime.store, runtime.session, now=time.time(), ttl_seconds=300
        ) is None
    finally:
        runtime.close()


def test_runtime_passes_companion_receipt_to_c3_without_creating_t8_transition(tmp_path):
    runtime = Runtime(Path(tmp_path) / "private-home")
    seen = {}
    try:
        runtime.sleep.cycle.set_policy("enabled", "off")
        runtime.cfg.update(
            deadline_seconds=30,
            observer_seconds=5,
            observer_mode="background",
            observer_schedule="A_THEN_B_SEQUENTIAL",
            observer_sample_rate=1.0,
            b2_quote_select="off",
            offer_quote_context_chars=0,
            b2_state_slots=0,
        )
        source_event, packet_value = seed_receipt(runtime)
        Operator(runtime).run(":effort max")
        runtime._route = Mock(
            return_value=("both", {"source": "SYNTHETIC_ANDROID_RECEIPT_E2E"})
        )
        runners = {
            role: SyntheticRunner(role, seen)
            for role in ("B1_DETAIL", "B2_GIST", "C3_LANGUAGE")
        }
        runtime.pool.get = Mock(side_effect=lambda role: runners[role])

        event_id = runtime.submit("Did it open?")
        answer = wait_for_answer(runtime)
        assert answer["event_id"] == event_id
        assert answer["status"] == "FINAL"
        assert "not independently verified" in answer["text"].lower()

        c3_system = "\n".join(
            message.get("content", "")
            for message in seen["C3_LANGUAGE"]
            if message.get("role") == "system"
        )
        assert "Android companion receipt" in c3_system
        assert "DISPATCHED_UNVERIFIED" in c3_system
        assert "COMPANION_RECEIPT_ONLY" in c3_system
        assert "not independently observed" in c3_system.lower()
        assert packet_value["actual"]["receipt_nonce"] not in c3_system
        assert packet_value["actual"]["digest"] not in c3_system

        answer_row = runtime.store.one(
            "SELECT metadata FROM messages "
            "WHERE event_id=? AND role='assistant' ORDER BY id DESC LIMIT 1",
            (event_id,),
        )
        metadata = json.loads(answer_row["metadata"])
        receipt_meta = metadata["android_companion_receipt"]
        assert receipt_meta["status"] == "COMPANION_ATTESTED_NOT_DEVICE_VERIFIED"
        assert receipt_meta["observed"] is False
        assert receipt_meta["t8_authoritative"] is False
        assert receipt_meta["world_learning_eligible"] is False
        assert source_event["source_ref"] in metadata["context_source_refs"]

        receipt = runtime.store.one(
            "SELECT payload FROM packets WHERE id=?", (packet_value["packet_id"],)
        )
        persisted = json.loads(receipt["payload"])
        assert persisted["actual"]["t8_authoritative"] is False
        assert persisted["actual"]["world_learning_eligible"] is False
        assert persisted["actual"]["trusted_transition_eligible"] is False
        assert runtime.store.rows(
            "SELECT id FROM packets WHERE event_id=? AND kind='WorldTransition'",
            (source_event["event_id"],),
        ) == []
        assert runtime.store.rows(
            "SELECT id FROM packets WHERE event_id=? AND kind='ExperienceRecord'",
            (source_event["event_id"],),
        ) == []
        ready = runtime.store.rows(
            "SELECT metrics FROM telemetry "
            "WHERE event_id=? AND kind='android_companion_receipt_context_ready'",
            (event_id,),
        )
        assert len(ready) == 1
        metrics = json.loads(ready[0]["metrics"])
        assert metrics["role"] == "C3_LANGUAGE"
        assert metrics["count"] == 1
        assert metrics["status"] == "PASS"
        assert runtime.store.integrity(True) == []
    finally:
        runtime.close()
