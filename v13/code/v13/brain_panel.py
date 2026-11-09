"""Human-readable, read-only brain map for the existing integrated V13 runtime.

Names are navigation metaphors, not claims of biological equivalence, trained
capability or integrated model-weight learning. Keep IDs stable for Termux UI.
"""
from __future__ import annotations

ORGANS = (
    ("sinne", ("input", "wahrnehmung", "perception", "a"), "Sinne / Wahrnehmung",
     "A0–A5", "Eingaben und Quellen in beobachtbare Eindruecke umwandeln.",
     "A0–A5; vision/audio remain gated"),
    ("detail", ("b1", "links", "detailhirn"), "Gehirnhaelfte Detail",
     "B1_DETAIL", "Kurze, genaue Details und Quellenausschnitte untersuchen.",
     "Dense body now; native weight learning not proven"),
    ("ueberblick", ("b2", "rechts", "gist", "overview"), "Gehirnhaelfte Ueberblick",
     "B2_GIST", "Grosse Zusammenhaenge und laengeren Kontext betrachten.",
     "Dense body now; native weight learning not proven"),
    ("leitstelle", ("jef", "c2", "steuerung", "executive"), "Leitstelle",
     "JEF / C2_CONTROL", "Aufmerksamkeit, Reihenfolge und Aktionen koordinieren.",
     "Control is not consciousness; learned decision utility is gated"),
    ("sprache", ("c3", "language"), "Sprachzentrum",
     "C3_LANGUAGE", "Die finale Sprachausgabe und Eingabetextverarbeitung.",
     "LoRA training code exists; real pinned-weight learning needs proof"),
    ("gedaechtnis", ("memory", "f1", "f3", "context"), "Gedaechtnis",
     "F1/F3 / Context OS", "Erfahrungen, Quellen und Abruf ueber Neustarts verbinden.",
     "Archive and source-bound integration remain under review"),
    ("weltmodell", ("jepa", "world", "prediction"), "Weltmodell",
     "World-JEPA / T8", "Vorhersagen aus beobachteten Uebergaengen lernen.",
     "Experimental local updates; no pretrained GGUF promotion"),
    ("verbindung", ("b3", "callosum", "bridge"), "Verbindung",
     "B3 Callosum", "Informationen zwischen den Gehirnhaelften vermitteln.",
     "Latent receiver injection and promotion remain OFF"),
    ("lernen", ("training", "plasticity", "learning"), "Lernwerkstatt",
     "Body-JEPA / C3-LoRA / Replay", "Gewichte aktualisieren und Vergessen messen.",
     "Different learners are not yet one proven native training system"),
    ("pruefung", ("safety", "checker", "c6", "proof"), "Pruefung",
     "C5/C6 / Gates", "Ausgaben, Berechtigungen, Fehler und Belege kontrollieren.",
     "Checks are fallible; a model self-check is no guarantee"),
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
            "note":"Gehirnnamen sind Wegweiser, keine biologischen oder AGI-Nachweise.",
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
            "meaning":"Instanziiert bedeutet geladen, NICHT nachgewiesen gelernt.",
            "checks":":doctor und :gates summary; Lernmessung auf echten Gewichten separat."}

def operator_command(r,args):
    if args==["map"]:return overview(r)
    if args==["status"]:return status(r)
    if len(args)==2 and args[0]=="explain":return explain(args[1])
    raise ValueError(":brain [map|status|explain <name>]  (ohne Argumente: bisherige Generation) ")
