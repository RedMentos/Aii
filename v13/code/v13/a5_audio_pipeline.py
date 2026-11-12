"""Synthetic PCM -> SQLite -> A3/A4 -> A5 -> source-bound B/C SHADOW.

No Android microphone, OS consent verification, canonical A5 or action authority.
"""
import json
import math
from .pcm_store_observer import observe_stored_pcm
from .a5_audio_envelope import from_timed_a3
from .a5_audio_integrity import checked_audio_integrity_view


def checked_projector_audio_view(store, projector, candidate, source_ref):
    """Recompute A3 output against supplied projector, not an authenticated model."""
    view = checked_audio_integrity_view(store, candidate, source_ref)
    raw = store.read_source(source_ref)
    data = json.loads(raw)
    expected = projector.predict(data['features'])
    actual = candidate['a3']['embedding']
    if len(expected) != len(actual) or any(
        not math.isfinite(v) or abs(v - a) > 1e-10
        for v, a in zip(expected, actual)
    ):
        raise ValueError('A3 embedding does not match supplied projector')
    if store.read_source(source_ref) != raw:
        raise PermissionError('source changed during projector verification')
    view['a3_recomputed'] = True
    view['projector_revision_authenticated'] = False
    return view


def observe_pcm_checked(runtime, projector, pcm, sample_rate_hz, *, consent=False,
                        start_ms=0, frame_ms=20, final=True):
    """Compose existing V13 contracts; real SQLite source and synthetic PCM."""
    observed = observe_stored_pcm(
        runtime, projector, pcm, sample_rate_hz, consent=consent,
        start_ms=start_ms, frame_ms=frame_ms, final=final,
    )
    ref = observed['source_ref']
    candidate = from_timed_a3(observed['observation'])
    view = checked_projector_audio_view(runtime.store, projector, candidate, ref)
    if view.get('android_action_allowed') is not False or view.get('runtime_activated') is not False:
        raise PermissionError('SHADOW view must not gain runtime or Android authority')
    return {'source_ref': ref, 'candidate': candidate, 'view': view}
