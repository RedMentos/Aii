"""Fail-closed CI evidence gate for a pinned commit (stdlib only)."""
import argparse
import json


def evaluate(payload, sha, required):
    if not sha or len(sha) < 12:
        raise ValueError("commit SHA must be pinned")
    runs = payload.get("workflow_runs")
    if not isinstance(runs, list):
        raise ValueError("missing workflow_runs")
    result = {}
    for name in required:
        matching = [r for r in runs if r.get("head_sha") == sha and r.get("name") == name]
        if not matching:
            result[name] = "MISSING"
            continue
        latest = max(matching, key=lambda r: (r.get("run_started_at") or "", r.get("run_attempt") or 0, r.get("id") or 0))
        result[name] = "PASS" if latest.get("status") == "completed" and latest.get("conclusion") == "success" else "BLOCKED"
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
