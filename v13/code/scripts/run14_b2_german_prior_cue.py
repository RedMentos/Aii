"""German earlier-rule source ordering (OFF, synthetic software candidate).

The original Run12b selector recognizes English 'earlier rules' only. This
candidate applies a conservative, value-free German cue to order *already
verified* B2 source offers before the unchanged cap. It is not a learned
German model, an answer, or an authority decision. No frozen Runtime changes.
"""
import re

from scripts import run12_b2_context_identity_candidate as original
from scripts import run13_b2_identity_ambiguity_guard as guard

REVISION = "b2-german-prior-lexical-shadow-v1"
OLDER = re.compile(r"\b(?:früher(?:e|en|er|es)?|vorherig(?:e|en|er|es)?|alt(?:e|en|er|es)?|ursprünglich(?:e|en|er|es)?)\b", re.I)
RULES = re.compile(r"\b(?:regeln?|vorgaben?|anforderungen?)\b", re.I)
REVISED = re.compile(
    r"\b(?:aktuell\w*|neu\w*|überarbeitet\w*|revidiert\w*|ersetzt\w*)\s+"
    r"(?:verbindlich\w*\s+)?(?:regeln?|vorgaben?|anforderungen?)\b", re.I)
CURRENT_COMPLETE = (
    re.compile(r"\bbudget\s+\d+\s+euros?\b", re.I),
    re.compile(r"\bfrist\s+\d+\s+tage\b", re.I),
    re.compile(r"\blokalpflicht\s+(?:ja|nein)\b", re.I),
)
CUES = (
    re.compile(r"\b(?:regeln?|vorgaben?|anforderungen?)\b", re.I),
    re.compile(r"\bbudget\b", re.I),
    re.compile(r"\bfrist\b", re.I),
    re.compile(r"\blokalpflicht\b", re.I),
)


def german_prior_requested(current):
    """Intent only, never interpret numerical values or binding rule truth."""
    if type(current) is not str:
        return False
    return bool(OLDER.search(current) and RULES.search(current)
                and not REVISED.search(current)
                and not all(rx.search(current) for rx in CURRENT_COMPLETE))


def _score(excerpt):
    # Source selection only: literal words, never values, prices or oracle.
    return 3 * bool(CUES[0].search(excerpt)) + sum(
        bool(rx.search(excerpt)) for rx in CUES[1:])


def select_context(current, current_event_id, session, generation, revision,
                   retained, read_source, cap=768, slots=4, excerpt_chars=240):
    """Source-pointer-only B2 shadow with bounded German rule-cue ordering."""
    if type(retained) is not list or len(retained) > 64 or not callable(read_source):
        raise ValueError("UNBOUNDED_OR_UNVERIFIED_INPUT")
    # Validate all original bounds before any candidate read.
    guard.select_context(current, current_event_id, session, generation, revision,
                         [], read_source, cap=cap, slots=slots,
                         excerpt_chars=excerpt_chars)
    prior = german_prior_requested(current)
    if not prior or len(original.named_entities(current)) != 1:
        result = guard.select_context(current, current_event_id, session,
                                      generation, revision, retained, read_source,
                                      cap=cap, slots=slots,
                                      excerpt_chars=excerpt_chars)
    else:
        bounded = retained[:slots]  # no backfill beyond original horizon
        scores = []
        for item in bounded:
            # A single-offer guard preflight enforces identity, metadata, digest,
            # tombstones, exact excerpt, and no cross-project source admission.
            pre = guard.select_context(current, current_event_id, session,
                                       generation, revision, [item], read_source,
                                       cap=4096, slots=1,
                                       excerpt_chars=excerpt_chars)
            if pre["items"]:
                excerpt = pre["items"][0]["native_context"]["exact_source_excerpt"]
                scores.append(_score(excerpt))
            else:
                scores.append(0)
        order = sorted(range(len(bounded)), key=lambda i: (-scores[i], i))
        ordered = [bounded[i] for i in order]
        result = guard.select_context(current, current_event_id, session,
                                      generation, revision, ordered, read_source,
                                      cap=cap, slots=slots,
                                      excerpt_chars=excerpt_chars)
    result["base_revision"] = guard.REVISION
    result["revision"] = REVISION
    result["german_prior_cue"] = prior
    result["source_priority"] = "VALUE_FREE_WORDS_ONLY" if prior else "UNCHANGED"
    result["authority"] = "SOURCE_POINTER_ONLY"
    result["canonical_gate_pass"] = False
    return result
