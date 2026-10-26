"""Independent read-only re-score of the frozen Run531 real-file Z12a raw artifact.

Never imports the original Z12a scorer. All reported rows, denominators,
rates, controls, criteria and verdict are reconstructed from per-run logs.
This verifies evidence integrity, not native/phone/learned JEPA performance.
"""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re

KINDS = ("own", "world", "interference", "fail", "ambiguous", "side_effect", "delayed")
SEEDS = (61, 62, 63)
CLASSES = ("SELF", "EXTERNAL", "MIXED", "UNCLEAR")
RAW_SHA256 = "73ba92ea8e2a28a00d639dcb21caca5f8991472c4513233ad659fab65e947ea7"


def require(ok, message):
    if not ok:
        raise ValueError("RUN534_AUDIT_FAIL: " + message)


def finite_number(v):
    return type(v) in (int, float) and math.isfinite(v)


def rate(rows, predicate):
    return round(sum(1 for row in rows if predicate(row)) / len(rows), 4) if rows else None


def independent_truth(obs, run):
    ch, val, t = obs["channel"], obs["value"], obs["t"]
    if ch.startswith("status:"):
        return "own"
    if ch == "listing":
        return "own" if any(x["name"].startswith("new_") and abs(x["t_done"] - t) < 1.5
                            for x in run["own_log"]) else "world"
    require(ch.startswith("file:"), "unexpected observation channel")
    name = ch[5:]
    own = any(x["name"] == name and x["sha"] == val and x["status"] == "EXECUTED"
              for x in run["own_log"])
    world = any(x["name"] == name and x.get("sha") == val for x in run["world_log"]) or val in ("DIR", None)
    return "both" if own and world else "own" if own else "world" if world else "unknown"


def independently_score(data):
    require(data.get("kind") == "V13_Z12A_SELF_WORLD_REAL", "wrong report kind")
    require(data.get("seeds") == "61,62,63" and type(data.get("episodes")) is int
            and data["episodes"] == 70, "frozen cohort mismatch")
    require(data.get("phone_measured") is False, "phone proof falsely asserted")
    runs = data.get("runs")
    require(isinstance(runs, list) and len(runs) == 3, "three runs required")
    require([r.get("seed") for r in runs] == list(SEEDS), "run seed mismatch")
    rows = []
    pids = set()
    status_failed = []
    for run in runs:
        kinds = run.get("kinds")
        require(isinstance(kinds, list) and len(kinds) == 70
                and Counter(kinds) == Counter({k: 10 for k in KINDS}), "episode balance mismatch")
        own, world, observations = (run.get(k) for k in ("own_log", "world_log", "observations"))
        require(all(isinstance(x, list) for x in (own, world, observations)), "missing raw log")
        require(len(own) == 70 and len(world) == 30, "incomplete own/world process logs")
        require(Counter(x.get("kind") for x in own) ==
                Counter({"ambiguous": 20, "own": 10, "world": 0, "interference": 10,
                         "fail": 10, "side_effect": 10, "delayed": 10}), "own kind coverage")
        require(Counter(x.get("op") for x in world) == Counter({"write": 20, "block": 10}),
                "independent world process coverage")
        seed_pids = {x.get("pid") for x in world}
        require(len(seed_pids) == 1 and all(type(p) is int and p > 0 for p in seed_pids),
                "missing independent world process PID")
        require(not (seed_pids & pids), "reused world process PID")
        pids.update(seed_pids)
        for action in own:
            require(type(action.get("ep")) is int and 0 <= action["ep"] < 70
                    and action.get("kind") == kinds[action["ep"]], "own action episode mismatch")
            require(action.get("status") in ("EXECUTED", "FAILED"), "invalid action status")
            require(finite_number(action.get("t_done")), "invalid own action timestamp")
        for action in world:
            require(finite_number(action.get("t")), "invalid world action timestamp")
            require(action.get("sha") is not None, "world log missing actual effect")
        for item in observations:
            require(isinstance(item, dict) and isinstance(item.get("obs"), dict),
                    "malformed raw observation")
            obs = item["obs"]
            require(isinstance(obs.get("channel"), str) and finite_number(obs.get("t")),
                    "invalid observation channel/time")
            require(item.get("cls") in CLASSES and item.get("no_corollary") == "EXTERNAL"
                    and item.get("timing_only") in ("SELF", "EXTERNAL"), "invalid attribution/control")
            require(isinstance(item.get("reason"), str), "missing attribution reason")
            channel = obs["channel"]
            kind = "listing"
            if channel != "listing":
                match = re.fullmatch(r"(?:file|status):(new_)?e(\d{3})", channel)
                require(match is not None, "unexpected file/status channel")
                idx = int(match.group(2))
                require(idx < 70, "out-of-range episode")
                kind = kinds[idx]
            truth = independent_truth(obs, run)
            rows.append({"seed": run["seed"], "channel": channel.split(":")[0],
                         "kind": kind, "truth": truth, "cls": item["cls"],
                         "reason": item["reason"], "no_corollary": item["no_corollary"],
                         "timing_only": item["timing_only"]})
            if channel.startswith("status:") and obs["value"] == "FAILED" and kind == "fail":
                status_failed.append(item)
    require(rows == data.get("rows"), "reported rows differ from raw observations/logs")
    file_rows = [r for r in rows if r["channel"] == "file" and r["truth"] in ("own", "world")]
    world_rows = [r for r in file_rows if r["truth"] == "world"]
    own_rows = [r for r in file_rows if r["truth"] == "own" and r["kind"] != "ambiguous"]
    interference = [r for r in world_rows if r["kind"] == "interference"]
    ambiguous = [r for r in file_rows if r["kind"] == "ambiguous" and r["truth"] == "own"]
    side = [r for r in rows if r["channel"] == "listing" and r["truth"] == "own"]
    delayed = [r for r in own_rows if r["kind"] == "delayed"]
    failed_actions = [x for run in runs for x in run["own_log"] if x["kind"] == "fail"]
    metrics = {
        "n_observations": len(rows), "n_world_file": len(world_rows),
        "n_own_file": len(own_rows), "n_interference_world": len(interference),
        "n_ambiguous": len(ambiguous), "n_side_effect": len(side),
        "n_delayed": len(delayed), "n_fail_actions": len(failed_actions),
        "false_self_on_world": rate(world_rows, lambda r: r["cls"] == "SELF"),
        "false_external_on_own": rate(own_rows, lambda r: r["cls"] == "EXTERNAL"),
        "ambiguous_unclear": rate(ambiguous, lambda r: r["cls"] == "UNCLEAR"),
        "side_effect_unclear": rate(side, lambda r: r["cls"] == "UNCLEAR"),
        "delayed_self": rate(delayed, lambda r: r["cls"] == "SELF"),
        "no_corollary_false_external_on_own": rate(own_rows, lambda r: r["no_corollary"] == "EXTERNAL"),
        "timing_only_false_self_on_interference": rate(interference, lambda r: r["timing_only"] == "SELF"),
        "corollary_false_self_on_interference": rate(interference, lambda r: r["cls"] == "SELF"),
        "fail_actions_failed": rate(failed_actions, lambda r: r["status"] == "FAILED"),
        "unknown_truth": sum(r["truth"] in ("unknown", "both") for r in rows),
        "failed_status_mixed": rate(status_failed, lambda r: r["cls"] == "MIXED"),
        "n_failed_status": len(status_failed),
        "modulator_packets": sum(run["modulator_packets"] for run in runs),
    }
    require(data.get("metrics") == metrics, "reported metrics differ from independent re-score")
    require(metrics["unknown_truth"] == 0 and len(rows) >= 210, "unknown truth or missing observations")
    criteria = {
        "K1_false_self_on_world_le_5pct": metrics["false_self_on_world"] is not None and metrics["false_self_on_world"] <= .05,
        "K2_false_external_on_own_le_5pct": metrics["false_external_on_own"] is not None and metrics["false_external_on_own"] <= .05,
        "K3_failed_own_action_mixed_ge_90pct": metrics["failed_status_mixed"] is not None and metrics["failed_status_mixed"] >= .9,
        "K4_ambiguous_unclear_ge_90pct": metrics["ambiguous_unclear"] is not None and metrics["ambiguous_unclear"] >= .9,
        "K5_side_effect_unclear_ge_90pct": metrics["side_effect_unclear"] is not None and metrics["side_effect_unclear"] >= .9,
        "K6_controls_worse": (metrics["no_corollary_false_external_on_own"] or 0)
            - (metrics["false_external_on_own"] or 0) >= .5
            and (metrics["timing_only_false_self_on_interference"] or 0)
            - (metrics["corollary_false_self_on_interference"] or 0) >= .2,
    }
    require(data.get("criteria") == criteria, "reported criteria differ from independent re-score")
    verdict = "Z12A_SELF_WORLD_REAL_PASS" if all(criteria.values()) else "Z12A_SELF_WORLD_REAL_FAIL"
    require(data.get("verdict") == verdict, "reported verdict differs from independent re-score")
    return {"status": "INDEPENDENT_RAW_AUDIT_PASS", "source_scope": "Run531 frozen real-file OS process, not JEPA",
            "seeds": list(SEEDS), "episodes_per_seed": 70, "metrics": metrics,
            "criteria": criteria, "verdict": verdict, "phone_measured": False,
            "canonical_gate_promoted": False}


def audit_file(path, expected_sha=RAW_SHA256):
    raw = Path(path).read_bytes()
    require(hashlib.sha256(raw).hexdigest() == expected_sha, "raw input SHA256 mismatch")
    return independently_score(json.loads(raw))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("raw_json")
    parser.add_argument("--sha256", default=RAW_SHA256)
    parser.add_argument("--output")
    args = parser.parse_args()
    result = audit_file(args.raw_json, args.sha256)
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        Path(args.output).write_text(text)
    print(text, end="")


if __name__ == "__main__":
    main()
