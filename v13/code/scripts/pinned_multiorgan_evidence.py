"""Fail-closed multi-organ evidence preflight. This never promotes runtime gates."""
import json
import re
import sys

REQUIRED = ("core", "jepa", "qa", "perception")
GATES = ("STEP2_UTILITY", "B3_PROMOTION", "BODY_JEPA", "REDMI_PROOF")
SHA = re.compile(r"[0-9a-f]{40}\Z")


def check(data):
    errors = []
    if not isinstance(data, dict):
        return ["manifest must be object"]
    chains = data.get("chains", {})
    if not isinstance(chains, dict) or any(x not in chains for x in REQUIRED):
        return ["missing organ chain"]
    for organ in REQUIRED:
        chain = chains[organ]
        if not isinstance(chain, dict):
            errors.append(organ + ": chain must be object")
            continue
        sha = chain.get("head_sha")
        if not isinstance(sha, str) or not SHA.fullmatch(sha):
            errors.append(organ + ": unpinned SHA")
        if chain.get("status") not in ("SHADOW", "REVIEW_ONLY", "OFF", "BLOCKED"):
            errors.append(organ + ": invalid status")
        runs = chain.get("runs")
        if not isinstance(runs, list) or not runs:
            errors.append(organ + ": missing or invalid CI list")
            continue
        for run in runs:
            if not isinstance(run, dict):
                errors.append(organ + ": CI run must be object")
                continue
            if run.get("head_sha") != sha:
                errors.append(organ + ": stale CI")
            if run.get("conclusion") != "success":
                errors.append(organ + ": CI not successful")
            if not str(run.get("url", "")).startswith("https://github.com/RedMentos/Aii/actions/runs/"):
                errors.append(organ + ": invalid evidence URL")
            if run.get("level") not in ("synthetic", "linux-native", "android-native"):
                errors.append(organ + ": invalid evidence level")
    if data.get("claim") != "REVIEW_ONLY":
        errors.append("promotion forbidden")
    gates = data.get("gates")
    if not isinstance(gates, dict):
        errors.append("gates must be object")
        gates = {}
    for gate in GATES:
        if gates.get(gate) not in ("FAIL", "OFF", "UNAVAILABLE", "UNVERIFIED"):
            errors.append(gate + ": negative gate overridden")
    return errors


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: python pinned_multiorgan_evidence.py MANIFEST.json")
    errors = check(json.load(open(sys.argv[1], encoding="utf-8")))
    print(json.dumps({"admitted": not errors, "errors": errors}, indent=2))
    raise SystemExit(bool(errors))
