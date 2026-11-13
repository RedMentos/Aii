"""Deadline-aware native prompt admission for the V13 phone.

This is a *loss-aware* budget governor, not hallucinated semantic compression.
Never rewrites the latest user source, system/conduct/operator rules, trusted
tool results or selected B1/B2 hypotheses. Removable context is explicitly
labelled as omitted in native metrics. Original source/packet lineage stays in
SQLite; this module only makes a bounded model-facing view.

The token-rate constant is a conservative BOOT policy for Redmi validation,
not a measured device speed. A prompt whose protected content cannot be
reduced is admitted with an explicit UNSATISFIED result; we never truncate
protected text in order to claim a success.
"""
from __future__ import annotations

import json
import math
from .prompts import text as prompt

REVISION = "v13.native-prompt-admission/1"
# Ordered from redundant system state to progressively useful historical cues.
REMOVABLE_C3 = ("task_context", "digest", "user_model")
HEADINGS = ("memories", "hypotheses", "digest", "task_context", "user_model",
            "clarify", "duplex_handoff")


def soft_limit(role, cfg, remaining):
    """BOOT token cap: reserve output/decode time before full native prefill."""
    if role not in ("C3_LANGUAGE", "B1_DETAIL", "B2_GIST"):
        return None
    if (type(remaining) not in (int, float) or not math.isfinite(remaining)
            or remaining >= 55 or remaining <= 0):
        return None
    # B1/B2 output is JSON-constrained. The native phase budget includes
    # grammar generation; C3 needs first-token and answer reserve as well.
    reserved = 10 if role == "C3_LANGUAGE" else 9
    n = int(max(0, remaining-reserved) * 13)
    return max(96, min(520, n))


def _remove_c3_layer(messages, cfg):
    if not messages or messages[0].get("role") != "system":
        return None
    system = messages[0].get("content")
    if not isinstance(system, str):
        return None
    stable = (prompt(cfg, "system") + " " + prompt(cfg, "conduct") + " " +
              prompt(cfg, "answer_rules"))
    if not system.startswith(stable):
        return None  # Unknown template: never cut a potentially pinned rule.
    heads = {name: "\n" + prompt(cfg, name) for name in HEADINGS}
    for name in REMOVABLE_C3:
        head = heads[name]
        start = system.find(head, len(stable))
        if start < 0:
            continue
        end = len(system)
        for other in heads.values():
            if other == head:
                continue
            pos = system.find(other, start+len(head))
            if pos >= 0:
                end = min(end, pos)
        # Only remove complete, typed JSON layers. Unknown template sections
        # or partially serialized JSON must remain untouched.
        try:
            json.loads(system[start+len(head):end].strip())
        except (ValueError, TypeError):
            continue
        result = [dict(x) for x in messages]
        result[0]["content"] = system[:start] + system[end:]
        return result, "C3_LAYER_" + name.upper()
    return None


def _remove_body_metadata(messages):
    if (len(messages) != 2 or messages[0].get("role") != "system"
            or messages[1].get("role") != "user"):
        return None
    try:
        original = json.loads(messages[1].get("content", ""))
    except (TypeError, ValueError):
        return None
    if not isinstance(original, dict) or not isinstance(original.get("source_segments"), list):
        return None
    item = json.loads(json.dumps(original))
    segments = item["source_segments"]
    # First strip *opaque source-address metadata* from the model view only.
    # The real sources, refs and hashes remain immutable in Query/Offer packets.
    if all(isinstance(x, dict) and isinstance(x.get("text"), str) for x in segments):
        if any("source_ref" in x for x in segments):
            for segment in segments:
                segment.pop("source_ref", None)
            reason = "BODY_SOURCE_ADDRESS_METADATA"
        elif isinstance(item.get("executive_broadcast"), dict) and "source_refs" in item["executive_broadcast"]:
            item["executive_broadcast"].pop("source_refs")
            reason = "BODY_DUPLICATE_EXECUTIVE_SOURCE_REFS"
        else:
            reason = None
    else:
        return None
    if reason is None and isinstance(item.get("body_state"), dict):
        body = item["body_state"]
        world = body.get("world")
        own = body.get("self")
        reduced = {k:body[k] for k in ("authority", "role") if k in body}
        if isinstance(world, dict):
            reduced["world"] = {k:world[k] for k in ("mode","observed_actions") if k in world}
        if isinstance(own, dict):
            reduced["self"] = {k:own[k] for k in ("external_tools","learning","system_stage") if k in own}
        if len(json.dumps(reduced)) < len(json.dumps(body)):
            item["body_state"] = reduced
            reason = "BODY_NON_SOURCE_STATE_DETAIL"
    if reason is None and isinstance(item.get("detail_windows"), list):
        exact = " ".join(x["text"] for x in segments)
        windows = item["detail_windows"]
        if windows and all(isinstance(x,str) and x in exact for x in windows):
            item.pop("detail_windows")
            reason = "BODY_DUPLICATE_EXACT_DETAIL_WINDOWS"
    if reason is None:
        return None
    # Strict source-integrity check: model gets the exact same source text and
    # the same peer-message content; never compress arbitrary source words.
    if ([s.get("text") for s in item["source_segments"]] !=
            [s.get("text") for s in original["source_segments"]] or
            item.get("peer_message") != original.get("peer_message")):
        return None
    result = [dict(x) for x in messages]
    result[1]["content"] = json.dumps(item, ensure_ascii=False, sort_keys=True,
                                      separators=(",", ":"))
    return result, reason


def reduce_once(messages, role, cfg):
    """Return (new messages, exact omission reason) or None, no silent clipping."""
    if role == "C3_LANGUAGE":
        candidate = _remove_c3_layer(messages, cfg)
        if candidate:
            return candidate
        # Oldest dialogue is a lower priority than the current exact input
        # and the current C4-selected body evidence.
        if len(messages) > 2:
            return ([dict(messages[0]), *[dict(x) for x in messages[2:]]],
                    "OLD_NATIVE_HISTORY")
    elif role in ("B1_DETAIL", "B2_GIST"):
        return _remove_body_metadata(messages)
    return None
