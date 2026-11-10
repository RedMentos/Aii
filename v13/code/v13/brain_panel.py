"""Human-readable, read-only brain map for the existing integrated V13 runtime.

Names are navigation metaphors, not claims of biological equivalence, trained
capability or integrated model-weight learning. Keep IDs stable for Termux UI.
"""
from __future__ import annotations

ORGANS = (
    ("sinne", ("input", "wahrnehmung", "perception", "a"), "Sinne und Wahrnehmung",
     "A0–A5", "Eingaben und Quellen aufnehmen und für die anderen Bereiche vorbereiten.",
     "A0–A5; Bild und Ton sind noch nicht als echte Sensorik freigegeben"),
    ("detail", ("b1", "links", "detailhirn"), "Gehirnhälfte Detail",
     "B1_DETAIL", "Kurze Texte genau untersuchen und wichtige Einzelheiten erkennen.",
     "Modell vorhanden; echtes Lernen seiner großen Gewichte noch nicht nachgewiesen"),
    ("ueberblick", ("b2", "rechts", "gist", "overview"), "Gehirnhälfte Überblick",
     "B2_GIST", "Längere Zusammenhänge verstehen und das große Bild behalten.",
     "Modell vorhanden; echtes Lernen seiner großen Gewichte noch nicht nachgewiesen"),
    ("leitstelle", ("jef", "c2", "steuerung", "executive"), "Leitstelle",
     "JEF / C2_CONTROL", "Entscheiden, welcher Bereich wann arbeitet und was als Nächstes passiert.",
     "Koordination ist nicht gleich Bewusstsein; selbst erlernte Entscheidungen sind begrenzt"),
    ("sprache", ("c3", "language"), "Sprachzentrum",
     "C3_LANGUAGE", "Gedanken und Ergebnisse in Sprache umsetzen.",
     "LoRA-Trainingscode vorhanden; echter Lernversuch mit den festgelegten Modellen fehlt"),
    ("gedaechtnis", ("memory", "f1", "f3", "context"), "Gedaechtnis",
     "F1/F3 / Context OS", "Erinnerungen, Quellen und frühere Erfahrungen über Neustarts speichern und abrufen.",
     "Archiv und quellgebundene Speicherung werden noch zusammengeführt"),
    ("weltmodell", ("jepa", "world", "prediction"), "Weltmodell",
     "World-JEPA / T8", "Aus beobachteten Veränderungen vorhersagen, was als Nächstes passiert.",
     "Experimentelle lokale Gewichtsupdates; die großen GGUF-Modelle werden damit nicht verändert"),
    ("verbindung", ("b3", "callosum", "bridge"), "Verbindung",
     "B3 Callosum", "Informationen zwischen den zwei Gehirnhälften austauschen.",
     "Direkte Eingriffe in interne Modellzustände bleiben gesperrt"),
    ("lernen", ("training", "plasticity", "learning"), "Lernwerkstatt",
     "Body-JEPA / C3-LoRA / Replay", "Lernen üben, ältere Erfahrungen wiederholen und Vergessen messen.",
     "Die Lernpfade sind noch kein vollständig nachgewiesenes gemeinsames Training"),
    ("pruefung", ("safety", "checker", "c6", "proof"), "Pruefung",
     "C5/C6 / Gates", "Antworten, Berechtigungen und Testergebnisse gegenprüfen.",
     "Auch Selbsttests können Fehler übersehen"),
)

def _entry(record):
    key, aliases, name, technical, purpose, limit = record
    return {"id":key, "name":name, "technical":technical,
            "job":purpose, "current_limit":limit}

def overview(r):
    """Intentionally descriptive; no fabricated per-organ PASS or completion %."""
    return {"kind":"READ_ONLY_NAVIGATION", "title":"V13 Gehirnkarte",
            "learning_mode":getattr(r, "cfg", {}).get("learning_mode", "UNKNOWN"),
            "organs":[_entry(x) for x in ORGANS],
            "note":"Die Gehirnnamen sind zur Orientierung da, nicht als Beweis für Bewusstsein oder AGI.",
            "detail":"Nutze :brain explain <name>; :brain status fuer Prozessstatus."}

def explain(name):
    word=name.strip().casefold()
    for row in ORGANS:
        if word==row[0] or word in row[1]:
            return {"kind":"READ_ONLY_EXPLANATION", **_entry(row)}
    raise ValueError("Unbekanntes Organ. Nutze :brain map fuer die verfuegbaren Namen.")

def status(r):
    """Runtime observations only, explicitly separate from learning evidence."""
    return {"kind":"READ_ONLY_RUNTIME_STATUS",
            "learning_mode":getattr(r, "cfg", {}).get("learning_mode", "UNKNOWN"),
            "runtime_job":getattr(r, "current", None),
            "t8_learner_instantiated":hasattr(r, "_online_world"),
            "world_jepa_instantiated":hasattr(r, "_world_jepa_online"),
            "native_model_training_proven":False,
            "meaning":"Geladen heißt nicht, dass ein Modell nachweislich etwas gelernt hat.",
            "checks":":doctor und :gates summary; Lernmessung auf echten Gewichten separat."}

def operator_command(r,args):
    if args and args[0]=="diagnose":
        from .brain_diagnosis import operator_command as diagnose
        return diagnose(r,args[1:])
    if args==["map"]:return overview(r)
    if args==["status"]:return status(r)
    if len(args)==2 and args[0]=="explain":return explain(args[1])
    raise ValueError(":brain [map|status|diagnose [N]|explain <name>]  (ohne Argumente: bisherige Generation) ")
