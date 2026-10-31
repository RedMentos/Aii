#!/usr/bin/env python3
"""Read-only Run77 compact native forensic: distinguish summary cap from utility.

Original independent verifier failure is retained, never relabelled GREEN.
This is retrospective evidence, not a new native experiment or causal proof.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
from pathlib import Path
from zipfile import BadZipFile, ZipFile

ZIP_SHA = "62ebd85d4c3defb40c15c03148d24aea3017687217f2299db561ac17ceba0e5c"
TABLE_SHA = "3c5c50be02d9bcb87384ea6a1f85c31ce276c02c3cb508f9fecd51c23da4fdbb"
PROJECTS = ("Alder", "Birch", "Cedar", "Dune", "Elm", "Fir")
ARMS = ("WITH_PRIOR", "CURRENT_ONLY")
ROLES = ("B1_DETAIL", "B2_GIST")
MODELS = {"B1_DETAIL": "LFM2.5-1.2B-Instruct-QAD-Q4_0.gguf",
          "B2_GIST": "Qwen3.5-0.8B-Q4_0.gguf"}
LATE_UNHASHED = {"SIZE_EXIT.txt", "SIZE_RAW.log"}
ZERO_STAGES = ("ANCESTRY", "AUDIT", "BOOTSTRAP", "COMPILE", "DEPS",
               "DIAG", "DIFF", "LEGACY_TEST", "NATIVE", "PINS", "PRIVACY",
               "SIZE", "TEST", "VENV")

class AuditError(ValueError):
    pass


def need(ok, code):
    if not ok:
        raise AuditError(code)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def summary_cap(observer_tokens, quote_min_chars):
    """Frozen v13.cognition.offer_schema math, not an adaptive model fit."""
    chars = max(110, int((int(observer_tokens) - 30) * 2.2))
    summary = max(48, int(chars * .45))
    uncertainty = max(16, int(chars * .15))
    quote = max(24, int(chars * .2))
    if quote_min_chars > quote:
        new_quote = min(int(quote_min_chars), (chars - 48 - uncertainty) // 2)
        if new_quote > quote:
            summary = chars - 2 * new_quote - uncertainty
    return summary


def audit_report(report, diag):
    need(type(report) is dict and report.get("schema") == "v13.run77.b1b2_disjoint_context_native.v1"
         and report.get("seed") == 797 and report.get("table_sha256") == TABLE_SHA
         and report.get("status") == "B1B2_CONTEXT_UTILITY_SCIENTIFIC_RED"
         and report.get("native_call_count") == 36
         and report.get("b2_prior_evidence") == 5
         and report.get("scores") == {role: {arm: 0 for arm in ARMS} for role in ROLES},
         "RUN77_FROZEN_NATIVE_REPORT_RED")
    negative = {"age0": "RECORD_ONLY", "step2": "UTILITY_FAIL",
                "b3": "NO_PROMOTION", "body_jepa": "UNAVAILABLE",
                "world_jepa": "SHADOW", "jepa_weight": 0,
                "redmi_measured": False, "whole_system_complete": False,
                "independent_utility_proven": False,
                "delivery_authority": 0, "learning_authority": 0,
                "output_committed": False, "tool_dispatches": 0}
    need(all(type(report.get(k)) is type(v) and report[k] == v for k, v in negative.items()),
         "RUN77_NEGATIVE_GATES_RED")
    rows = report.get("rows")
    need(type(rows) is list and len(rows) == 12, "RUN77_ROW_COUNT_RED")
    summaries = []
    native_calls = 0
    driver_b2_evidence = 0
    for i, project in enumerate(PROJECTS):
        for j, arm in enumerate(ARMS):
            row = rows[2 * i + j]
            count = 4 if arm == "WITH_PRIOR" else 2
            need(type(row) is dict and row.get("project") == project
                 and row.get("arm") == arm and row.get("status") == "RECORDED"
                 and row.get("native_call_count") == count
                 and row.get("processes_reaped") is True
                 and row.get("closed_store_ok") is True
                 and row.get("no_live_output") is True,
                 "RUN77_ROW_STRUCTURE_RED")
            offers = row.get("offers")
            need(type(offers) is list and len(offers) == count,
                 "RUN77_OFFER_COUNT_RED")
            sequence = ([(role, "prior") for role in ROLES] if arm == "WITH_PRIOR" else [])
            sequence += [(role, "current") for role in ROLES]
            for entry, (role, phase) in zip(offers, sequence):
                need(type(entry) is dict and entry.get("role") == role
                     and entry.get("phase") == phase
                     and entry.get("status") == "RECORDED"
                     and entry.get("process_reaped") is True,
                     "RUN77_OFFER_ORDER_RED")
                offer = entry.get("offer")
                need(type(offer) is dict and type(offer.get("offer")) is dict
                     and type(offer["offer"].get("summary")) is str
                     and offer.get("native_metrics", {}).get("status") == "FINAL"
                     and offer.get("native_metrics", {}).get("actual_model") == MODELS[role],
                     "RUN77_NATIVE_OFFER_RED")
                summary = offer["offer"]["summary"]
                need(len(summary) == 48, "RUN77_SUMMARY_LENGTH_NOT_FROZEN_48_RED")
                summaries.append(len(summary))
                if phase == "current":
                    need(type(entry.get("strict")) is int and entry["strict"] == 0,
                         "RUN77_STRICT_SCORE_RED")
                    if role == "B2_GIST" and arm == "WITH_PRIOR":
                        driver_b2_evidence += int(entry.get("prior_evidence_refs_verified") is True)
                native_calls += 1
    need(native_calls == 36 and len(summaries) == 36
         and driver_b2_evidence == report["b2_prior_evidence"],
         "RUN77_NATIVE_COUNT_OR_B2_DRIVER_RED")
    need(type(diag) is dict and diag.get("schema") == "v13.run77.forensic_diagnostic.v1"
         and diag.get("status") == "ORIGINAL_VERIFIER_RED"
         and diag.get("original_error") == "ValueError:RUN77_B2_PRIOR_EVIDENCE_RED"
         and diag.get("original_scientific_status") == "B1B2_CONTEXT_UTILITY_SCIENTIFIC_RED"
         and diag.get("native_calls_observed") == 36,
         "RUN77_ORIGINAL_VERIFIER_DIAGNOSTIC_RED")
    need(summary_cap(96, 80) == 48 and summary_cap(160, 80) == 84,
         "RUN77_SCHEMA_CAP_MATH_RED")
    return {"status": "CAP_CONFOUND_OBSERVED_NOT_CAUSAL_PROOF",
            "native_body_calls_reported": native_calls,
            "persisted_summary_lengths": {"48": 36},
            "original_strict_scores": report["scores"],
            "driver_b2_prior_evidence": driver_b2_evidence,
            "original_independent_verifier": "RED",
            "observer_tokens_original": 96,
            "summary_max_chars_original": summary_cap(96, 80),
            "summary_max_chars_160_candidate": summary_cap(160, 80),
            "native_replay_new": False,
            "causal_summary_cap_proven": False,
            "step2_promoted": False}


def audit_bytes(raw, *, expected_zip_sha=ZIP_SHA):
    need(type(raw) is bytes and sha(raw) == expected_zip_sha, "RUN77_ZIP_SHA_RED")
    try:
        with ZipFile(io.BytesIO(raw)) as z:
            names = z.namelist()
            need(len(names) == len(set(names)) == 58, "RUN77_ZIP_MEMBERS_RED")
            need(z.testzip() is None, "RUN77_ZIP_CRC_RED")
            manifest = z.read("SHA256SUMS").decode("ascii").splitlines()
            found = {}
            for line in manifest:
                m = re.fullmatch(r"([0-9a-f]{64})  \./([A-Za-z0-9_./-]+)", line)
                need(m is not None and m[2] not in found, "RUN77_MANIFEST_DUPLICATE_OR_SYNTAX_RED")
                found[m[2]] = m[1]
            need(len(found) == 55 and set(found) == set(names) - LATE_UNHASHED - {"SHA256SUMS"},
                 "RUN77_MANIFEST_COVERAGE_RED")
            for name, digest in found.items():
                need(sha(z.read(name)) == digest, "RUN77_MEMBER_SHA_RED:" + name)
            for stage in ZERO_STAGES:
                need(z.read(stage + "_EXIT.txt") == b"0\n",
                     "RUN77_STAGE_EXIT_RED:" + stage)
            need(z.read("VERIFY_EXIT.txt") == b"1\n",
                 "RUN77_ORIGINAL_VERIFIER_MUST_STAY_RED")
            report = json.loads(z.read("report.json"))
            diag = json.loads(z.read("DIAG.json"))
            result = audit_report(report, diag)
    except (BadZipFile, OSError, UnicodeError, KeyError, json.JSONDecodeError) as exc:
        raise AuditError("RUN77_UNREADABLE_ZIP_RED") from exc
    result.update(original_zip_sha256=sha(raw),
                  original_inner_hashed=55,
                  original_unhashed_late_receipts=sorted(LATE_UNHASHED))
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("original_compact_zip", type=Path)
    args = p.parse_args()
    print(json.dumps(audit_bytes(args.original_compact_zip.read_bytes()), indent=2, sort_keys=True))

if __name__ == "__main__":
    main()
