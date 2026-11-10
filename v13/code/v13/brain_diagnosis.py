"""Human-readable per-organ error location; read-only, current chat, no models.

An observed failure is not proof that model weights were damaged by learning.
A last-stage location is evidence of where execution stopped, not the root cause.
"""
import json
import re

REVISION = "brain-diagnosis-v1"
MAX_ITEMS = 30
WORD = re.compile(r"[A-Za-z][A-Za-z0-9_]{0,79}\Z")
ORGANS = {
    "sinne": ("Sinne / Wahrnehmung", "A0-A5", "Quelle und PerceptPacket prüfen"),
    "detail": ("Detail-Gehirnhälfte", "B1_DETAIL", "B1-Ausgabe und Quelle prüfen"),
    "ueberblick": ("Überblick-Gehirnhälfte", "B2_GIST", "B2-Ausgabe und Kontext prüfen"),
    "leitstelle": ("Leitstelle", "JEF / C2", "Routing und Focal-Entscheidung prüfen"),
    "sprache": ("Sprachzentrum", "C3_LANGUAGE", "Native Lade-/Decode-Phasen prüfen"),
    "gedaechtnis": ("Gedächtnis", "Context OS / F1", "Quellen und Abruf prüfen"),
    "weltmodell": ("Weltmodell", "World-JEPA / T8", "Replay, Vorhersage und Holdout prüfen"),
    "verbindung": ("Verbindung", "B3 Callosum", "Bridge-Key und Freigabe-Gates prüfen"),
    "lernen": ("Lernwerkstatt", "Body-JEPA / LoRA", "Gradienten, Retention und Rollback prüfen"),
    "pruefung": ("Prüfung / Aktionen", "C5/C6", "Berechtigung und Validierung prüfen"),
    "unknown": ("Nicht lokalisiert", "UNKNOWN", "Mit :logs und :doctor eingrenzen"),
}
KINDS = (
    ("body_jepa", "lernen"), ("lora", "lernen"), ("train", "lernen"),
    ("plastic", "lernen"), ("jepa", "weltmodell"),
    ("online_world", "weltmodell"), ("world_model", "weltmodell"),
    ("callosum", "verbindung"), ("bridge", "verbindung"),
    ("ctxos", "gedaechtnis"), ("context_os", "gedaechtnis"),
    ("memory", "gedaechtnis"), ("retrieval", "gedaechtnis"),
    ("episode", "gedaechtnis"), ("percept", "sinne"), ("source", "sinne"),
    ("attention", "sinne"), ("b1_", "detail"), ("b2_", "ueberblick"),
    ("jef", "leitstelle"), ("executive", "leitstelle"),
    ("routing", "leitstelle"), ("focal", "leitstelle"),
    ("needle", "leitstelle"), ("c2_", "leitstelle"),
    ("c3_", "sprache"), ("runner", "sprache"), ("decode", "sprache"),
    ("tool", "pruefung"), ("permission", "pruefung"),
    ("broker", "pruefung"), ("c5_", "pruefung"), ("c6_", "pruefung"),
)
STAGES = {
    "ingress": "sinne", "policy_check": "pruefung",
    "perception_and_state": "sinne", "memory_recall": "gedaechtnis",
    "routing": "leitstelle", "preanswer_observers": "leitstelle",
    "focal_loop": "leitstelle", "output_prepare": "pruefung",
    "native_answer": "sprache",
}
MARKERS = ("unavailable", "failed", "error", "rejected", "interrupted", "invalid")


def _word(value, fallback="UNSPECIFIED"):
    return value if type(value) is str and WORD.fullmatch(value) else fallback


def _json(value):
    try:
        item = json.loads(value)
        return item if type(item) is dict else {}
    except (ValueError, TypeError):
        return {}


def _info(area):
    name, code, next_step = ORGANS[area]
    return {"organ_id": area, "organ": name, "technical": code,
            "next_step": next_step}


def _telemetry(row):
    kind = _word(row.get("kind"))
    if kind == "UNSPECIFIED":
        return None
    metrics = _json(row.get("metrics"))
    if not (any(m in kind.lower() for m in MARKERS)
            or _word(metrics.get("error"), "") not in ("", "UNSPECIFIED")
            or metrics.get("status") in ("ERROR", "CANCELLED", "DEADLINE")):
        return None
    area = next((a for needle, a in KINDS if needle in kind.lower()), "unknown")
    role = _word(metrics.get("role"), "")
    affected = {
        "B1_DETAIL": "detail", "B2_GIST": "ueberblick",
        "C3_LANGUAGE": "sprache", "C2_CONTROL": "leitstelle",
    }.get(role)
    # The native role is a stronger location signal than generic
    # offer_rejected/runner failure, but does not establish root cause.
    if area == "unknown" and affected:
        area = affected
        strength = "EXPLICIT_RECORDED_ROLE_NOT_CAUSE"
    else:
        strength = "MODULE_NAME_ONLY" if area != "unknown" else "UNLOCATED"
    result = {**_info(area),
            "event_id": _word(row.get("event_id")), "signal": kind,
            "error_class": _word(metrics.get("error")),
            "source": "SANITISED_TELEMETRY",
            "confidence": strength,
            "weight_damage_proven": False}
    if affected:
        result["affected_model_role"] = role
    return result


def _message(row):
    meta = _json(row.get("metadata"))
    stage = _word(meta.get("failure_stage"), "UNKNOWN_STAGE")
    area = STAGES.get(stage, "unknown")
    return {**_info(area),
            "event_id": _word(row.get("event_id")),
            "signal": "TURN_" + _word(row.get("status")),
            "stage": stage, "error_class": _word(meta.get("error")),
            "source": "COMMITTED_TURN_METADATA",
            "confidence": "LAST_STAGE_ONLY" if area != "unknown" else "UNLOCATED",
            "weight_damage_proven": False}


def diagnose(store, session, limit=10):
    """Inspect current-session rows, not global logs or conversation text."""
    if type(session) is not str or not session:
        raise ValueError("active chat session required")
    if type(limit) is not int or not 1 <= limit <= MAX_ITEMS:
        raise ValueError(":brain diagnose [1..30]")
    tel = store.rows(
        "SELECT t.kind,t.event_id,t.metrics FROM telemetry t "
        "JOIN events e ON e.id=t.event_id WHERE e.session_id=? "
        "ORDER BY t.id DESC LIMIT 128", (session,))
    msg = store.rows(
        "SELECT event_id,status,metadata FROM messages "
        "WHERE session_id=? AND role='assistant' "
        "AND status IN ('ERROR','CANCELLED','DEADLINE','INTERRUPTED') "
        "ORDER BY id DESC LIMIT 128", (session,))
    findings, seen = [], set()
    for rows, parser in ((tel, _telemetry), (msg, _message)):
        for row in rows:
            item = parser(row)
            if item is None:
                continue
            key = (item["event_id"], item["organ_id"])
            if key in seen:
                continue
            seen.add(key)
            findings.append(item)
            if len(findings) == limit:
                break
        if len(findings) == limit:
            break
    counts = {}
    for item in findings:
        key = item["organ_id"]
        counts[key] = counts.get(key, 0) + 1
    return {"revision": REVISION, "kind": "READ_ONLY_DIAGNOSTIC",
            "scope": "CURRENT_SESSION", "findings": findings,
            "counts_by_organ": counts, "total": len(findings),
            "help": "Der letzte Fehlerort ist nicht zwingend die Ursache. Ein Laufzeitfehler ist kein nachgewiesener Lernfehler.",
            "next": ":brain explain NAME | :doctor | :logs | :organ status ROLLE",
            "no_model_calls": True, "no_state_mutation": True}


def operator_command(runtime, args):
    if len(args) > 1:
        raise ValueError(":brain diagnose [1..30]")
    try:
        number = int(args[0]) if args else 10
    except ValueError as exc:
        raise ValueError(":brain diagnose [1..30]") from exc
    return diagnose(runtime.store, runtime.session, number)
