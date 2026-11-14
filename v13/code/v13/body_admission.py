"""Bounded optional context admission for Redmi body inference.

Never edits the current source, peer message, or JEF question. Optional
self/world/older hypotheses are lower authority than current evidence.
"""
import json

OPTIONAL = (
    "self_corollary", "jef_broadcast", "body_state", "executive_broadcast",
    "prior_hypothesis", "earlier_context", "recent_source",
    "detail_windows", "local_gist", "quote_choices",
)

def admit(query, *, max_optional_chars=320):
    """Return a new query and explicit drop receipt, without changing source/peer.

    No source is silently truncated. The caller retains the full QueryPacket
    source pointer and can inspect the dropped optional fields.
    """
    if type(query) is not dict or type(max_optional_chars) is not int or max_optional_chars < 0:
        raise ValueError("invalid body admission request")
    result = dict(query)
    removed = []
    def size(value):
        return len(json.dumps(value, ensure_ascii=False, separators=(",", ":")))
    optional_size = sum(size(result[k]) for k in OPTIONAL if k in result)
    for key in OPTIONAL:
        if optional_size <= max_optional_chars:
            break
        if key in result:
            optional_size -= size(result.pop(key))
            removed.append(key)
    return result, {"removed_optional_fields": removed,
                    "remaining_optional_chars": optional_size,
                    "current_source_preserved": result.get("source_segments") == query.get("source_segments")
                        and result.get("gist_slots") == query.get("gist_slots"),
                    "peer_preserved": result.get("peer_message") == query.get("peer_message")}
