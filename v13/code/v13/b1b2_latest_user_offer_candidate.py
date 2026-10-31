"""Run76 default-OFF B1/B2 latest-USER source guard for SHADOW offers.

Detects stale replay before native inference and USER/source drift after an
offer. Post-call RED cannot undo a persisted SHADOW OfferPacket; no authority.
Not wired into production Cognition or Runtime.
"""
from __future__ import annotations

from .b1b2_causal_context_candidate import _bound_user_event
from .b1b2_topic_partition_candidate import TopicPartitionOfferConsumer
from .jef_f1f5_live_current_candidate import _latest_authoritative_user

ROLES = ("B1_DETAIL", "B2_GIST")
REVISION = "b1b2-latest-user-offer-shadow-run76-v1"


def _result(status, **extra):
    return {
        "schema": "v13.b1b2_latest_user_offer_shadow.v1",
        "revision": REVISION, "status": status,
        "delivery_authority": 0, "learning_authority": 0,
        "tool_dispatches": 0, "output_committed": False,
        "native_proof": False, "real_tty_approved": False,
        "age0": "RECORD_ONLY", "step2": "UTILITY_FAIL",
        "b3": "NO_PROMOTION", "jepa_weight": 0,
        "whole_system_complete": False, **extra,
    }


def _bound_latest(runtime, role, event):
    if role not in ROLES or type(event) is not dict:
        raise ValueError("ROLE_OR_EVENT_RED")
    store = runtime.store
    current = _bound_user_event(
        store, event["event_id"], runtime.session)
    if (event.get("source_ref") != current["source_ref"]
            or event.get("brain_generation_id") != current["generation"]
            or current["generation"] != store.generation_id
            or _latest_authoritative_user(store, runtime.session)
            != event["event_id"]):
        raise ValueError("LATEST_USER_OR_SOURCE_RED")
    return current


class LatestUserOfferConsumer:
    """Isolated opt-in adapter; never a production or output consumer."""

    def __init__(self, runtime):
        self.r = runtime

    def guarded_offer(self, role, event, version, deadline, *,
                      operator_opt_in=False):
        if operator_opt_in is not True:
            return _result("OFF", runner_called=False,
                           shadow_offer_may_exist=False)
        if role not in ROLES or type(event) is not dict:
            return _result("INVALID_ROLE_OR_EVENT", runner_called=False,
                           shadow_offer_may_exist=False)
        try:
            before = _bound_latest(self.r, role, event)
        except Exception:
            return _result("PRE_OFFER_STALE_USER_OR_SOURCE_RED",
                           runner_called=False, shadow_offer_may_exist=False)
        result = TopicPartitionOfferConsumer(self.r).guarded_offer(
            role, event, version, deadline, operator_opt_in=True)
        if result.get("status") != "SHADOW_OFFER_PRODUCED":
            return _result(result.get("status", "OFFER_ERROR"),
                           runner_called=result.get("runner_called", False),
                           shadow_offer_may_exist=False)
        try:
            after = _bound_latest(self.r, role, event)
            if after != before:
                raise ValueError("USER_SOURCE_CHANGED")
        except Exception:
            return _result(
                "POST_OFFER_STALE_USER_OR_SOURCE_RED",
                runner_called=True,
                shadow_offer_may_exist=True,
                orphaned_shadow_offer_packet_id=result.get("offer_packet_id"))
        return _result(
            "SHADOW_LATEST_USER_OFFER_PRODUCED",
            runner_called=True, shadow_offer_may_exist=True,
            offer_packet_id=result.get("offer_packet_id"),
            query_packet_id=result.get("query_packet_id"),
            partition_key_sha256=result.get("partition_key_sha256"),
            topic_partitioned=result.get("topic_partitioned") is True)
