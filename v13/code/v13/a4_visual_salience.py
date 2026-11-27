"""A5 -> A4 visual-structure and temporal-change salience adapter.

This keeps the pinned core attention controller byte-stable while adding
source-bound RAW-EYE structural and same-session temporal cues to its A4
receipt. Both are handcrafted BOOT signals: not semantic recognition,
probabilities, learned representations, truth, action authority or learning
authority. Temporal state is process-local, bounded, and never persisted.
"""
from __future__ import annotations

import hashlib
import math
import threading
from collections import OrderedDict


RAW_EYE_STRUCTURE_GAIN = 0.20
RAW_EYE_TEMPORAL_GAIN = 0.10
RAW_EYE_TEMPORAL_THRESHOLD = 0.08
RAW_EYE_TEMPORAL_MAX_GAP_MS = 120_000
RAW_EYE_TEMPORAL_MAX_STREAMS = 32
_COMPONENTS = (
    "global_contrast",
    "global_edge_energy",
    "cell_edge_energy",
    "spatial_color",
    "luminance_range",
)


def _unit(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be numeric")
    value = float(value)
    if not math.isfinite(value) or not 0.0 <= value <= 1.0:
        raise ValueError(f"{label} must be finite and within [0, 1]")
    return value


def _sha256_text(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _valid_sha256(value):
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(char in "0123456789abcdef" for char in value.lower())
    )


class VisionTemporalEvidenceRegistry:
    """Bounded process-local delta tracker scoped to source/session/consent.

    The registry retains only five normalized RAW-EYE components and a frame
    digest. It never stores pixels, OCR, text, app contents, or persistent
    state. A scope change, long gap, clock regression, or provisional frame
    cannot produce a change score.
    """

    def __init__(self, *, max_streams=RAW_EYE_TEMPORAL_MAX_STREAMS,
                 max_gap_ms=RAW_EYE_TEMPORAL_MAX_GAP_MS):
        if type(max_streams) is not int or max_streams < 1:
            raise ValueError("max_streams must be a positive integer")
        if type(max_gap_ms) is not int or max_gap_ms < 1:
            raise ValueError("max_gap_ms must be a positive integer")
        self.max_streams = max_streams
        self.max_gap_ms = max_gap_ms
        self._states = OrderedDict()
        self._lock = threading.Lock()

    @property
    def state_count(self):
        with self._lock:
            return len(self._states)

    def clear(self):
        with self._lock:
            self._states.clear()

    def observe(self, *, source_id, capture_session_id, consent_receipt_ref,
                start_ms, end_ms, finality, frame_sha256, components):
        if (
            not isinstance(source_id, str) or not source_id
            or not isinstance(capture_session_id, str) or not capture_session_id
            or not isinstance(consent_receipt_ref, str) or not consent_receipt_ref
            or type(start_ms) is not int or type(end_ms) is not int
            or start_ms < 0 or end_ms <= start_ms
            or finality not in {"FINAL", "PROVISIONAL"}
            or not _valid_sha256(frame_sha256)
            or not isinstance(components, dict)
            or set(components) != set(_COMPONENTS)
        ):
            return self._result("UNAVAILABLE", frame_sha256=frame_sha256)

        try:
            clean = tuple(_unit(components[key], f"RAW-EYE {key}") for key in _COMPONENTS)
        except ValueError:
            return self._result("UNAVAILABLE", frame_sha256=frame_sha256)

        source_hash = _sha256_text(source_id)
        session_hash = _sha256_text(capture_session_id)
        consent_hash = _sha256_text(consent_receipt_ref)
        key = (source_hash, session_hash, consent_hash)
        binding_hash = _sha256_text("|".join(key))

        with self._lock:
            # Never retain/reuse temporal state across a source, session, or
            # consent boundary, even when the incoming frame is provisional.
            scope_reset = False
            for old_key in list(self._states):
                if old_key != key and (
                    old_key[0] == source_hash
                    or old_key[1] == session_hash
                ):
                    del self._states[old_key]
                    scope_reset = True

            if finality != "FINAL":
                return self._result(
                    "PROVISIONAL_IGNORED",
                    frame_sha256=frame_sha256,
                    stream_binding_sha256=binding_hash,
                )

            previous = self._states.get(key)
            if previous is None:
                self._store(key, start_ms, end_ms, frame_sha256, clean)
                return self._result(
                    "SCOPE_RESET" if scope_reset else "WARMUP",
                    frame_sha256=frame_sha256,
                    stream_binding_sha256=binding_hash,
                )

            gap_ms = start_ms - previous["end_ms"]
            if start_ms <= previous["start_ms"] or end_ms <= previous["end_ms"] or gap_ms < 0:
                self._store(key, start_ms, end_ms, frame_sha256, clean)
                return self._result(
                    "CLOCK_OR_OVERLAP_RESET",
                    frame_sha256=frame_sha256,
                    previous_frame_sha256=previous["frame_sha256"],
                    gap_ms=gap_ms,
                    stream_binding_sha256=binding_hash,
                )
            if gap_ms > self.max_gap_ms:
                self._store(key, start_ms, end_ms, frame_sha256, clean)
                return self._result(
                    "GAP_RESET",
                    frame_sha256=frame_sha256,
                    previous_frame_sha256=previous["frame_sha256"],
                    gap_ms=gap_ms,
                    stream_binding_sha256=binding_hash,
                )

            change_score = math.fsum(
                abs(current - old)
                for current, old in zip(clean, previous["components"])
            ) / len(_COMPONENTS)
            previous_sha = previous["frame_sha256"]
            self._store(key, start_ms, end_ms, frame_sha256, clean)
            return self._result(
                "MEASURED",
                frame_sha256=frame_sha256,
                previous_frame_sha256=previous_sha,
                gap_ms=gap_ms,
                change_score=round(change_score, 6),
                stream_binding_sha256=binding_hash,
            )

    def _store(self, key, start_ms, end_ms, frame_sha256, components):
        self._states[key] = {
            "start_ms": start_ms,
            "end_ms": end_ms,
            "frame_sha256": frame_sha256.lower(),
            "components": components,
        }
        self._states.move_to_end(key)
        while len(self._states) > self.max_streams:
            self._states.popitem(last=False)

    @staticmethod
    def _result(status, *, frame_sha256=None, previous_frame_sha256=None,
                gap_ms=None, change_score=None, stream_binding_sha256=None):
        measured = status == "MEASURED" and change_score is not None
        return {
            "schema": "v14.raw-eye.temporal-change/1",
            "method": "RAW_EYE_COMPONENT_DELTA_V1",
            "status": status,
            "frame_sha256": frame_sha256.lower() if _valid_sha256(frame_sha256) else None,
            "previous_frame_sha256": (
                previous_frame_sha256.lower() if _valid_sha256(previous_frame_sha256) else None
            ),
            "stream_binding_sha256": stream_binding_sha256,
            "gap_ms": gap_ms,
            "change_score": change_score if measured else None,
            "change_detected": bool(measured and change_score >= RAW_EYE_TEMPORAL_THRESHOLD),
            "score_is_probability": False,
            "authority": "ATTENTION_ONLY",
            "persisted": False,
            "learned": False,
            "truth_authority": 0,
            "action_authority": False,
            "learning_authority": False,
        }


_VISION_TEMPORAL_REGISTRY = VisionTemporalEvidenceRegistry()


def reset_visual_temporal_state():
    """Clear process-local temporal state; intended for lifecycle cleanup/tests."""
    _VISION_TEMPORAL_REGISTRY.clear()


def _temporal_visual_change(a4_result, segment, clean_components):
    rows = a4_result.get("segments")
    if not isinstance(rows, list):
        return _VISION_TEMPORAL_REGISTRY._result("UNAVAILABLE")
    ui_rows = [
        row for row in rows
        if isinstance(row, dict)
        and isinstance(row.get("source_ref"), dict)
        and row["source_ref"].get("modality") == "ui"
    ]
    if len(ui_rows) != 1:
        return _VISION_TEMPORAL_REGISTRY._result("UNAVAILABLE")
    source_id = ui_rows[0]["source_ref"].get("source_id")
    source_ref = segment.get("source_ref") or {}
    return _VISION_TEMPORAL_REGISTRY.observe(
        source_id=source_id,
        capture_session_id=segment.get("capture_session_id"),
        consent_receipt_ref=segment.get("consent_receipt_ref"),
        start_ms=segment.get("start_ms"),
        end_ms=segment.get("end_ms"),
        finality=segment.get("finality"),
        frame_sha256=source_ref.get("sha256"),
        components=clean_components,
    )


def apply_raw_eye_structure(a4_result, segment, score, components, *, segment_index=0):
    """Attach RAW-EYE structure and same-session visual change to one A4 row.

    A5 may emit several hypotheses for one visual source. Source identity alone
    therefore does not identify a unique A4 row; the base visual segment is
    explicitly addressed by its stable segment index.
    """
    if not isinstance(a4_result, dict) or not isinstance(segment, dict):
        raise ValueError("A4 result and visual segment must be mappings")
    if type(segment_index) is not int or segment_index < 0:
        raise ValueError("RAW-EYE target segment index must be a non-negative integer")
    source_ref = segment.get("source_ref")
    if (
        segment.get("modality") != "visual"
        or not isinstance(source_ref, dict)
        or source_ref.get("modality") != "visual"
        or segment.get("capture_method") != "MEDIA_PROJECTION"
        or segment.get("producer_component") != "A5_VISUAL"
    ):
        raise ValueError("RAW-EYE salience lacks A5 MediaProjection provenance")
    score = _unit(score, "RAW-EYE structure score")
    if not isinstance(components, dict) or set(components) != set(_COMPONENTS):
        raise ValueError("RAW-EYE structure components are incomplete")
    clean_components = {
        key: round(_unit(components[key], f"RAW-EYE {key}"), 6)
        for key in _COMPONENTS
    }
    rows = a4_result.get("segments")
    if not isinstance(rows, list):
        raise ValueError("A4 result has no segment salience rows")
    matches = [
        row for row in rows
        if isinstance(row, dict)
        and row.get("index") == segment_index
        and row.get("source_ref") == source_ref
    ]
    if len(matches) != 1:
        raise ValueError("RAW-EYE source/index does not map to exactly one A4 row")
    row = matches[0]

    # Validate the target row before mutating the process-local temporal ledger.
    temporal_change = _temporal_visual_change(a4_result, segment, clean_components)
    temporal_score = (
        temporal_change["change_score"]
        if temporal_change["status"] == "MEASURED" else 0.0
    )
    temporal_contribution = RAW_EYE_TEMPORAL_GAIN * temporal_score
    base_score = _unit(row.get("score"), "A4 base salience")
    contribution = RAW_EYE_STRUCTURE_GAIN * score
    row["base_score"] = round(base_score, 6)
    row["raw_eye_structure"] = round(score, 6)
    row["raw_eye_components"] = clean_components
    row["raw_eye_contribution"] = round(contribution, 6)
    row["temporal_visual_change"] = temporal_change
    row["temporal_visual_change_contribution"] = round(temporal_contribution, 6)
    row["score"] = round(min(1.0, base_score + contribution + temporal_contribution), 6)
    row["reason_detail"] = (
        "raw_eye_temporal_change"
        if temporal_change["change_detected"]
        else "raw_eye_structure" if score > 0.0 else row.get("reason")
    )

    # Both structural and temporal contributions change A4 salience, so
    # refresh normalized weights/suppression and re-look ranking instead of
    # leaving them tied to the pre-RAW-EYE scores.
    from .attention import A4 as ATTENTION_A4

    temperature = float(ATTENTION_A4["attention_temperature"])
    if not math.isfinite(temperature) or temperature <= 0.0:
        raise ValueError("A4 attention temperature must be finite and positive")
    if rows:
        scores = [_unit(item.get("score"), "A4 segment salience") for item in rows]
        maximum = max(scores)
        weights = [math.exp((value - maximum) / temperature) for value in scores]
        normalizer = sum(weights)
        if not math.isfinite(normalizer) or normalizer <= 0.0:
            raise ValueError("A4 attention normalization is invalid")
        for item, value, weight in zip(rows, scores, weights):
            if not isinstance(item, dict) or type(item.get("index")) is not int:
                raise ValueError("A4 segment row identity is invalid")
            item["weight"] = round(weight / normalizer, 6)
            item["suppression"] = round(
                ATTENTION_A4["suppression_max"] * (1.0 - value / maximum)
                if maximum > 0.0 else 0.0,
                6,
            )
        relook = sorted(
            (
                item for item in rows
                if item["score"] >= ATTENTION_A4["reentry_threshold"]
            ),
            key=lambda item: (-item["score"], item["index"]),
        )[:ATTENTION_A4["max_highres_regions"]]
        a4_result["highres"] = [item["index"] for item in relook]

    a4_result["raw_eye_signal"] = {
        "source_ref": source_ref,
        "score": round(score, 6),
        "gain": RAW_EYE_STRUCTURE_GAIN,
        "contribution": round(contribution, 6),
        "temporal_visual_change": temporal_change,
        "temporal_gain": RAW_EYE_TEMPORAL_GAIN,
        "temporal_contribution": round(temporal_contribution, 6),
        "authority": "ATTENTION_ONLY",
        "learned": False,
        "truth_authority": 0,
        "action_authority": False,
        "learning_authority": False,
    }
    return a4_result