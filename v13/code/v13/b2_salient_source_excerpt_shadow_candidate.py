"""Default-OFF exact USER source span selection for B2 retained context.

Isolated Run117S candidate. It selects a 240-character source-verified window
around a unique explicit binding policy instead of always the first 240 chars.
It never computes an eligibility answer, upgrades Body hypotheses to facts,
changes the frozen Cognition implementation or authorizes output/learning.
"""
from __future__ import annotations

import json
import re

from .b1b2_causal_context_candidate import _project_scope, _bound_user_event
from .b1b2_c3_source_envelope_candidate import _latest_authoritative_user

SCHEMA = "v13.b2_salient_source_excerpt_shadow.v1"
ANCHOR = re.compile(
    r"Binding policy: budget [1-9][0-9]{0,5} euros; "
    r"deadline [1-9][0-9]{0,5} days; local-only (?:true|false)\."
)
WINDOW = 240


def _result(status, **extra):
    return {
        "schema": SCHEMA, "status": status, "applied": False,
        "model_called": False, "native_calls": 0,
        "output_committed": False, "tool_dispatches": 0,
        "delivery_authority": 0, "learning_authority": 0,
        "age0": "RECORD_ONLY", "step2_exit": "EVIDENCE_NOT_PASSING",
        "b3": "NO_PROMOTION", "body_jepa": "UNAVAILABLE",
        "jepa_weight": 0, "redmi_measured": False,
        "whole_system_complete": False,
        "source_semantic_truth_authority": False, **extra,
    }


def select(runtime, current_event, original_context, *, operator_opt_in=False):
    """Read-only replacement candidate for B2 body_context's retained view.

    The caller must explicitly inject the returned view into an isolated
    SHADOW evaluation; this function does NOT install or monkeypatch itself.
    The 240-char cap is preserved. Missing or ambiguous policy => RED.
    """
    if operator_opt_in is not True:
        return _result("OFF")
    try:
        if (type(current_event) is not dict
                or type(original_context) is not list
                or len(original_context) != 1):
            return _result("PRIOR_CONTEXT_COUNT_RED")
        store = runtime.store
        current_ref = current_event["source_ref"]
        bound = _bound_user_event(store, current_event["event_id"], runtime.session)
        if (bound["source_ref"] != current_ref
                or _latest_authoritative_user(store, runtime.session) !=
                current_event["event_id"]):
            return _result("STALE_OR_FOREIGN_CURRENT_EVENT_RED")
        current_text = store.read_source(current_ref)
        current_scope = _project_scope(current_text)
        if (len(current_scope) != 1
                or current_event["brain_generation_id"] != store.generation_id):
            return _result("CURRENT_SOURCE_OR_SCOPE_RED")
        ctx = original_context[0]
        if (type(ctx) is not dict or type(ctx.get("source_ref")) is not dict
                or type(ctx.get("native_context")) is not dict
                or type(ctx.get("offer_id")) is not str):
            return _result("ORIGINAL_CONTEXT_SHAPE_RED")
        offer_row = store.one(
            "SELECT event_id,payload FROM packets WHERE id=? AND kind='OfferPacket'",
            (ctx["offer_id"],))
        if offer_row is None:
            return _result("PRIOR_OFFER_MISSING_RED")
        offer = json.loads(offer_row["payload"])
        if (offer.get("packet_id") != ctx["offer_id"]
                or offer.get("role") != "B2_GIST"
                or offer.get("event_id") != offer_row["event_id"]
                or offer.get("brain_generation_id") != store.generation_id
                or offer.get("model_revision") != runtime.models.revision("B2_GIST")):
            return _result("PRIOR_OFFER_BINDING_RED")
        row = store.one("SELECT session_id,packet FROM events WHERE id=?",
                        (offer_row["event_id"],))
        if row is None or row["session_id"] != runtime.session:
            return _result("FOREIGN_SESSION_RED")
        prior_event = json.loads(row["packet"])
        prior_ref = prior_event["source_ref"]
        prior_text = store.read_source(prior_ref)
        if (_project_scope(prior_text) != current_scope
                or prior_ref["source_id"] != ctx["source_ref"]["source_id"]
                or prior_ref["sha256"] != ctx["source_ref"]["sha256"]
                or prior_ref["modality"] != ctx["source_ref"]["modality"]
                or ctx["source_ref"]["char_start"] != prior_ref["char_start"]
                or ctx["source_ref"]["char_end"] !=
                min(prior_ref["char_end"], prior_ref["char_start"] + WINDOW)
                or store.read_source(ctx["source_ref"]) !=
                ctx["native_context"].get("exact_source_excerpt")):
            return _result("ORIGINAL_CONTEXT_SOURCE_RED")
        matches = list(ANCHOR.finditer(prior_text))
        if len(matches) != 1:
            return _result("POLICY_ANCHOR_MISSING_OR_AMBIGUOUS_RED")
        match = matches[0]
        if match.end() - match.start() > WINDOW:
            return _result("POLICY_EXCEEDS_WINDOW_RED")
        start = max(0, match.start() - 48)
        end = min(len(prior_text), start + WINDOW)
        if match.end() > end:
            start = max(0, match.end() - WINDOW)
            end = min(len(prior_text), start + WINDOW)
        if not (start <= match.start() < match.end() <= end):
            return _result("POLICY_SPAN_WINDOW_RED")
        ref = dict(prior_ref, char_start=prior_ref["char_start"] + start,
                   char_end=prior_ref["char_start"] + end)
        exact = store.read_source(ref)
        if (len(exact) > WINDOW or match.group() not in exact
                or store.read_source(prior_ref) != prior_text
                or store.read_source(current_ref) != current_text
                or store.one("SELECT payload FROM packets WHERE id=?",
                             (ctx["offer_id"],))["payload"] != offer_row["payload"]):
            return _result("POST_SELECTION_SOURCE_CHANGED_RED")
        view = [{"offer_id": ctx["offer_id"], "source_ref": ref,
                 "native_context": {
                     "exact_source_excerpt": exact,
                     "hypothesis": ctx["native_context"].get("hypothesis", ""),
                     "authority": "PRIOR_HYPOTHESIS_NOT_FACT"}}]
        return _result("SHADOW_SALIENT_B2_EXCERPT_VERIFIED",
                       context=view, source_ref=ref,
                       selected_char_count=len(exact),
                       selection_rule="UNIQUE_EXPLICIT_BINDING_POLICY_240",
                       answer_computed=False, source_semantic_truth_authority=False)
    except (AttributeError, KeyError, TypeError, ValueError, RuntimeError,
            OSError, UnicodeError, OverflowError, json.JSONDecodeError):
        return _result("SOURCE_OR_OFFER_INTEGRITY_RED")


class _SalientCausalOfferConsumer:
    """Adapter: wrap the existing CausalOfferConsumer, not frozen Cognition."""

    def __init__(self, runtime, state_view):
        from .b1b2_causal_offer_consumer_candidate import CausalOfferConsumer

        class _Consumer(CausalOfferConsumer):
            def body_context(self, role, event):
                base = super().body_context(role, event)
                if role != "B2_GIST":
                    return base
                selected = select(self.r, event, base, operator_opt_in=True)
                if selected.get("status") != "SHADOW_SALIENT_B2_EXCERPT_VERIFIED":
                    raise ValueError("SALIENT_B2_CONTEXT_RED")
                return selected["context"]

        self.worker = _Consumer(runtime)
        self.worker.s = state_view

    def guarded_offer(self, role, event, version, deadline):
        return self.worker.guarded_offer(
            role, event, version, deadline, operator_opt_in=True)


def guarded_salient_b2_offer(runtime, event, version, deadline, *,
                             operator_opt_in=False):
    """Opt-in isolated B2-current offer; prior B2 offer uses existing consumer.

    May invoke the supplied runtime's Body model. The return is only a SHADOW
    OfferPacket and cannot be delivered or treated as a verified model result.
    """
    if operator_opt_in is not True:
        return _result("OFF")
    try:
        from .b1b2_topic_partition_candidate import _TopicStateView
        current = _bound_user_event(
            runtime.store, event["event_id"], runtime.session)
        if (event.get("source_ref") != current["source_ref"]
                or current["generation"] != runtime.store.generation_id
                or len(_project_scope(current["text"])) != 1
                or _latest_authoritative_user(runtime.store, runtime.session) !=
                event["event_id"]):
            return _result("CURRENT_USER_SOURCE_RED")
        topic = next(iter(_project_scope(current["text"])))
        view = _TopicStateView(
            runtime.store, "B2_GIST", runtime.session,
            current["generation"], runtime.models.revision("B2_GIST"), topic)
        worker = _SalientCausalOfferConsumer(runtime, view)
        outcome = worker.guarded_offer("B2_GIST", event, version, deadline)
        if outcome.get("status") != "SHADOW_OFFER_PRODUCED":
            return _result("SALIENT_B2_OFFER_RED",
                           component_status=outcome.get("status"),
                           model_called=outcome.get("runner_called") is True,
                           native_calls=None if outcome.get("runner_called") is True else 0)
        return _result("SHADOW_SALIENT_B2_OFFER_PRODUCED",
                       runner_called=True, model_called=True,
                       native_calls=None, offer_packet_persisted=True,
                       offer_packet_id=outcome["offer_packet_id"],
                       query_packet_id=outcome["query_packet_id"],
                       native_model_proven=False,
                       hypothesis_authority="MODEL_HYPOTHESIS_NOT_FACT")
    except (AttributeError, KeyError, TypeError, ValueError, RuntimeError,
            OSError, UnicodeError, OverflowError):
        return _result("SALIENT_B2_OFFER_INTEGRITY_RED")
