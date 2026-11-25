"""Human-readable, read-only brain map for the existing integrated V13 runtime.

Names are navigation metaphors, not claims of biological equivalence, trained
capability or integrated model-weight learning. Keep IDs stable for Termux UI.
"""
from __future__ import annotations

import json
import math

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

def _mapping(value):
    if type(value) is dict:
        return value
    if type(value) is str:
        try:
            decoded = json.loads(value)
        except (TypeError, ValueError):
            return {}
        return decoded if type(decoded) is dict else {}
    return {}


def _count(value):
    return value if type(value) is int and value >= 0 else None


def _seconds(value):
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        return None
    return round(float(value), 4)


def _sha256(value):
    if type(value) is not str or len(value) != 64:
        return None
    if any(char not in "0123456789abcdef" for char in value):
        return None
    return value


def _latest_native_evidence(r):
    """Read the last persisted runner/receipt summary; never return chat text."""
    try:
        row = r.store.one(
            "SELECT event_id,status,metadata FROM messages "
            "WHERE role='assistant' AND status IN ('FINAL','CANCELLED','DEADLINE','ERROR','INTERRUPTED') "
            "ORDER BY id DESC LIMIT 1"
        )
    except Exception as exc:
        return {"status": "UNAVAILABLE", "reason": type(exc).__name__}
    if not row:
        return None

    metadata = _mapping(row.get("metadata"))
    runner = _mapping(metadata.get("runner"))
    model_revision = metadata.get("model_revision") if type(metadata.get("model_revision")) is str else None
    receipt = _mapping(runner.get("native_offer_prompt_receipt"))
    c4_metrics = {}
    c4_recorded = False
    event_id = row.get("event_id")
    if type(event_id) is str and event_id:
        try:
            c4_row = r.store.one(
                "SELECT metrics FROM telemetry WHERE event_id=? AND kind='c4_offer_context_ready' "
                "ORDER BY id DESC LIMIT 1", (event_id,)
            )
            if c4_row:
                c4_recorded = True
                c4_metrics = _mapping(c4_row.get("metrics"))
        except Exception:
            c4_recorded = False
            c4_metrics = {}

    native_offers = receipt.get("offers") if type(receipt.get("offers")) is list else []
    native_ids = [x.get("packet_id") for x in native_offers
                  if type(x) is dict and type(x.get("packet_id")) is str]
    c4_ids = c4_metrics.get("selected_offer_ids")
    if type(c4_ids) is not list:
        c4_ids = []
    c4_ids = [x for x in c4_ids if type(x) is str]
    c4_accepted = bool(c4_recorded and c4_metrics.get("status") == "PASS"
                       and c4_metrics.get("role") == "C3_LANGUAGE")
    ids_match = bool(c4_accepted and c4_ids and native_ids and set(c4_ids) == set(native_ids))
    native_prompt_sha256 = _sha256(receipt.get("native_prompt_sha256"))
    native_token_ids_sha256 = _sha256(receipt.get("native_token_ids_sha256"))
    native_prompt_tokens = _count(receipt.get("native_prompt_tokens"))
    native_prefill_observed = receipt.get("native_prefill_observed") is True
    native_prefill_verified = receipt.get("native_prompt_prefill_verified") is True
    native_generation_completed = receipt.get("native_generation_completed") is True

    synthetic = runner.get("synthetic") is True or receipt.get("synthetic") is True
    native_submitted = receipt.get("native_template_submitted") is True
    synthetic_submitted = synthetic and receipt.get("synthetic_template_submitted") is True
    submitted = native_submitted or synthetic_submitted
    prefix = "SYNTHETIC_" if synthetic else "NATIVE_"
    if not receipt:
        flow_status = "OFFER_RECEIPT_UNAVAILABLE"
    elif submitted and c4_recorded and ids_match:
        fingerprint_complete = bool(
            native_prompt_sha256 and native_token_ids_sha256
            and native_prompt_tokens is not None and native_prompt_tokens > 0)
        if (not synthetic and fingerprint_complete
                and native_prefill_verified and native_generation_completed):
            flow_status = "NATIVE_PREFILL_VERIFIED_AND_GENERATION_COMPLETED_MATCHED_C4"
        elif (not synthetic and fingerprint_complete
                and native_prefill_observed and native_generation_completed):
            flow_status = "NATIVE_PREFILL_OBSERVED_AND_GENERATION_COMPLETED_MATCHED_C4"
        else:
            flow_status = prefix + "TEMPLATE_SUBMITTED_MATCHED_C4"
    elif submitted and c4_recorded:
        flow_status = prefix + "TEMPLATE_SUBMITTED_C4_ID_MISMATCH"
    elif submitted:
        flow_status = prefix + "TEMPLATE_SUBMITTED_C4_RECEIPT_UNAVAILABLE"
    elif receipt.get("status") == "RENDERED_WITH_QUOTES":
        flow_status = "TEMPLATE_RENDERED_NOT_SUBMITTED"
    else:
        flow_status = "OFFERS_NOT_VERIFIED_IN_NATIVE_TEMPLATE"

    offers = []
    for item in native_offers[:2]:
        if type(item) is not dict:
            continue
        role = item.get("role")
        if role not in ("B1_DETAIL", "B2_GIST"):
            continue
        offers.append({"role": role, "rendered_quote_count": _count(item.get("rendered_quote_count"))})

    return {
        "turn_status": row.get("status"),
        "runner_role": runner.get("role"),
        "actual_model": runner.get("actual_model") if type(runner.get("actual_model")) is str else None,
        "model_revision": model_revision,
        "prompt_tokens": _count(runner.get("prompt_tokens")),
        "generated_tokens": _count(runner.get("generated_tokens")),
        "ttft_s": _seconds(runner.get("ttft_s")),
        "duration_s": _seconds(runner.get("duration_s")),
        "sampled_peak_pss_bytes": _count(runner.get("sampled_peak_pss_bytes")),
        "evidence_environment": "SYNTHETIC" if synthetic else "RUNNER_REPORTED",
        "native_prompt_sha256": native_prompt_sha256 if not synthetic else None,
        "native_token_ids_sha256": native_token_ids_sha256 if not synthetic else None,
        "native_prompt_tokens": native_prompt_tokens if not synthetic else None,
        "offer_flow": {
            "status": flow_status,
            "native_receipt_status": receipt.get("status"),
            "model_revision": model_revision,
            "native_completion_http_200": receipt.get("native_completion_http_200") is True,
            "native_prompt_prefill_verified": native_prefill_verified,
            "native_prefill_observed": native_prefill_observed,
            "native_stream_completed": receipt.get("native_stream_completed") is True,
            "native_generation_completed": native_generation_completed,
            "native_prompt_sha256": native_prompt_sha256 if not synthetic else None,
            "native_token_ids_sha256": native_token_ids_sha256 if not synthetic else None,
            "native_prompt_tokens": native_prompt_tokens if not synthetic else None,
            "native_tokenizer": receipt.get("native_tokenizer") if not synthetic and receipt.get("native_tokenizer") == "LLAMA_SERVER_TOKENIZE" else None,
            "native_template_submitted": native_submitted,
            "template_submitted": submitted,
            "c4_receipt_status": c4_metrics.get("status") if c4_recorded else "NOT_RECORDED",
            "c4_selected_offer_count": _count(c4_metrics.get("count")) if c4_recorded else None,
            "native_prompt_offer_count": len(offers),
            "c4_native_offer_ids_match": ids_match if c4_recorded else None,
            "offers": offers,
            "semantic_use_proven": False,
        },
    }



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
            "latest_turn":_latest_native_evidence(r),
            "native_model_training_proven":False,
            "meaning":"Geladen heißt nicht, dass ein Modell nachweislich etwas gelernt hat; ein nativer Prompt-Receipt beweist keine semantische Nutzung.",
            "checks":":doctor und :gates summary; Lernmessung auf echten Gewichten separat."}

def operator_command(r,args):
    if args==["map"]:return overview(r)
    if args==["status"]:return status(r)
    if len(args)==2 and args[0]=="explain":return explain(args[1])
    raise ValueError(":brain [map|status|explain <name>]  (ohne Argumente: bisherige Generation) ")
