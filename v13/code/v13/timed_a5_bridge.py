"""Consent-bound observation-only bridge: timed A-plane events to A5 admission.

Does not capture audio/UI, ingest transcript text, authorize permissions or infer.
"""
from dataclasses import dataclass
from typing import Iterable
from .timed_percept import TimedPercept
from .percept_admission import Percept, Admission, admit

@dataclass(frozen=True)
class TimedAdmission:
    admission: Admission
    refused_ids: tuple[str, ...]

def admit_timed(events: Iterable[TimedPercept], *, allowed_consent_ids: frozenset[str], token_budget: int) -> TimedAdmission:
    if not isinstance(allowed_consent_ids, frozenset) or any(type(x) is not str or not x for x in allowed_consent_ids):
        raise ValueError("explicit consent allowlist required")
    records = tuple(events)
    if len(records) > 4096:
        raise ValueError("too many events")
    seen, candidates, refused = set(), [], []
    for event in records:
        if not isinstance(event, TimedPercept):
            raise TypeError("expected TimedPercept")
        key = (event.modality, event.source, event.start_ms)
        if key in seen:
            raise ValueError("duplicate event lineage")
        seen.add(key)
        if event.consent_id not in allowed_consent_ids or event.stage != "final":
            refused.append(event.source)
            continue
        if event.modality == "audio":
            fields = []
            if event.rms is not None:
                fields.append(f"rms={event.rms:.4g}")
            if event.pitch_hz is not None:
                fields.append(f"pitch_hz={event.pitch_hz:.4g}")
            if event.speech_probability is not None:
                fields.append(f"speech_probability={event.speech_probability:.3g}")
            if event.non_speech is not None:
                fields.append("non_speech_event_present")
            summary = "audio acoustic: " + (", ".join(fields) if fields else "unspecified")
        else:
            summary = event.modality + " observation; no screen content provided"
        candidates.append(Percept(source_id=f"{event.modality}:{event.source}:{event.start_ms}",
                                  modality="ui" if event.modality == "android_ui" else event.modality,
                                  start_ms=event.start_ms, end_ms=event.end_ms,
                                  summary=summary, consent=True, final=True))
    return TimedAdmission(admit(candidates, token_budget), tuple(refused))
