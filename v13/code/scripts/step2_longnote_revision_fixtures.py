"""New STEP2 long-note/revision fixture candidate (software-only; no native runs).

Disjoint from frozen Z2/Z2b/Z2c registered episodes, seeds and measurements.
B1 sees recent exact option data; B2 can retrieve an older bounded rule
excerpt. One revision episode explicitly supersedes the old rules.
"""
from v13.agi.eligibility import recipe

REVISION = "step2-longnote-revision-fixtures-v1"
# (project, kind, old rules, option A, option B, new rules if revised)
# Fresh project names and budgets versus the immutable Z2 cohort.
CASES = (
    ("Aquila", "SPLIT", (134, 9, True), (91, 7, True), (105, 8, False), None),
    ("Borealis", "SPLIT", (142, 10, False), (116, 9, False), (128, 12, True), None),
    ("Cygnus", "SPLIT", (157, 11, True), (131, 10, True), (139, 12, True), None),
    ("Draco", "RULE", (166, 12, True), (147, 11, True), (151, 10, False), None),
    ("Equinox", "RULE", (173, 13, False), (154, 13, False), (161, 14, False), None),
    ("Fornax", "RULE", (184, 14, True), (165, 12, True), (179, 13, True), None),
    ("Gemini", "DETAIL", (191, 15, True), (171, 14, True), (181, 16, False), None),
    ("Helios", "DETAIL", (203, 16, False), (187, 15, False), (194, 17, True), None),
    ("Icarus", "DETAIL", (217, 17, True), (199, 17, True), (208, 18, True), None),
    ("Janus", "REVISION", (229, 18, True), (207, 17, True), (221, 16, False), (223, 17, False)),
)
DISTRACTOR = ("Project Atlas archive index. An unrelated maintenance meeting is planned; "
              "the index contains no active project rules or supplier prices.")
TAIL = (" Archival context: this copy is preserved for audit only. "
        "No later project policy is implied by the archive heading.") * 4


def _tf(value):
    return str(bool(value)).lower()


def rules_text(rules):
    budget, deadline, local = rules
    return (f"Budget {budget} euros. Deadline {deadline} days. "
            f"Local-only requirement: {_tf(local)}.")


def options_text(a, b):
    return (f"Option A: cost {a[0]} euros, duration {a[1]} days, local {_tf(a[2])}. "
            f"Option B: cost {b[0]} euros, duration {b[1]} days, local {_tf(b[2])}.")


def long_kickoff(name, rules):
    # Actual rule values occur within the first 240 source characters for
    # the registered B2 excerpt width; the title alone cannot carry all.
    intro = (f"Project {name} kickoff memo. This heading only identifies the archived "
             "note; the binding decision limits appear below, not in the title. ")
    text = intro + rules_text(rules) + TAIL
    if not (len(text) > 400 and len(intro + rules_text(rules)) <= 240):
        raise ValueError("Long-note source visibility contract changed")
    return text


def recent_sheet(name, a, b):
    intro = (f"Project {name} supplier data sheet, revision 3, compiled by the procurement "
             "desk after the vendor calls on Monday. The sheet lists the two remaining "
             "offers in the order received; earlier offers were withdrawn. All figures "
             "below were confirmed by both vendors in writing. ")
    if len(intro) <= 240:
        # Preserve the original Z2 intended B1-vs-B2 short/long separation.
        intro += "The figures in this paragraph supersede any preliminary quote. "
    return intro + options_text(a, b)


def fixture(name, kind, old, a, b, revised=None):
    if kind not in ("SPLIT", "RULE", "DETAIL", "REVISION"):
        raise ValueError("Unknown STEP2 fixture type")
    if (kind == "REVISION") != (revised is not None):
        raise ValueError("Only revision episodes may supersede rules")
    current_rules = revised if revised is not None else old
    note = long_kickoff(name, old)
    sheet = recent_sheet(name, a, b)
    if kind == "SPLIT":
        history = [note, DISTRACTOR, sheet]
        current = (f"Project {name}. Decide between Option A and Option B from the "
                   "latest supplier sheet using the earlier binding project rules.")
        needs = ["B2_GIST:rules", "B1_DETAIL:options"]
    elif kind == "RULE":
        history = [note, DISTRACTOR,
                   f"Project {name} status: supplier offers are included in the decision request."]
        current = (f"Project {name}. Use the earlier binding project rules. "
                   + options_text(a, b))
        needs = ["B2_GIST:rules", "CURRENT:options"]
    elif kind == "DETAIL":
        history = [f"Project {name} kickoff: the binding rules will appear in the request.",
                   DISTRACTOR, sheet]
        current = (f"Project {name}. Decide from the latest supplier data sheet. "
                   "Current binding rules: " + rules_text(current_rules))
        needs = ["CURRENT:rules", "B1_DETAIL:options"]
    else:
        history = [note, DISTRACTOR, sheet]
        current = (f"Project {name}. The old kickoff rules are superseded in full. "
                   "Current revised binding rules: " + rules_text(current_rules)
                   + " Use the latest supplier sheet for option values.")
        needs = ["CURRENT:revised_rules", "B1_DETAIL:options"]
    current += " Compute remaining budgets and eligibility; choose the cheapest eligible."
    opts = [{"entity": entity, "cost": o[0], "days": o[1], "local": o[2]}
            for entity, o in (("A", a), ("B", b))]
    action, options = recipe(*current_rules, opts)
    return {
        "id": name, "type": kind, "history": history, "current": current,
        "rules": {"budget": current_rules[0], "deadline": current_rules[1],
                  "local_only": current_rules[2]},
        "old_rules": {"budget": old[0], "deadline": old[1], "local_only": old[2]},
        "needs": needs,
        "temporal_mode": ("REVISED_CURRENT_RULES" if kind == "REVISION"
                          else "CURRENT_RULES" if kind == "DETAIL"
                          else "RETAIN_PRIOR_RULES"),
        "oracle": {"project": name, "action": action, "options": options},
        "source_contract": {"old_note_revision": 2, "sheet_revision": 3,
                            "quote_window_chars": 200, "b2_excerpt_chars": 240},
    }


FIXTURES = tuple(fixture(*case) for case in CASES)
