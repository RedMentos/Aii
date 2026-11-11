"""V13 read-only learning receipts: memory versus prediction versus model weights.

A trained checkpoint file, telemetry event or model already loaded is NOT proof
that B1/B2/C3 learned. Report only observed structured counters and approved
generation-component bindings, never invent trainability, retention, utility,
causality, Android speed or full JEPA status.
"""
from __future__ import annotations
import json

REVISION = "v13-learning-receipts-v1"
KNOWN_UPDATE_STATES = frozenset({
    "PENDING_APPROVAL", "COMMITTED", "ROLLED_BACK", "ABORTED",
    "SHADOW_TRAINING", "EVALUATING", "FAILED", "REJECTED",
})
ORGAN_LABELS = {
    "B1_DETAIL": "Detail-Gehirnhälfte",
    "B2_GIST": "Überblick-Gehirnhälfte",
    "C3_LANGUAGE": "Sprachzentrum",
    "C2_CONTROL": "Leitstelle",
    "WORLD": "Weltmodell",
}


def _count(store, sql, session):
    data = store.one(sql, (session,))
    return int(data["n"]) if data and type(data.get("n")) is int else 0


def _counter(value):
    return value if type(value) is int and 0 <= value <= 1000000000 else None


def _read_manifest(value):
    try:
        result = json.loads(value)
        return result if type(result) is dict else {}
    except (TypeError, ValueError):
        return {}


def _weight_status(store):
    """Report record and active component *counts*, not raw manifests/paths."""
    rows = store.rows(
        "SELECT status,manifest FROM updates ORDER BY created DESC LIMIT 256"
    )
    states = {state: 0 for state in sorted(KNOWN_UPDATE_STATES)}
    unknown = 0
    roles = {role: {"candidate_update_records": 0, "committed_update_records": 0}
             for role in ORGAN_LABELS}
    for row in rows:
        status = row.get("status")
        if type(status) is not str or status not in KNOWN_UPDATE_STATES:
            unknown += 1
            continue
        states[status] += 1
        manifest = _read_manifest(row.get("manifest"))
        role = manifest.get("role")
        if role not in roles:
            # This field is informative only when a canonical role was
            # explicitly recorded, never inferred from a freeform objective.
            continue
        roles[role]["candidate_update_records"] += 1
        if status == "COMMITTED":
            roles[role]["committed_update_records"] += 1
    active = store.generation()
    components = active.get("components")
    if type(components) is not dict:
        components = store.components(active)
    permitted = {}
    for name, value in components.items():
        if type(name) is not str or type(value) is not dict:
            continue
        if type(value.get("update_id")) is not str or not value["update_id"]:
            continue
        # Only the component category and binding count are exposed. The
        # generation itself must be inspected by a separate integrity audit.
        permitted[name] = {"active_binding_recorded": True}
    return {
        "update_status_counts_last_256": states,
        "unknown_update_status_count": unknown,
        "roles": roles,
        "active_generation_component_bindings": permitted,
        "active_binding_count": len(permitted),
        "active_artifact_integrity_checked_here": False,
        "model_weight_learning_proven_here": False,
        "retention_proven_here": False,
        "operator_approval_inferred_from_pending": False,
        "note": ("Ein COMMITTED-Eintrag belegt nur den Generationseintrag, "
                 "nicht selbständig den Lernerfolg oder echte Redmi-Ausführung."),
    }


def _current_predictor(runtime):
    instance = getattr(runtime, "_online_world", None)
    model = getattr(instance, "model", None) if instance is not None else None
    seen = _counter(getattr(model, "seen", None)) if model is not None else None
    jepa = getattr(runtime, "_world_jepa_online", None)
    fit_steps = _counter(getattr(jepa, "_fit_steps", None)) if jepa is not None else None
    return {
        "local_numeric_predictor": {
            "instantiated": instance is not None,
            "reported_observations_in_memory": seen,
            "independent_weight_delta_verified": False,
        },
        "world_jepa": {
            "instantiated": jepa is not None,
            "reported_fit_steps_in_memory": fit_steps,
            "checkpoint_and_retention_verified_here": False,
        },
    }


def report(runtime):
    store = runtime.store
    session = getattr(runtime, "session", None)
    if type(session) is not str or not session:
        raise ValueError("active chat session required")
    # Session-scope join prevents other chats/withdrawn sources from leaking
    # counts, even when their records remain in the durable Store.
    memory_count = _count(store,
        "SELECT COUNT(*) AS n FROM memories m JOIN sources s ON s.id=m.source_id "
        "WHERE m.session_id=? AND m.active=1 AND s.deleted=0", session)
    replay_count = _count(store,
        "SELECT COUNT(*) AS n FROM replay r JOIN events e ON e.id=r.event_id "
        "JOIN sources s ON s.id=e.source_id "
        "WHERE e.session_id=? AND s.deleted=0", session)
    feedback_count = _count(store,
        "SELECT COUNT(*) AS n FROM feedback f JOIN events e ON e.id=f.event_id "
        "JOIN sources s ON s.id=f.source_id "
        "WHERE e.session_id=? AND s.deleted=0", session)
    return {
        "revision": REVISION, "kind": "READ_ONLY_LEARNING_RECEIPTS",
        "scope": "CURRENT_SESSION_EXPERIENCE_GLOBAL_GENERATION",
        "experience": {
            "active_source_bound_memory_records": memory_count,
            "recorded_replay_items": replay_count,
            "recorded_feedback_items": feedback_count,
            "counts_do_not_prove_learning": True,
        },
        "predictors": _current_predictor(runtime),
        "active_model_updates": _weight_status(store),
        "explanation": [
            "Erfahrung: Erinnerungen und Rückmeldungen werden gespeichert.",
            "Lokale Plastizität: Ein kleiner Prädiktor kann Zahlengewichte ändern; sein Zähler ist noch kein Retentionsbeweis.",
            "Modelllernen: B1/B2/C3 müssen separat echte Adaptergewichte, alte Fähigkeiten, Restart und Rollback beweisen.",
            "Freigabe: Eine Kandidatenaktualisierung verändert nicht automatisch das aktive Modell.",
        ],
        "next_checks": ":growth status | :doctor | :brain status | :gates summary",
        "model_calls": 0, "state_mutation": False,
        "native_redmi_learning_proven": False,
        "full_agi_proven": False,
    }
