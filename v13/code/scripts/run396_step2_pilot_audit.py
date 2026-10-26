#!/usr/bin/env python3
"""Run396 read-only Run394 pilot audit; distinguishes stale historical quotes from wrong actions."""
import argparse
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARMS = ("O", "P", "S")
FIXTURES = ("Alder", "Delta")
VARIANTS = ("b1_only", "b2_only", "both_none", "both_exact", "both_control",
            "same_policy_dual", "prompt_only_dual")
B2_VARIANTS = ("b2_only", "both_none", "both_exact", "both_control")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def canonical_sha(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def load(path):
    return json.loads(Path(path).read_bytes())


def require(condition, message):
    if not condition:
        raise ValueError(message)


def finite_unit(value):
    return type(value) in (int, float) and math.isfinite(value) and 0 <= value <= 1


def validated_rows(report, expected, label):
    from v13.common import digest, dumps
    rows = report.get("rows")
    hashes = report.get("row_sha256")
    require(isinstance(rows, list) and isinstance(hashes, dict), label + ": rows/hashes missing")
    found = {}
    for row in rows:
        require(isinstance(row, dict), label + ": nonobject row")
        key = (row.get("fixture"), row.get("variant"))
        require(key in expected and key not in found, label + ": unexpected/duplicate row")
        text_key = ":".join(key)
        require(hashes.get(text_key) == digest(dumps(row)), label + ": row digest mismatch " + text_key)
        require(row.get("status") == "RECORDED", label + ": incomplete row " + text_key)
        found[key] = row
    require(set(found) == expected and set(hashes) == {":".join(k) for k in expected},
            label + ": incomplete/extra row keys")
    return found


def quote_provenance(rows, fixture):
    """Count exact historical-rule B2 quote deliveries, not model-generated paraphrases."""
    old = fixture["old_rules"]
    rule = (f"Budget {old['budget']} euros. Deadline {old['deadline']} days. "
            f"Local-only requirement: {str(old['local_only']).lower()}.")
    historical = 0
    for variant in B2_VARIANTS:
        row = rows[(fixture["id"], variant)]
        messages = row.get("consumer_messages")
        require(isinstance(messages, list), "missing consumer messages")
        users = [m for m in messages if m.get("role") == "user"]
        require(len(users) == 1, "consumer user message not unique")
        packet = json.loads(users[0]["content"])
        require(isinstance(packet.get("analysts"), list), "missing analyst provenance")
        for analyst in packet["analysts"]:
            if analyst.get("role") != "B2_GIST":
                continue
            quotes = analyst.get("verified_quotes")
            require(isinstance(quotes, list), "missing B2 verified quotes")
            for q in quotes:
                require(type(q) is str, "non-string verified quote")
                if rule in q:
                    require(rule in fixture["history"][0], "historical quote not in frozen source")
                    historical += 1
    return {"historical_exact_rule_quotes": historical,
            "revision_overrides_historical_rule": fixture["revision_case"],
            "historical_quote_is_not_by_itself_hallucination": True}


def audit(folder):
    from v13.common import digest, dumps
    folder = Path(folder)
    manifest_path = folder / "RUN394_PREREGISTERED_FIXTURES.json"
    manifest = load(manifest_path)
    require(manifest.get("run") == "Run394" and manifest.get("stage") == "PILOT", "not Run394 pilot")
    require(manifest.get("fixture_ids") == list(FIXTURES), "pilot fixture IDs changed")
    require(manifest.get("seeds") == [20], "pilot seed changed")
    require(manifest.get("arms") == {
        "O": {"base": "C", "query": True, "pointer": "off"},
        "P": {"base": "C", "query": True, "pointer": "pointer"},
        "S": {"base": "D", "query": True, "pointer": "pointer"},
    }, "arm controls changed")
    require(manifest.get("fixture_sha256") == canonical_sha(manifest["fixtures"]), "fixture hash mismatch")
    require(manifest.get("canonical_gate_pass") is False and manifest.get("step2_exit") == "UTILITY_FAIL",
            "unexpected preregistered promotion")
    sources = {"run394_script": ROOT / "scripts/run394_step2_fresh.py",
               "z2_fixture_runner": ROOT / "scripts/step2_z2_timescale.py"}
    require(manifest.get("source_sha256") == {k: sha(p) for k, p in sources.items()},
            "frozen source identity mismatch")
    fixtures = {f["id"]: f for f in manifest["fixtures"]}
    require(set(fixtures) == set(FIXTURES), "fixture map mismatch")
    result = load(folder / "RUN394_RESULT.json")
    require(result.get("run") == "Run394" and result.get("status") == "PILOT_DIAGNOSTIC",
            "pilot incomplete/unsafe")
    require(result.get("canonical_gate_pass") is False and result.get("step2_exit") == "UTILITY_FAIL",
            "result falsely promotes gate")
    require(result.get("preregistration_sha256") == sha(manifest_path), "preregistration bytes changed")
    require(set(result.get("results", {})) == {f"{a}_s20" for a in ARMS}, "result arms incomplete")

    expected = {(f, v) for f in FIXTURES for v in VARIANTS}
    arm_rows = {}
    arm_utilities = {}
    provenance = {}
    sources_bound = {}
    for arm in ARMS:
        rid = f"{arm}_s20"
        source_path = folder / f"step2_{rid}.json"
        tool_path = folder / f"tool_{rid}.json"
        summary_path = folder / f"summary_{rid}.json"
        source, tool, summary = load(source_path), load(tool_path), load(summary_path)
        require(source.get("fixtures") == manifest["fixtures"], rid + ": frozen fixture changed")
        require(source.get("all_structural_checks_passed") is True, rid + ": source structural failure")
        require(source.get("status") in ("UTILITY_FAIL", "UTILITY_PASS_SCOPED"),
                rid + ": source report incomplete")
        require(source.get("wire_arm", {}).get("arm") == "w1", rid + ": source wire changed")
        require(tool.get("installed_artifacts_unchanged") is True, rid + ": installed model changed")
        require(tool.get("status") != "STRUCTURAL_FAIL", rid + ": tool structural failure")
        require(tool.get("canonical_gate_pass") is False and tool.get("phone_measured") is False,
                rid + ": tool claims unsupported promotion")
        require(summary.get("arm") == arm and summary.get("seed") == 20 and summary.get("run") == rid,
                rid + ": summary identity mismatch")
        require(summary.get("z2c", {}).get("b2_quote_select") == manifest["arms"][arm]["pointer"],
                rid + ": quote mode mismatch")
        require(summary.get("z2c", {}).get("wrong_committed_tool") == 0, rid + ": wrong committed tool")
        require(sum(s["wrong_committed"] for s in tool["summary"]["tool"].values()) == 0,
                rid + ": tool wrong-action summary mismatch")
        require(result["results"][rid]["summary_sha256"] == sha(summary_path) and
                result["results"][rid]["tool_sha256"] == sha(tool_path), rid + ": result digest mismatch")
        require(tool.get("preregistration_sha256") ==
                sha(folder / f"tool_{rid}.preregistration.json"), rid + ": tool preregistration mismatch")
        require(load(folder / f"tool_{rid}.preregistration.json")["source_report"]["sha256"] ==
                sha(source_path), rid + ": source/tool replay binding mismatch")
        source_rows = validated_rows(source, expected, rid + ":source")
        tool_rows = validated_rows(tool, expected, rid + ":tool")
        for key in expected:
            s, t = source_rows[key], tool_rows[key]
            require(t.get("oracle_visible_to_native") is False, rid + ": oracle leaked")
            require(t.get("consumer_messages_sha256") == digest(dumps(s["consumer_messages"])),
                    rid + ": consumer source binding mismatch")
            require(finite_unit(t.get("score", {}).get("utility")), rid + ": nonfinite/invalid utility")
            require(type(t.get("elapsed_s")) in (int, float) and math.isfinite(t["elapsed_s"]) and t["elapsed_s"] >= 0,
                    rid + ": invalid elapsed")
        by_variant = {v: sum(tool_rows[(f, v)]["score"]["utility"] for f in FIXTURES) / len(FIXTURES)
                      for v in VARIANTS}
        for v, u in by_variant.items():
            require(abs(u - tool["paired_tool"]["mean_utility"][v]) < 1e-10,
                    rid + ": tool utility mismatch")
            require(abs(u - summary["paired_tool"]["mean_utility"][v]) < 1e-10,
                    rid + ": summary utility mismatch")
        require(result["results"][rid]["rows"] == len(expected), rid + ": row count mismatch")
        arm_rows[arm] = tool_rows
        arm_utilities[arm] = by_variant
        provenance[arm] = {f: quote_provenance(source_rows, fixtures[f]) for f in FIXTURES}
        sources_bound[rid] = {"source_sha256": sha(source_path),
                              "tool_sha256": sha(tool_path), "summary_sha256": sha(summary_path)}

    paired = {}
    for contrast, a, b in (("pointer_minus_off", "P", "O"), ("pointer_minus_shared_body", "P", "S")):
        paired[contrast] = {
            v: {"per_fixture": {f: arm_rows[a][(f, v)]["score"]["utility"] -
                                   arm_rows[b][(f, v)]["score"]["utility"] for f in FIXTURES},
                "mean": arm_utilities[a][v] - arm_utilities[b][v]}
            for v in VARIANTS
        }
    return {"run": "Run396", "status": "PILOT_POSTFLIGHT_VERIFIED",
            "evidence_level": "LINUX_NATIVE_REPORT_AUDIT_NOT_REDMi",
            "source_run": "Run394", "native_rerun": False,
            "rows_verified": len(expected) * len(ARMS), "arm_utility": arm_utilities,
            "paired_differences": paired, "historical_quote_provenance": provenance,
            "source_binding": sources_bound, "manifest_sha256": sha(manifest_path),
            "canonical_gate_pass": False, "step2_exit": "UTILITY_FAIL",
            "redmi_measured": False, "jepa_weight": 0,
            "claim_limit": "Two-fixture seed20 pilot: no significance/causality or STEP2/B3/Body-JEPA/Age/V13 promotion."}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input-dir", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    report = audit(args.input_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n")
    print(json.dumps({"status": report["status"], "rows": report["rows_verified"],
                      "canonical_gate_pass": False, "step2_exit": "UTILITY_FAIL"}, sort_keys=True))


if __name__ == "__main__":
    main()
