"""Bounded temporal evidence smoothing for RAW EAR attention.

This is a deterministic scalar state-space filter, not a trained VAD or a
calibrated speech probability. It consumes already extracted RAW EAR cues and
is used only to smooth A4 voice salience. It does not alter source provenance,
persist raw PCM, or grant body, learning, or action authority.
"""
from __future__ import annotations

import math


class TemporalVoiceEvidence:
    """Per-stream attack/release evidence accumulator for sequential audio windows."""

    METHOD = "RAW_EAR_TEMPORAL_EVIDENCE_V1"

    def __init__(
        self,
        *,
        attack_tau_ms: float = 80.0,
        release_tau_ms: float = 240.0,
        onset_threshold: float = 0.55,
        offset_threshold: float = 0.22,
        reset_gap_ms: int = 1000,
        eot_silence_ms: int = 400,
    ) -> None:
        for name, value in (("attack_tau_ms", attack_tau_ms), ("release_tau_ms", release_tau_ms)):
            if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
                raise ValueError(name + " must be finite and positive")
        if (type(onset_threshold) not in (int, float) or not math.isfinite(onset_threshold)
                or not 0 < onset_threshold <= 1):
            raise ValueError("onset_threshold must be in (0, 1]")
        if (type(offset_threshold) not in (int, float) or not math.isfinite(offset_threshold)
                or not 0 <= offset_threshold < onset_threshold):
            raise ValueError("offset_threshold must be in [0, onset_threshold)")
        if type(reset_gap_ms) is not int or reset_gap_ms < 0:
            raise ValueError("reset_gap_ms must be a nonnegative integer")
        if type(eot_silence_ms) is not int or not 80 <= eot_silence_ms <= 2000:
            raise ValueError("eot_silence_ms must be an integer in [80, 2000]")
        self.eot_silence_ms = eot_silence_ms
        self.attack_tau_ms = float(attack_tau_ms)
        self.release_tau_ms = float(release_tau_ms)
        self.onset_threshold = float(onset_threshold)
        self.offset_threshold = float(offset_threshold)
        self.reset_gap_ms = reset_gap_ms
        self.reset()

    def reset(self) -> None:
        self._source_id: str | None = None
        self._generation_id: str | None = None
        self._consent_receipt_ref: str | None = None
        self._last_end_ms: int | None = None
        self._evidence = 0.0
        self._active = False
        self._silence_ms = 0
        self._speech_seen = False
        self._eot_emitted = False
        # A4 non-speech event state is source/consent scoped like voice evidence.
        self._non_speech_active = False
        self._non_speech_kind = None
        self._non_speech_score = 0.0

    def update(
        self,
        *,
        source_id: str,
        generation_id: str,
        start_ms: int,
        end_ms: int,
        cues: dict,
        consent_receipt_ref: str | None = None,
    ) -> dict:
        if type(source_id) is not str or not source_id.strip() or len(source_id) > 128:
            raise ValueError("source_id is invalid")
        if type(generation_id) is not str or not generation_id.strip() or len(generation_id) > 128:
            raise ValueError("generation_id is invalid")
        if type(start_ms) is not int or start_ms < 0:
            raise ValueError("start_ms must be a nonnegative integer")
        if type(end_ms) is not int or end_ms <= start_ms:
            raise ValueError("end_ms must be an integer after start_ms")
        if type(cues) is not dict:
            raise ValueError("cues must be an object")
        if consent_receipt_ref is not None and (
            type(consent_receipt_ref) is not str
            or not consent_receipt_ref.strip()
            or len(consent_receipt_ref) > 256
        ):
            raise ValueError("consent_receipt_ref is invalid")
        hint = cues.get("activity_hint")
        score = cues.get("activity_score")
        if type(hint) is not str or hint not in {"SILENCE", "VOICED", "UNVOICED_NOISE", "IMPULSIVE", "UNCERTAIN"}:
            raise ValueError("activity_hint is invalid")
        if type(score) not in (int, float) or not math.isfinite(score) or not 0 <= score <= 1:
            raise ValueError("activity_score must be finite and in [0, 1]")

        reset_reason = None
        if self._source_id is not None and (
            source_id != self._source_id or generation_id != self._generation_id
        ):
            self.reset()
            reset_reason = "SOURCE_OR_GENERATION_CHANGED"
        elif self._source_id is not None and consent_receipt_ref != self._consent_receipt_ref:
            # A renewed/replaced consent receipt starts a new acoustic epoch.
            # Never carry voice-activity evidence across that boundary.
            self.reset()
            reset_reason = "CONSENT_RECEIPT_CHANGED"

        previous_end_ms = self._last_end_ms
        gap_ms = 0
        gap_offset = False
        non_speech_gap_offset = False
        if previous_end_ms is not None:
            if end_ms <= previous_end_ms:
                raise ValueError("audio windows must advance monotonically")
            gap_ms = max(0, start_ms - previous_end_ms)
            if gap_ms > self.reset_gap_ms:
                self.reset()
                reset_reason = "STREAM_GAP"
                previous_end_ms = None

        if previous_end_ms is None:
            # First window or a deliberate stream reset: no unobserved interval
            # is allowed to contribute positive evidence.
            gap_evidence = 0.0
            active_after_gap = False
            observed_ms = end_ms - start_ms
            elapsed_ms = observed_ms
            gap_decay_ms = 0
        else:
            # Decay old evidence through an unobserved gap before applying the
            # new window. Never smear the new window's label backward in time.
            if gap_ms:
                gap_evidence = self._evidence * math.exp(-gap_ms / self.release_tau_ms)
                gap_offset = self._active and gap_evidence <= self.offset_threshold
                active_after_gap = self._active and not gap_offset
            else:
                gap_evidence = self._evidence
                active_after_gap = self._active
            # Sliding windows may overlap. Only the newly covered suffix advances
            # the state, avoiding double-counting already observed audio.
            observed_start_ms = max(start_ms, previous_end_ms)
            observed_ms = end_ms - observed_start_ms
            if observed_ms <= 0:
                raise ValueError("audio windows must add newly observed time")
            elapsed_ms = gap_ms + observed_ms
            gap_decay_ms = gap_ms

        # Decay non-speech activity across observed gaps; an unobserved interval
        # is never itself a new event or evidence of a semantic sound.
        if gap_ms and self._non_speech_active:
            self._non_speech_score *= math.exp(-gap_ms / self.release_tau_ms)
            if self._non_speech_score <= self.offset_threshold:
                self._non_speech_active = False
                self._non_speech_kind = None
                self._non_speech_score = 0.0
                non_speech_gap_offset = True

        # Only the already-voiced RAW EAR class contributes speech evidence.
        # Silence, impulsive activity and unvoiced noise remain distinct cues.
        target = float(score) if hint == "VOICED" else 0.0
        tau = self.attack_tau_ms if target > gap_evidence else self.release_tau_ms
        alpha = math.exp(-observed_ms / tau)
        evidence = alpha * gap_evidence + (1.0 - alpha) * target
        onset = not active_after_gap and evidence >= self.onset_threshold
        window_offset = active_after_gap and evidence <= self.offset_threshold
        if onset:
            active = True
        elif window_offset:
            active = False
        else:
            active = active_after_gap
        offset = gap_offset or window_offset

        # Non-speech cues remain distinct from speech. A continuous noise bed or
        # overlapping impulse windows emits one onset, not repeated A4 novelty.
        # SILENCE/VOICED end the episode; UNCERTAIN decays it conservatively.
        non_speech_kind = hint if hint in {"UNVOICED_NOISE", "IMPULSIVE"} else None
        non_speech_onset = False
        non_speech_offset = non_speech_gap_offset
        if non_speech_kind is not None:
            updated_non_speech_score = max(
                self._non_speech_score * math.exp(-observed_ms / self.release_tau_ms),
                float(score),
            )
            if updated_non_speech_score > self.offset_threshold:
                non_speech_onset = (
                    not self._non_speech_active or self._non_speech_kind != non_speech_kind
                )
                self._non_speech_active = True
                self._non_speech_kind = non_speech_kind
                self._non_speech_score = updated_non_speech_score
            else:
                non_speech_offset = non_speech_offset or self._non_speech_active
                self._non_speech_active = False
                self._non_speech_kind = None
                self._non_speech_score = 0.0
        elif hint in {"SILENCE", "VOICED"}:
            non_speech_offset = non_speech_offset or self._non_speech_active
            self._non_speech_active = False
            self._non_speech_kind = None
            self._non_speech_score = 0.0
        else:
            self._non_speech_score *= math.exp(-observed_ms / self.release_tau_ms)
            if self._non_speech_active and self._non_speech_score <= self.offset_threshold:
                non_speech_offset = True
                self._non_speech_active = False
                self._non_speech_kind = None
                self._non_speech_score = 0.0
        non_speech_novelty = float(score) if non_speech_onset else 0.0

        # Turn candidates are deliberately separate from floor-transfer truth.
        # Only newly observed, contiguous SILENCE after sustained voiced activity
        # can produce one EOT candidate; noise, uncertainty and unobserved gaps
        # never count as silence. This is a BOOT heuristic, not a learned verifier.
        if hint == "VOICED":
            self._silence_ms = 0
            if onset or active:
                self._speech_seen = True
                self._eot_emitted = False
        elif hint == "SILENCE":
            if self._speech_seen:
                self._silence_ms += observed_ms
        else:
            self._silence_ms = 0

        eot_candidate = (
            self._speech_seen and not active and not self._eot_emitted
            and self._silence_ms >= self.eot_silence_ms
        )
        if eot_candidate:
            self._speech_seen = False
            self._eot_emitted = True

        self._source_id = source_id
        self._generation_id = generation_id
        self._consent_receipt_ref = consent_receipt_ref
        self._last_end_ms = end_ms
        self._evidence = max(0.0, min(1.0, evidence))
        self._active = active
        return {
            "method": self.METHOD,
            "voice_evidence": round(self._evidence, 6),
            "voice_active": self._active,
            "voice_onset": onset,
            "voice_offset": offset,
            "gap_offset": gap_offset,
            "non_speech_active": self._non_speech_active,
            "non_speech_kind": self._non_speech_kind,
            "non_speech_onset": non_speech_onset,
            "non_speech_offset": non_speech_offset,
            "non_speech_score": round(self._non_speech_score, 6),
            "non_speech_novelty": round(non_speech_novelty, 6),
            "turn_candidates": {
                "method": "RAW_EAR_TURN_CANDIDATES_V1",
                "speech_candidate": bool(self._active),
                "eot_candidate": bool(eot_candidate),
                "interrupt_candidate": bool(onset),
                "floor_transfer_verified": False,
                "floor_transfer_status": "UNVERIFIED",
                "observed_silence_ms": self._silence_ms,
                "minimum_silence_ms": self.eot_silence_ms,
            },
            "gap_ms": gap_ms,
            "gap_decay_ms": gap_decay_ms,
            "observed_ms": observed_ms,
            "elapsed_ms": elapsed_ms,
            "state_reset": reset_reason is not None,
            "reset_reason": reset_reason,
        }


from collections import OrderedDict
import threading


class TemporalVoiceEvidenceRegistry:
    """Bounded temporal filters isolated by source, generation and consent receipt."""

    def __init__(self, *, max_streams: int = 16, **state_options) -> None:
        if type(max_streams) is not int or not 1 <= max_streams <= 256:
            raise ValueError("max_streams must be an integer in [1, 256]")
        self.max_streams = max_streams
        self._state_options = dict(state_options)
        self._states = OrderedDict()
        self._lock = threading.RLock()

    def update(self, *, source_id: str, generation_id: str,
               start_ms: int, end_ms: int, cues: dict,
               consent_receipt_ref: str | None = None) -> dict:
        if type(source_id) is not str or not source_id.strip() or len(source_id) > 128:
            raise ValueError("source_id is invalid")
        if type(generation_id) is not str or not generation_id.strip() or len(generation_id) > 128:
            raise ValueError("generation_id is invalid")
        if consent_receipt_ref is not None and (
            type(consent_receipt_ref) is not str
            or not consent_receipt_ref.strip()
            or len(consent_receipt_ref) > 256
        ):
            raise ValueError("consent_receipt_ref is invalid")
        key = (source_id, generation_id, consent_receipt_ref)
        with self._lock:
            receipt_changed = any(
                old_key[0] == source_id and old_key[1] == generation_id
                and old_key[2] != consent_receipt_ref
                for old_key in self._states
            )
            state = self._states.get(key)
            if state is None:
                state = TemporalVoiceEvidence(**self._state_options)
            result = state.update(
                source_id=source_id, generation_id=generation_id,
                start_ms=start_ms, end_ms=end_ms, cues=cues,
                consent_receipt_ref=consent_receipt_ref,
            )
            if receipt_changed and result.get("reset_reason") is None:
                result["state_reset"] = True
                result["reset_reason"] = "CONSENT_RECEIPT_CHANGED"
            for old_key in list(self._states):
                if old_key[0] == source_id and old_key != key:
                    del self._states[old_key]
            self._states.pop(key, None)
            self._states[key] = state
            while len(self._states) > self.max_streams:
                self._states.popitem(last=False)
            return result

    def reset(self, *, source_id: str | None = None,
              generation_id: str | None = None,
              consent_receipt_ref: str | None = None) -> int:
        if source_id is None and generation_id is not None:
            raise ValueError("generation_id requires source_id")
        if source_id is not None and (
            type(source_id) is not str or not source_id.strip() or len(source_id) > 128
        ):
            raise ValueError("source_id is invalid")
        if generation_id is not None and (
            type(generation_id) is not str or not generation_id.strip() or len(generation_id) > 128
        ):
            raise ValueError("generation_id is invalid")
        if consent_receipt_ref is not None and (
            type(consent_receipt_ref) is not str
            or not consent_receipt_ref.strip()
            or len(consent_receipt_ref) > 256
        ):
            raise ValueError("consent_receipt_ref is invalid")
        if consent_receipt_ref is not None and source_id is None:
            raise ValueError("consent_receipt_ref requires source_id")
        with self._lock:
            keys = [
                key for key in self._states
                if source_id is None or (
                    key[0] == source_id and
                    (generation_id is None or key[1] == generation_id) and
                    (consent_receipt_ref is None or key[2] == consent_receipt_ref)
                )
            ]
            for key in keys:
                del self._states[key]
            return len(keys)

    def __len__(self) -> int:
        with self._lock:
            return len(self._states)
