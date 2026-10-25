#!/usr/bin/env python3
"""Run394 fresh STEP2 long-note/revision cohort; never promotes a gate."""
import argparse
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEEDS = (20, 21, 22)
ARMS = {"O": {"base": "C", "query": True, "pointer": "off"},
        "P": {"base": "C", "query": True, "pointer": "pointer"},
        "S": {"base": "D", "query": True, "pointer": "pointer"}}
PILOT_IDS = ("Alder", "Delta")
SPECS = (
    ("Alder", "SPLIT", (140, 5, True), None, (90, 4, True), (110, 3, False)),
    ("Beacon", "SPLIT", (105, 6, False), None, (75, 7, True), (100, 5, False)),
    ("Cypress", "SPLIT", (95, 4, True), None, (80, 3, False), (90, 4, True)),
    ("Delta", "RULE", (160, 8, False), (100, 4, True), (70, 5, True), (90, 3, True)),
    ("Ember", "RULE", (70, 3, True), (130, 7, False), (95, 6, False), (120, 5, True)),
    ("Fable", "RULE", (120, 6, False), (80, 3, True), (75, 2, False), (85, 2, True)),
)
ADMIN = "This administrative paragraph contains no limits or option figures. " * 2
DISTRACTOR = "Project Zenith. The unrelated maintenance meeting is scheduled for tomorrow. No budget or decision is requested."


def rule_text(values):
    b, d, local = values
    return f"Budget {b} euros. Deadline {d} days. Local-only requirement: {str(local).lower()}."


def note(name, old):
    prefix = f"Project {name} kickoff memo. " + ADMIN
    return prefix + rule_text(old)


def sheet(name, a, b):
    from step2_z2_timescale import sheet as original
    return original(name, a, b)


def make_fixture(name, kind, old, revision, a, b):
    from v13.agi.eligibility import recipe
    from step2_z2_timescale import options_text, COMPUTE
    current_rules = revision if revision is not None else old
    history = [note(name, old), DISTRACTOR, sheet(name, a, b)]
    if revision is None:
        current = (f"Project {name}. Decide between Option A and Option B from the latest supplier data sheet, "
                   "using the earlier kickoff rules." + COMPUTE)
    else:
        current = (f"Project {name}. Revision 4 supersedes the kickoff memo. The rules for this decision are now: "
                   + rule_text(revision) + " Ignore the old budget, deadline and local-only values." + COMPUTE)
    opts = [{"entity": e, "cost": o[0], "days": o[1], "local": o[2]} for e, o in (("A", a), ("B", b))]
    action, options = recipe(*current_rules, opts)
    return {
        "id": name, "type": kind, "rules": {"budget": current_rules[0], "deadline": current_rules[1],
                                             "local_only": current_rules[2]},
        "old_rules": {"budget": old[0], "deadline": old[1], "local_only": old[2]},
        "revision_case": revision is not None,
        "history": history, "current": current,
        "needs": ["B2_GIST:rules", "B1_DETAIL:options"] if revision is None else ["B1_DETAIL:options"],
        "temporal_mode": "RETAIN_PRIOR_RULES" if revision is None else "CURRENT_RULES_OVERRIDE",
        "oracle": {"project": name, "action": action, "options": options},
    }


FIXTURES = [make_fixture(*s) for s in SPECS]


def validate_fixtures(fixtures):
    ids = [f["id"] for f in fixtures]
    if not ids or len(ids) != len(set(ids)):
        raise ValueError("empty or duplicate fixtures")
    for f in fixtures:
        name = f["id"]
        old = f["old_rules"]
        rule = rule_text((old["budget"], old["deadline"], old["local_only"]))
        note_text = f["history"][0]
        start = note_text.find(rule)
        if not 140 <= start < 200 or start + len(rule) > 240 or start + len(rule) <= 200:
            raise ValueError(name + ": B2 long-note span outside preregistered bounds")
        if note_text.count(rule) != 1:
            raise ValueError(name + ": duplicated rule")
        option_start = f["history"][2].find("Option A:")
        if not 240 < option_start < 600 or "Option B:" not in f["history"][2]:
            raise ValueError(name + ": B1/B2 detail isolation lost")
        if f["revision_case"]:
            if f["rules"] == f["old_rules"] or "supersedes" not in f["current"] or rule in f["current"]:
                raise ValueError(name + ": current revision not explicit")
        elif any(str(old[k]) not in note_text for k in ("budget", "deadline")):
            raise ValueError(name + ": old rule missing")
        if f["oracle"]["project"] != name or f["oracle"]["action"] not in ("A", "B", "NONE", "UNKNOWN"):
            raise ValueError(name + ": invalid oracle")
    return True


def configure(fixtures):
    """Private script-module overrides only; original source files remain unchanged."""
    import step2_z2_timescale as z2
    z2.FIXTURES = fixtures
    import step2_z2c_b2_rule as z2c
    z2c.FIX = {f["id"]: f for f in fixtures}
    z2c.RULE_EPISODES = [f["id"] for f in fixtures if f["type"] in ("SPLIT", "RULE")]
    z2c.ARMS.clear()
    z2c.ARMS.update({a: v["pointer"] for a, v in ARMS.items()})
    z2c.z2b.ARMS.clear()
    z2c.z2b.ARMS.update({a: {"base": v["base"], "query": v["query"]} for a, v in ARMS.items()})
    z2c.SEEDS = SEEDS
    z2c.z2b.SEEDS = SEEDS
    return z2c


def file_sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def manifest(fixtures, pilot, arms, seeds):
    from step2_z2_timescale import __file__ as z2_path
    return {"run": "Run394", "stage": "PILOT" if pilot else "FULL",
            "status": "PREREGISTERED_FIXTURES", "canonical_gate_pass": False,
            "step2_exit": "UTILITY_FAIL", "redmi_measured": False,
            "fixture_ids": [f["id"] for f in fixtures], "fixtures": fixtures,
            "fixture_sha256": hashlib.sha256(json.dumps(fixtures, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
            "arms": {a: ARMS[a] for a in arms}, "seeds": seeds,
            "source_sha256": {"run394_script": file_sha(__file__), "z2_fixture_runner": file_sha(z2_path)}}


def run(installed, work, fixtures, arms, seeds, pilot=True):
    z2c = configure(fixtures)
    work = Path(work)
    work.mkdir(parents=True, exist_ok=True)
    base = manifest(fixtures, pilot, arms, seeds)
    prereg = work / "RUN394_PREREGISTERED_FIXTURES.json"
    if prereg.exists():
        if json.loads(prereg.read_text()) != base:
            raise ValueError("existing preregistration differs; never overwrite")
    else:
        prereg.write_text(json.dumps(base, sort_keys=True, indent=2) + "\n")
    results = {}
    for seed in seeds:
        for arm in arms:
            key = f"{arm}_s{seed}"
            print(json.dumps({"run_start": key, "fixture_ids": base["fixture_ids"]}), flush=True)
            summary = z2c.run(Path(installed), work, arm, seed)
            tool_path = work / f"tool_{key}.json"
            tool = json.loads(tool_path.read_text())
            if len(tool.get("rows", [])) != len(fixtures) * 7 or not tool.get("installed_artifacts_unchanged"):
                raise ValueError(key + ": native structural/identity failure")
            metrics = [r.get("consumer_metrics") or {} for r in tool["rows"]]
            rss = [m.get("sampled_peak_rss_bytes") for m in metrics]
            rss = [v for v in rss if type(v) in (int, float) and math.isfinite(v) and v >= 0]
            results[key] = {
                "arm": arm, "seed": seed, "rows": len(tool["rows"]),
                "step2_status": summary["step2_status"], "tool_status": summary["tool_status"],
                "wrong_committed_tool": summary["z2c"]["wrong_committed_tool"],
                "historical_quote_mismatch_not_hallucination": summary["z2c"]["b2_wrong_rule_rows"],
                "mean_utility": summary["paired_tool"]["mean_utility"],
                "mean_elapsed_s": sum(r["elapsed_s"] for r in tool["rows"]) / len(tool["rows"]),
                "max_sampled_rss_bytes": max(rss) if rss else None,
                "summary_sha256": file_sha(work / f"summary_{key}.json"),
                "tool_sha256": file_sha(tool_path),
            }
            (work / "RUN394_PROGRESS.json").write_text(json.dumps({"preregistered": base, "results": results}, sort_keys=True, indent=2) + "\n")
    status = "PILOT_DIAGNOSTIC" if pilot else "FULL_DIAGNOSTIC_NO_GATE_PROMOTION"
    if any(x["wrong_committed_tool"] or x["tool_status"] == "STRUCTURAL_FAIL" for x in results.values()):
        status = "UNSAFE_OR_INCOMPLETE"
    out = {"run": "Run394", "status": status, "canonical_gate_pass": False, "step2_exit": "UTILITY_FAIL",
           "preregistration_sha256": file_sha(prereg), "results": results,
           "limits": "Linux-native pilot/full research only; no new heldout STEP2 acceptance or Redmi evidence."}
    (work / "RUN394_RESULT.json").write_text(json.dumps(out, sort_keys=True, indent=2) + "\n")
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--work", type=Path, required=True)
    p.add_argument("--installed-home", type=Path)
    p.add_argument("--pilot", action="store_true", help="Alder+Delta only; default when --full omitted")
    p.add_argument("--full", action="store_true", help="all six preregistered episodes")
    p.add_argument("--fixture-only", action="store_true", help="write fixture manifest without models")
    p.add_argument("--arms", nargs="+", choices=tuple(ARMS), default=list(ARMS))
    p.add_argument("--seeds", nargs="+", type=int, default=[20])
    args = p.parse_args()
    if args.full and args.pilot:
        p.error("choose --pilot or --full")
    if any(seed not in SEEDS for seed in args.seeds) or len(set(args.seeds)) != len(args.seeds):
        p.error("only distinct preregistered seeds 20/21/22")
    if len(set(args.arms)) != len(args.arms):
        p.error("duplicate arm")
    fixtures = FIXTURES if args.full else [f for f in FIXTURES if f["id"] in PILOT_IDS]
    validate_fixtures(fixtures)
    args.work.mkdir(parents=True, exist_ok=True)
    if args.fixture_only:
        out = manifest(fixtures, not args.full, args.arms, args.seeds)
        path = args.work / "RUN394_PREREGISTERED_FIXTURES.json"
        if path.exists() and json.loads(path.read_text()) != out:
            raise ValueError("existing fixture manifest differs")
        path.write_text(json.dumps(out, sort_keys=True, indent=2) + "\n")
        print(json.dumps({"status": out["status"], "fixture_sha256": out["fixture_sha256"], "fixtures": out["fixture_ids"]}))
        return
    if not args.installed_home:
        p.error("--installed-home required for real native execution")
    out = run(args.installed_home, args.work, fixtures, args.arms, args.seeds, not args.full)
    print(json.dumps({"status": out["status"], "rows": sum(v["rows"] for v in out["results"].values()),
                      "canonical_gate_pass": False, "step2_exit": "UTILITY_FAIL"}))


if __name__ == "__main__":
    main()
