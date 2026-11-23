"""Preregistered source-exact B2 quote x C3 input counterfactuals.

Only constructs oracle-free, deterministic input envelopes for a future
exclusive native C3 experiment. No models, Runtime, learning, approval, live
answers, native score or STEP2 gate are executed or promoted here.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts import run15_step2_disjoint_bilingual_fixtures as fresh
from tests import integration_step2_utility as frozen_consumer
from v13.common import dumps

ROOT = Path(__file__).resolve().parents[1]
FROZEN_RUN15_BLOB = "635e5727a42cb1eac4f84441afda2977b0c8109c"
FROZEN_CONSUMER_BLOB = "a7ba12a8807a1ca8236f1c70d54dedb65c212caa"
CASES_SHA256 = "ab028737ef1f3f70a5c31cb3626a4a1f0b589685dd6728e41c93bf083526b011"
SEEDS = (20261121, 20261122, 20261123)
ARMS = ("CURRENT_ONLY", "B1_ONLY", "B1_B2_MISSING",
        "B1_B2_EXACT", "B1_B2_DISTRACTOR")
CASES = (
    ("Velaris", "EN", "SPLIT", (171, 11, True), (118, 9, True), (144, 12, False), None),
    ("Elyndra", "EN", "SPLIT", (195, 12, False), (174, 11, False), (181, 10, True), None),
    ("Seloria", "EN", "SPLIT", (182, 10, True), (168, 11, True), (171, 9, True), None),
    ("Zeradia", "DE", "SPLIT", (213, 14, True), (205, 13, False), (198, 12, True), None),
    ("Torvian", "DE", "SPLIT", (154, 7, True), (165, 6, True), (141, 8, False), None),
    ("Veyron", "DE", "SPLIT", (164, 9, True), (153, 10, True), (174, 8, True), None),
)
FIXTURES = tuple(fresh._fixture(case) for case in CASES)


def _sha(content):
    return hashlib.sha256(content).hexdigest()


def _blob(path):
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") +
                        b"\0" + raw).hexdigest()


def prereg():
    if (_blob(ROOT / "scripts/run15_step2_disjoint_bilingual_fixtures.py")
            != FROZEN_RUN15_BLOB or
            _blob(ROOT / "tests/integration_step2_utility.py")
            != FROZEN_CONSUMER_BLOB):
        raise ValueError("frozen_source_changed")
    raw = json.dumps(CASES, sort_keys=True, ensure_ascii=False,
                     separators=(",", ":")).encode("utf-8")
    if _sha(raw) != CASES_SHA256:
        raise ValueError("cohort_parameters_changed")
    fresh._validate(CASES)
    if (len(FIXTURES) != 6 or
            {f["id"] for f in FIXTURES} != {c[0] for c in CASES} or
            any(f["type"] != "SPLIT" for f in FIXTURES)):
        raise ValueError("cohort_identity_changed")
    languages = {lang: sum(f["language"] == lang for f in FIXTURES)
                 for lang in ("EN", "DE")}
    balance = {a: sum(f["oracle"]["action"] == a for f in FIXTURES)
               for a in ("A", "B", "NONE")}
    if languages != {"EN": 3, "DE": 3} or balance != {"A": 2, "B": 2, "NONE": 2}:
        raise ValueError("cohort_not_balanced")
    return {
        "schema": "v13.run33.b2_c3.counterfactual.prereg.v1",
        "fixtures": len(FIXTURES), "languages": languages,
        "oracle_action_balance": balance, "seeds": list(SEEDS),
        "arms": list(ARMS), "cases_sha256": CASES_SHA256,
        "frozen_source_blobs": {
            "run15": FROZEN_RUN15_BLOB,
            "consumer": FROZEN_CONSUMER_BLOB,
        },
        "evidence_level": "SYNTHETIC_SOURCE_ONLY_NO_C3",
        "native_executed": False, "canonical_gate_pass": False,
        "jepa_weight": 0,
    }


def _quote(source, expected, source_role):
    if (not isinstance(source, str) or not isinstance(expected, str) or
            not expected or source.count(expected) != 1 or
            source_role not in ("old", "sheet")):
        raise ValueError("quote_not_unique_source_exact")
    start = source.index(expected)
    return expected, {
        "source_role": source_role,
        "source_sha256": _sha(source.encode("utf-8")),
        "quote_sha256": _sha(expected.encode("utf-8")),
        "char_start": start,
        "char_end": start + len(expected),
    }


def _quotes(case, fixture):
    name, lang, kind, old, a, b, revised = case
    if kind != "SPLIT" or revised is not None or fixture["id"] != name:
        raise ValueError("fixture_type_changed")
    old_text = fixture["history"][0]
    sheet_text = fixture["history"][2]
    rules = fresh._rules(lang, old)
    options = fresh._options(lang, a, b)
    b2_exact = _quote(old_text, rules, "old")
    b1_exact = _quote(sheet_text, options, "sheet")
    # A real, source-exact same-project negative control, but without rules.
    intro = old_text[:min(160, old_text.index(rules))]
    if not intro or rules in intro:
        raise ValueError("distractor_contains_rules")
    b2_distractor = _quote(old_text, intro, "old")
    return b1_exact, b2_exact, b2_distractor


def build_envelope(fixture_id, arm, seed):
    prereg()
    if (type(fixture_id) is not str or
            type(arm) is not str or arm not in ARMS or
            type(seed) is not int or seed not in SEEDS):
        raise ValueError("unregistered_counterfactual")
    index = next((i for i, f in enumerate(FIXTURES)
                  if f["id"] == fixture_id), None)
    if index is None:
        raise ValueError("unregistered_fixture")
    fixture = FIXTURES[index]
    b1, b2, distractor = _quotes(CASES[index], fixture)
    analysts = []
    provenance = []
    if arm != "CURRENT_ONLY":
        analysts.append({"role": "B1_DETAIL", "hypothesis": "SOURCE_EXACT",
                         "verified_quotes": [b1[0]]})
        provenance.append(dict(b1[1]))
    if arm in ("B1_B2_MISSING", "B1_B2_EXACT", "B1_B2_DISTRACTOR"):
        quote = (b2 if arm == "B1_B2_EXACT" else
                 distractor if arm == "B1_B2_DISTRACTOR" else None)
        analysts.append({"role": "B2_GIST", "hypothesis": "SOURCE_EXACT",
                         "verified_quotes": [quote[0]] if quote else []})
        if quote:
            provenance.append(dict(quote[1]))
    context = {"current_source": fixture["current"], "analysts": analysts}
    return {
        "schema": "v13.run33.b2_c3.counterfactual.envelope.v1",
        "evidence_level": "SYNTHETIC_SOURCE_ONLY_NO_C3",
        "fixture_id": fixture_id, "language": fixture["language"],
        "arm": arm, "seed": seed,
        "messages": [
            {"role": "system", "content": frozen_consumer.SYSTEM},
            {"role": "user", "content": dumps(context)},
        ],
        "consumer_schema_sha256": _sha(dumps(frozen_consumer.SCHEMA).encode("utf-8")),
        "quote_provenance": provenance,
        "source_only": True, "authority": False,
        "model_output_used": False, "native_executed": False,
        "canonical_gate_pass": False, "jepa_weight": 0,
    }


def verify_envelope(report):
    if not isinstance(report, dict):
        raise ValueError("envelope_type")
    expected = build_envelope(report.get("fixture_id"),
                              report.get("arm"), report.get("seed"))
    if report != expected:
        raise ValueError("envelope_changed_or_unregistered")
    return True


def main():
    # No native mode exists in this source-only package.
    print(dumps(prereg()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
