"""Offline PR changed-file overlap audit; input is an explicit verified JSON snapshot.

This does NOT establish merge conflicts. It identifies paths touched by multiple
independent PRs, so the integration owner can test a combined candidate.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def audit(snapshot: dict) -> list[dict]:
    prs = snapshot.get("pull_requests")
    if not isinstance(prs, list):
        raise ValueError("pull_requests must be a list")
    by_path: dict[str, set[int]] = {}
    seen: set[int] = set()
    for pr in prs:
        if not isinstance(pr, dict) or type(pr.get("number")) is not int:
            raise ValueError("PR entry requires integer number")
        number = pr["number"]
        if number in seen:
            raise ValueError(f"duplicate PR: {number}")
        seen.add(number)
        files = pr.get("files")
        if not isinstance(files, list) or any(
            not isinstance(p, str) or not p or p.startswith("/")
            or "\\x00" in p or ".." in Path(p).parts
            for p in files
        ):
            raise ValueError(f"invalid file paths for PR {number}")
        for path in files:
            by_path.setdefault(path, set()).add(number)
    return [
        {"path": path, "prs": sorted(numbers)}
        for path, numbers in sorted(by_path.items())
        if len(numbers) > 1
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path, help="verified PR changed-file JSON")
    parser.add_argument("--strict", action="store_true",
                        help="exit 2 when overlapping paths are detected")
    args = parser.parse_args()
    try:
        report = audit(json.loads(args.snapshot.read_text(encoding="utf-8")))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    print(json.dumps({"overlaps": report, "count": len(report)}, indent=2))
    return 2 if args.strict and report else 0


if __name__ == "__main__":
    raise SystemExit(main())
