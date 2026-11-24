"""Fresh disjoint EN/DE STEP2 long-note/revision source corpus (no model calls).

Separate preregistration from the immutable TP/s27 Aquila–Janus cohort.
These fixtures are *inputs* for a future native experiment, not evidence of
B2/C3 utility. The oracle stays out of current/history source text.
"""
import hashlib
import json

from scripts import step2_longnote_revision_fixtures as frozen
from v13.agi.eligibility import recipe

REVISION = "run15-step2-disjoint-bilingual-fixtures-v1"
SEEDS = (20261114, 20261115, 20261116)
CANONICAL_GATE_PASS = False
JEPA_WEIGHT = 0
# (name, language, kind, old rules, A, B, revised rules or None)
CASES = (
    ("Keldara", "EN", "SPLIT", (146, 8, True), (97, 7, True), (129, 9, False), None),
    ("Lysoria", "EN", "RULE", (162, 10, False), (138, 9, False), (153, 11, True), None),
    ("Meridian", "EN", "REVISION", (178, 12, True), (149, 11, True), (159, 10, False), (154, 10, False)),
    ("Nerava", "DE", "SPLIT", (189, 13, True), (166, 12, True), (176, 11, False), None),
    ("Orenda", "DE", "RULE", (206, 15, False), (192, 14, False), (199, 16, True), None),
    ("Pyrion", "DE", "REVISION", (233, 18, True), (212, 15, True), (219, 17, False), (215, 16, False)),
)
DISTRACTOR = {
    "EN": "Project Quasar archive index. It contains no active project rules or supplier prices.",
    "DE": "Projekt Quasar Archivindex. Er enthält keine aktiven Projektregeln oder Lieferantenpreise.",
}
TAIL = (" Archival context: preserved for source audit, not a new binding rule."
        " No later project policy is implied by the archive heading.") * 4


def _tf(value):
    return str(bool(value)).lower()


def _rules(lang, triple):
    budget, deadline, local = triple
    if lang == "DE":
        return (f"Budget {budget} Euro. Frist {deadline} Tage. "
                f"Lokalpflicht {'ja' if local else 'nein'}.")
    return (f"Budget {budget} euros. Deadline {deadline} days. "
            f"Local-only requirement: {_tf(local)}.")


def _options(lang, a, b):
    if lang == "DE":
        return (f"Option A: Kosten {a[0]} Euro, Dauer {a[1]} Tage, lokal {'ja' if a[2] else 'nein'}. "
                f"Option B: Kosten {b[0]} Euro, Dauer {b[1]} Tage, lokal {'ja' if b[2] else 'nein'}.")
    return (f"Option A: cost {a[0]} euros, duration {a[1]} days, local {_tf(a[2])}. "
            f"Option B: cost {b[0]} euros, duration {b[1]} days, local {_tf(b[2])}.")


def _note(name, lang, rules):
    intro = (f"Projekt {name} Auftaktnotiz: Die Archivüberschrift ist keine neue Richtlinie; "
             "verbindliche Grenzen stehen nach diesem kurzen Prüfvermerk. "
             if lang == "DE" else
             f"Project {name} kickoff memo: this archived heading is not a new policy; "
             "binding limits follow this short audit description. ")
    text = intro + _rules(lang, rules) + TAIL
    if not len(text) > 400 or len(intro + _rules(lang, rules)) > 240:
        raise ValueError("Old rules outside B2 240-char source excerpt")
    return text


def _sheet(name, lang, a, b):
    intro = (f"Projekt {name} Lieferantenblatt Revision 4. Der Einkauf hat die Angebote nach "
             "den aktuellen Gesprächen erneut geprüft und protokolliert. Die beiden verbleibenden "
             "Angebote stehen nach dieser Einleitung; frühere unverbindliche Preislisten sind "
             "nicht die Quelle für diese Entscheidung. " if lang == "DE" else
             f"Project {name} supplier data sheet revision 4, independently confirmed by "
             "procurement after the latest vendor calls. The two remaining offers appear "
             "after this introduction. Earlier preliminary quotes are not the source for "
             "this decision. ")
    while len(intro) <= 250:
        intro += ("Die konkreten Zahlen folgen nach der Einleitung. " if lang == "DE"
                  else "The exact figures follow after this introduction. ")
    return intro + _options(lang, a, b), len(intro)


def _validate(cases):
    if type(cases) not in (tuple, list) or not 1 <= len(cases) <= 32:
        raise ValueError("Fresh fixture count invalid")
    old_names = {x[0] for x in frozen.CASES}
    names = set()
    for case in cases:
        if type(case) not in (tuple, list) or len(case) != 7:
            raise ValueError("Invalid fresh fixture case")
        name, lang, kind, old, a, b, revised = case
        if (type(name) is not str or not name.isascii() or
                not name.isalpha() or name in names or name in old_names or
                name in ("Atlas", "Quasar") or lang not in ("EN", "DE") or
                kind not in ("SPLIT", "RULE", "REVISION") or
                (kind == "REVISION") != (revised is not None)):
            raise ValueError("Non-disjoint or ambiguous fixture")
        for triple in (old, a, b) + ((revised,) if revised is not None else ()):
            if (type(triple) not in (tuple, list) or len(triple) != 3 or
                    type(triple[0]) is not int or triple[0] <= 0 or
                    type(triple[1]) is not int or triple[1] <= 0 or
                    type(triple[2]) is not bool):
                raise ValueError("Invalid numeric/boolean fixture values")
        names.add(name)


def _fixture(case):
    name, lang, kind, old, a, b, revised = case
    current_rules = revised if revised is not None else old
    note = _note(name, lang, old)
    sheet, start = _sheet(name, lang, a, b)
    if kind == "SPLIT":
        history = [note, DISTRACTOR[lang], sheet]
        current = ((f"Projekt {name}. Nutze die früheren verbindlichen Regeln und das aktuelle "
                    "Lieferantenblatt für Option A und Option B." if lang == "DE" else
                    f"Project {name}. Decide between Option A and Option B from the latest "
                    "supplier sheet using the earlier binding project rules."))
        needs = ["B2_GIST:rules", "B1_DETAIL:options"]
    elif kind == "RULE":
        history = [note, DISTRACTOR[lang],
                   (f"Projekt {name} Status: Die Angebote stehen in der aktuellen Anfrage." if lang == "DE"
                    else f"Project {name} status: supplier offers appear in the current request.")]
        current = ((f"Projekt {name}. Nutze die früheren verbindlichen Regeln. " if lang == "DE"
                    else f"Project {name}. Use the earlier binding project rules. ")
                   + _options(lang, a, b))
        needs = ["B2_GIST:rules", "CURRENT:options"]
    else:
        history = [note, DISTRACTOR[lang], sheet]
        current = ((f"Projekt {name}. Alte Auftaktregeln wurden vollständig ersetzt. "
                    "Aktuelle verbindliche Regeln: " + _rules(lang, current_rules) +
                    " Nutze das aktuelle Lieferantenblatt für die Optionen." if lang == "DE"
                    else f"Project {name}. Old kickoff rules are superseded in full. "
                    "Current revised binding rules: " + _rules(lang, current_rules) +
                    " Use the latest supplier sheet for options."))
        needs = ["CURRENT:revised_rules", "B1_DETAIL:options"]
    current += (" Berechne die Restbudgets und wähle das günstigste geeignete Angebot."
                if lang == "DE" else
                " Compute remaining budgets and choose the cheapest eligible offer.")
    options = [{"entity": entity, "cost": v[0], "days": v[1], "local": v[2]}
               for entity, v in (("A", a), ("B", b))]
    action, details = recipe(*current_rules, options)
    return {
        "id": name, "language": lang, "type": kind, "history": history,
        "current": current, "rules": {"budget": current_rules[0],
                                      "deadline": current_rules[1],
                                      "local_only": current_rules[2]},
        "old_rules": {"budget": old[0], "deadline": old[1], "local_only": old[2]},
        "needs": needs,
        "temporal_mode": "REVISED_CURRENT_RULES" if kind == "REVISION" else "RETAIN_PRIOR_RULES",
        "oracle": {"project": name, "action": action, "options": details},
        "source_contract": {"old_note_revision": 2, "sheet_revision": 4,
                            "b2_excerpt_chars": 240, "quote_window_chars": 200,
                            "sheet_options_start": start, "options": [a, b]},
    }


def build_cases(cases):
    _validate(cases)
    return tuple(_fixture(x) for x in cases)


FIXTURES = build_cases(CASES)
FIXTURE_SHA256 = hashlib.sha256(json.dumps(
    FIXTURES, ensure_ascii=False, sort_keys=True, separators=(",", ":")
).encode("utf-8")).hexdigest()
