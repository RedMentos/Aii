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
from .context_os import VOLATILE_HEAD

REVISION = "v13.native-prompt-admission/1"
# Ordered from redundant system state to progressively useful historical cues.
REMOVABLE_C3 = ("task_context", "digest", "user_model")
def soft_limit(role, cfg, remaining):
    """BOOT token cap: reserve output/decode time before full native prefill."""
    if role not in ("C3_LANGUAGE", "B1_DETAIL", "B2_GIST"):
        return None
    if (type(remaining) not in (int, float) or not math.isfinite(remaining)
            or remaining <= 0):
        return None
    # C3 always has a bounded first-prefill envelope, even when the overall
    # turn deadline is generous. This is a BOOT latency policy, not a claim
    # about measured Redmi token rate. B1/B2 keep their existing short-window
    # policy until real device timings justify changing their admission.
    if role == "C3_LANGUAGE":
        reserved = 10
    else:
        if remaining >= 55:
            return None
        reserved = 9
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
    # With Context OS ACTIVE the volatile blocks can be a separate user
    # message immediately before the current question. This is reference
    # material, not an old chat turn; it can contain selected B1/B2 offers
    # and exact tool output.
    layers = [(0, len(stable))]
    if (len(messages) >= 3 and messages[-1].get("role") == "user"
            and messages[-2].get("role") == "user"
            and isinstance(messages[-2].get("content"), str)
            and messages[-2]["content"].startswith(VOLATILE_HEAD + "\n")):
        layers.append((len(messages)-2, len(VOLATILE_HEAD)))

    decoder = json.JSONDecoder()
    for name in REMOVABLE_C3:
        head = "\n" + prompt(cfg, name)
        for index, offset in layers:
            content = messages[index]["content"]
            start = content.find(head, offset)
            if start < 0:
                continue
            # Parse exactly one JSON value. Searching for another known
            # heading as the end would also delete unknown sections and
            # exact tool output following this layer.
            value_start = start + len(head)
            while value_start < len(content) and content[value_start] in " \t\r":
                value_start += 1
            try:
                _, end = decoder.raw_decode(content, value_start)
            except (ValueError, TypeError):
                continue
            tail = end
            while tail < len(content) and content[tail] in " \t\r":
                tail += 1
            if tail < len(content) and content[tail] != "\n":
                continue  # Ambiguous, incomplete framing: preserve it.
            result = [dict(x) for x in messages]
            result[index]["content"] = content[:start] + content[end:]
            return result, "C3_LAYER_" + name.upper()
    return None


def _remove_old_turn(messages):
    """Drop one complete, recognizable old turn; keep the current input.

    The append-only layout may include a reference block before each old
    question and answer. Remove all three together or leave all three intact.
    Unknown message order/fields are not assumed to be disposable history.
    """
    if (len(messages) < 4 or messages[0].get("role") != "system"
            or messages[-1].get("role") != "user"):
        return None
    first, second = messages[1:3]
    def simple(message, role):
        return (type(message) is dict and set(message) == {"role", "content"}
                and message["role"] == role and isinstance(message["content"], str))
    if not simple(first, "user"):
        return None
    if first["content"].startswith(VOLATILE_HEAD):
        if (len(messages) < 5 or not first["content"].startswith(VOLATILE_HEAD + "\n")
                or not simple(second, "user") or not simple(messages[3], "assistant")):
            return None
        end = 4
    elif simple(second, "assistant"):
        end = 3
    else:
        return None
    return ([dict(messages[0]), *[dict(x) for x in messages[end:]]],
            "OLD_NATIVE_HISTORY")


def _remove_body_metadata(messages):
    if (len(messages) != 2 or messages[0].get("role") != "system"
            or messages[1].get("role") != "user"):
        return None
    try:
        original = json.loads(messages[1].get("content", ""))
    except (TypeError, ValueError):
        return None
    if not isinstance(original, dict):
        return None
    # B2 can receive GIST slots rather than A1 segments. Each holds exact
    # source text and a separate persisted source pointer.
    source_key = ("source_segments" if isinstance(original.get("source_segments"), list)
                  else "gist_slots" if isinstance(original.get("gist_slots"), list)
                  else None)
    if source_key is None:
        return None
    item = json.loads(json.dumps(original))
    segments = item[source_key]
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
    if reason is None and isinstance(item.get("enlightened_space"), dict):
        shared = item["enlightened_space"]
        rows = shared.get("messages")
        if isinstance(rows, list) and all(isinstance(row, dict) for row in rows):
            # The real shared-space consumer already checked every source
            # and packet. B1/B2 need its ORGAN CONTENT and exact excerpts,
            # not repeated 64-byte digests and database addresses. This is
            # still one inter-organ context, never separate chatbot prompts.
            compact = []
            for row in rows:
                keep = {k:row[k] for k in (
                    "from", "channel", "authority", "semantic_cue_not_fact")
                    if k in row}
                sources = row.get("exact_sources", [])
                if not isinstance(sources, list) or not all(
                    isinstance(x,dict) and isinstance(x.get("exact_source_text"),str)
                    for x in sources):
                    compact = []
                    break
                keep["exact_sources"] = [
                    {"exact_source_text":x["exact_source_text"],
                     "verification":x.get("verification","RECHECKED_EXACT_BYTES")}
                    for x in sources]
                if row.get("time_scale") in ("MEDIUM", "SLOW"):
                    keep["time_scale"] = row["time_scale"]
                if type(row.get("coactivations")) is int and row["coactivations"] > 1:
                    keep["coactivations"] = row["coactivations"]
                compact.append(keep)
            if compact:
                compressed = {
                    "representation":shared.get("representation"),
                    "messages":compact,
                    "authority":"SOURCE_REFS_REVALIDATED_BEFORE_VIEW_NO_NEW_FACTS"}
                if len(json.dumps(compressed)) < len(json.dumps(shared)):
                    item["enlightened_space"] = compressed
                    reason = "BODY_GLOBAL_SPACE_POINTER_METADATA"
    if reason is None and isinstance(item.get("enlightened_space"), dict):
        # After pointer metadata compaction, the A/Stream A/Stream B exact
        # source pointers may *still* echo source_segments or gist_slots.
        # Remove only a verified duplicate of the already retained exact
        # source, never original B1/B2/B3/JEF/World/Self or memory content.
        shared = item["enlightened_space"]
        rows = shared.get("messages")
        if isinstance(rows,list):
            exact = "".join(x["text"] for x in segments)
            preserved = []
            for row in rows:
                if not isinstance(row,dict):
                    preserved.append(row)
                    continue
                excerpts=row.get("exact_sources")
                duplicate = (
                    row.get("from") in ("A_PERCEPTION","STREAM_A","STREAM_B")
                    and row.get("authority") == "SOURCE_POINTER"
                    and isinstance(excerpts,list) and len(excerpts)>0
                    and all(isinstance(x,dict) and isinstance(x.get("exact_source_text"),str)
                            and x["exact_source_text"] and
                            x["exact_source_text"] in exact for x in excerpts))
                if not duplicate:
                    preserved.append(row)
            if len(preserved) < len(rows):
                shared["messages"] = preserved
                reason = "BODY_DUPLICATE_STREAM_SOURCE"
    if reason is None and isinstance(item.get("self_corollary"), dict):
        corollary = item["self_corollary"]
        history = corollary.get("recent_own_action_outcomes")
        if isinstance(history,list) and len(history) > 1:
            # Keep the most recent committed self-action outcome, but do not
            # erase the original persisted self-model or invent new outcomes.
            item["self_corollary"] = dict(corollary,
                recent_own_action_outcomes=history[:1],
                more_own_action_outcomes_in_store=len(history)-1)
            reason = "BODY_OLDER_SELF_OUTCOMES_NOT_IN_NATIVE_VIEW"
    if reason is None:
        return None
    # Strict source-integrity check: model gets the exact same source text and
    # the same peer-message content; never compress arbitrary source words.
    if ([seg.get("text") for seg in item[source_key]] !=
            [seg.get("text") for seg in original[source_key]] or
            item.get("peer_message") != original.get("peer_message") or
            item.get("jef_query") != original.get("jef_query") or
            item.get("quote_choices") != original.get("quote_choices")):
        return None
    result = [dict(x) for x in messages]
    result[1]["content"] = json.dumps(item, ensure_ascii=False, sort_keys=True,
                                      separators=(",", ":"))
    return result, reason


def reduce_once(messages, role, cfg, *, allow_old_turn=True):
    """Return (new messages, exact omission reason) or None, no silent clipping.

    Normal C3 turns may remove explicitly redundant control layers but retain
    complete history when the prefill target is only a soft latency envelope.
    Whole old turns are removable only when the caller's remaining deadline is
    already in the short-window recovery band.
    """
    if type(allow_old_turn) is not bool:
        raise TypeError("allow_old_turn must be bool")
    # Unknown message fields can carry semantics outside this admission
    # contract. Preserve all content instead of guessing which part is optional.
    if any(type(message) is not dict or set(message) != {"role", "content"}
           for message in messages):
        return None
    if role == "C3_LANGUAGE":
        candidate = _remove_c3_layer(messages, cfg)
        if candidate:
            return candidate
        return _remove_old_turn(messages) if allow_old_turn else None
    elif role in ("B1_DETAIL", "B2_GIST"):
        return _remove_body_metadata(messages)
    return None
