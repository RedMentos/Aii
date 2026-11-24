"""Run77 preregistered disjoint B1/B2 source-context utility fixture seed797.

Six paired cases, policy only in prior USER source. Scorer frozen before native.
"""
from __future__ import annotations

import hashlib
import json
import re

SEED = 797
TABLE = (
    ("Alder", 180, 20, True, (160, 15, True), (170, 10, False), "A", 20),
    ("Birch", 200, 18, True, (210, 12, True), (180, 16, True), "B", 20),
    ("Cedar", 150, 14, True, (130, 16, True), (145, 12, False), "NONE", None),
    ("Dune", 240, 22, False, (190, 20, False), (200, 18, True), "A", 50),
    ("Elm", 170, 12, True, (160, 13, True), (155, 11, True), "B", 15),
    ("Fir", 130, 10, True, (120, 9, False), (125, 11, True), "NONE", None),
)
TABLE_SHA256 = "3c5c50be02d9bcb87384ea6a1f85c31ce276c02c3cb508f9fecd51c23da4fdbb"
B1_SHA256 = "bb741ebb106d543e9de114b843a3d3d73d51c74b5801e69da2abde821a0cb3e1"
B2_SHA256 = "57d1997790d1744fba5b40a7317df71ea5e2acee28c47e78f0cce39c0703f8cf"
RUNNER_SHA256 = "79e312188dc1d75c28201771f106e91de470b5cebdd838d31bb4db25eecf5d39"
ROLES = ("B1_DETAIL", "B2_GIST")
ARMS = ("WITH_PRIOR", "CURRENT_ONLY")


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _oracle(row):
    _, budget, deadline, required, a, b, _, _ = row
    eligible = [(opt[0], opt[1], name)
                for name, opt in (("A", a), ("B", b))
                if opt[0] <= budget and opt[1] <= deadline
                and (not required or opt[2])]
    if not eligible:
        return "NONE", None
    _, _, action = min(eligible)
    chosen = a if action == "A" else b
    return action, budget - chosen[0]


def fixtures():
    digest = sha(json.dumps(TABLE, sort_keys=True,
                            separators=(",", ":")).encode())
    if digest != TABLE_SHA256:
        raise ValueError("RUN77_TABLE_HASH_RED")
    if [r[6] for r in TABLE] != ["A", "B", "NONE", "A", "B", "NONE"]:
        raise ValueError("RUN77_BALANCE_RED")
    if any(_oracle(r) != (r[6], r[7]) for r in TABLE):
        raise ValueError("RUN77_ORACLE_RED")
    tf = lambda value: "true" if value else "false"
    result = []
    for row in TABLE:
        project, budget, deadline, required, a, b, action, remaining = row
        prior = (f"Project {project} archived logistics policy. "
                 f"Maximum budget: {budget} credits. "
                 f"Maximum deadline: {deadline} ticks. "
                 f"Required local-only: {tf(required)}.")
        option = lambda name, x: (
            f"Option {name}: budget {x[0]} credits; "
            f"deadline {x[1]} ticks; local-only {tf(x[2])}.")
        current = (
            f"Project {project} latest logistics options. "
            + option("A", a) + " " + option("B", b)
            + " Which option meets the archived policy? "
              "Choose A, B, or NONE and state remaining budget.")
        if (f"Maximum budget: {budget}" in current
                or f"Maximum deadline: {deadline}" in current):
            raise ValueError("RUN77_POLICY_THRESHOLD_LEAK_RED")
        result.append({
            "project": project, "prior": prior, "current": current,
            "action": action, "remaining": remaining,
            "source_sha256": {
                "prior": sha(prior.encode()),
                "current": sha(current.encode()),
            },
        })
    return result


def strict_summary(summary, action, remaining):
    """Frozen intentionally conservative English semantic scoring."""
    if type(summary) is not str or len(summary) > 4096:
        return 0
    text = summary.lower()
    if action == "NONE":
        none = (
            re.search(r"\b(?:choose|select|answer|recommend)\s+(?:option\s+)?none\b", text)
            or re.search(r"\bneither\s+option\b", text)
            or re.search(r"\bno\s+(?:option|candidate)\s+qualifies\b", text))
        invented = re.search(r"\bremaining\s+\d+\b|\b\d+\s+credits\s+remaining\b", text)
        return int(bool(none) and not invented)
    chosen = (
        re.search(r"\b(?:choose|select|recommend|answer|best|pick)\s+(?:is\s+)?(?:option\s+)?"
                  + action.lower() + r"\b", text)
        or re.search(r"\boption\s+" + action.lower()
                     + r"\s+(?:is\s+)?(?:best|recommended|qualifies)\b", text))
    n = str(remaining)
    rem = (
        re.search(r"\bremaining\b.{0,30}\b" + n + r"\b", text)
        or re.search(r"\b" + n + r"\b.{0,30}\bremaining\b", text))
    return int(bool(chosen) and bool(rem))


def scientific_verdict(scores, b2_prior_evidence):
    """Registered paired thresholds; never promotes STEP2."""
    if (type(scores) is not dict or set(scores) != set(ROLES)
            or type(b2_prior_evidence) is not int
            or not 0 <= b2_prior_evidence <= 6):
        raise ValueError("RUN77_SCORES_SHAPE_RED")
    passed = True
    for role in ROLES:
        arms = scores[role]
        if (type(arms) is not dict or set(arms) != set(ARMS)
                or any(type(n) is not int or not 0 <= n <= 6
                       for n in arms.values())):
            raise ValueError("RUN77_ARMS_SHAPE_RED")
        passed &= (arms["WITH_PRIOR"] >= 3
                   and arms["WITH_PRIOR"] - arms["CURRENT_ONLY"] >= 2)
    passed &= b2_prior_evidence >= 3
    return ("B1B2_SMALL_CONTEXT_UTILITY_SIGNAL_SHADOW"
            if passed else "B1B2_CONTEXT_UTILITY_SCIENTIFIC_RED")
