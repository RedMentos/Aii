"""Separate preregistered STEP2 counterbalanced source-only controls.

No change to original TP27 or Run15 cohorts. These are prospective inputs,
not native measurements and not an authority or learning gate.
"""
from collections import Counter
import hashlib
import json

from scripts import run15_step2_disjoint_bilingual_fixtures as run15
from scripts import step2_longnote_revision_fixtures as tp27

REVISION = "run18-step2-balanced-controls-v1"
SEEDS = (20261201, 20261202, 20261203)
GATE_PASS = False
# (name, language, kind, old rules, A, B, revised rules)
CASES = (
    ("Sableton", "EN", "SPLIT", (143, 9, True), (110, 8, True), (117, 10, False), None),
    ("Tavoria", "EN", "RULE", (171, 12, True), (145, 10, False), (154, 11, True), None),
    ("Uldara", "EN", "REVISION", (192, 14, False), (160, 7, True), (148, 9, True), (151, 8, True)),
    ("Veldora", "DE", "SPLIT", (185, 12, False), (164, 13, True), (173, 11, False), None),
    ("Wynora", "DE", "RULE", (202, 13, True), (187, 12, False), (194, 14, True), None),
    ("Xerion", "DE", "REVISION", (230, 17, True), (199, 14, True), (208, 16, False), (215, 15, False)),
)


def build_controls(cases):
    if type(cases) not in (tuple, list) or len(cases) != 6:
        raise ValueError("control_count")
    controls = run15.build_cases(cases)
    names = {x["id"] for x in controls}
    if names & ({x["id"] for x in run15.FIXTURES} | {x["id"] for x in tp27.FIXTURES}):
        raise ValueError("cohort_name_collision")
    if Counter(x["oracle"]["action"] for x in controls) != {"A": 2, "B": 2, "NONE": 2}:
        raise ValueError("label_imbalance")
    for language in ("EN", "DE"):
        selected = [x for x in controls if x["language"] == language]
        if (Counter(x["oracle"]["action"] for x in selected) !=
                {"A": 1, "B": 1, "NONE": 1}):
            raise ValueError("language_imbalance")
        if {x["type"] for x in selected} != {"SPLIT", "RULE", "REVISION"}:
            raise ValueError("type_coverage")
    return controls


def always_a_score(fixtures):
    if not fixtures:
        raise ValueError("empty_cohort")
    return {"correct": sum(x["oracle"]["action"] == "A" for x in fixtures),
            "total": len(fixtures)}


FIXTURES = build_controls(CASES)
FIXTURE_SHA256 = hashlib.sha256(json.dumps(
    FIXTURES, ensure_ascii=False, sort_keys=True, separators=(",", ":")
).encode("utf-8")).hexdigest()
RUN15_ALWAYS_A = always_a_score(run15.FIXTURES)
RUN18_ALWAYS_A = always_a_score(FIXTURES)
