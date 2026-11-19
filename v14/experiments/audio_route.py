"""V14 A5 -> B/C observation route, offline only; no Android or tool authority."""
from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Callable

@dataclass(frozen=True)
class AudioObservation:
    source_id: str
    consent_id: str
    source_digest: str
    start_ms: int
    end_ms: int
    frame_count: int
    feature_digest: str
    peak_max: float
    rms_mean: float
    provisional: bool
    authority: str = 'OBSERVATION_ONLY'

def route_timed_audio(packets, source, *, b_detail: Callable, b_gist: Callable, c_observer: Callable):
    """Validate A5 first, then fan out immutable, source-bound observation.

    Consumers are callbacks supplied by caller; this function grants no action,
    learning or model-weight rights. No PCM or transcript is forwarded.
    """
    from v14.experiments.timed_perception import validate_packet_sequence
    validate_packet_sequence(packets, source)
    if not packets:
        raise ValueError('empty observation cannot be routed')
    canonical = json.dumps(packets, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
    observation = AudioObservation(
        source_id=source.source_id, consent_id=source.consent_id,
        source_digest=source.pcm_sha256,
        start_ms=packets[0]['time_start_ms'], end_ms=packets[-1]['time_end_ms'],
        frame_count=len(packets), feature_digest=sha256(canonical).hexdigest(),
        peak_max=max(p['peak'] for p in packets),
        rms_mean=sum(p['rms'] * (p['sample_end'] - p['sample_start']) for p in packets) / source.sample_count,
        provisional=source.provisional)
    return {'observation': observation,
            'B1_DETAIL': b_detail(observation),
            'B2_GIST': b_gist(observation),
            'C_OBSERVER': c_observer(observation)}
