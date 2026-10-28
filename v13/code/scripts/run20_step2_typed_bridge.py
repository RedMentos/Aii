"""Run20 source-only EN/DE STEP2 typed bridge (NO native model or Runtime).

Explicit source positions stand in for future verified B1/B2 source selection.
The oracle is never read. No automatic tool execution or learning authority.
"""
import hashlib
import re

from scripts import run17_german_typed_shadow as german
from v13.agi import eligibility as english

REVISION = "run20-step2-typed-bridge-v1"
SOURCE_ONLY = True
AUTHORITY = False
PROJECT = re.compile(r"\b(?:Projekt|Project)\s+([A-Z][A-Za-z0-9]*)\b")


class Refusal(ValueError):
    pass


def _project(text, name):
    if {x.lower() for x in PROJECT.findall(text)} != {name.lower()}:
        raise Refusal("source_project")


def _row(ref, text, project, kind, seq):
    return {"ref": ref, "text": text, "sha256": hashlib.sha256(text.encode()).hexdigest(),
            "project": project, "session": "run20-synthetic", "kind": kind,
            "seq": seq, "verified": True, "active": True}


def evaluate(case):
    """No oracle/rules/answer may enter this function; use only source text."""
    if not isinstance(case, dict) or set(case) != {
            "id", "language", "type", "history", "current", "temporal_mode"}:
        raise Refusal("unexpected_oracle_or_input_fields")
    name = case["id"]
    if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z]+", name):
        raise Refusal("project")
    if case["language"] not in ("EN", "DE") or case["type"] not in ("SPLIT", "RULE", "REVISION"):
        raise Refusal("kind")
    history = case["history"]
    if not isinstance(history, list) or len(history) != 3 or any(type(x) is not str for x in history):
        raise Refusal("history")
    now = case["current"]
    if not isinstance(now, str):
        raise Refusal("current")
    note, sheet = history[0], history[2]
    opts = now if case["type"] == "RULE" else sheet
    for source in (now, note, opts):
        _project(source, name)
    if case["language"] == "EN":
        if (case["type"] == "REVISION") != (case["temporal_mode"] == "REVISED_CURRENT_RULES"):
            raise Refusal("temporal_mode")
        # Current SPLIT questions mention "Option A and Option B" without
        # typed values. The legacy fixed_read stops at that incomplete clause;
        # select the exact, project-bound option source explicitly instead.
        values = {k: english.fixed_rule(k, now, [note])
                  for k in ("budget", "deadline", "local_only")}
        values["options"] = [english.fixed_option(entity, opts) for entity in "AB"]
        if any(values[k] is None for k in ("budget", "deadline", "local_only")) or not all(values["options"]):
            raise Refusal("missing_exact_english_values")
        args = english.args_for(values, now, [note, sheet])
        outcome = english.tool(**args)
        if outcome["action"] == "UNKNOWN" or outcome["rejected"]:
            raise Refusal("english_evidence_guard")
        action, details = outcome["action"], outcome["options"]
    else:
        refs = {"current": name+":current", "old": name+":old", "sheet": name+":sheet"}
        records = {
            refs["current"]: _row(refs["current"], now, name, "current", 3),
            refs["old"]: _row(refs["old"], note, name, "history", 0),
            refs["sheet"]: _row(refs["sheet"], sheet, name, "history", 2),
        }
        result = german.evaluate(name, refs["current"], refs["old"],
                                 refs["current"] if case["type"] == "RULE" else refs["sheet"],
                                 case["temporal_mode"], records.get)
        action, details = result["action"], result["options"]
    return {"status": "SOFTWARE_SOURCE_ONLY", "authority": AUTHORITY,
            "revision": REVISION, "action": action, "options": details,
            "project": name, "language": case["language"],
            "source_sha256": [hashlib.sha256(x.encode()).hexdigest()
                              for x in (now, note, opts)]}
