"""Safe dashboard projection of the globally latest completed, session-bound turn audit."""
from __future__ import annotations

import math
import re
import sqlite3
from pathlib import Path

from .flow_audit import audit_latest_completed

_ROLES = frozenset({
    "A5_PERCEPTION", "B1_DETAIL", "B2_GIST", "B3_CALLOSUM",
    "C2_CONTROL", "C3_LANGUAGE", "C4_FOCAL", "C5_ACTION",
})
_MODALITIES = frozenset({"text", "audio", "image", "video"})
_EVIDENCE = frozenset({
    "SYNTHETIC_FIXTURE",
    "RUNTIME_REPORTED_NOT_DEVICE_VERIFIED",
    "METRICS_MISSING_OR_INCOMPLETE",
})
_TOKEN = re.compile(r"^[A-Z0-9_]{1,64}$")
_MODEL = re.compile(r"^[A-Za-z0-9_.: -]{1,80}$")


def _count(value):
    return value if type(value) is int and 0 <= value <= 1_000_000 else None


def _seconds(value):
    if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 3600:
        return None
    return round(float(value), 4)


def _token(value):
    return value if isinstance(value, str) and _TOKEN.fullmatch(value) else "UNKNOWN"


def _role(value):
    return value if isinstance(value, str) and value in _ROLES else None


def _model(value):
    return value if isinstance(value, str) and _MODEL.fullmatch(value) else None


def _boolean(value):
    return value if type(value) is bool else None


def _evidence(value):
    return value if isinstance(value, str) and value in _EVIDENCE else "METRICS_MISSING_OR_INCOMPLETE"


def _roles(value):
    if not isinstance(value, list):
        return []
    return [role for role in (_role(item) for item in value[:16]) if role is not None]


def _tokens(value):
    if not isinstance(value, list):
        return []
    return [token for token in (_token(item) for item in value[:32]) if token != "UNKNOWN"]


def snapshot(home: str | Path) -> dict:
    """Return counts/roles/timing only; never return IDs, text, prompts or source hashes."""
    root = Path(home).expanduser()
    try:
        report = audit_latest_completed(root)
        if report is None:
            return {
                "availability": "NO_TURNS",
                "selection_scope": "LATEST_COMPLETED_TURN_ALL_SESSIONS",
            }
        if report.get("read_only") is not True or report.get("private_text_returned") is not False:
            return {"availability": "UNAVAILABLE", "reason": "AUDIT_BOUNDARY_REJECTED"}

        perception = report.get("perception") if isinstance(report.get("perception"), dict) else {}
        queries = report.get("queries") if isinstance(report.get("queries"), dict) else {}
        bodies = report.get("bodies") if isinstance(report.get("bodies"), dict) else {}
        c4 = report.get("c4") if isinstance(report.get("c4"), dict) else {}
        c3 = report.get("c3") if isinstance(report.get("c3"), dict) else {}
        c5 = report.get("c5") if isinstance(report.get("c5"), dict) else {}
        latent = report.get("latent") if isinstance(report.get("latent"), dict) else {}
        integrity = report.get("source_integrity") if isinstance(report.get("source_integrity"), dict) else {}

        modalities = [
            item for item in perception.get("modalities", [])
            if isinstance(item, str) and item in _MODALITIES
        ][:8]
        offers = []
        raw_offers = bodies.get("offers", [])
        if isinstance(raw_offers, list):
            for item in raw_offers[:16]:
                if not isinstance(item, dict):
                    continue
                offers.append({
                    "role": _role(item.get("role")),
                    "query_role_match": _boolean(item.get("query_role_match")),
                    "prompt_tokens": _count(item.get("prompt_tokens")),
                    "generated_tokens": _count(item.get("generated_tokens")),
                    "status": _token(item.get("status")),
                    "actual_model": _model(item.get("actual_model")),
                    "prompt_token_source": _token(item.get("prompt_token_source")),
                    "evidence_level": _evidence(item.get("evidence_level")),
                })

        return {
            "availability": "AVAILABLE",
            "selection_scope": "LATEST_COMPLETED_TURN_ALL_SESSIONS",
            "read_only": True,
            "private_text_returned": False,
            "assistant_status": _token(report.get("assistant_status")),
            "perception": {
                "packet_count": _count(perception.get("packet_count")),
                "modalities": modalities,
            },
            "queries": {
                "count": _count(queries.get("count")),
                "target_roles": _roles(queries.get("target_roles")),
            },
            "bodies": {
                "offer_count": _count(bodies.get("offer_count")),
                "roles": _roles(bodies.get("roles")),
                "query_binding_status": _token(bodies.get("query_binding_status")),
                "offers": offers,
            },
            "c4": {
                "status": _token(c4.get("status")),
                "consumed_offer_count": _count(c4.get("consumed_offer_count")),
                "consumed_roles": _roles(c4.get("consumed_roles")),
                "selected_offer_count": _count(c4.get("selected_offer_count")),
            },
            "c3": {
                "status": _token(c3.get("status")),
                "context_binding_status": _token(c3.get("context_binding_status")),
                "semantic_use_status": _token(c3.get("semantic_use_status")),
                "source_bound_offer_count": _count(c3.get("source_bound_offer_count")),
                "prompt_tokens": _count(c3.get("prompt_tokens")),
                "generated_tokens": _count(c3.get("generated_tokens")),
                "ttft_s": _seconds(c3.get("ttft_s")),
                "duration_s": _seconds(c3.get("duration_s")),
                "actual_model": _model(c3.get("actual_model")),
                "prompt_token_source": _token(c3.get("prompt_token_source")),
                "native_completion_http_200": _boolean(c3.get("native_completion_http_200")),
                "native_template_submitted": _boolean(c3.get("native_template_submitted")),
                "native_attention_or_semantic_use_proven": _boolean(
                    c3.get("native_attention_or_semantic_use_proven")
                ),
                "can_latent_tap": _boolean(c3.get("can_latent_tap")),
                "can_latent_inject": _boolean(c3.get("can_latent_inject")),
                "can_train_body": _boolean(c3.get("can_train_body")),
                "evidence_level": _evidence(c3.get("evidence_level")),
            },
            "c5": {
                "selected_action_type": _token(c5.get("selected_action_type")),
                "selected_role": _role(c5.get("selected_role")),
                "action_outcome_packet_count": _count(c5.get("action_outcome_packet_count")),
                "world_action_statuses": _tokens(c5.get("world_action_statuses")),
            },
            "latent": {
                "tap_packet_count": _count(latent.get("tap_packet_count")),
                "symbolic_message_count": _count(latent.get("symbolic_message_count")),
                "receiver_packet_count": _count(latent.get("receiver_packet_count")),
                "native_injection_proven": False,
                "status": _token(latent.get("status")),
            },
            "source_integrity": {
                "unique_refs_checked": _count(integrity.get("unique_refs_checked")),
                "valid_refs": _count(integrity.get("valid_refs")),
                "invalid_refs": _count(integrity.get("invalid_refs")),
            },
            "evidence_level": _evidence(report.get("evidence_level")),
            "warnings": _tokens(report.get("warnings")),
            "redmi_status": "REDMI_UNVERIFIED",
            "claim_boundary": (
                "Store/Runner-Metadaten: source-bound context beweist weder Modellaufmerksamkeit "
                "noch semantische Nutzung oder trainierte native Latent-Injektion; kein Geräteattest."
            ),
        }
    except (OSError, ValueError, KeyError, sqlite3.Error):
        return {"availability": "UNAVAILABLE", "reason": "AUDIT_READ_FAILED"}
