#!/usr/bin/env python3
"""Run77 B2 quote/SourceRef diagnostic; read-only, non-promoting.

Mirrors the *bounded* source/quote rule used by Cognition.analyst_context,
rather than either frozen Run77 driver's loose substring predicate or the
frozen independent verifier's equality-only predicate. Does not re-score,
repair, or replace either original native report or frozen verifier.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts import jef_b1b2_context_fixture_797 as fixture79
from scripts.run77_b1b2_context_verify import SCHEMA as ORIGINAL_SCHEMA
from v13.cognition import quote_span

SCHEMA = "v13.run77.b2_quote_provenance_diagnostic.v1"
# Frozen Run52 OVERRIDES['offer_quote_context_chars']; inherited unchanged by Run77.
# The initial 200-char diagnostic cap was too narrow for real seed797 replay.
MAX_POINTER_CONTEXT_CHARS = 400


def audit_report(report):
    findings = []
    verified_prior_refs = 0
    verified_current_refs = 0
    verified_prior_projects = []
    examined = 0

    def fail(code, row=None, ref=None):
        finding = {"code": code}
        if row is not None:
            finding["row"] = row
        if ref is not None:
            finding["ref"] = ref
        findings.append(finding)

    def result():
        return {
            "schema": SCHEMA,
            "status": ("B2_QUOTE_PROVENANCE_DIAGNOSTIC_RED" if findings
                       else "B2_QUOTE_PROVENANCE_DIAGNOSTIC_COMPLETE_SHADOW"),
            "examined_b2_with_prior_current": examined,
            "verified_prior_refs": verified_prior_refs,
            "verified_current_refs": verified_current_refs,
            "verified_prior_projects": verified_prior_projects,
            "missing_prior_projects": [
                x["project"] for x in fixture79.fixtures()
                if x["project"] not in verified_prior_projects],
            "findings": findings,
            "original_frozen_verifier_unchanged": True,
            "native_utility_proven": False,
            "delivery_authority": 0,
            "learning_authority": 0,
            "step2_promoted": False,
            "b3_promoted": False,
            "jepa_weight": 0,
            "whole_system_complete": False,
        }

    if (type(report) is not dict
            or report.get("schema") != ORIGINAL_SCHEMA
            or report.get("seed") != fixture79.SEED
            or report.get("table_sha256") != fixture79.TABLE_SHA256):
        fail("REPORT_IDENTITY_RED")
        return result()
    rows = report.get("rows")
    if type(rows) is not list or len(rows) != 12:
        fail("ROW_COUNT_RED")
        return result()

    for i, registered in enumerate(fixture79.fixtures()):
        row_index = i * 2
        row = rows[row_index]
        other = rows[row_index + 1]
        if (type(row) is not dict or type(other) is not dict
                or row.get("project") != registered["project"]
                or row.get("arm") != "WITH_PRIOR"
                or other.get("project") != registered["project"]
                or other.get("arm") != "CURRENT_ONLY"
                or row.get("source_sha256") != registered["source_sha256"]):
            fail("ROW_IDENTITY_RED", row_index)
            continue
        refs = {
            "prior": row.get("prior_source_ref"),
            "current": row.get("current_source_ref"),
        }
        if any(type(v) is not dict
               or type(v.get("source_id")) is not str
               or not v["source_id"]
               or v.get("sha256") != registered["source_sha256"][k]
               for k, v in refs.items()):
            fail("SOURCE_REF_IDENTITY_RED", row_index)
            continue
        if refs["prior"]["source_id"] == refs["current"]["source_id"]:
            fail("SOURCE_REF_ALIAS_RED", row_index)
            continue
        entries = row.get("offers")
        if type(entries) is not list:
            fail("OFFERS_SHAPE_RED", row_index)
            continue
        candidates = [e for e in entries if type(e) is dict
                      and e.get("role") == "B2_GIST"
                      and e.get("phase") == "current"]
        if len(candidates) != 1:
            fail("B2_CURRENT_OFFER_COUNT_RED", row_index)
            continue
        entry = candidates[0]
        offer = entry.get("offer")
        if type(offer) is not dict or type(offer.get("offer")) is not dict:
            fail("OFFER_SHAPE_RED", row_index)
            continue
        evidence = offer.get("evidence_refs")
        quotes = offer["offer"].get("quotes")
        wide = offer.get("quote_context_chars", 0)
        if (type(evidence) is not list or type(quotes) is not list
                or any(type(q) is not str for q in quotes)
                or type(wide) is not int
                or not 0 <= wide <= MAX_POINTER_CONTEXT_CHARS):
            fail("QUOTE_OR_POINTER_SHAPE_RED", row_index)
            continue
        examined += 1
        project_prior_count = 0
        for ref_index, ref in enumerate(evidence):
            if type(ref) is not dict:
                fail("REF_SHAPE_RED", row_index, ref_index)
                continue
            source_key = next(
                (k for k, v in refs.items()
                 if ref.get("source_id") == v["source_id"]), None)
            if source_key is None:
                fail("FOREIGN_SOURCE_RED", row_index, ref_index)
                continue
            expected = refs[source_key]
            text = registered[source_key]
            start, end = ref.get("char_start"), ref.get("char_end")
            if (ref.get("sha256") != expected["sha256"]
                    or ref.get("modality") != "text"
                    or type(start) is not int or type(end) is not int
                    or not 0 <= start < end <= len(text)
                    or type(expected.get("char_start")) is not int
                    or type(expected.get("char_end")) is not int
                    or not expected["char_start"] <= start < end
                    <= expected["char_end"]):
                fail("SOURCE_SPAN_OR_HASH_RED", row_index, ref_index)
                continue
            exact = text[start:end]
            quoted = exact in quotes
            pointer = (wide > 0 and len(exact) <= wide
                       and any(quote_span(q, exact, wide) is not None
                               for q in quotes))
            if not (quoted or pointer):
                fail("QUOTE_NOT_BOUND_TO_SPAN_RED", row_index, ref_index)
                continue
            if source_key == "prior":
                verified_prior_refs += 1
                project_prior_count += 1
            else:
                verified_current_refs += 1
        if project_prior_count:
            verified_prior_projects.append(registered["project"])
    if examined != 6:
        fail("INCOMPLETE_B2_CURRENT_EXAMINATION_RED")
    return result()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    report = json.loads(args.report.read_text(encoding="utf-8"))
    result = audit_report(report)
    print(json.dumps(result, sort_keys=True, indent=2))
    raise SystemExit(0 if result["status"] ==
                     "B2_QUOTE_PROVENANCE_DIAGNOSTIC_COMPLETE_SHADOW" else 1)


if __name__ == "__main__":
    main()
