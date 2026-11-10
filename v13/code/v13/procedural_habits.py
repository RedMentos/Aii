"""Read-only, source-bound discovery of repeated text procedures from FINAL turns.

V13 can recognise a *candidate* numbered output habit, not autonomously
promote it. Input is the local authoritative Store history for the selected
session only. The candidate is re-rendered and compared byte-for-byte with
each observed FINAL output. No hidden model calls, eval, code execution,
network access or tool authority are granted.

A single confirmed sequence permits only a *literal* numbered pattern.
Two distinct sequences with the same skeleton and different constant values
permit a {value} placeholder, but still require local human SHA approval.
"""
from __future__ import annotations

import hashlib
import re

from .procedural_batch import (
    MAX_TEMPLATE_BYTES, ProceduralBatch, _parts, _render,
)

MAX_SOURCE_BYTES = 16_384
MAX_OBSERVED_ROWS = 64
MIN_OBSERVED_ROWS = 4
MAX_HISTORY = 64
MAX_EVIDENCE = 3
_COUNTER = re.compile(r"[0-9]{1,8}")


def _escape(text):
    return text.replace("{", "{{").replace("}", "}}")


def _extract(text):
    """Find exactly one 1-indexed counter across multiple constant-format rows."""
    if not isinstance(text, str) or not text.endswith("\n"):
        return None
    if len(text.encode("utf-8")) > MAX_SOURCE_BYTES:
        return None
    lines = text.splitlines(keepends=True)
    if not MIN_OBSERVED_ROWS <= len(lines) <= MAX_OBSERVED_ROWS:
        return None
    if any(not line.endswith("\n") or "\r" in line or not line[:-1] for line in lines):
        return None
    matches = []
    first = lines[0][:-1]
    for num in _COUNTER.finditer(first):
        if num.group() != "1":
            continue
        prefix, suffix = first[:num.start()], first[num.end():]
        if all(line == prefix + str(i) + suffix + "\n"
               for i, line in enumerate(lines, 1)):
            template = _escape(prefix) + "{i}" + _escape(suffix)
            try:
                parts = _parts(template)
            except ValueError:
                continue
            if all(_render(parts, i, "") == line
                   for i, line in enumerate(lines, 1)):
                matches.append((prefix, suffix, template))
    # Ambiguity (two counters in one row): refuse rather than guess.
    if len(matches) != 1:
        return None
    prefix, suffix, template = matches[0]
    return {"prefix": prefix, "suffix": suffix,
            "template": template, "rows": len(lines)}


def _common_prefix(a, b):
    n = 0
    for left, right in zip(a, b):
        if left != right:
            break
        n += 1
    return a[:n]


def _common_suffix(a, b):
    n = 0
    for left, right in zip(reversed(a), reversed(b)):
        if left != right:
            break
        n += 1
    return a[len(a)-n:] if n else ""


def _generalise(first, other):
    """Admit one exact {value} span only if TWO examples differ consistently."""
    if first["prefix"] != other["prefix"]:
        return None
    a, b = first["suffix"], other["suffix"]
    if a == b:
        return None
    before = _common_prefix(a, b)
    ra, rb = a[len(before):], b[len(before):]
    after = _common_suffix(ra, rb)
    va = ra[:-len(after)] if after else ra
    vb = rb[:-len(after)] if after else rb
    if (not va or not vb or va == vb
            or len(va.encode("utf-8")) > 1024
            or len(vb.encode("utf-8")) > 1024):
        return None
    template = (
        _escape(first["prefix"]) + "{i}" + _escape(before)
        + "{value}" + _escape(after)
    )
    if len(template.encode("utf-8")) > MAX_TEMPLATE_BYTES:
        return None
    parts = _parts(template)
    for sample, value in ((first, va), (other, vb)):
        if any(_render(parts, i, value) != sample["prefix"] + str(i) + sample["suffix"] + "\n"
               for i in range(1, sample["rows"]+1)):
            return None
    return {"template": template,
            "sample_values": (va, vb), "kind": "PARAMETRIC_NUMBERED_REPEAT"}


def _source(runtime, cap):
    """Read only FINAL visible assistant messages in the active local session."""
    if type(cap) is not int or not 1 <= cap <= MAX_HISTORY:
        raise ValueError("history limit must be 1..64")
    session = runtime.session
    if not isinstance(session, str) or not session:
        raise ValueError("active session required")
    # The database contains authoritative, final/provisional status; the
    # model cannot write these rows directly. Never read cancelled/draft text.
    rows = runtime.store.rows(
        "SELECT event_id,text FROM messages "
        "WHERE session_id=? AND role='assistant' AND status='FINAL' "
        "AND event_id IS NOT NULL ORDER BY id DESC LIMIT ?",
        (session, cap))
    return rows


def discover(runtime, name, history=16):
    """Generate a SHA-bound *candidate*, not an executable procedure."""
    rows = _source(runtime, history)
    found = []
    for row in rows:
        sample = _extract(row["text"])
        if sample:
            sample["event_id"] = row["event_id"]
            sample["output_sha256"] = hashlib.sha256(row["text"].encode("utf-8")).hexdigest()
            found.append(sample)
    if not found:
        raise ValueError("no repeated numbered FINAL response in this session")
    first = found[0]
    template, kind = first["template"], "LITERAL_NUMBERED_REPEAT"
    evidence = [first]
    sample_values = None
    # Compare against real earlier examples: don't infer variables from a
    # single answer. Every recognised value must replay both originals.
    for other in found[1:]:
        variant = _generalise(first, other)
        if variant:
            template = variant["template"]
            kind = variant["kind"]
            sample_values = variant["sample_values"]
            evidence.append(other)
            break
    worker = ProceduralBatch(runtime.home)
    metadata = {
        "method": "EXACT_FINAL_HISTORY_REPLAY_V1",
        "kind": kind,
        "source_event_ids": [item["event_id"] for item in evidence],
        "source_output_sha256": [item["output_sha256"] for item in evidence],
        "observed_rows": [item["rows"] for item in evidence],
        "validation": "BYTE_EXACT_BEFORE_PROPOSE",
        "scope": "CURRENT_SESSION_ONLY",
    }
    result = worker.propose(name, template, evidence=metadata)
    result.update(kind=kind, template=template, source_count=len(evidence),
                  source_event_ids=metadata["source_event_ids"],
                  observed_rows=metadata["observed_rows"],
                  needs_operator_activation=True,
                  claim_limit="Only extrapolates a visible numbered text pattern; no learned reasoning")
    if sample_values:
        # Examples are local private data and shown only to the local user.
        result["sample_values"] = list(sample_values)
    return result
