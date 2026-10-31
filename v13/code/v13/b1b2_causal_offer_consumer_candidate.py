"""Default-off B1/B2 causal source guard wired to real Cognition.offer in SHADOW.

Not installed into Runtime. A normal synthetic offer is produced via the
unchanged Cognition.offer implementation, but stale replay is refused before
the runner or Query/Offer state can be touched.
"""
from __future__ import annotations
import json

from .cognition import Cognition
from .b1b2_causal_context_candidate import causal_body_context, _bound_user_event


def _result(status, **extra):
    return {"schema": "v13.b1b2_causal_offer_consumer_shadow.v1",
            "status": status, "delivery_authority": 0,
            "learning_authority": 0, "native_proof": False, **extra}


class CausalOfferConsumer(Cognition):
    """Isolated opt-in software consumer; never replace Runtime.cognition live."""

    def body_context(self, role, event):
        result = causal_body_context(
            self.r, role, event, operator_opt_in=True,
            context_reader=super().body_context)
        if result["status"] != "SHADOW_CONTEXT_FILTERED":
            raise ValueError("CAUSAL_CONTEXT_RED")
        return result["context"]

    def guarded_offer(self, role, event, version, deadline, *, operator_opt_in=False):
        if operator_opt_in is not True:
            return _result("OFF", runner_called=False)
        if role not in ("B1_DETAIL", "B2_GIST") or type(event) is not dict:
            return _result("INVALID_ROLE_OR_EVENT", runner_called=False)
        try:
            current = _bound_user_event(self.s, event["event_id"], self.r.session)
            if (event.get("source_ref") != current["source_ref"]
                    or event.get("brain_generation_id") != current["generation"]
                    or current["generation"] != self.s.generation_id):
                raise ValueError("CURRENT_SOURCE_RED")
            state, _ = self.s.state(role + ":" + self.r.session, {})
            pid = state.get("packet_id")
            if pid:
                prior = self.s.one("SELECT event_id,payload FROM packets "
                                   "WHERE id=? AND kind='OfferPacket'", (pid,))
                if not prior:
                    raise ValueError("RETAINED_OFFER_MISSING")
                packet = json.loads(prior["payload"])
                if (packet.get("event_id") != prior["event_id"]
                        or packet.get("role") != role
                        or packet.get("brain_generation_id") != current["generation"]
                        or packet.get("model_revision") != self.r.models.revision(role)):
                    raise ValueError("RETAINED_OFFER_BINDING_RED")
                previous = _bound_user_event(self.s, prior["event_id"], self.r.session)
                if previous["message_id"] >= current["message_id"]:
                    return _result("STALE_REPLAY_NO_OFFER", runner_called=False)
        except Exception:
            return _result("EVENT_OR_RETAINED_STATE_RED", runner_called=False)
        try:
            offer = super().offer(role, event, version, deadline)
        except Exception:
            return _result("OFFER_ERROR_NO_DELIVERY", runner_called=True)
        return _result("SHADOW_OFFER_PRODUCED", runner_called=True,
                       offer_packet_id=offer["packet_id"],
                       query_packet_id=offer["query_packet_id"])
