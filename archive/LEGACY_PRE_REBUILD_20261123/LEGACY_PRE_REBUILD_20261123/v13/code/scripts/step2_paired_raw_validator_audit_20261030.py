"""Read-only posthoc audit of the exact original STEP2 paired native RED ZIP.

Does not re-score the registered pilot, change its verdict, or grant gates.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import zipfile

ORIGINAL_ZIP_SHA256 = "fcc66cf5d0d2c59bfe3bbd7a8b5b3c140169ee5a05020d9e4df12e566c30d9ce"
ORIGINAL_HEAD = "c6a9de775c2e7f4f450472f75db0481458894386"
ORIGINAL_FIXTURE_SHA256 = "203db76970a98d3ef54a3f78c665bdfedfe2d619e008d3f4315e4df7115004df"
ARMS = ("A_C3_ONLY", "B_DEFAULT_BOTH", "C_ARITH_BOTH")
EXPECTED_MODELS = {
    "A_C3_ONLY": "LFM2.5-350M-QAD-Q4_0.gguf",
    "B_DEFAULT_BOTH": "LFM2.5-1.2B-Instruct-QAD-Q4_0.gguf",
    "C_ARITH_BOTH": "LFM2.5-1.2B-Instruct-QAD-Q4_0.gguf",
}
_AMOUNT = r"(?<!\d)(?P<amount>[0-9]{1,9})\s*(?:euros?|eur|€)(?!\w)"


def _need(ok, reason):
    if not ok:
        raise ValueError(reason)


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _number_claims(text, label, other):
    """Conservative diagnostic; only explicit option-local remainder claims.

    This is posthoc and is NOT the preregistered STEP2 scorer. Contradictory
    claims veto credit, even when one occurrence is numerically correct.
    """
    _need(type(text) is str and type(label) is str and type(other) is str,
          "SEMANTIC_INPUT_SHAPE_RED")
    label_pat = re.compile(r"\b" + re.escape(label) + r"\b", re.I)
    other_pat = re.compile(r"\b" + re.escape(other) + r"\b", re.I)
    claims = set()
    for clause in re.split(r"[.;\n]", text):
        for m in label_pat.finditer(clause):
            # No amount belonging to the other option may be inherited.
            suffix = clause[m.end():]
            stop = other_pat.search(suffix)
            if stop is not None:
                suffix = suffix[:stop.start()]
            # An explicit remainder verb/phrase must be adjacent to the amount.
            for hit in re.finditer(
                    r"\b(?:leaves?|remaining\s+budget(?:\s+of)?|balance(?:\s+of)?)"
                    r"\b[^0-9]{0,25}" + _AMOUNT, suffix, re.I):
                claims.add(int(hit.group("amount")))
            # Amount followed by 'remaining/left', excluding raw cost figures.
            for hit in re.finditer(_AMOUNT +
                                   r"\s*(?:\b(?:left|remaining|remainder)\b)",
                                   suffix, re.I):
                claims.add(int(hit.group("amount")))
            # 'The remaining budget for Option X is N Euro, and for Option Y
            # it is M Euro' inherits only the same clause's explicit premise.
            prefix = clause[:m.start()]
            if re.search(r"\bremaining\s+budget\b", prefix, re.I):
                for hit in re.finditer(r"\b(?:it\s+is|is|has)\s+" + _AMOUNT,
                                       suffix, re.I):
                    claims.add(int(hit.group("amount")))
    return sorted(claims)


def semantic_diagnostic(fixture, text):
    _need(type(fixture) is dict and type(text) is str, "SEMANTIC_INPUT_RED")
    verdicts = {}
    for name_key, cost_key, foreign_key in (("a", "a_cost", "b"),
                                            ("b", "b_cost", "a")):
        label = fixture[name_key]
        claims = _number_claims(text, label, fixture[foreign_key])
        expected = fixture["budget"] - fixture[cost_key]
        status = ("MISSING" if not claims else
                  "CONTRADICTORY" if len(claims) != 1 else
                  "CORRECT" if claims[0] == expected else "WRONG")
        verdicts[name_key] = {"status": status, "claims": claims,
                              "expected": expected, "correct": status == "CORRECT"}
    return verdicts


def audit_zip(path):
    raw = Path(path).read_bytes()
    _need(_sha(raw) == ORIGINAL_ZIP_SHA256, "ORIGINAL_ZIP_SHA_RED")
    with zipfile.ZipFile(path) as z:
        _need(z.testzip() is None, "ZIP_CRC_RED")
        names = z.namelist()
        _need(len(names) == len(set(names)), "DUPLICATE_ZIP_MEMBER_RED")
        manifest = z.read("SHA256SUMS").decode("utf-8").splitlines()
        declared = set()
        for line in manifest:
            m = re.fullmatch(r"([a-f0-9]{64})  \./([^\n]+)", line)
            _need(m is not None, "MANIFEST_FORMAT_RED")
            digest, name = m.groups()
            _need(name not in declared and name in names and name != "SHA256SUMS",
                  "MANIFEST_MEMBER_RED")
            declared.add(name)
            _need(_sha(z.read(name)) == digest, "INNER_SHA_RED")
        _need(declared == set(names) - {"SHA256SUMS"}, "MANIFEST_COVERAGE_RED")
        _need(z.read("HEAD.txt").decode("utf-8").strip() == ORIGINAL_HEAD,
              "ORIGINAL_HEAD_RED")
        report = json.loads(z.read("pilot/report.json"))
        _need(report.get("status") == "PILOT_PARTIAL_RED" and
              report.get("pilot_gain") is False and
              report.get("comparative_step2_gate_promoted") is False and
              report.get("jepa_weight") == 0 and
              report.get("redmi_measured") is False,
              "ORIGINAL_NEGATIVE_GATE_RED")
        _need(report.get("fixture_sha256") == ORIGINAL_FIXTURE_SHA256,
              "FIXTURE_SHA_RED")
        fixtures = report["fixtures"]
        _need(len(fixtures) == 4 and len({x["project"] for x in fixtures}) == 4,
              "FIXTURE_IDENTITY_RED")
        _need(report.get("arms") == list(ARMS) and len(report["rows"]) == 12,
              "PAIRING_SHAPE_RED")
        _need(all(x.get("ok") is True and x.get("hash_checked") is True
                  for x in report["model_verification"].values()) and
              set(report["model_verification"]) ==
              {"needle", "language", "body", "gist"}, "MODEL_PINS_RED")
        lookup = {f["project"]: f for f in fixtures}
        seen, diagnostic = set(), []
        reaped = 0
        for row in report["rows"]:
            key = (row.get("fixture"), row.get("arm"))
            _need(key[0] in lookup and key[1] in ARMS and key not in seen,
                  "ROW_IDENTITY_RED")
            seen.add(key)
            _need(row.get("valid_native") is False and
                  row.get("native_control") is False and
                  row.get("score") == {"a": False, "b": False,
                                       "correct": 0, "out_of": 2},
                  "ORIGINAL_ROW_RED_MUTATED")
            filename = row["raw_file"]
            _need(filename == f'{list(lookup).index(key[0]):02d}_{key[1]}.json',
                  "RAW_NAME_RED")
            event = json.loads(z.read("pilot/raw/" + filename))
            _need(event["event_id"] == row["event_id"] and
                  event["output"] == row["final_output"],
                  "RAW_REPORT_OUTPUT_RED")
            checks = event["checks"]
            _need(len(checks) == 13 and all(v is True for v in checks.values())
                  and event.get("source_errors") == [],
                  "RAW_STRUCTURAL_CHECK_RED")
            meta = event["output_metadata"]
            runner = meta["runner"]
            _need(meta.get("model_generated") is True and
                  runner.get("actual_model") == EXPECTED_MODELS[key[1]] and
                  runner.get("role") == row.get("runner_role"),
                  "NATIVE_MODEL_OR_ROLE_RED")
            route = "simple" if key[1] == ARMS[0] else "both"
            _need(meta.get("c2_packet", {}).get("route") == route,
                  "C2_PACKET_ROUTE_RED")
            _need(meta.get("route") == {"source": "OPERATOR_ROUTE_OVERRIDE"}
                  and "native_control" not in meta["route"],
                  "EXPECTED_VALIDATOR_SCHEMA_MISMATCH_NOT_FOUND")
            offers = set(row.get("body_offer_roles", []))
            releases = row.get("native_process_releases", [])
            if key[1] == ARMS[0]:
                _need(not offers and not releases and runner["role"] == "C3_LANGUAGE",
                      "C3_ONLY_SCOPE_RED")
            else:
                _need(offers == {"B1_DETAIL", "B2_GIST"} and
                      runner["role"] in offers and len(releases) == 2 and
                      {x.get("role") for x in releases} == offers and
                      all(x.get("process_reaped") is True for x in releases),
                      "BODY_RELEASE_OR_OFFERS_RED")
                reaped += 2
            diagnostic.append({"fixture": key[0], "arm": key[1],
                               "verdict": semantic_diagnostic(
                                   lookup[key[0]], event["output"])})
        _need(len(seen) == 12 and reaped == 16, "PAIRING_OR_RELEASE_RED")
        totals = {arm: sum(int(item["verdict"][k]["correct"])
                           for item in diagnostic if item["arm"] == arm
                           for k in ("a", "b")) for arm in ARMS}
        return {
            "schema": "v13.step2.original_pilot_readonly_audit.v1",
            "original_zip_sha256": ORIGINAL_ZIP_SHA256,
            "original_head": ORIGINAL_HEAD,
            "original_status_unchanged": "PILOT_PARTIAL_RED",
            "original_report_valid_native": "0/12",
            "raw_crc_clean": True,
            "inner_sha256_verified": f"{len(manifest)}/{len(manifest)}",
            "native_generated_raw_rows": "12/12",
            "raw_structural_checks": "156/156",
            "original_validator_route_native_control_missing": "12/12",
            "body_process_reaped_receipts": "16/16 (C3-only close not measured)",
            "diagnostic_semantic_out_of_8": totals,
            "diagnostic_rows": diagnostic,
            "native_c2_control_proven_here": False,
            "comparative_step2_gate_promoted": False,
            "jepa_weight": 0,
            "redmi_measured": False,
            "claim_limit": "Posthoc read-only lexical diagnostic; not original scorer, no gate or native re-run",
        }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("original_zip", type=Path)
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()
    result = audit_zip(args.original_zip)
    text = json.dumps(result, sort_keys=True, indent=2, allow_nan=False) + "\n"
    if args.out:
        if args.out.exists():
            raise FileExistsError("FRESH_RESULT_PATH_REQUIRED")
        args.out.write_text(text, encoding="utf-8")
    else:
        print(text, end="")


if __name__ == "__main__":
    main()
