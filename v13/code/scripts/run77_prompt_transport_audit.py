#!/usr/bin/env python3
"""Independent Run77 native *prompt-byte* prior-source transport audit.

A persisted QueryPacket context SourceRef is not proof that the model actually
received the source. Reparse captured LlamaRunner.generate messages and bind
the exact archived policy to the actual user prompt. Read-only, no utility
claim or change to frozen scorer/native protocol.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts import jef_b1b2_context_fixture_797 as f
from v13.common import dumps

SCHEMA = "v13.run77.prompt_byte_transport_audit.v1"


def audit_report(report):
    findings = []
    counts = {role: {"WITH_PRIOR": 0, "CURRENT_ONLY": 0}
              for role in f.ROLES}

    def issue(code, index, role=None):
        findings.append({"code": code, "row": index, "role": role})

    rows = report.get("rows") if type(report) is dict else None
    if type(rows) is not list or len(rows) != 12:
        return {"schema": SCHEMA, "status": "PROMPT_TRANSPORT_RED",
                "findings": [{"code": "ROW_COUNT_RED"}],
                "verified": counts, "native_utility_proven": False}
    for fi, fixture in enumerate(f.fixtures()):
        for ai, arm in enumerate(f.ARMS):
            index = fi * 2 + ai
            row = rows[index]
            if type(row) is not dict or row.get("project") != fixture["project"] or row.get("arm") != arm:
                issue("ROW_IDENTITY_RED", index)
                continue
            entries = row.get("offers")
            if type(entries) is not list:
                issue("OFFERS_MISSING", index)
                continue
            for role in f.ROLES:
                matching = [e for e in entries if type(e) is dict
                            and e.get("role") == role and e.get("phase") == "current"]
                if len(matching) != 1:
                    issue("CURRENT_OFFER_MISSING", index, role)
                    continue
                capture = (row.get("captures") or {}).get(role + ":current")
                if type(capture) is not dict:
                    issue("NATIVE_CAPTURE_MISSING", index, role)
                    continue
                messages = capture.get("messages")
                if (type(messages) is not list or len(messages) != 2
                        or capture.get("messages_sha256")
                        != f.sha(dumps(messages).encode())):
                    issue("NATIVE_CAPTURE_HASH_RED", index, role)
                    continue
                system, user = messages
                if (type(system) is not dict or system.get("role") != "system"
                        or type(user) is not dict or user.get("role") != "user"
                        or type(user.get("content")) is not str):
                    issue("NATIVE_MESSAGES_SHAPE_RED", index, role)
                    continue
                try:
                    query = json.loads(user["content"])
                except Exception:
                    issue("NATIVE_QUERY_JSON_RED", index, role)
                    continue
                if type(query) is not dict:
                    issue("NATIVE_QUERY_SHAPE_RED", index, role)
                    continue
                key = "recent_source" if role == "B1_DETAIL" else "earlier_context"
                context = query.get(key, [])
                if type(context) is not list:
                    issue("NATIVE_CONTEXT_SHAPE_RED", index, role)
                    continue
                excerpts = [x.get("exact_source_excerpt") for x in context
                            if type(x) is dict]
                if len(excerpts) != len(context):
                    issue("NATIVE_CONTEXT_ENTRY_RED", index, role)
                    continue
                if arm == "WITH_PRIOR":
                    if excerpts != [fixture["prior"]]:
                        issue("PRIOR_POLICY_NOT_EXACT_IN_NATIVE_QUERY", index, role)
                        continue
                    if fixture["prior"] not in user["content"]:
                        issue("PRIOR_POLICY_NOT_IN_CAPTURED_PROMPT", index, role)
                        continue
                    authority = context[0].get("authority")
                    allowed = ("RECENT_SOURCE_NOT_FACT" if role == "B1_DETAIL"
                               else "PRIOR_HYPOTHESIS_NOT_FACT")
                    if authority != allowed:
                        issue("PRIOR_CONTEXT_AUTHORITY_RED", index, role)
                        continue
                else:
                    if context or fixture["prior"] in user["content"]:
                        issue("ABLATION_PRIOR_POLICY_LEAK_RED", index, role)
                        continue
                counts[role][arm] += 1
    return {
        "schema": SCHEMA,
        "status": ("PROMPT_BYTES_SOURCE_TRANSPORT_VERIFIED_SHADOW"
                   if not findings and all(n == 6 for arm in counts.values()
                                           for n in arm.values())
                   else "PROMPT_TRANSPORT_RED"),
        "verified": counts,
        "findings": findings,
        "native_utility_proven": False,
        "learning_authority": 0,
        "delivery_authority": 0,
        "step2_promoted": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    result = audit_report(json.loads(args.report.read_text(encoding="utf-8")))
    print(json.dumps(result, sort_keys=True, indent=2))
    raise SystemExit(0 if result["status"] ==
                     "PROMPT_BYTES_SOURCE_TRANSPORT_VERIFIED_SHADOW" else 1)


if __name__ == "__main__":
    main()
