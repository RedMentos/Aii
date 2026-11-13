"""Liminal/Stream-A function: source-bound multi-timescale context fusion.

This is the *executable symbolic bootstrap* for the old Liminal/Stream-A
requirement and B4 distributed-state interface. It is not a trained JEPA
manifold, a native KV cache, a replacement for B1/B2, a fact database or a
second independent chat agent.

L0 working semantic cues -> L1 meso timescale -> L2 slow gist cues. Concepts
are lossy, but exact source references are held separately and revalidated
before a cue can influence C3. Opposing B1/B2 private representations are
never averaged into a fictitious shared truth. This module cannot modify
native model weights, tool rights, Age, source content, or permission policy.
"""
from __future__ import annotations

from collections import Counter
import hashlib
import math
import re

SCHEMA = "v13.liminal-context/1"
STATE_PREFIX = "LIMINAL_SPACE:"
ROLE_SET = frozenset(("B1_DETAIL", "B2_GIST", "MEMORY"))
LEVELS = ("working", "meso", "slow")
CAPS = {"working": 12, "meso": 12, "slow": 8}
MAX_REFS = 5
MAX_TERMS = 20
MAX_ITEMS = 32
MAX_TEXT = 600
READ_CONTEXT_CAP = 2700
SOURCE_QUOTE_CAP = 190
SIMILARITY_THRESHOLD = 0.48
STOPWORDS = frozenset((
    "the","and","for","with","from","are","was","were","this","that",
    "und","der","die","das","den","dem","ein","eine","einer","einem",
    "ist","sind","auf","mit","von","für","oder","aber","also","dass",
    "you","your","our","not","nicht","nur","noch","auch","über","unter",
    "their","have","has","had","than","then","into","seine","seinen",
))
WORDS = re.compile(r"(?u)\b[\wÄÖÜäöüß]{3,}\b")


def terms(value):
    """Lossy lexical surface. NEVER an evidentiary assertion."""
    if not isinstance(value, str):
        return {}
    c = Counter(w.casefold() for w in WORD.findall(value[:MAX_TEXT]) if
                w.casefold() not in STOPWORDS)
    return dict(sorted(c.items(), key=lambda x: (-x[1], x[0]))[:MAX_TERMS])


def similarity(a, b):
    """Weighted cosine of bounded sparse semantics, no learned claims."""
    if not a or not b:
        return 0.0
    keys = set(a) & set(b)
    dot = sum(a[k] * b[k] for k in keys)
    norm = math.sqrt(sum(v*v for v in a.values()) *
                     sum(v*v for v in b.values()))
    return dot / norm if norm else 0.0


def numeric_set(ts):
    return {key for key in ts if key.isdigit()}


def mergeable(a, b):
    # Preserve fine/coarse diversity and numerical disagreements.
    if a["role"] != b["role"] or a["authority"] != b["authority"]:
        return False
    na, nb = numeric_set(a["terms"]), numeric_set(b["terms"])
    if na and nb and na != nb:
        return False
    return similarity(a["terms"], b["terms"]) >= SIMILARITY_THRESHOLD


def _refs_valid(store, refs):
    out = []
    for ref in refs[:MAX_REFS]:
        if not isinstance(ref, dict) or ref.get("modality") != "text":
            continue
        try:
            restored = store.read_source(ref)
        except (OSError, ValueError, KeyError, TypeError, UnicodeError):
            continue
        if restored is not None:
            out.append((ref, restored))
    return out


def _make_id(role, payload_ref, source_refs):
    digest = hashlib.sha256((role + ":" + str(payload_ref) + ":" +
                             ":".join(r.get("source_id", "") for r in source_refs)).encode()).hexdigest()
    return digest[:24]


def _normal_form(node):
    if not isinstance(node, dict):
        return None
    if (node.get("role") not in ROLE_SET or node.get("level") not in LEVELS or
            node.get("authority") not in ("MODEL_HYPOTHESIS", "MEMORY_CUE") or
            not isinstance(node.get("source_refs"), list) or
            not isinstance(node.get("terms"), dict) or
            type(node.get("n")) is not int or not 1 <= node["n"] <= 1000000 or
            not isinstance(node.get("anchor_id"), str) or
            not isinstance(node.get("event_id"), str)):
        return None
    node = dict(node)
    node["terms"] = {k: v for k, v in list(node["terms"].items())[:MAX_TERMS]
                     if isinstance(k, str) and 3 <= len(k) <= 36 and
                     type(v) is int and 0 < v <= 1000000}
    node["source_refs"] = node["source_refs"][:MAX_REFS]
    return node if node["terms"] and node["source_refs"] else None


def _combine(a, b, level):
    counts = Counter(a["terms"])
    counts.update(b["terms"])
    refs = []
    seen = set()
    for ref in b["source_refs"] + a["source_refs"]:
        sig = ref.get("source_id") if isinstance(ref, dict) else None
        if sig and sig not in seen:
            seen.add(sig)
            refs.append(ref)
        if len(refs) == MAX_REFS:
            break
    return {
        "id": _make_id(a["role"], a["anchor_id"], refs),
        "level": level,
        "role": a["role"],
        "authority": a["authority"],
        "anchor_id": b["anchor_id"],
        "event_id": b["event_id"],
        "n": min(1000000, a["n"] + b["n"]),
        "terms": dict(sorted(counts.items(), key=lambda x: (-x[1], x[0]))[:MAX_TERMS]),
        "source_refs": refs,
    }


def _admit(levels, record):
    """Similarity-conditional recurrent coactivation + slow promotion.

    Dissimilar cues are never force-merged. This preserves contradictory
    hypotheses even under memory pressure. Old pointers may be dropped from
    the *working context*, but their original source blobs are not deleted.
    """
    level = record["level"]
    slot = levels[level]
    best = max(
        (i for i, old in enumerate(slot) if mergeable(old, record)),
        key=lambda i: similarity(slot[i]["terms"], record["terms"]),
        default=None,
    )
    if best is not None:
        previous = slot.pop(best)
        record = _combine(previous, record, level)
    slot.append(record)
    if len(slot) > CAPS[level]:
        promoted = slot.pop(0)
        index = LEVELS.index(level)
        if index + 1 < len(LEVELS):
            promoted = dict(promoted, level=LEVELS[index + 1])
            _admit(levels, promoted)
    return record


class LiminalSpace:
    """One session's layered semantic context. No user text in telemetry."""

    def __init__(self, store, session):
        self.store = store
        self.key = STATE_PREFIX + str(session)

    def _load(self, generation):
        raw, version = self.store.state(self.key, {})
        if not isinstance(raw, dict) or raw.get("schema") != SCHEMA or raw.get("generation") != generation:
            return {"schema": SCHEMA, "generation": generation,
                    "levels": {level: [] for level in LEVELS}, "observations": 0}, version
        src = raw.get("levels", {})
        layers = {}
        for level in LEVELS:
            rows = src.get(level, []) if isinstance(src, dict) else []
            layers[level] = [x for z in rows[:CAPS[level]]
                             if (x := _normal_form(z)) and x["level"] == level] if isinstance(rows, list) else []
        return {"schema": SCHEMA, "generation": generation, "levels": layers,
                "observations": max(0, min(1_000_000, int(raw.get("observations", 0))))}, version

    def observe(self, event, coalition):
        """Capture *focally admitted* B1/B2/MEMORY cues, never unselected drafts.

        Local state adaptation is allowed in Age0 RECORD_ONLY: it does not
        update any native weights or grant semantic/factual authority.
        """
        eid, generation = event["event_id"], event["brain_generation_id"]
        state, version = self._load(generation)
        accepted = 0
        for item in coalition[:MAX_ITEMS]:
            if not isinstance(item, dict) or item.get("source_kind") not in ROLE_SET:
                continue
            if item.get("origin_event_id") != eid or item.get("state_type") != "ACTIVE":
                continue
            content = item.get("text")
            if not isinstance(content, str):
                continue
            semantic = terms(content)
            if not semantic:
                continue
            pairs = _refs_valid(self.store, item.get("source_refs") or [])
            if not pairs:
                continue
            refs = [ref for ref, _ in pairs]
            role = item["source_kind"]
            pid = item.get("payload_ref")
            if not isinstance(pid, str):
                continue
            record = {
                "id": _make_id(role, pid, refs),
                "level": "working",
                "role": role,
                "authority": "MEMORY_CUE" if role == "MEMORY" else "MODEL_HYPOTHESIS",
                "anchor_id": pid,
                "event_id": eid,
                "n": 1,
                "terms": semantic,
                "source_refs": refs,
            }
            _admit(state["levels"], record)
            accepted += 1
        if accepted:
            state["observations"] = min(1_000_000, state["observations"] + 1)
            self.store.set_state(self.key, state, expected=version)
        return {"admitted": accepted, "revision": SCHEMA, "weights_modified": False}

    def view(self, event, query, *, limit=4, exact_limit=2):
        """Source-revalidate *before* exposing any cue to C3.

        Neither a lexical coincidence nor a compressed model hypothesis is
        truth. Return source text separately, with explicit nonfact labels.
        """
        if not isinstance(query, str):
            raise ValueError("query must be text")
        if type(limit) is not int or not 0 <= limit <= 8:
            raise ValueError("invalid liminal read budget")
        if type(exact_limit) is not int or not 0 <= exact_limit <= 4:
            raise ValueError("invalid exact restoration budget")
        state, version = self._load(event["brain_generation_id"])
        qterms = terms(query)
        candidates = []
        for level in LEVELS:
            for i, node in enumerate(state["levels"][level]):
                if node["event_id"] == event["event_id"]:
                    continue  # current event already has fresh B1/B2 Offers
                valid = _refs_valid(self.store, node["source_refs"])
                if not valid:
                    continue
                score = similarity(qterms, node["terms"])
                # Even exact-need with no lexical overlap must not invent a hit.
                if qterms and score < .10:
                    continue
                candidates.append((round(score, 5), LEVELS.index(level),
                                   i, node, valid))
        candidates.sort(key=lambda row: (row[0], row[1], row[2]), reverse=True)
        result = []
        total_chars = 0
        for score, _, _, node, valid in candidates[:limit]:
            excerpts = []
            for ref, text in valid[:exact_limit]:
                if total_chars + len(text) > READ_CONTEXT_CAP:
                    text = text[:max(0, min(SOURCE_QUOTE_CAP, READ_CONTEXT_CAP-total_chars))]
                else:
                    text = text[:SOURCE_QUOTE_CAP]
                if text:
                    excerpts.append({"source_ref": ref, "exact_text": text})
                    total_chars += len(text)
            cues = list(node["terms"])[:12]
            if not cues and not excerpts:
                continue
            result.append({
                "scale": node["level"],
                "role": node["role"],
                "truth_authority": "NOT_A_FACT" if node["authority"] == "MODEL_HYPOTHESIS" else "MEMORY_CUE_VERIFY",
                "semantic_terms": cues,
                "recurrence": node["n"],
                "relevance": score,
                "exact_sources": excerpts,
            })
        return {
            "schema": SCHEMA,
            "representation": "SYMBOLIC_SOURCE_BOUND_NOT_TRAINED_LATENT",
            "native_jepa_trained": False,
            "generation": event["brain_generation_id"],
            "state_version": version,
            "observations": state["observations"],
            "counts": {level: len(state["levels"][level]) for level in LEVELS},
            "contexts": result,
            "source_refs": [x["source_ref"] for hit in result for x in hit["exact_sources"]],
        }

    def report(self, generation):
        state, v = self._load(generation)
        return {"schema": SCHEMA, "representation": "SYMBOLIC_SOURCE_BOUND_NOT_TRAINED_LATENT",
                "native_jepa_trained": False, "state_version": v,
                "observations": state["observations"],
                "counts": {level: len(state["levels"][level]) for level in LEVELS},
                "weights_modified": False}
