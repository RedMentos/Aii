"""Isolated German STEP2 typed-value SHADOW; not a Runtime/ToolStep consumer.

Only a caller's authoritative F1/F5 source reader may supply records. A
SHA256 self-check detects corruption, but is not a substitute for source
verification. No model or answer text is consulted. This candidate has zero
live decision authority and does not change the frozen English eligibility
reader, original STEP2 cohort, or Age-0 gates.
"""
import hashlib
import re

from v13.agi.eligibility import recipe

REVISION = "run17-de-typed-shadow-v1"
EVIDENCE_LEVEL = "software_source_only"
RULES = {
    "budget": re.compile(r"\bBudget\s+(\d+)\s+Euro\b", re.I),
    "deadline": re.compile(r"\bFrist\s+(\d+)\s+Tage\b", re.I),
    "local_only": re.compile(r"\bLokalpflicht\s+(ja|nein)\b", re.I),
}
OPTIONS = re.compile(
    r"\bOption\s+([AB])\s*:\s*Kosten\s+(\d+)\s+Euro\s*,\s*"
    r"Dauer\s+(\d+)\s+Tage\s*,\s*lokal\s+(ja|nein)(?=\s*[.;]|$)", re.I)
PROJECT = re.compile(r"\b(?:Projekt|Project)\s+([A-Za-z][A-Za-z0-9]*)\b", re.I)
REF = re.compile(r"[A-Za-z0-9:._/-]{1,256}\Z")


class Refusal(ValueError):
    """Source, temporal or value contract could not be established."""


def _record(ref, reader):
    if not isinstance(ref, str) or REF.fullmatch(ref) is None:
        raise Refusal("invalid_source_ref")
    try:
        row = reader(ref)
    except Exception as exc:
        raise Refusal("source_unavailable") from exc
    if not isinstance(row, dict) or row.get("ref") != ref:
        raise Refusal("source_identity")
    if row.get("verified") is not True or row.get("active") is not True:
        raise Refusal("source_not_live_verified")
    for key in ("project", "session", "kind"):
        if not isinstance(row.get(key), str) or not row[key]:
            raise Refusal("source_metadata")
    value, digest = row.get("text"), row.get("sha256")
    if not isinstance(value, str) or not 1 <= len(value) <= 6000:
        raise Refusal("source_text")
    if not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
        raise Refusal("source_hash_format")
    if hashlib.sha256(value.encode("utf-8")).hexdigest() != digest:
        raise Refusal("source_hash_mismatch")
    seq = row.get("seq")
    if type(seq) is not int or not 0 <= seq < 1_000_000_000_000:
        raise Refusal("source_sequence")
    return row


def _project(text, name):
    found = {m.lower() for m in PROJECT.findall(text)}
    if found != {name.lower()}:
        raise Refusal("ambiguous_or_cross_project_source")


def _rules(text):
    result = {}
    for key, pattern in RULES.items():
        values = pattern.findall(text)
        if len(values) != 1:
            raise Refusal("missing_or_ambiguous_" + key)
        token = values[0].lower()
        result[key] = (token == "ja") if key == "local_only" else int(token)
    if result["budget"] <= 0 or result["deadline"] <= 0:
        raise Refusal("nonpositive_rule")
    return result


def _options(text):
    matches = OPTIONS.findall(text)
    if len(matches) != 2 or [m[0].upper() for m in matches] != ["A", "B"]:
        raise Refusal("missing_or_ambiguous_options")
    options = []
    for entity, cost, days, local in matches:
        if int(cost) <= 0 or int(days) <= 0:
            raise Refusal("nonpositive_option")
        options.append({"entity": entity.upper(), "cost": int(cost),
                        "days": int(days), "local": local.lower() == "ja"})
    return options


def evaluate(project, current_ref, old_ref, options_ref, temporal_mode, source_reader):
    """Compute a fallible SHADOW candidate from three verified source records.

    source_reader(ref) must query current F1/F5 authority and return a record
    with ref, text, sha256, project, session, kind, seq, verified=True, active=True.
    This module does not implement F1/F5; callers must not substitute arbitrary
    user-supplied text or self-asserted hashes for that authoritative reader.
    """
    if not isinstance(project, str) or not re.fullmatch(r"[A-Za-z]+", project):
        raise Refusal("project")
    if temporal_mode not in ("RETAIN_PRIOR_RULES", "REVISED_CURRENT_RULES"):
        raise Refusal("temporal_mode")
    if not callable(source_reader) or current_ref == old_ref:
        raise Refusal("reader_or_ref")
    if temporal_mode == "REVISED_CURRENT_RULES" and options_ref in (current_ref, old_ref):
        raise Refusal("revised_option_source")
    rows = {ref: _record(ref, source_reader) for ref in
            dict.fromkeys((current_ref, old_ref, options_ref))}
    current, old, opt = (rows[x] for x in (current_ref, old_ref, options_ref))
    if (current["kind"] != "current" or old["kind"] != "history" or
            opt["kind"] != ("current" if options_ref == current_ref else "history")):
        raise Refusal("source_origin")
    if (len({x["session"] for x in (current, old, opt)}) != 1 or
            any(x["project"].lower() != project.lower() for x in (current, old, opt))):
        raise Refusal("source_scope")
    for row in (current, old, opt):
        _project(row["text"], project)
    if old["seq"] >= current["seq"]:
        raise Refusal("old_source_not_before_current")
    if options_ref != current_ref and not old["seq"] < opt["seq"] < current["seq"]:
        raise Refusal("supplier_sheet_not_between_note_and_current")
    now = current["text"]
    if temporal_mode == "RETAIN_PRIOR_RULES":
        if ("früheren verbindlichen Regeln" not in now or
                "vollständig ersetzt" in now or "Aktuelle verbindliche Regeln" in now or
                any(pattern.search(now) for pattern in RULES.values())):
            raise Refusal("prior_temporal_contract")
        if any(len(pattern.findall(old["text"][:240])) != 1 for pattern in RULES.values()):
            raise Refusal("old_rules_outside_b2_excerpt")
        rules = _rules(old["text"][:240])
        if _rules(old["text"]) != rules:
            raise Refusal("ambiguous_full_old_source")
    else:
        if ("Alte Auftaktregeln wurden vollständig ersetzt." not in now or
                "Aktuelle verbindliche Regeln:" not in now):
            raise Refusal("revision_temporal_contract")
        rules = _rules(now)
    has_current_options = re.search(r"\bOption\s+[AB]\s*:", now, re.I) is not None
    if has_current_options != (options_ref == current_ref):
        raise Refusal("current_options_take_precedence")
    if options_ref != current_ref and "Lieferantenblatt" not in opt["text"]:
        raise Refusal("option_source_kind")
    options = _options(opt["text"])
    action, details = recipe(rules["budget"], rules["deadline"],
                             rules["local_only"], options)
    return {"revision": REVISION, "evidence_level": EVIDENCE_LEVEL,
            "status": "SHADOW_ONLY", "authority": False, "action": action,
            "rules": rules, "options": details, "temporal_mode": temporal_mode,
            "source_refs": {"current": current_ref, "old": old_ref, "options": options_ref},
            "source_hashes": {"current": current["sha256"], "old": old["sha256"],
                              "options": opt["sha256"]}}
