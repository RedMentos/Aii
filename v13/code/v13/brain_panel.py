"""Human-readable, read-only brain map for the existing integrated V13 runtime.

Names are navigation metaphors, not claims of biological equivalence, trained
capability or integrated model-weight learning. Keep IDs stable for Termux UI.
"""
from __future__ import annotations

import json
import math
import re

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



_ID = re.compile(
    r"(?:[a-f0-9]{40}|[a-f0-9]{64}|(?:pkt|evt|gen|mem|src|upd|req|rule|fixed|chat|exp|consolidation)_[a-f0-9]{28,32})\Z",
    re.ASCII,
)
_BODY_ROLES = {"B1_DETAIL", "B2_GIST"}
_BODY_STATUSES = {"FINAL", "DEADLINE", "ERROR", "CANCELLED", "INTERRUPTED"}


def _identifier(value):
    return value if type(value) is str and len(value) <= 160 and _ID.fullmatch(value) else None


def _source_ref_key(ref):
    if type(ref) is not dict:
        return None
    source_id = _identifier(ref.get("source_id"))
    sha256 = _sha256(ref.get("sha256"))
    start = ref.get("char_start")
    end = ref.get("char_end")
    modality = ref.get("modality")
    if (not source_id or not sha256 or type(start) is not int or type(end) is not int
            or not 0 <= start < end or type(modality) is not str or not modality):
        return None
    return source_id, sha256, start, end, modality


def _source_ref_contains(parent, child):
    parent_key = _source_ref_key(parent)
    child_key = _source_ref_key(child)
    return bool(
        parent_key and child_key
        and parent_key[0] == child_key[0]
        and parent_key[1] == child_key[1]
        and parent_key[4] == child_key[4]
        and parent_key[2] <= child_key[2]
        and child_key[3] <= parent_key[3]
    )


def _verify_offer_packet(store, packet_id, event_id, event_generation_id, role, query_id):
    """Verify persisted OfferPacket identity and its source spans without returning text."""
    try:
        row = store.one(
            "SELECT kind,event_id,generation_id,payload FROM packets WHERE id=?",
            (packet_id,),
        )
        if (not row or row.get("kind") != "OfferPacket"
                or row.get("event_id") != event_id
                or row.get("generation_id") != event_generation_id
                or type(event_generation_id) is not str):
            return {"offer_packet_verified": False, "source_bound": False,
                    "verified_source_span_count": None}
        payload = _mapping(row.get("payload"))
        if (payload.get("packet_id") != packet_id
                or payload.get("event_id") != event_id
                or payload.get("brain_generation_id") != event_generation_id
                or payload.get("producer_component") != role
                or payload.get("role") != role
                or payload.get("query_packet_id") != query_id):
            return {"offer_packet_verified": False, "source_bound": False,
                    "verified_source_span_count": None}
        evidence_refs = payload.get("evidence_refs")
        provenance = payload.get("provenance")
        if (type(evidence_refs) is not list or len(evidence_refs) > 16
                or type(provenance) is not list or len(provenance) > 64):
            return {"offer_packet_verified": False, "source_bound": False,
                    "verified_source_span_count": None}
        if not evidence_refs:
            return {"offer_packet_verified": True, "source_bound": False,
                    "verified_source_span_count": 0}
        verified = 0
        all_bound = True
        for ref in evidence_refs:
            if not _source_ref_key(ref) or not any(
                _source_ref_contains(parent, ref) for parent in provenance
            ):
                all_bound = False
                continue
            try:
                store.read_source(ref)
            except Exception:
                all_bound = False
                continue
            verified += 1
        return {
            "offer_packet_verified": True,
            "source_bound": bool(all_bound and verified == len(evidence_refs) and verified > 0),
            "verified_source_span_count": verified,
        }
    except Exception:
        return {"offer_packet_verified": False, "source_bound": False,
                "verified_source_span_count": None}


def _body_offer_evidence(
    store, event_id, *, event_generation_id=None, c4_ids=(), c4_recorded=False, c4_accepted=False,
    template_ids=(), template_role_by_id=None, template_receipt_available=False,
    template_submitted=False, synthetic=False,
    native_prefill_verified=False, native_prefill_observed=False,
    native_prefill_token_count_matched=False, native_generation_completed=False,
    synthetic_prefill_verified=False,
    synthetic_generation_completed=False,
):
    """Join bounded B1/B2 metrics to C4 selection and C3 native-prefill receipts.

    Only numeric metrics, role enums and packet IDs leave telemetry. Raw prompt,
    summaries, quotes and exception text are never returned.
    """
    if type(event_id) is not str or not event_id:
        return []
    try:
        rows = store.rows(
            "SELECT kind,metrics FROM telemetry WHERE event_id=? "
            "AND kind IN ('body_offer_attempt','body_offer_delivered') "
            "ORDER BY id ASC LIMIT 17",
            (event_id,),
        )
    except Exception:
        return []
    if type(rows) is not list:
        return []
    truncated = len(rows) > 16
    rows = rows[:16]
    c4_values = c4_ids if type(c4_ids) in (list, tuple, set) else ()
    template_values = template_ids if type(template_ids) in (list, tuple, set) else ()
    c4_ids = {value for value in c4_values if _identifier(value)}
    template_ids = {value for value in template_values if _identifier(value)}
    raw_template_roles = template_role_by_id if type(template_role_by_id) is dict else {}
    template_roles = {
        packet_id: role for packet_id, role in raw_template_roles.items()
        if _identifier(packet_id) and type(role) is str and role in _BODY_ROLES
    }
    by_role_query = {}
    verified_packet_cache = {}
    for row in rows:
        if type(row) is not dict:
            continue
        metrics = _mapping(row.get("metrics"))
        role = metrics.get("role")
        query_id = _identifier(metrics.get("query_packet_id"))
        kind = row.get("kind")
        if (type(role) is not str or role not in _BODY_ROLES or not query_id
                or type(kind) is not str or kind not in {
                    "body_offer_attempt", "body_offer_delivered"
                }):
            continue
        packet_id = _identifier(metrics.get("packet_id")) if kind == "body_offer_delivered" else None
        if kind == "body_offer_delivered" and not packet_id:
            continue
        item = by_role_query.setdefault((query_id, role), {
            "query_packet_id": query_id,
            "role": role,
            "attempt_status": "UNAVAILABLE",
            "delivered": False,
            "body_attempt_recorded": False,
            "prompt_tokens": None,
            "generated_tokens": None,
            "ttft_s": None,
            "duration_s": None,
            "sampled_peak_pss_bytes": None,
            "evidence_environment": "UNAVAILABLE",
            "packet_id": None,
            "native_template_role": None,
            "template_role_matches": None,
            "offer_packet_verified": False,
            "source_bound": False,
            "source_count_matches": False,
            "reported_source_span_count": None,
            "verified_source_span_count": None,
            "delivery_duration_s": None,
            "selected_by_c4": None,
            "included_in_c3_template": None,
            "native_prefill_observed": False,
            "native_prefill_verified": False,
            "native_prefill_token_count_matched": False,
            "native_generation_completed": False,
            "consumption_state": "ATTEMPT_NOT_DELIVERED",
            "semantic_use_proven": False,
        })
        if kind == "body_offer_attempt":
            runner = _mapping(metrics.get("runner"))
            status = metrics.get("status")
            item["body_attempt_recorded"] = True
            item["attempt_status"] = (
                status if type(status) is str and status in _BODY_STATUSES else "UNKNOWN"
            )
            item["prompt_tokens"] = _count(runner.get("prompt_tokens"))
            item["generated_tokens"] = _count(runner.get("generated_tokens"))
            item["ttft_s"] = _seconds(runner.get("ttft_s"))
            item["duration_s"] = _seconds(runner.get("duration_s"))
            item["sampled_peak_pss_bytes"] = _count(runner.get("sampled_peak_pss_bytes"))
            runner_synthetic = runner.get("synthetic")
            item["evidence_environment"] = (
                "SYNTHETIC" if synthetic or runner_synthetic is True
                else "RUNNER_REPORTED" if runner_synthetic is False
                else "UNVERIFIED"
            )
        else:
            item["delivered"] = True
            item["packet_id"] = packet_id
            item["native_template_role"] = template_roles.get(packet_id)
            item["template_role_matches"] = template_roles.get(packet_id) == role
            item["reported_source_span_count"] = _count(metrics.get("count"))
            verification = verified_packet_cache.get(packet_id)
            if verification is None:
                verification = _verify_offer_packet(
                    store, packet_id, event_id, event_generation_id, role, query_id
                )
                verified_packet_cache[packet_id] = verification
            item["offer_packet_verified"] = verification["offer_packet_verified"]
            item["source_bound"] = verification["source_bound"]
            item["verified_source_span_count"] = verification["verified_source_span_count"]
            item["source_count_matches"] = bool(
                item["offer_packet_verified"]
                and item["verified_source_span_count"] is not None
                and item["reported_source_span_count"] == item["verified_source_span_count"]
            )
            item["delivery_duration_s"] = _seconds(metrics.get("duration_s"))
            item["selected_by_c4"] = packet_id in c4_ids if c4_accepted else None
            item["included_in_c3_template"] = (
                packet_id in template_ids and item["template_role_matches"]
                if template_submitted else None
            )
            path_synthetic = synthetic or item["evidence_environment"] == "SYNTHETIC"
            item["native_prefill_observed"] = bool(not path_synthetic and native_prefill_observed)
            item["native_prefill_verified"] = bool(not path_synthetic and native_prefill_verified)
            item["native_prefill_token_count_matched"] = bool(
                not path_synthetic and native_prefill_token_count_matched
            )
            item["native_generation_completed"] = bool(
                not path_synthetic and native_generation_completed
            )
            if not c4_recorded:
                state = "C4_RECEIPT_UNAVAILABLE"
            elif not c4_accepted:
                state = "C4_RECEIPT_NOT_ACCEPTED"
            elif packet_id not in c4_ids:
                state = "DELIVERED_NOT_SELECTED_BY_C4"
            elif not template_receipt_available:
                state = "C4_SELECTED_C3_RECEIPT_UNAVAILABLE"
            elif not template_submitted:
                state = "C4_SELECTED_C3_TEMPLATE_NOT_SUBMITTED"
            elif packet_id not in template_ids:
                state = "C4_C3_PACKET_ID_MISMATCH"
            elif template_roles.get(packet_id) != role:
                state = "C4_C3_PACKET_ROLE_MISMATCH"
            elif not item["offer_packet_verified"]:
                state = "DELIVERED_OFFER_PACKET_UNVERIFIED"
            elif not item["source_bound"]:
                state = "DELIVERED_WITHOUT_VERIFIED_SOURCE_SPANS"
            elif not item["source_count_matches"]:
                state = "DELIVERED_SOURCE_SPAN_COUNT_MISMATCH"
            elif path_synthetic:
                state = (
                    "SYNTHETIC_PREFILL_AND_GENERATION_VERIFIED"
                    if synthetic_prefill_verified and synthetic_generation_completed
                    else "SYNTHETIC_TEMPLATE_INCLUDED_ONLY"
                )
            elif not item["body_attempt_recorded"]:
                state = "BODY_ATTEMPT_METRICS_UNAVAILABLE"
            elif item["evidence_environment"] == "UNVERIFIED":
                state = "BODY_ATTEMPT_ENVIRONMENT_UNVERIFIED"
            elif native_prefill_verified and native_generation_completed:
                state = "C4_SELECTED_C3_NATIVE_PREFILL_AND_GENERATION_VERIFIED"
            elif native_prefill_token_count_matched and native_generation_completed:
                state = "C4_SELECTED_C3_NATIVE_PREFILL_TOKEN_COUNT_MATCHED_AND_GENERATION_COMPLETED"
            elif native_prefill_observed and native_generation_completed:
                state = "C4_SELECTED_C3_NATIVE_PREFILL_OBSERVED_AND_GENERATION_COMPLETED"
            elif native_prefill_observed:
                state = "C4_SELECTED_C3_NATIVE_PREFILL_OBSERVED_GENERATION_INCOMPLETE"
            elif native_generation_completed:
                state = "C4_SELECTED_C3_GENERATION_COMPLETED_PREFILL_UNOBSERVED"
            else:
                state = "TEMPLATE_INCLUDED_PREFILL_UNVERIFIED"
            item["consumption_state"] = state
    result = list(by_role_query.values())
    if truncated:
        result = [dict(item, telemetry_truncated=True) for item in result]
    return result


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
    event_generation_id = None
    if type(event_id) is str and event_id:
        try:
            event_row = r.store.one(
                "SELECT generation_id FROM events WHERE id=?", (event_id,)
            )
            if event_row:
                event_generation_id = event_row.get("generation_id")
        except Exception:
            event_generation_id = None
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

    raw_native_offers = receipt.get("offers")
    native_offers = raw_native_offers if type(raw_native_offers) is list else []
    native_ids_valid = bool(native_offers) and all(
        type(item) is dict and item.get("role") in _BODY_ROLES
        and _identifier(item.get("packet_id"))
        for item in native_offers
    )
    native_ids = (
        [_identifier(item.get("packet_id")) for item in native_offers]
        if native_ids_valid else []
    )
    native_role_by_id = (
        {_identifier(item.get("packet_id")): item.get("role") for item in native_offers}
        if native_ids_valid and len(set(native_ids)) == len(native_ids) else {}
    )
    raw_c4_ids = c4_metrics.get("selected_offer_ids")
    c4_ids_valid = (
        type(raw_c4_ids) is list and bool(raw_c4_ids)
        and all(_identifier(value) for value in raw_c4_ids)
    )
    c4_ids = list(raw_c4_ids) if c4_ids_valid else []
    c4_accepted = bool(c4_recorded and c4_metrics.get("status") == "PASS"
                       and c4_metrics.get("role") == "C3_LANGUAGE")
    ids_match = bool(
        c4_accepted and c4_ids_valid and native_ids_valid
        and len(c4_ids) == len(native_ids)
        and len(set(c4_ids)) == len(c4_ids)
        and len(set(native_ids)) == len(native_ids)
        and set(c4_ids) == set(native_ids)
    )
    native_prompt_sha256 = _sha256(receipt.get("native_prompt_sha256"))
    native_token_ids_sha256 = _sha256(receipt.get("native_token_ids_sha256"))
    native_prompt_tokens = _count(receipt.get("native_prompt_tokens"))
    rendered_prompt_sha256 = _sha256(receipt.get("rendered_prompt_sha256"))
    rendered_prompt_chars = _count(receipt.get("rendered_prompt_chars"))
    native_prompt_render_match = bool(
        receipt.get("native_prompt_render_match") is True
        and rendered_prompt_sha256 is not None
        and rendered_prompt_sha256 == native_prompt_sha256
        and rendered_prompt_chars is not None and rendered_prompt_chars > 0
    )
    first_step_raw = runner.get("output_adapter_native_first_step")
    if type(first_step_raw) is dict:
        # The first request receives the full prompt; continuation timings are
        # for token IDs plus the first generated token and are not its prefill.
        native_timings = _mapping(first_step_raw.get("timings"))
        native_prefill_timing_source = "FIRST_TOKEN_STEP"
    else:
        native_timings = _mapping(runner.get("timings"))
        native_prefill_timing_source = "STREAM_COMPLETION"
    native_prefill_processed_tokens = _count(native_timings.get("prompt_n"))
    native_prefill_cached_tokens = _count(native_timings.get("cache_n"))
    native_prefill_prompt_tokens = (
        native_prefill_processed_tokens + native_prefill_cached_tokens
        if native_prefill_processed_tokens is not None
        and native_prefill_cached_tokens is not None
        and native_prefill_processed_tokens + native_prefill_cached_tokens <= 100000
        else None
    )
    native_prefill_prompt_ms = _seconds(native_timings.get("prompt_ms"))

    synthetic = runner.get("synthetic") is True or receipt.get("synthetic") is True
    raw_native_submitted = receipt.get("native_template_submitted") is True
    native_submitted = (not synthetic) and raw_native_submitted
    synthetic_submitted = synthetic and (
        receipt.get("synthetic_template_submitted") is True or raw_native_submitted
    )
    submitted = native_submitted or synthetic_submitted
    native_prefill_observed = (not synthetic) and receipt.get("native_prefill_observed") is True
    native_prefill_verified = (not synthetic) and receipt.get("native_prompt_prefill_verified") is True
    native_generation_completed = (not synthetic) and receipt.get("native_generation_completed") is True
    native_prefill_token_count_matched = bool(
        not synthetic and native_submitted and ids_match
        and receipt.get("revision") in ("v13.native-offer-prompt-receipt/1",
                                             "v13.native-offer-prompt-receipt/2")
        and (receipt.get("revision") != "v13.native-offer-prompt-receipt/2"
             or native_prompt_render_match)
        and receipt.get("status") == "RENDERED_WITH_QUOTES"
        and receipt.get("native_template_rendered") is True
        and receipt.get("native_template_submitted") is True
        and receipt.get("native_completion_http_200") is True
        and receipt.get("source_span_revalidated_here") is False
        and receipt.get("native_semantic_use_proven") is False
        and native_generation_completed
        and native_prompt_sha256 and native_token_ids_sha256
        and native_prompt_tokens is not None and native_prompt_tokens > 0
        and native_prefill_prompt_tokens == native_prompt_tokens
        and _count(runner.get("prompt_tokens")) == native_prompt_tokens
    )
    synthetic_prefill_verified = synthetic and (
        receipt.get("synthetic_prompt_prefill_verified") is True
        or receipt.get("native_prompt_prefill_verified") is True
    )
    synthetic_generation_completed = synthetic and (
        receipt.get("synthetic_generation_completed") is True
        or receipt.get("native_generation_completed") is True
    )
    prefix = "SYNTHETIC_" if synthetic else "NATIVE_"
    fingerprint_complete = bool(
        not synthetic and native_prompt_sha256 and native_token_ids_sha256
        and native_prompt_tokens is not None and native_prompt_tokens > 0
    )
    native_prompt_span_by_id = {}
    if (not synthetic and native_submitted
            and receipt.get("native_completion_http_200") is True
            and native_prompt_render_match and ids_match
            and receipt.get("revision") == "v13.native-offer-prompt-receipt/2"):
        candidate_spans = []
        span_rows_valid = True
        for item in native_offers:
            if type(item) is not dict:
                span_rows_valid = False
                break
            packet_id = _identifier(item.get("packet_id"))
            start = item.get("native_prompt_char_start")
            end = item.get("native_prompt_char_end")
            span_sha = _sha256(item.get("native_prompt_span_sha256"))
            if (packet_id is None or type(start) is not int or type(end) is not int
                    or start < 0 or end <= start or end > rendered_prompt_chars
                    or span_sha is None or packet_id in native_prompt_span_by_id):
                span_rows_valid = False
                break
            native_prompt_span_by_id[packet_id] = {
                "start": start, "end": end, "sha256": span_sha,
                "role": item.get("role"),
            }
            candidate_spans.append((start, end))
        candidate_spans.sort()
        if (not span_rows_valid or any(
                candidate_spans[index][0] < candidate_spans[index - 1][1]
                for index in range(1, len(candidate_spans)))):
            native_prompt_span_by_id = {}
    native_prompt_span_roles = {
        item.get("role") for item in native_offers
        if type(item) is dict
        and _identifier(item.get("packet_id")) in native_prompt_span_by_id
    }
    if not receipt:
        flow_status = "OFFER_RECEIPT_UNAVAILABLE"
    elif submitted and c4_recorded and not c4_accepted:
        flow_status = prefix + "TEMPLATE_SUBMITTED_C4_RECEIPT_NOT_ACCEPTED"
    elif submitted and c4_recorded and ids_match:
        if fingerprint_complete and native_prefill_verified and native_generation_completed:
            flow_status = "NATIVE_PREFILL_VERIFIED_AND_GENERATION_COMPLETED_MATCHED_C4"
        elif fingerprint_complete and native_prefill_token_count_matched and native_generation_completed:
            flow_status = "NATIVE_PREFILL_TOKEN_COUNT_MATCHED_AND_GENERATION_COMPLETED_MATCHED_C4"
        elif fingerprint_complete and native_prefill_observed and native_generation_completed:
            flow_status = "NATIVE_PREFILL_OBSERVED_AND_GENERATION_COMPLETED_MATCHED_C4"
        elif fingerprint_complete and native_prefill_observed:
            flow_status = "NATIVE_PREFILL_OBSERVED_MATCHED_C4"
        elif synthetic and synthetic_prefill_verified and synthetic_generation_completed:
            flow_status = "SYNTHETIC_PREFILL_AND_GENERATION_VERIFIED_MATCHED_C4"
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
        packet_id = _identifier(item.get("packet_id"))
        span = native_prompt_span_by_id.get(packet_id)
        offers.append({
            "role": role,
            "rendered_quote_count": _count(item.get("rendered_quote_count")),
            "native_prompt_span_bound": span is not None and span.get("role") == role,
            "native_prompt_char_start": span.get("start") if span else None,
            "native_prompt_char_end": span.get("end") if span else None,
            "native_prompt_span_sha256": span.get("sha256") if span else None,
        })

    body_attempts = _body_offer_evidence(
        r.store,
        event_id,
        event_generation_id=event_generation_id,
        c4_ids=c4_ids,
        c4_recorded=c4_recorded,
        c4_accepted=c4_accepted,
        template_ids=native_ids,
        template_role_by_id=native_role_by_id,
        template_receipt_available=bool(receipt),
        template_submitted=submitted,
        synthetic=synthetic,
        native_prefill_verified=native_prefill_verified,
        native_prefill_observed=native_prefill_observed,
        native_prefill_token_count_matched=native_prefill_token_count_matched,
        native_generation_completed=native_generation_completed,
        synthetic_prefill_verified=synthetic_prefill_verified,
        synthetic_generation_completed=synthetic_generation_completed,
    )
    for item in body_attempts:
        packet_id = _identifier(item.get("packet_id"))
        span = native_prompt_span_by_id.get(packet_id)
        item["native_prompt_span_bound"] = bool(
            span is not None and span.get("role") == item.get("role"))
    selected_body_items = [
        item for item in body_attempts
        if item.get("delivered") and item.get("selected_by_c4") is True
    ]
    if (submitted and c4_recorded and c4_accepted and ids_match
            and any(item.get("telemetry_truncated") for item in body_attempts)):
        flow_status = prefix + "TEMPLATE_MATCHED_C4_BODY_TELEMETRY_TRUNCATED"
    elif (submitted and c4_recorded and c4_accepted and ids_match and selected_body_items
            and any(
                item.get("template_role_matches") is not True
                or item.get("offer_packet_verified") is not True
                or item.get("source_bound") is not True
                or item.get("source_count_matches") is not True
                for item in selected_body_items
            )):
        flow_status = prefix + "TEMPLATE_MATCHED_C4_BODY_EVIDENCE_UNVERIFIED"


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
            "native_completion_http_200": (not synthetic) and receipt.get("native_completion_http_200") is True,
            "synthetic_completion_http_200": synthetic and receipt.get("native_completion_http_200") is True,
            "native_prompt_prefill_verified": native_prefill_verified,
            "native_prefill_observed": native_prefill_observed,
            "native_prefill_token_count_matched": native_prefill_token_count_matched,
            "native_prefill_prompt_tokens": native_prefill_prompt_tokens if not synthetic else None,
            "native_prefill_processed_tokens": native_prefill_processed_tokens if not synthetic else None,
            "native_prefill_cached_tokens": native_prefill_cached_tokens if not synthetic else None,
            "native_prefill_prompt_ms": native_prefill_prompt_ms if not synthetic else None,
            "native_prefill_timing_source": native_prefill_timing_source if not synthetic else None,
            "native_stream_completed": (not synthetic) and receipt.get("native_stream_completed") is True,
            "synthetic_stream_completed": synthetic and receipt.get("native_stream_completed") is True,
            "native_generation_completed": native_generation_completed,
            "synthetic_generation_completed": synthetic_generation_completed,
            "native_prompt_sha256": native_prompt_sha256 if not synthetic else None,
            "rendered_prompt_sha256": rendered_prompt_sha256 if not synthetic else None,
            "rendered_prompt_chars": rendered_prompt_chars if not synthetic else None,
            "native_prompt_render_match": native_prompt_render_match,
            "native_prompt_span_bound": set(native_prompt_span_roles) == set(_BODY_ROLES),
            "native_prompt_span_bound_roles": sorted(native_prompt_span_roles),
            "native_token_ids_sha256": native_token_ids_sha256 if not synthetic else None,
            "native_prompt_tokens": native_prompt_tokens if not synthetic else None,
            "native_tokenizer": receipt.get("native_tokenizer") if not synthetic and receipt.get("native_tokenizer") == "LLAMA_SERVER_TOKENIZE" else None,
            "native_template_submitted": native_submitted,
            "synthetic_template_submitted": synthetic_submitted,
            "template_submitted": submitted,
            "c4_receipt_status": c4_metrics.get("status") if c4_recorded else "NOT_RECORDED",
            "c4_selected_offer_count": _count(c4_metrics.get("count")) if c4_recorded else None,
            "native_prompt_offer_count": len(offers),
            "c4_native_offer_ids_match": ids_match if c4_recorded else None,
            "offers": offers,
            "body_attempts": body_attempts,
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
