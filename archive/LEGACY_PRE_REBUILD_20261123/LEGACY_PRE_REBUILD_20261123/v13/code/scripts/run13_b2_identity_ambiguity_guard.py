"""Conservative cross-project source admission around Run12b B2 selector (OFF).

Review-only, software/synthetic; no frozen Runtime modification or native claim.
A mention of another named project is not an authorization to retrieve its
rules. This guard refuses ambiguous requests and ambiguous source spans.
It preserves the original B2 state-slot horizon, cap, and source-reader contract.
"""
from collections import Counter
import re

from scripts import run12_b2_context_identity_candidate as base

REVISION = "b2-source-identity-single-project-review-v1"


def _empty(reason, n):
    return {"revision": REVISION, "base_revision": base.REVISION,
            "items": [], "reasons": {reason: n},
            "authority": "SOURCE_POINTER_ONLY", "canonical_gate_pass": False}


def select_context(current, current_event_id, session, generation, revision,
                   retained, read_source, cap=768, slots=4, excerpt_chars=240):
    """Read-only single-project source selector.

    Refuse any current request naming multiple projects, including negated
    mentions (e.g. 'ignore Project Atlas'). For each of the original newest
    slots offers, require a single, matching named project in the verified
    source span. Metadata-out-of-scope offers are not read. The underlying
    Run12b selector still validates source refs, excerpt re-reads, duplicate
    IDs, generation, session, model, tombstones and output cap. A caller must
    supply Store.read_source or an equivalently hash-verified source reader.
    """
    if type(retained) is not list or len(retained) > 64 or not callable(read_source):
        raise ValueError("UNBOUNDED_OR_UNVERIFIED_INPUT")

    # Validate all original numerical bounds and text type before any read.
    base.select_context(current, current_event_id, session, generation, revision,
                        [], read_source, cap=cap, slots=slots,
                        excerpt_chars=excerpt_chars)
    entities = base.named_entities(current)
    if len(entities) != 1:
        return _empty("AMBIGUOUS_CURRENT_IDENTITY" if entities else
                      "NO_CURRENT_NAMED_ENTITY", len(retained))
    project = next(iter(entities))
    accepted = []
    reasons = Counter()
    # Never refill from beyond the original B2 slot horizon after rejection.
    for item in retained[:slots]:
        if type(item) is not dict:
            accepted.append(item)  # base records BAD_ITEM
            continue
        if (item.get("role") != "B2_GIST" or item.get("session") != session or
                item.get("generation") != generation or
                item.get("model_revision") != revision or
                item.get("event_id") == current_event_id):
            accepted.append(item)  # base records OUT_OF_SCOPE; do not read
            continue
        ref = item.get("source_ref")
        if (type(ref) is not dict or type(ref.get("source_id")) is not str or
                type(ref.get("sha256")) is not str or
                re.fullmatch(r"[0-9a-f]{64}", ref["sha256"]) is None or
                type(ref.get("char_start")) is not int or
                type(ref.get("char_end")) is not int or
                ref["char_start"] < 0 or
                ref["char_end"] < ref["char_start"] or
                ref["char_end"] - ref["char_start"] > base.MAX_SOURCE_CHARS or
                ref.get("modality") != "text"):
            accepted.append(item)  # base records BAD_REF
            continue
        try:
            source = read_source(ref)
            identities = base.named_entities(source)
        except (KeyError, LookupError, ValueError, OSError, TypeError):
            reasons["SOURCE_UNAVAILABLE"] += 1
            continue
        if len(identities) != 1:
            reasons["AMBIGUOUS_SOURCE_IDENTITY"] += 1
            continue
        if project not in identities:
            reasons["PROJECT_MISMATCH"] += 1
            continue
        accepted.append(item)

    result = base.select_context(current, current_event_id, session,
                                 generation, revision, accepted, read_source,
                                 cap=cap, slots=slots, excerpt_chars=excerpt_chars)
    merged = Counter(result["reasons"])
    merged.update(reasons)
    result["reasons"] = dict(merged)
    result["base_revision"] = base.REVISION
    result["revision"] = REVISION
    result["authority"] = "SOURCE_POINTER_ONLY"
    result["canonical_gate_pass"] = False
    return result
