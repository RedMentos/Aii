#!/usr/bin/env python3
"""Run397 opt-in append-only Run394 native cohort resume; never changes frozen source or gates."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import time

import run394_step2_fresh as r394
import run396_step2_pilot_audit as audit
from v13.common import atomic_write, digest, dumps
from v13.models import ModelManager, catalog, platform_tag

VARIANTS = tuple(audit.VARIANTS)
OWNER = "RUN397_STEP2_NATIVE_EXCLUSIVE"
SCHEMA = "RUN397_APPEND_ONLY_NATIVE_ATTEMPT_V1"


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def checked_manifest(work, fixtures, arms, seeds, pilot):
    work = Path(work)
    expected = r394.manifest(fixtures, pilot, arms, seeds)
    path = work / "RUN394_PREREGISTERED_FIXTURES.json"
    require(not path.is_symlink(), "UNSAFE_MANIFEST_SYMLINK")
    if path.exists():
        require(json.loads(path.read_bytes()) == expected, "FROZEN_MANIFEST_MISMATCH")
    else:
        atomic_write(path, json.dumps(expected, sort_keys=True, indent=2) + "\n")
    return expected


def evidence_hashes(directory):
    return {p.name: audit.sha(p) for p in sorted(Path(directory).glob("*.json"))
            if p.is_file() and not p.is_symlink()}


def validate_completed(directory, arm, seed, fixtures, expected_manifest, current_runner_sha=None):
    """Validate every native row and replay link; do not accept merely present files."""
    directory = Path(directory)
    rid = f"{arm}_s{seed}"
    source_path = directory / f"step2_{rid}.json"
    tool_path = directory / f"tool_{rid}.json"
    summary_path = directory / f"summary_{rid}.json"
    prereg_path = directory / f"tool_{rid}.preregistration.json"
    require(not directory.is_symlink(), "UNSAFE_ATTEMPT_SYMLINK")
    for path in (source_path, tool_path, summary_path, prereg_path):
        require(not path.is_symlink() and path.resolve().is_relative_to(directory.resolve()),
                "UNSAFE_ATTEMPT_EVIDENCE_SYMLINK")
    source, tool, summary, prereg = (audit.load(p) for p in
                                     (source_path, tool_path, summary_path, prereg_path))
    expected = {(f["id"], v) for f in fixtures for v in VARIANTS}
    require(source.get("fixtures") == fixtures, "SOURCE_FIXTURE_MISMATCH")
    # Preserve the full native runtime/harness identity, not only the wrapper
    # and model catalog. A prior arm from changed source cannot be reused.
    require(source.get("source_hashes") == r394.z2.harness().source_hashes(),
            "RECORDED_RUNTIME_SOURCE_HASH_MISMATCH")
    # A self-consistent report from another valid installed model is not a
    # reusable result for this preregistered cohort. Bind actual role hashes.
    models = catalog()["models"]
    role_models = {"B1_DETAIL": "body", "B2_GIST": "body" if arm == "S" else "gist",
                   "C3_LANGUAGE": "language"}
    stored_artifacts = source.get("installed_artifacts") or {}
    stored_hashes = stored_artifacts.get("model_sha256") or {}
    stored_revisions = stored_artifacts.get("model_revisions") or {}
    for role, key in role_models.items():
        spec = models[key]
        require(stored_hashes.get(role) == spec["files"][0]["sha256"] and
                stored_revisions.get(role) == spec["revision"],
                "RECORDED_MODEL_IDENTITY_MISMATCH:" + role)
    if current_runner_sha is not None:
        require(stored_artifacts.get("runner_sha256") == current_runner_sha,
                "RECORDED_RUNNER_IDENTITY_MISMATCH")
    require(source.get("all_structural_checks_passed") is True, "SOURCE_STRUCTURAL_FAIL")
    require(source.get("status") in ("UTILITY_FAIL", "UTILITY_PASS_SCOPED"), "SOURCE_INCOMPLETE")
    require(source.get("installed_artifacts_unchanged") is True, "SOURCE_MODEL_CHANGED")
    require(source.get("phone_measured") is False, "NOT_LINUX_ONLY")
    require(source.get("canonical_gate_pass") is False, "SOURCE_GATE_PROMOTION")
    require(tool.get("installed_artifacts_unchanged") is True, "TOOL_MODEL_CHANGED")
    require(tool.get("status") in ("TOOL_UTILITY_PASS_SCOPED", "TOOL_UTILITY_FAIL"), "TOOL_INCOMPLETE")
    require(tool.get("canonical_gate_pass") is False and tool.get("phone_measured") is False, "TOOL_GATE_PROMOTION")
    require(summary.get("run") == rid and summary.get("arm") == arm and summary.get("seed") == seed, "SUMMARY_ID_MISMATCH")
    require(summary.get("z2c", {}).get("b2_quote_select") == r394.ARMS[arm]["pointer"], "QUOTE_MODE_MISMATCH")
    require(summary.get("z2c", {}).get("wrong_committed_tool") == 0, "WRONG_COMMITTED_TOOL")
    require(sum(s["wrong_committed"] for s in tool["summary"]["tool"].values()) == 0, "WRONG_TOOL_SUMMARY")
    require(tool.get("preregistration_sha256") == audit.sha(prereg_path), "TOOL_PREREG_HASH_MISMATCH")
    require(prereg.get("source_report", {}).get("sha256") == audit.sha(source_path), "SOURCE_REPLAY_HASH_MISMATCH")
    source_rows = audit.validated_rows(source, expected, rid + ":source")
    tool_rows = audit.validated_rows(tool, expected, rid + ":tool")
    for key in expected:
        sr, tr = source_rows[key], tool_rows[key]
        require(tr.get("oracle_visible_to_native") is False, "ORACLE_LEAK")
        require(tr.get("consumer_messages_sha256") == digest(dumps(sr["consumer_messages"])),
                "CONSUMER_MESSAGES_CHANGED")
        require(audit.finite_unit(tr.get("score", {}).get("utility")), "UTILITY_NOT_FINITE")
        require(type(tr.get("elapsed_s")) in (int, float) and
                0 <= tr["elapsed_s"] < float("inf"), "INVALID_ELAPSED")
    require(set(tool["paired_tool"]["mean_utility"]) == set(VARIANTS), "VARIANT_UTILITY_MISSING")
    for v in VARIANTS:
        mean = sum(tool_rows[(f["id"], v)]["score"]["utility"] for f in fixtures) / len(fixtures)
        require(abs(mean - tool["paired_tool"]["mean_utility"][v]) < 1e-10, "UTILITY_AGGREGATE_MISMATCH")
    return {"run_id": rid, "rows": len(expected), "sha256": {
        "source": audit.sha(source_path), "tool": audit.sha(tool_path),
        "summary": audit.sha(summary_path), "tool_prereg": audit.sha(prereg_path)},
        "fixture_sha256": expected_manifest["fixture_sha256"],
        "source_sha256": expected_manifest["source_sha256"],
        "canonical_gate_pass": False, "step2_exit": "UTILITY_FAIL"}


def _attempts(work, rid):
    root = Path(work) / "attempts"
    base = root / rid
    require(not root.is_symlink() and not base.is_symlink(), "UNSAFE_ATTEMPT_SYMLINK")
    if not base.exists():
        return []
    require(base.is_dir(), "INVALID_ATTEMPT_DIRECTORY")
    entries = list(base.iterdir())
    require(not any(p.is_symlink() for p in entries), "UNSAFE_ATTEMPT_SYMLINK")
    return sorted((p for p in entries if p.is_dir() and
                   p.name.startswith("attempt-") and p.name[8:].isdigit()),
                  key=lambda p: int(p.name[8:]))


def previous_success(work, arm, seed, fixtures, manifest, current_runner_sha=None):
    """Any invalid/partial attempt is preserved and ignored, never rewritten."""
    rid = f"{arm}_s{seed}"
    failures = []
    for p in _attempts(work, rid):
        receipt = p / "RUN397_ATTEMPT.json"
        require(not receipt.is_symlink(), "UNSAFE_ATTEMPT_RECEIPT_SYMLINK")
        if not receipt.exists():
            failures.append({"attempt": str(p.relative_to(work)), "reason": "NO_COMPLETED_RECEIPT"})
            continue
        try:
            stored = audit.load(receipt)
            require(stored.get("schema") == SCHEMA and stored.get("status") == "COMPLETE",
                    "RECEIPT_NOT_COMPLETE")
            require(stored.get("arm") == arm and stored.get("seed") == seed, "RECEIPT_ID_MISMATCH")
            actual = validate_completed(p, arm, seed, fixtures, manifest, current_runner_sha)
            require(stored.get("validated") == actual, "RECEIPT_HASH_MISMATCH")
            return {"attempt": str(p.relative_to(work)), "validated": actual}, failures
        except Exception as exc:
            failures.append({"attempt": str(p.relative_to(work)),
                             "reason": type(exc).__name__ + ": " + str(exc)[:180]})
    return None, failures


def journal(work, record):
    path = Path(work) / "RUN397_EVENTS.jsonl"
    require(not path.is_symlink(), "UNSAFE_EVENTS_SYMLINK")
    line = dumps(record) + "\n"
    with path.open("ab") as f:
        f.write(line.encode())
        f.flush()
        os.fsync(f.fileno())


def progress(work, manifest, completed, failures):
    payload = {"schema": SCHEMA, "status": "ALL_ARMS_STRUCTURALLY_RECORDED" if
               len(completed) == len(manifest["arms"]) * len(manifest["seeds"]) else "INCOMPLETE",
               "manifest_sha256": audit.sha(Path(work) / "RUN394_PREREGISTERED_FIXTURES.json"),
               "completed": completed, "failures_preserved": failures,
               "canonical_gate_pass": False, "step2_exit": "UTILITY_FAIL",
               "native_success_does_not_promote_step2": True}
    atomic_write(Path(work) / "RUN397_PROGRESS.json", json.dumps(payload, sort_keys=True, indent=2) + "\n")
    return payload


def run(work, installed, pilot=True, execute=False, max_new_arms=None):
    require(max_new_arms is None or
            (type(max_new_arms) is int and max_new_arms > 0), "INVALID_MAX_NEW_ARMS")
    work = Path(work).expanduser().resolve()
    work.mkdir(parents=True, exist_ok=True)
    fixtures = [f for f in r394.FIXTURES if f["id"] in r394.PILOT_IDS] if pilot else r394.FIXTURES
    r394.validate_fixtures(fixtures)
    arms = list(r394.ARMS)
    seeds = [20] if pilot else list(r394.SEEDS)
    lockpath = work / "RUN397_OWNER.lock"
    require(not lockpath.is_symlink(), "UNSAFE_WORK_OWNER_LOCK")
    require(not (work / "attempts").is_symlink(), "UNSAFE_ATTEMPT_SYMLINK")
    with lockpath.open("a+") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError("RUN397_WORK_OWNER_ACTIVE") from exc
        manifest = checked_manifest(work, fixtures, arms, seeds, pilot)
        completed = {}
        failures = {}
        launched = 0
        current_runner_sha = None
        if execute:
            require(installed is not None, "INSTALLED_HOME_REQUIRED")
            installed = Path(installed).expanduser().resolve()
            manager = ModelManager(installed)
            checks = manager.verify(deep=True)
            keys = ("needle", "language", "body", "gist")
            require(set(keys) <= set(checks) and
                    all(checks[k]["ok"] and checks[k]["hash_checked"] for k in keys),
                    "INSTALLED_MODEL_HASHES_INVALID")
            specs = catalog()["models"]
            for key in keys:
                spec, stored = specs[key], manager.installed.get(key, {})
                required_files = list(spec["files"])
                if key == "needle":
                    required_files += spec["platforms"][platform_tag()]
                expected = {f["local_name"]: (f["sha256"], f["size"]) for f in required_files}
                found = stored.get("files", {})
                actual = {name: (meta.get("sha256"), meta.get("size"))
                          for name, meta in found.items()} if isinstance(found, dict) else {}
                require(stored.get("model_id") == spec["model_id"] and
                        stored.get("exact_revision") == spec["revision"] and
                        stored.get("license_id") == spec["license_id"] and actual == expected,
                        "INSTALLED_CATALOG_IDENTITY_MISMATCH:" + key)
            runner = installed / "bin/llama-server"
            meta = audit.load(installed / "config/runner.json")
            require(meta.get("tag") == catalog()["runner"]["tag"] and
                    meta.get("binary_sha256") == audit.sha(runner), "RUNNER_HASH_INVALID")
            current_runner_sha = audit.sha(runner)
            z2c = r394.configure(fixtures)
        for seed in seeds:
            for arm in arms:
                rid = f"{arm}_s{seed}"
                existing, prior_failures = previous_success(work, arm, seed, fixtures, manifest, current_runner_sha)
                if prior_failures:
                    failures[rid] = prior_failures
                if existing:
                    completed[rid] = existing
                    progress(work, manifest, completed, failures)
                    continue
                if not execute or (max_new_arms is not None and launched >= max_new_arms):
                    continue
                launched += 1
                all_attempts = _attempts(work, rid)
                number = 1 + max((int(p.name[8:]) for p in all_attempts), default=0)
                attempt = work / "attempts" / rid / f"attempt-{number:04d}"
                attempt.mkdir(parents=True, exist_ok=False)
                journal(work, {"event": "START", "owner": OWNER, "run_id": rid,
                               "attempt": str(attempt.relative_to(work)), "time": time.time()})
                try:
                    summary = z2c.run(installed, attempt, arm, seed)
                    validated = validate_completed(attempt, arm, seed, fixtures, manifest, current_runner_sha)
                    require(summary.get("run") == rid, "RETURNED_SUMMARY_MISMATCH")
                    receipt = {"schema": SCHEMA, "status": "COMPLETE", "arm": arm,
                               "seed": seed, "validated": validated, "owner": OWNER}
                    atomic_write(attempt / "RUN397_ATTEMPT.json",
                                 json.dumps(receipt, sort_keys=True, indent=2) + "\n")
                    completed[rid] = {"attempt": str(attempt.relative_to(work)), "validated": validated}
                    journal(work, {"event": "COMPLETE", "run_id": rid,
                                   "receipt_sha256": audit.sha(attempt / "RUN397_ATTEMPT.json"),
                                   "time": time.time()})
                except BaseException as exc:
                    failure = {"event": "FAILED", "run_id": rid, "attempt": str(attempt.relative_to(work)),
                               "error_type": type(exc).__name__, "reason": str(exc)[:350],
                               "available_hashes": evidence_hashes(attempt), "time": time.time()}
                    atomic_write(attempt / "RUN397_FAILED.json",
                                 json.dumps(failure, sort_keys=True, indent=2) + "\n")
                    journal(work, failure)
                    failures.setdefault(rid, []).append(failure)
                    progress(work, manifest, completed, failures)
                    if isinstance(exc, (KeyboardInterrupt, SystemExit)):
                        raise
                progress(work, manifest, completed, failures)
        return progress(work, manifest, completed, failures)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--work", type=Path, required=True)
    p.add_argument("--installed-home", type=Path)
    p.add_argument("--full", action="store_true")
    p.add_argument("--execute", action="store_true", help="explicitly start actual pinned native inference")
    p.add_argument("--max-new-arms", type=int, help="optional bounded attempt count for checkpointed staged execution")
    args = p.parse_args()
    out = run(args.work, args.installed_home, pilot=not args.full, execute=args.execute,
              max_new_arms=args.max_new_arms)
    print(json.dumps({"status": out["status"], "completed": len(out["completed"]),
                      "failures_preserved": sum(map(len, out["failures_preserved"].values())),
                      "canonical_gate_pass": False, "step2_exit": "UTILITY_FAIL"}, sort_keys=True))


if __name__ == "__main__":
    main()
