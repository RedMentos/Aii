"""Run87 frozen disjoint seed877 B1/B2 96-vs-160 observer-budget cohort.

Preregistered before code. Software-only fixture; NO native calls or gates.
The original Run77 strict scorer is imported, never silently redefined.
"""
from __future__ import annotations

import hashlib
import json

SEED = 877
TABLE = (
    ("Quartz", 230, 18, True, (200, 16, True), (210, 15, False), "A", 30),
    ("Rowan", 210, 16, True, (215, 12, True), (195, 14, True), "B", 15),
    ("Sable", 160, 13, True, (150, 15, True), (155, 12, False), "NONE", None),
    ("Tundra", 260, 24, False, (215, 22, False), (230, 20, True), "A", 45),
    ("Umber", 190, 19, True, (180, 21, True), (175, 17, True), "B", 15),
    ("Vesper", 140, 11, True, (130, 10, False), (145, 10, True), "NONE", None),
)
TABLE_SHA256 = "6466f5c146495209241e0ee1abf911b708774d00109383fd3c8f1fc48e27f39d"
B1_SHA256 = "bb741ebb106d543e9de114b843a3d3d73d51c74b5801e69da2abde821a0cb3e1"
B2_SHA256 = "57d1997790d1744fba5b40a7317df71ea5e2acee28c47e78f0cce39c0703f8cf"
RUNNER_SHA256 = "79e312188dc1d75c28201771f106e91de470b5cebdd838d31bb4db25eecf5d39"
ROLES = ("B1_DETAIL", "B2_GIST")
ARMS = ("SHORT_96", "LONG_160")
OBSERVER_TOKENS = {"SHORT_96": 96, "LONG_160": 160}
QUOTE_MIN_CHARS = 80


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def oracle(row):
    _, budget, deadline, required, option_a, option_b, _, _ = row
    eligible = [(option[0], option[1], name)
                for name, option in (("A", option_a), ("B", option_b))
                if option[0] <= budget and option[1] <= deadline
                and (not required or option[2])]
    if not eligible:
        return "NONE", None
    action = min(eligible)[2]
    chosen = option_a if action == "A" else option_b
    return action, budget - chosen[0]


def texts(row):
    project, budget, deadline, required, a, b, _, _ = row
    tf = lambda v: "true" if v else "false"
    prior = (f"Project {project} archived logistics policy. "
             f"Maximum budget: {budget} credits. "
             f"Maximum deadline: {deadline} ticks. "
             f"Required local-only: {tf(required)}.")
    def option(label, x):
        return (f"Option {label}: budget {x[0]} credits; "
                f"deadline {x[1]} ticks; local-only {tf(x[2])}.")
    current = (f"Project {project} latest logistics options. "
               + option("A", a) + " " + option("B", b)
               + " Which option meets the archived policy? "
                 "Choose A, B, or NONE and state remaining budget.")
    return prior, current


def fixtures():
    digest = sha(json.dumps(TABLE, sort_keys=True, separators=(",", ":")).encode())
    if digest != TABLE_SHA256:
        raise ValueError("RUN87_TABLE_HASH_RED")
    if [r[6] for r in TABLE] != ["A", "B", "NONE", "A", "B", "NONE"]:
        raise ValueError("RUN87_BALANCE_RED")
    if any(oracle(row) != (row[6], row[7]) for row in TABLE):
        raise ValueError("RUN87_ORACLE_RED")
    result = []
    for i, row in enumerate(TABLE):
        prior, current = texts(row)
        if (f"Maximum budget: {row[1]}" in current
                or f"Maximum deadline: {row[2]}" in current):
            raise ValueError("RUN87_POLICY_THRESHOLD_LEAK_RED")
        result.append({
            "index": i, "project": row[0],
            "prior": prior, "current": current,
            "action": row[6], "remaining": row[7],
            "arm_order": ARMS if i % 2 == 0 else ARMS[::-1],
            "source_sha256": {"prior": sha(prior.encode()),
                              "current": sha(current.encode())},
        })
    return result


def summary_cap(tokens, quote_min_chars=QUOTE_MIN_CHARS):
    """Frozen v13.cognition.offer_schema math; diagnostic only."""
    chars = max(110, int((int(tokens) - 30) * 2.2))
    summary = max(48, int(chars * .45))
    uncertainty = max(16, int(chars * .15))
    quote = max(24, int(chars * .2))
    if quote_min_chars > quote:
        q = min(int(quote_min_chars), (chars - 48 - uncertainty) // 2)
        if q > quote:
            summary = chars - 2 * q - uncertainty
    return summary


def strict_summary(summary, action, remaining):
    """Delegate to frozen Run77 scorer, no posthoc rubric drift."""
    from scripts.jef_b1b2_context_fixture_797 import strict_summary as frozen
    return frozen(summary, action, remaining)


def verdict(scores, b2_long_prior_evidence):
    if (type(scores) is not dict or set(scores) != set(ROLES)
            or type(b2_long_prior_evidence) is not int
            or not 0 <= b2_long_prior_evidence <= 6):
        raise ValueError("RUN87_SCORE_SHAPE_RED")
    for role in ROLES:
        arms = scores[role]
        if (type(arms) is not dict or set(arms) != set(ARMS)
                or any(type(n) is not int or not 0 <= n <= 6
                       for n in arms.values())):
            raise ValueError("RUN87_ARM_SCORE_RED")
    if (all(scores[role]["LONG_160"] >= 3
            and scores[role]["LONG_160"] - scores[role]["SHORT_96"] >= 2
            for role in ROLES)
            and b2_long_prior_evidence >= 3):
        return "BUDGET_LONG_SMALL_SIGNAL_SHADOW"
    if all(scores[role]["LONG_160"] >= scores[role]["SHORT_96"]
           for role in ROLES):
        return "BUDGET_NONINFERIOR_SHADOW"
    return "BUDGET_UTILITY_RED"
