"""Fail-closed CI evidence gate for a pinned GitHub commit (stdlib only)."""
import argparse
import json
import re

_SHA = re.compile(r"[0-9a-fA-F]{40}\Z")


def evaluate(payload, sha, required):
    if not isinstance(sha, str) or not _SHA.fullmatch(sha):
        raise ValueError("commit SHA must be a full 40-character hex digest")
    if not isinstance(required, (list, tuple)) or not required or any(not isinstance(n, str) or not n.strip() for n in required):
        raise ValueError("at least one nonempty required workflow name is mandatory")
    if len(set(required)) != len(required):
        raise ValueError("duplicate required workflow name")
    if not isinstance(payload, dict) or not isinstance(payload.get("workflow_runs"), list):
        raise ValueError("missing workflow_runs")
    runs = payload["workflow_runs"]
    if any(not isinstance(r, dict) for r in runs):
        raise ValueError("malformed workflow run")
    result = {}
    for name in required:
        matching = [r for r in runs if r.get("head_sha") == sha and r.get("name") == name]
        if not matching:
            result[name] = "MISSING"
            continue
        # A later successful run must not hide a failed or still-running
        # check for the exact same pinned commit and workflow name.
        result[name] = "PASS" if all(r.get("status") == "completed" and r.get("conclusion") == "success" for r in matching) else "BLOCKED"
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument("json_file")
    p.add_argument("--sha", required=True)
    p.add_argument("--require", action="append", required=True)
    a = p.parse_args()
    with open(a.json_file, encoding="utf-8") as f:
        result = evaluate(json.load(f), a.sha, a.require)
    print(json.dumps(result, sort_keys=True))
    return 0 if all(x == "PASS" for x in result.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
