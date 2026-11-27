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
        self.attack_tau_ms = float(attack_tau_ms)
        self.release_tau_ms = float(release_tau_ms)
        self.onset_threshold = float(onset_threshold)
        self.offset_threshold = float(offset_threshold)
        self.reset_gap_ms = reset_gap_ms
        self.reset()

    def reset(self) -> None:
        self._source_id: str | None = None
        self._generation_id: str | None = None
        self._session_id: str | None = None
        self._consent_scope_id: str | None = None
        self._last_start_ms: int | None = None
        self._last_end_ms: int | None = None
        self._evidence = 0.0
        self._active = False
        # Provisional windows use a reversible shadow state. FINAL windows alone
        # advance the committed filter state.
        self._preview_state = None
        self._preview_signature = None
        self._preview_result = None
        self._preview_start_ms = None
        self._preview_end_ms = None
        self._preview_revision = 0

    def _clone_committed_state(self) -> "TemporalVoiceEvidence":
        clone = TemporalVoiceEvidence(
            attack_tau_ms=self.attack_tau_ms,
            release_tau_ms=self.release_tau_ms,
            onset_threshold=self.onset_threshold,
            offset_threshold=self.offset_threshold,
            reset_gap_ms=self.reset_gap_ms,
        )
        clone._source_id = self._source_id
        clone._generation_id = self._generation_id
        clone._session_id = self._session_id
        clone._consent_scope_id = self._consent_scope_id
        clone._last_start_ms = self._last_start_ms
        clone._last_end_ms = self._last_end_ms
        clone._evidence = self._evidence
        clone._active = self._active
        return clone

    def preview(
        self,
        *,
        source_id: str,
        generation_id: str,
        start_ms: int,
        end_ms: int,
        cues: dict,
        session_id: str | None = None,
        consent_scope_id: str | None = None,
    ) -> dict:
        """Evaluate provisional cues without committing temporal evidence.

        Consecutive provisional windows may accumulate in a private preview copy.
        Repeated identical windows are idempotent; a revised or rewound window is
        recomputed from the last committed FINAL state. A later FINAL update then
        commits once, even when it promotes the exact same interval.
        """
        if type(cues) is not dict:
            raise ValueError("cues must be an object")
        signature = (
            source_id, generation_id, session_id, consent_scope_id,
            start_ms, end_ms, cues.get("activity_hint"), cues.get("activity_score"),
        )
        if self._preview_state is not None and signature == self._preview_signature:
            return dict(self._preview_result)

        rebuild = self._preview_state is None
        if not rebuild:
            rebuild = (
                self._preview_start_ms is None
                or self._preview_end_ms is None
                or start_ms < self._preview_start_ms
                or end_ms <= self._preview_end_ms
            )
        candidate = self._clone_committed_state() if rebuild else self._preview_state
        result = candidate.update(
            source_id=source_id,
            generation_id=generation_id,
            start_ms=start_ms,
            end_ms=end_ms,
            cues=cues,
            session_id=session_id,
            consent_scope_id=consent_scope_id,
        )
        result = dict(result)
        result["preview_only"] = True
        result["preview_revision"] = self._preview_revision + 1
        self._preview_state = candidate
        self._preview_signature = signature
        self._preview_result = dict(result)
        self._preview_start_ms = start_ms
        self._preview_end_ms = end_ms
        self._preview_revision += 1
        return result

    def update(
        self,
        *,
        source_id: str,
        generation_id: str,
        start_ms: int,
        end_ms: int,
        cues: dict,
        session_id: str | None = None,
        consent_scope_id: str | None = None,
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
        if (session_id is None) != (consent_scope_id is None):
            raise ValueError("session_id and consent_scope_id must be supplied together")
        if session_id is not None and (
            type(session_id) is not str or not session_id.strip() or len(session_id) > 128
        ):
            raise ValueError("session_id is invalid")
        if consent_scope_id is not None and (
            type(consent_scope_id) is not str or len(consent_scope_id) != 64
            or any(char not in "0123456789abcdef" for char in consent_scope_id)
        ):
            raise ValueError("consent_scope_id must be a lowercase SHA-256 digest")
        hint = cues.get("activity_hint")
        score = cues.get("activity_score")
        if type(hint) is not str or hint not in {"SILENCE", "VOICED", "UNVOICED_NOISE", "IMPULSIVE", "UNCERTAIN"}:
            raise ValueError("activity_hint is invalid")
        if type(score) not in (int, float) or not math.isfinite(score) or not 0 <= score <= 1:
            raise ValueError("activity_score must be finite and in [0, 1]")

        reset_reason = None
        if self._source_id is not None:
            if source_id != self._source_id or generation_id != self._generation_id:
                self.reset()
                reset_reason = "SOURCE_OR_GENERATION_CHANGED"
            elif (session_id, consent_scope_id) != (self._session_id, self._consent_scope_id):
                self.reset()
                reset_reason = "SESSION_OR_CONSENT_SCOPE_CHANGED"
        self._session_id = session_id
        self._consent_scope_id = consent_scope_id

        previous_start_ms = self._last_start_ms
        if previous_start_ms is not None and start_ms < previous_start_ms:
            raise ValueError("audio window start times must advance monotonically")

        previous_end_ms = self._last_end_ms
        gap_ms = 0
        gap_offset = False
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

        self._source_id = source_id
        self._generation_id = generation_id
        self._last_start_ms = start_ms
        self._last_end_ms = end_ms
        self._evidence = max(0.0, min(1.0, evidence))
        self._active = active
        # A committed FINAL update supersedes all provisional preview history.
        self._preview_state = None
        self._preview_signature = None
        self._preview_result = None
        self._preview_start_ms = None
        self._preview_end_ms = None
        self._preview_revision = 0
        return {
            "method": self.METHOD,
            "voice_evidence": round(self._evidence, 6),
            "voice_active": self._active,
            "voice_onset": onset,
            "voice_offset": offset,
            "gap_offset": gap_offset,
            "gap_ms": gap_ms,
            "gap_decay_ms": gap_decay_ms,
            "observed_ms": observed_ms,
            "elapsed_ms": elapsed_ms,
            "state_reset": reset_reason is not None,
            "reset_reason": reset_reason,
            "preview_only": False,
            "preview_revision": 0,
        }


from collections import OrderedDict
import threading


class TemporalVoiceEvidenceRegistry:
    """Bounded, runtime-local temporal filters keyed by source and generation."""

    def __init__(self, *, max_streams: int = 16, **state_options) -> None:
        if type(max_streams) is not int or not 1 <= max_streams <= 256:
            raise ValueError("max_streams must be an integer in [1, 256]")
        self.max_streams = max_streams
        self._state_options = dict(state_options)
        self._states = OrderedDict()
        self._lock = threading.RLock()

    def update(self, *, source_id: str, generation_id: str,
               start_ms: int, end_ms: int, cues: dict,
               session_id: str | None = None,
               consent_scope_id: str | None = None) -> dict:
        if type(source_id) is not str or not source_id.strip() or len(source_id) > 128:
            raise ValueError("source_id is invalid")
        if type(generation_id) is not str or not generation_id.strip() or len(generation_id) > 128:
            raise ValueError("generation_id is invalid")
        if (session_id is None) != (consent_scope_id is None):
            raise ValueError("session_id and consent_scope_id must be supplied together")
        if session_id is not None and (
            type(session_id) is not str or not session_id.strip() or len(session_id) > 128
        ):
            raise ValueError("session_id is invalid")
        if consent_scope_id is not None and (
            type(consent_scope_id) is not str or len(consent_scope_id) != 64
            or any(char not in "0123456789abcdef" for char in consent_scope_id)
        ):
            raise ValueError("consent_scope_id must be a lowercase SHA-256 digest")
        scope = (session_id, consent_scope_id)
        key = (source_id, generation_id, session_id, consent_scope_id)
        with self._lock:
            scope_changed = False
            for old_key in list(self._states):
                if old_key[0] == source_id and (
                    old_key[1] != generation_id or old_key[2:] != scope
                ):
                    if old_key[1] == generation_id and old_key[2:] != scope:
                        scope_changed = True
                    del self._states[old_key]
            state = self._states.get(key)
            if state is None:
                state = TemporalVoiceEvidence(**self._state_options)
            result = state.update(
                source_id=source_id, generation_id=generation_id,
                start_ms=start_ms, end_ms=end_ms, cues=cues,
                session_id=session_id, consent_scope_id=consent_scope_id,
            )
            if scope_changed:
                result["state_reset"] = True
                result["reset_reason"] = "SESSION_OR_CONSENT_SCOPE_CHANGED"
            self._states.pop(key, None)
            self._states[key] = state
            while len(self._states) > self.max_streams:
                self._states.popitem(last=False)
            return result

    def preview(self, *, source_id: str, generation_id: str,
                start_ms: int, end_ms: int, cues: dict,
                session_id: str | None = None,
                consent_scope_id: str | None = None) -> dict:
        if type(source_id) is not str or not source_id.strip() or len(source_id) > 128:
            raise ValueError("source_id is invalid")
        if type(generation_id) is not str or not generation_id.strip() or len(generation_id) > 128:
            raise ValueError("generation_id is invalid")
        if (session_id is None) != (consent_scope_id is None):
            raise ValueError("session_id and consent_scope_id must be supplied together")
        if session_id is not None and (
            type(session_id) is not str or not session_id.strip() or len(session_id) > 128
        ):
            raise ValueError("session_id is invalid")
        if consent_scope_id is not None and (
            type(consent_scope_id) is not str or len(consent_scope_id) != 64
            or any(char not in "0123456789abcdef" for char in consent_scope_id)
        ):
            raise ValueError("consent_scope_id must be a lowercase SHA-256 digest")
        scope = (session_id, consent_scope_id)
        key = (source_id, generation_id, session_id, consent_scope_id)
        with self._lock:
            scope_changed = False
            for old_key in list(self._states):
                if old_key[0] == source_id and (
                    old_key[1] != generation_id or old_key[2:] != scope
                ):
                    if old_key[1] == generation_id and old_key[2:] != scope:
                        scope_changed = True
                    del self._states[old_key]
            state = self._states.get(key)
            if state is None:
                state = TemporalVoiceEvidence(**self._state_options)
            result = state.preview(
                source_id=source_id, generation_id=generation_id,
                start_ms=start_ms, end_ms=end_ms, cues=cues,
                session_id=session_id, consent_scope_id=consent_scope_id,
            )
            if scope_changed:
                result["state_reset"] = True
                result["reset_reason"] = "SESSION_OR_CONSENT_SCOPE_CHANGED"
            self._states.pop(key, None)
            self._states[key] = state
            while len(self._states) > self.max_streams:
                self._states.popitem(last=False)
            return result

    def reset(self, *, source_id: str | None = None,
              generation_id: str | None = None) -> int:
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
        with self._lock:
            keys = [
                key for key in self._states
                if source_id is None or (
                    key[0] == source_id and
                    (generation_id is None or key[1] == generation_id)
                )
            ]
            for key in keys:
                del self._states[key]
            return len(keys)

    def __len__(self) -> int:
        with self._lock:
            return len(self._states)
