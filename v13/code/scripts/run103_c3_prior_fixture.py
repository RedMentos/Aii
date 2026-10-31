"""Run103 preregistered disjoint C3 prior-rule pilot fixture (NO native here)."""
from __future__ import annotations

import hashlib
import json

SEED = 1031
TABLE = (
    ("Pavo", 173, 17, 161, 15, True, 160, 14, False, "A", 12),
    ("Rill", 205, 20, 210, 18, True, 190, 19, True, "B", 15),
    ("Sorrel", 148, 12, 140, 13, True, 147, 11, False, "NONE", None),
    ("Wexford", 232, 23, 220, 22, True, 229, 21, False, "A", 12),
    ("Yarrow", 187, 16, 180, 17, True, 176, 15, True, "B", 11),
    ("Zorin", 214, 18, 216, 17, True, 200, 16, False, "NONE", None),
)
TABLE_SHA256 = "2c05efcb1c035ccf7cfa8756cca40be2b36ffd313b6603fd4a240f9085cda582"
ARMS = ("CURRENT_ONLY", "DIRECT_FULL", "B2_WIDE_VERIFIED_SYNTHETIC",
        "B2_NARROW_SYNTHETIC")
MODEL_SHA256 = "3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d"
RUNNER_SHA256 = "79e312188dc1d75c28201771f106e91de470b5cebdd838d31bb4db25eecf5d39"
SCHEMA = "v13.run103.c3_disjoint_prior_rule_pilot.v1"
SYSTEM = (
    "You are C3_LANGUAGE. Decide only from the supplied exact source. "
    "The archived policy has three required rules: maximum budget, maximum "
    "deadline, and whether local-only is required. If any required archived "
    "rule is absent, answer UNKNOWN. If neither option meets all rules, "
    "answer NONE. Do not infer missing rules from options or hypotheses. "
    "Reply ONLY a JSON object with keys choice (A, B, NONE or UNKNOWN) and "
    "remaining (decimal credits as a string for A/B, otherwise NA)."
)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def fixtures():
    if sha(json.dumps(TABLE, sort_keys=True, separators=(",", ":")).encode()) != TABLE_SHA256:
        raise ValueError("RUN103_REGISTERED_TABLE_CHANGED")
    rows = []
    for i, (name, budget, deadline, a_cost, a_ticks, a_local,
            b_cost, b_ticks, b_local, expected, remaining) in enumerate(TABLE):
        valid_a = a_cost <= budget and a_ticks <= deadline and a_local
        valid_b = b_cost <= budget and b_ticks <= deadline and b_local
        oracle = "A" if valid_a and not valid_b else (
            "B" if valid_b and not valid_a else "NONE" if not valid_a and not valid_b else "AMBIGUOUS")
        calc_remaining = (budget - a_cost if oracle == "A" else
                          budget - b_cost if oracle == "B" else None)
        if oracle != expected or calc_remaining != remaining:
            raise ValueError("RUN103_ORACLE_OR_UNIQUENESS_CHANGED")
        prior = (f"Project {name} archived rules. Maximum budget: {budget} credits. "
                 f"Maximum deadline: {deadline} ticks. Required local-only: true.")
        current = (f"Project {name} latest options. "
                   f"Option A costs {a_cost} credits, takes {a_ticks} ticks, "
                   f"local-only {'true' if a_local else 'false'}. "
                   f"Option B costs {b_cost} credits, takes {b_ticks} ticks, "
                   f"local-only {'true' if b_local else 'false'}. "
                   "Which option meets the archived policy?")
        rows.append({"index": i, "project": name, "prior": prior,
                     "current": current, "expected": expected,
                     "remaining": remaining,
                     "source_sha256": {"prior": sha(prior.encode()),
                                       "current": sha(current.encode())},
                     "arm_order": ARMS[i % 4:] + ARMS[:i % 4]})
    return rows


def build_messages(store, row, arm, prior_ref, current_ref):
    if arm not in ARMS:
        raise ValueError("RUN103_ARM_INVALID")
    current = store.read_source(current_ref)
    if sha(current.encode()) != row["source_sha256"]["current"]:
        raise ValueError("RUN103_CURRENT_SOURCE_CHANGED")
    payload = {"current_source": current}
    evidence_refs = [current_ref]
    if arm != "CURRENT_ONLY":
        prior = store.read_source(prior_ref)
        if sha(prior.encode()) != row["source_sha256"]["prior"]:
            raise ValueError("RUN103_PRIOR_SOURCE_CHANGED")
        if arm == "DIRECT_FULL":
            payload["archived_policy_exact_source"] = prior
            evidence_refs.append(prior_ref)
        elif arm == "B2_WIDE_VERIFIED_SYNTHETIC":
            payload["b2_hypothesis"] = {
                "hypothesis": "Synthetic B2 source pointer; NOT a model observation.",
                "hypothesis_authority": "MODEL_HYPOTHESIS_NOT_FACT",
                "verified_quotes": [{"text": prior, "source_ref": prior_ref,
                    "verification": "EXACT_SOURCE_SENTENCES_POINTED_BY_QUOTE",
                    "semantic_truth_authority": False}]}
            evidence_refs.append(prior_ref)
        else:
            quote = ("Maximum budget: "
                     + prior.split("Maximum budget: ", 1)[1].split(".", 1)[0] + ".")
            start = prior.index(quote)
            span = {**prior_ref, "char_start": prior_ref["char_start"] + start,
                    "char_end": prior_ref["char_start"] + start + len(quote)}
            if store.read_source(span) != quote:
                raise ValueError("RUN103_NARROW_SOURCE_MISMATCH")
            payload["b2_hypothesis"] = {
                "hypothesis": "Synthetic narrow B2 quote pointer; NOT a model observation.",
                "hypothesis_authority": "MODEL_HYPOTHESIS_NOT_FACT",
                "verified_quotes": [{"text": quote, "source_ref": span,
                    "verification": "EXACT_SOURCE_SUBSTRING_ONLY",
                    "semantic_truth_authority": False}]}
            evidence_refs.append(span)
    messages = [{"role": "system", "content": SYSTEM},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False, sort_keys=True)}]
    return {"messages": messages, "evidence_refs": evidence_refs,
            "input_sha256": sha(json.dumps(messages, sort_keys=True,
                                           separators=(",", ":")).encode())}


def score(raw, row, arm):
    try:
        parsed = json.loads(raw.strip())
    except (ValueError, AttributeError):
        return 0
    if type(parsed) is not dict or set(parsed) != {"choice", "remaining"}:
        return 0
    if type(parsed["choice"]) is not str or type(parsed["remaining"]) is not str:
        return 0
    if arm in ("CURRENT_ONLY", "B2_NARROW_SYNTHETIC"):
        return int(parsed == {"choice": "UNKNOWN", "remaining": "NA"})
    expected = {"choice": row["expected"],
                "remaining": str(row["remaining"]) if row["remaining"] is not None else "NA"}
    return int(parsed == expected)


def verdict(scores):
    if type(scores) is not dict or set(scores) != set(ARMS):
        raise ValueError("RUN103_SCORE_SHAPE_INVALID")
    if any(type(scores[a]) is not int or not 0 <= scores[a] <= 6 for a in ARMS):
        raise ValueError("RUN103_SCORE_VALUE_INVALID")
    if (scores["DIRECT_FULL"] >= 4
            and scores["B2_WIDE_VERIFIED_SYNTHETIC"] >= 4
            and scores["B2_WIDE_VERIFIED_SYNTHETIC"] >= scores["DIRECT_FULL"] - 1
            and scores["CURRENT_ONLY"] >= 4
            and scores["B2_NARROW_SYNTHETIC"] >= 4):
        return "C3_SOURCE_RULE_SMALL_SIGNAL_SHADOW"
    return "C3_SOURCE_RULE_UTILITY_RED"
