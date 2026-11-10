"""Fail-closed static audit of V13 component contract evolution (stdlib only).

Run: python -m v13.contract_audit BASE.json CANDIDATE.json
No runtime capability is inferred from this structural check.
"""
import json
import sys
from pathlib import Path

ALLOWED = {"IMPLEMENTED", "PARTIAL", "UNAVAILABLE", "OFF", "SHADOW", "EXPERIMENTAL"}
REQUIRED = {"component_id", "name", "current_mode", "implementation_files",
            "runtime_owner", "state_owner", "known_limits", "canon_source"}


def validate(doc):
    if not isinstance(doc, dict) or type(doc.get("schema_version")) is not int:
        raise ValueError("missing contract schema_version")
    components = doc.get("components")
    if not isinstance(components, list) or not components:
        raise ValueError("missing components")
    ids = set()
    for item in components:
        if not isinstance(item, dict) or not REQUIRED.issubset(item):
            raise ValueError("malformed component contract")
        cid = item["component_id"]
        if not isinstance(cid, str) or not cid or cid in ids:
            raise ValueError("duplicate or invalid component id")
        ids.add(cid)
        if item["current_mode"] not in ALLOWED:
            raise ValueError("unknown capability mode: " + str(cid))
        if not isinstance(item["implementation_files"], list):
            raise ValueError("invalid implementation_files: " + cid)
        if not isinstance(item["known_limits"], str):
            raise ValueError("invalid known_limits: " + cid)
    if doc.get("canonical_architecture_complete") is True:
        raise ValueError("architecture completion requires separate acceptance evidence")
    return {x["component_id"]: x for x in components}


def compare(base, candidate):
    before = validate(base)
    after = validate(candidate)
    problems = []
    for cid in sorted(before.keys() - after.keys()):
        problems.append("REMOVED_COMPONENT " + cid)
    for cid in sorted(before.keys() & after.keys()):
        old, new = before[cid], after[cid]
        if old["name"] != new["name"]:
            problems.append("RENAMED_COMPONENT " + cid)
        if old["current_mode"] != new["current_mode"]:
            problems.append("MODE_CHANGE_REQUIRES_PROOF " + cid + " " +
                            old["current_mode"] + "->" + new["current_mode"])
        if old["implementation_files"] and not new["implementation_files"]:
            problems.append("LOST_IMPLEMENTATION_REFERENCES " + cid)
    if base.get("canon_sha256") != candidate.get("canon_sha256"):
        problems.append("CANON_HASH_CHANGED_REQUIRES_REVIEW")
    return problems


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 2:
        print("usage: python -m v13.contract_audit BASE.json CANDIDATE.json", file=sys.stderr)
        return 2
    try:
        base, candidate = (json.loads(Path(p).read_text(encoding="utf-8")) for p in args)
        findings = compare(base, candidate)
    except (ValueError, OSError, TypeError) as exc:
        print("INVALID_CONTRACT: " + str(exc), file=sys.stderr)
        return 2
    for finding in findings:
        print(finding)
    print("CONTRACT_REVIEW_REQUIRED" if findings else "STRUCTURAL_CONTRACT_OK")
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
