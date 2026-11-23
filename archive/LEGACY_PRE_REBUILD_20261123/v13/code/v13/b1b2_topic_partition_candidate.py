"""Isolated opt-in, project-scoped B1/B2 retained state for synthetic software tests.

The frozen Cognition.offer and Store are unchanged. This is not installed into
Runtime. Topic inference is deliberately conservative and cannot authorize
live output, learning or native deployment.
"""
from __future__ import annotations

import hashlib
import json

from .b1b2_causal_context_candidate import _bound_user_event, _project_scope
from .b1b2_causal_offer_consumer_candidate import CausalOfferConsumer, _result


class _TopicStateView:
    """Delegate all Store operations except the *one* role/session state slot.

    Per-invocation views avoid monkeypatching the shared Runtime Store. Legacy
    unscoped state remains intact and is never consulted for this role.
    """

    def __init__(self, store, role, session, generation, revision, topic):
        self._store = store
        self._legacy_key = role + ":" + session
        identity = json.dumps(
            ["v1", session, generation, role, revision, topic],
            ensure_ascii=True, separators=(",", ":"))
        self.partition_key = "shadow:b1b2_topic:v1:" + hashlib.sha256(
            identity.encode("utf-8")).hexdigest()

    def _key(self, key):
        return self.partition_key if key == self._legacy_key else key

    def state(self, key, default=None):
        return self._store.state(self._key(key), default)

    def set_state(self, key, payload, expected=None):
        return self._store.set_state(self._key(key), payload, expected)

    def __getattr__(self, name):
        return getattr(self._store, name)


class TopicPartitionOfferConsumer:
    """Use the real causal-guarded Cognition.offer with a per-topic Store view."""

    def __init__(self, runtime):
        self.r = runtime

    def guarded_offer(self, role, event, version, deadline, *,
                      operator_opt_in=False):
        if operator_opt_in is not True:
            return _result("OFF", runner_called=False)
        if role not in ("B1_DETAIL", "B2_GIST") or type(event) is not dict:
            return _result("INVALID_ROLE_OR_EVENT", runner_called=False)
        try:
            current = _bound_user_event(
                self.r.store, event["event_id"], self.r.session)
            if (event.get("source_ref") != current["source_ref"]
                    or event.get("brain_generation_id") != current["generation"]
                    or current["generation"] != self.r.store.generation_id):
                raise ValueError("CURRENT_SOURCE_RED")
            scope = _project_scope(current["text"])
            if len(scope) != 1:
                return _result("TOPIC_SCOPE_RED", runner_called=False)
            topic = next(iter(scope))
            view = _TopicStateView(
                self.r.store, role, self.r.session, current["generation"],
                self.r.models.revision(role), topic)
            worker = CausalOfferConsumer(self.r)
            worker.s = view
            result = worker.guarded_offer(
                role, event, version, deadline, operator_opt_in=True)
            return dict(result, topic_partitioned=True,
                        partition_key_sha256=view.partition_key.rsplit(":", 1)[1])
        except Exception:
            return _result("EVENT_OR_TOPIC_RED", runner_called=False)
