#!/usr/bin/env python3
"""Run117AP independent offline audit of original Run117AM native ZIP.

No model execution. Original frozen seed1073 source/model/runner are unchanged.
A valid original native receipt is NOT a semantic utility or promotion proof.
"""
from __future__ import annotations

import argparse
from hashlib import sha1, sha256
from io import BytesIO
import json
from pathlib import Path
import stat
import zipfile

SCHEMA = "v13.run117ap.original_native_body_source_id_audit.v1"
OUTER_SHA = "9a853e3e8cfbd16228b0573d9023fda01746c59a79a6c7e17c51c33254eb8131"
SOURCE_ZIP_SHA = "a453588cb2ebca24412cd3445767703a645ca272670ff30dc3ae080ecf52314a"
HEAD = "5edeeffe9689ac32faabf0ff3bff7572e579c918"
FIXTURE_SHA = "18c0c9211daca9b1e5df12443713f6001db10ea6b5e9a778c8c9eb744d7579d1"
IDS = ("Halcyon", "Iris", "Juniper", "Kestrel", "Lumen", "Meridian")
BLOBS = {
    "scripts/run117am_body_source_id_native.py": "4afe7c2cb0521f480414befe150bb614dc3deaac",
    "v13/body_source_id_prewarm_candidate.py": "2ee2ed21a70b36b1d470cc40a761c614daadc89a",
    "v13/b1b2_source_id_quote_candidate.py": "e431eecaa4a7643a548a512036225343f681ee23",
}
MODELS = {
    "B1_DETAIL": ("LFM2.5-1.2B-Instruct-QAD-Q4_0.gguf",
                  "bb741ebb106d543e9de114b843a3d3d73d51c74b5801e69da2abde821a0cb3e1"),
    "B2_GIST": ("Qwen3.5-0.8B-Q4_0.gguf",
                "57d1997790d1744fba5b40a7317df71ea5e2acee28c47e78f0cce39c0703f8cf"),
}


def fail(code):
    raise ValueError("RUN117AP_" + code + "_RED")


def pairs(items):
    out = {}
    for k, v in items:
        if k in out:
            fail("DUPLICATE_JSON_KEY")
        out[k] = v
    return out


def decode(data):
    return json.loads(data, object_pairs_hook=pairs,
                      parse_constant=lambda _: fail("NONFINITE_JSON"))


def verify_zip(blob, expected_members, manifest_name, *, nested=False):
    try:
        z = zipfile.ZipFile(BytesIO(blob))
        names = z.namelist()
        if len(names) != len(set(names)) or len(names) != expected_members + 1:
            fail("ZIP_MEMBERS")
        for info in z.infolist():
            name = info.filename
            if (not name or name.startswith("/") or "\\" in name
                    or any(x in ("", ".", "..") for x in name.split("/"))
                    or stat.S_IFMT(info.external_attr >> 16) == stat.S_IFLNK):
                fail("ZIP_PATH")
        if z.testzip() is not None:
            fail("ZIP_CRC")
        if nested:
            m = decode(z.read(manifest_name))
            if (m.get("schema_version") != 1 or
                    type(m.get("files")) is not dict or
                    len(m["files"]) != expected_members):
                fail("SOURCE_MANIFEST")
            for name, digest in m["files"].items():
                if (type(digest) is not str or len(digest) != 64 or
                        sha256(z.read("V13-Phone/" + name)).hexdigest() != digest):
                    fail("SOURCE_INNER_SHA")
            if set(names) != {"V13-Phone/" + x for x in m["files"]} | {manifest_name}:
                fail("SOURCE_COVERAGE")
        else:
            lines = z.read(manifest_name).decode("utf-8").splitlines()
            seen = set()
            for line in lines:
                try:
                    digest, name = line.split("  ", 1)
                except ValueError:
                    fail("MANIFEST_SHAPE")
                name = name.removeprefix("./")
                if (len(digest) != 64 or name in seen or
                        name == manifest_name or name not in names):
                    fail("MANIFEST_SHAPE")
                seen.add(name)
                if sha256(z.read(name)).hexdigest() != digest:
                    fail("INNER_SHA")
            if len(seen) != expected_members or seen != set(names) - {manifest_name}:
                fail("MANIFEST_COVERAGE")
        return z
    except (zipfile.BadZipFile, KeyError, UnicodeError) as exc:
        fail("ZIP_FORMAT")


def git_blob(data):
    return sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def verify_ref(source, ref):
    if (type(ref) is not dict or ref.get("char_start") != 0 or
            ref.get("char_end") != len(source) or
            ref.get("sha256") != sha256(source.encode("utf-8")).hexdigest() or
            ref.get("modality") != "text" or
            type(ref.get("source_id")) is not str):
        fail("SOURCE_REF")


def evidence(item, key, kind):
    obj = item.get(key)
    if (type(obj) is not dict or obj.get("kind") != kind or
            type(obj.get("raw")) is not str or
            sha256(obj["raw"].encode("utf-8")).hexdigest() != obj.get("sha256")):
        fail("RAW_PACKET_SHA")
    return decode(obj["raw"])


def audit_bytes(blob, *, expected_outer=None):
    if type(blob) is not bytes or sha256(blob).hexdigest() != (
            OUTER_SHA if expected_outer is None else expected_outer):
        fail("OUTER_SHA")
    z = verify_zip(blob, 31, "SHA256SUMS")
    if z.read("HEAD.txt").decode().strip() != HEAD:
        fail("HEAD")
    receipt = decode(z.read("RESULT.json"))
    if receipt != decode(z.read("RESULT_RAW.log")):
        fail("RECEIPT")
    exits = receipt.get("exits")
    if (receipt.get("head") != HEAD or
            receipt.get("seed") != 1073 or
            receipt.get("fixture_sha256") != FIXTURE_SHA or
            receipt.get("schema") !=
            "v13.run117am.original_native_workflow_receipt.v1" or
            type(exits) is not dict or len(exits) != 12 or
            set(exits) != {n[:-9] for n in z.namelist() if n.endswith("_EXIT.txt")} or
            any(type(rc) is not int or rc != 0 or
                z.read(name + "_EXIT.txt").decode().strip() != "0"
                for name, rc in exits.items())):
        fail("WORKFLOW_RECEIPT")
    if (receipt.get("step2_promoted") is not False or
            receipt.get("b3_promoted") is not False or
            receipt.get("jepa_weight") != 0 or
            receipt.get("redmi_measured") is not False or
            receipt.get("whole_system_complete") is not False):
        fail("WORKFLOW_GATES")
    source_blob = z.read("V13-Phone-Run117AM.zip")
    if sha256(source_blob).hexdigest() != SOURCE_ZIP_SHA:
        fail("SOURCE_ZIP_SHA")
    source_zip = verify_zip(source_blob, 2304, "V13-Phone/WORKSPACE_FILES.json",
                            nested=True)
    for path, sha in BLOBS.items():
        if git_blob(source_zip.read("V13-Phone/" + path)) != sha:
            fail("SOURCE_BLOB")
    fixture_raw = source_zip.read(
        "V13-Phone/docs/fixtures/RUN117AM_BODY_SOURCE_ID_SEED1073.json")
    if sha256(fixture_raw).hexdigest() != FIXTURE_SHA:
        fail("FIXTURE_SHA")
    fixture = decode(fixture_raw)
    if (fixture.get("seed") != 1073 or
            tuple(x["id"] for x in fixture["rows"]) != IDS):
        fail("FIXTURE_ROWS")
    install_log = z.read("INSTALL_BODIES_RAW.log").decode("utf-8")
    try:
        install = next(decode(line) for line in reversed(install_log.splitlines())
                       if line.startswith('{"model_sha256":'))
    except StopIteration:
        fail("MODEL_RECEIPT")
    if (install.get("status") != "RUN117AM_PINNED_B1_B2_INSTALLED" or
            install.get("weights_exported") is not False or
            install.get("model_sha256") != {
                "body": MODELS["B1_DETAIL"][1],
                "gist": MODELS["B2_GIST"][1]}):
        fail("MODEL_RECEIPT")
    report = decode(z.read("NATIVE_CASE/report.json"))
    if (report.get("schema") != "v13.run117am.body_source_id_native_seed1073.v1"
            or report.get("seed") != 1073 or
            report.get("fixture_sha256") != FIXTURE_SHA or
            report.get("status") != "NATIVE_COMPLETE_BODY_ID_DIAGNOSTIC" or
            report.get("native_body_calls") != 30 or
            any(report.get(k) != 0 for k in
                ("native_c3_calls", "native_jef_calls", "native_c2_calls")) or
            report.get("age0") != "RECORD_ONLY" or
            report.get("step2_exit") != "EVIDENCE_NOT_PASSING" or
            report.get("b3") != "NO_PROMOTION" or
            report.get("body_jepa") != "UNAVAILABLE" or
            report.get("jepa_weight") != 0 or
            report.get("output_committed") is not False or
            report.get("tool_dispatches") != 0 or
            report.get("learning_authority") != 0 or
            report.get("delivery_authority") != 0 or
            report.get("redmi_measured") is not False or
            report.get("whole_system_complete") is not False):
        fail("NATIVE_REPORT_GATES")
    rows = report.get("rows")
    if type(rows) is not list or len(rows) != 6:
        fail("ROW_COUNT")
    by_role = {"B1_DETAIL": 0, "B2_GIST": 0}
    pair_count = 0
    quote_count = 0
    raw_packets = 0
    for row, source_row in zip(rows, fixture["rows"]):
        if (row.get("id") != source_row["id"] or
                row.get("prior_source_text") != source_row["prior"] or
                row.get("current_source_text") != source_row["current"] or
                row.get("status") != "RECORDED" or
                row.get("closed_store_ok") is not True or
                row.get("no_live_output") is not True or
                type(row.get("baseline_quote_ready")) is not bool or
                type(row.get("offers")) is not list or
                type(row.get("id_selections")) is not list or
                len(row["offers"]) != 3 or len(row["id_selections"]) != 2):
            fail("ROW_SOURCE")
        prior, current = row["prior_source_text"], row["current_source_text"]
        verify_ref(prior, row["prior_source_ref"])
        verify_ref(current, row["current_source_ref"])
        quote_count += int(row["baseline_quote_ready"])
        for item, role, source in (
            (row["offers"][0], "B2_GIST", prior),
            (row["offers"][1], "B1_DETAIL", current),
            (row["offers"][2], "B2_GIST", current),
        ):
            ref = row["prior_source_ref"] if source == prior else row["current_source_ref"]
            if (item.get("role") != role or item.get("source_ref") != ref or
                    item.get("status") != "RECORDED" or
                    item.get("process_reaped") is not True or
                    item.get("native_metrics", {}).get("status") != "FINAL" or
                    item["native_metrics"].get("actual_model") != MODELS[role][0]):
                fail("BASELINE_NATIVE")
            p = evidence(item, "packet_evidence", "OfferPacket")
            q = evidence(item, "query_evidence", "QueryPacket")
            if (p.get("packet_id") != item.get("packet_id") or
                    q.get("packet_id") != item.get("query_packet_id") or
                    p.get("role") != role or q.get("role") != role):
                fail("BASELINE_PACKET")
            raw_packets += 2
        role_correct = []
        for item, role, source, ref in (
            (row["id_selections"][0], "B2_GIST", prior, row["prior_source_ref"]),
            (row["id_selections"][1], "B1_DETAIL", current, row["current_source_ref"]),
        ):
            if (item.get("role") != role or item.get("source_ref") != ref or
                    item.get("status") != "RECORDED" or
                    item.get("native_final") is not True or
                    item.get("process_reaped") is not True or
                    item.get("native_metrics", {}).get("status") != "FINAL" or
                    item["native_metrics"].get("actual_model") != MODELS[role][0]):
                fail("ID_NATIVE")
            p = evidence(item, "packet_evidence", "BodySourceIdSelection")
            if (p.get("packet_id") != item.get("packet_id") or
                    p.get("role") != role or p.get("source_ref") != ref or
                    p.get("provenance") != [ref] or
                    p.get("output_committed") is not False or
                    p.get("delivery_authority") != 0 or
                    p.get("learning_authority") != 0 or
                    p.get("source_semantic_truth_authority") is not False or
                    p.get("model_hypothesis_not_fact") is not True or
                    p.get("raw_output_sha256") !=
                    sha256(item["raw_output"].encode("utf-8")).hexdigest() or
                    p.get("raw_output_bytes") != len(item["raw_output"].encode("utf-8"))):
                fail("ID_PACKET")
            candidates = p.get("candidates")
            if type(candidates) is not list or len(candidates) != 2:
                fail("ID_CANDIDATES")
            ids = set()
            for candidate in candidates:
                sub = candidate.get("source_ref")
                if (type(sub) is not dict or
                        candidate.get("origin") != "STORE_EXACT_USER_NOT_MODEL_QUOTE" or
                        sub.get("source_id") != ref["source_id"] or
                        sub.get("sha256") != ref["sha256"] or
                        type(sub.get("char_start")) is not int or
                        type(sub.get("char_end")) is not int or
                        not 0 <= sub["char_start"] < sub["char_end"] <= len(source) or
                        candidate.get("text") !=
                        source[sub["char_start"]:sub["char_end"]]):
                    fail("ID_SOURCE_SPAN")
                ids.add(candidate.get("span_id"))
            if len(ids) != 2:
                fail("ID_CANDIDATE_IDS")
            target = [c for c in candidates if c["text"].startswith(
                "Binding policy:" if role == "B2_GIST" else "Option A:")]
            if len(target) != 1:
                fail("ID_TARGET_UNIQUE")
            selected = p.get("selected_id")
            if selected not in ids | {"NONE"}:
                fail("ID_SELECTION_SHAPE")
            correct = selected == target[0]["span_id"]
            chosen = next((c for c in candidates if c["span_id"] == selected), None)
            expected_span = None if chosen is None else {
                k: v for k, v in chosen.items() if k != "span_id"}
            if (p.get("selected_span") != expected_span or
                    p.get("selection_correct_shadow") is not correct or
                    item.get("model_id_correct") is not correct or
                    item.get("component_status") != (
                        "SHADOW_SOURCE_ID_SELECTED" if correct else
                        ("SHADOW_ABSTAIN_RECORDED" if selected == "NONE" else
                         "SHADOW_WRONG_SOURCE_ID_RECORDED"))):
                fail("ID_SCORE_FORGED")
            by_role[role] += int(correct)
            role_correct.append(correct)
            raw_packets += 1
        pair = all(role_correct)
        if row.get("id_pair_correct") is not pair:
            fail("PAIR_SCORE_FORGED")
        pair_count += int(pair)
    if (raw_packets != 30 or
            by_role != {"B1_DETAIL": 3, "B2_GIST": 4} or
            pair_count != 2 or quote_count != 4 or
            report.get("model_id_by_role_correct") != by_role or
            report.get("model_id_pair_correct_count") != pair_count or
            report.get("baseline_quote_ready_count") != quote_count):
        fail("TOTAL_SCORE_FORGED")
    return {
        "schema": SCHEMA, "status": "INDEPENDENT_ORIGINAL_NATIVE_COMPLETE_LOW_UTILITY",
        "original_zip_sha256": sha256(blob).hexdigest(),
        "original_source_head": HEAD, "nested_source_zip_sha256": SOURCE_ZIP_SHA,
        "nested_source_files_verified": 2304, "outer_inner_files_verified": 31,
        "fixture_sha256": FIXTURE_SHA, "native_body_calls": 30,
        "raw_packets_verified": raw_packets,
        "body_id_correct_by_role": by_role, "body_id_pair_correct": pair_count,
        "baseline_quote_ready_reported": quote_count,
        "model_weights_independently_rehashed": False,
        "native_execution_by_auditor": False,
        "redmi_measured": False, "step2_promoted": False, "b3_promoted": False,
        "body_jepa_promoted": False, "jepa_weight": 0,
        "output_committed": False, "tool_dispatches": 0,
        "learning_authority": 0, "whole_system_complete": False,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("original_zip", type=Path)
    a = p.parse_args()
    print(json.dumps(audit_bytes(a.original_zip.read_bytes()), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
