"""Post-hoc read-only native B1/B2 verified quote coverage (no model execution).

The original Run26 raw ZIP is verified first by the pinned Run30 auditor.
No source text, quotations, model completions or oracle values are emitted.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import zipfile

from scripts import run30_native_keldara_aggregate_audit as sealed
from scripts import step2_z2_timescale as z2

EXPECTED_ROLES = {
    "b1_only": ("B1_DETAIL",),
    "b2_only": ("B2_GIST",),
    "both_none": ("B1_DETAIL", "B2_GIST"),
    "both_exact": ("B1_DETAIL", "B2_GIST"),
    "both_control": ("B1_DETAIL", "B2_GIST"),
    "same_policy_dual": ("B1_DETAIL", "B1_DETAIL"),
    "prompt_only_dual": ("B1_DETAIL", "B2_GIST"),
}


def summarize_report(report):
    """Summarize already-sealed consumer evidence, never publish source text."""
    if (not isinstance(report, dict) or
            report.get("fixture_sha256") != sealed.FIXTURE_SHA256):
        raise ValueError("quote_report_fixture_mismatch")
    rows = report.get("rows")
    if not isinstance(rows, list) or len(rows) != len(sealed.VARIANTS):
        raise ValueError("quote_rows_incomplete")
    if {r.get("variant") for r in rows if isinstance(r, dict)} != set(sealed.VARIANTS):
        raise ValueError("quote_variants_invalid")
    if len({r.get("variant") for r in rows if isinstance(r, dict)}) != len(rows):
        raise ValueError("quote_variants_duplicate")
    access = z2.information_access(report)
    if set(access) != {"Keldara:" + v for v in sealed.VARIANTS}:
        raise ValueError("quote_access_index_invalid")
    counts = {}
    coverage = {}
    for row in rows:
        variant = row["variant"]
        if row.get("fixture") != "Keldara":
            raise ValueError("quote_fixture_invalid")
        messages = row.get("consumer_messages")
        if not isinstance(messages, list):
            raise ValueError("quote_messages_missing")
        user = [m for m in messages if isinstance(m, dict) and m.get("role") == "user"]
        if len(user) != 1 or not isinstance(user[0].get("content"), str):
            raise ValueError("quote_user_envelope_invalid")
        try:
            payload = json.loads(user[0]["content"])
        except (TypeError, ValueError) as exc:
            raise ValueError("quote_user_json_invalid") from exc
        if (not isinstance(payload, dict) or
                set(payload) != {"current_source", "analysts"} or
                not isinstance(payload["current_source"], str) or
                not isinstance(payload["analysts"], list)):
            raise ValueError("quote_user_payload_invalid")
        analysts = payload["analysts"]
        roles = []
        by_role = {}
        for a in analysts:
            if not isinstance(a, dict) or a.get("role") not in ("B1_DETAIL", "B2_GIST"):
                raise ValueError("quote_role_invalid")
            quotes = a.get("verified_quotes")
            if (not isinstance(quotes, list) or
                    any(not isinstance(q, str) for q in quotes)):
                raise ValueError("quote_verified_list_invalid")
            role = a["role"]
            roles.append(role)
            by_role[role] = by_role.get(role, 0) + len(quotes)
        if tuple(roles) != EXPECTED_ROLES[variant]:
            raise ValueError("quote_variant_role_contract")
        role_access = access["Keldara:" + variant]
        if set(role_access) != set(roles):
            raise ValueError("quote_coverage_role_mismatch")
        for role, flags in role_access.items():
            if (not isinstance(flags, dict) or
                    set(flags) != {"rules", "options"} or
                    type(flags["rules"]) is not bool or
                    type(flags["options"]) is not bool or
                    (flags["rules"] or flags["options"]) and by_role[role] == 0):
                raise ValueError("quote_coverage_invalid")
        counts[variant] = {role: by_role.get(role, 0)
                           for role in ("B1_DETAIL", "B2_GIST")}
        coverage[variant] = {
            role: {"rules": flags["rules"], "options": flags["options"]}
            for role, flags in sorted(role_access.items())
        }
    return {
        "schema": "v13.run32.keldara.quote_coverage.v1",
        "evidence_level": "POST_HOC_ORIGINAL_LINUX_NATIVE_ONE_FIXTURE_QUOTE_COVERAGE",
        "source_run_id": 40715223545,
        "quote_counts": {v: counts[v] for v in sealed.VARIANTS},
        "role_coverage": {v: coverage[v] for v in sealed.VARIANTS},
        "both_exact_b2_verified_quotes": counts["both_exact"]["B2_GIST"],
        "both_exact_b2_rules_present": coverage["both_exact"]["B2_GIST"]["rules"],
        "both_exact_b1_options_present": coverage["both_exact"]["B1_DETAIL"]["options"],
        "canonical_gate_pass": False,
        "phone_measured": False,
        "jepa_weight": 0,
        "whole_system_complete": False,
    }


def audit_zip(path):
    sealed.audit_zip(path)
    with zipfile.ZipFile(Path(path)) as z:
        report = json.loads(z.read("STEP2_RAW.json"))
    return summarize_report(report)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("private_original_run26_zip")
    args = p.parse_args(argv)
    print(json.dumps(audit_zip(args.private_original_run26_zip),
                     sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
