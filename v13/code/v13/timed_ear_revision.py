"""A5 timed EAR revision joiner: explicit source provenance, no raw capture.

Final frames replace provisional frames only for identical intervals. Different
sources/consent scopes never join. No microphone access or action authority.
"""
from dataclasses import dataclass
from typing import Tuple
from .timed_ear_contract import TimedEarPacket, AcousticFrame


@dataclass(frozen=True)
class EarRevision:
    packet: TimedEarPacket
    sequence: int


def reconcile_ear_revisions(revisions: Tuple[EarRevision, ...]) -> TimedEarPacket:
    if not 1 <= len(revisions) <= 32:
        raise ValueError("bounded revision batch required")
    first = revisions[0].packet
    if len({r.sequence for r in revisions}) != len(revisions):
        raise ValueError("duplicate revision sequence")
    if any(r.sequence < 0 for r in revisions):
        raise ValueError("negative revision sequence")
    if any((r.packet.source, r.packet.consent_scope, r.packet.provenance) !=
           (first.source, first.consent_scope, first.provenance) for r in revisions):
        raise PermissionError("source or consent boundary changed")
    frames = {}
    for revision in sorted(revisions, key=lambda r: r.sequence):
        for frame in revision.packet.frames:
            key = (frame.start_ms, frame.end_ms)
            previous = frames.get(key)
            if previous is not None and not previous.provisional and frame.provisional:
                raise ValueError("provisional regression after final")
            if previous is not None and not previous.provisional and not frame.provisional and frame != previous:
                raise ValueError("conflicting final acoustic observation")
            frames[key] = frame
    ordered = tuple(frames[key] for key in sorted(frames))
    if len(ordered) > 128 or any(a.end_ms > b.start_ms for a,b in zip(ordered, ordered[1:])):
        raise ValueError("overlap or unbounded merged frames")
    asr = [(r.sequence,r.packet.transcript,r.packet.teacher_revision)
           for r in revisions if r.packet.transcript is not None]
    if asr and len({(text, rev) for _,text,rev in asr}) > 1:
        raise ValueError("teacher ASR revision conflict requires explicit review")
    latest = max(asr, default=None)
    return TimedEarPacket(source=first.source, consent_scope=first.consent_scope,
                          frames=ordered, provenance=first.provenance,
                          transcript=latest[1] if latest else None,
                          teacher_revision=latest[2] if latest else None)
