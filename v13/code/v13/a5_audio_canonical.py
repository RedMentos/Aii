"""Canonical V13 PerceptPacket from source-verified timed RAW EAR (SHADOW only).

No Android microphone permission, B/C inference or action authority.
"""
import math
from .contracts import packet, validate
from .a5_audio_pipeline import checked_projector_audio_view


def canonical_audio_percept(store, projector, candidate, source_ref, *, event_id, generation_id):
    """Revalidate final source/A3 and construct a genuine V13 contract packet."""
    if not isinstance(event_id, str) or not event_id or not isinstance(generation_id, str) or not generation_id:
        raise ValueError('event and generation identifiers required')
    view = checked_projector_audio_view(store, projector, candidate, source_ref)
    if view.get('authority') != 'observation_only' or view.get('android_action_allowed') is not False:
        raise PermissionError('non-observation source view')
    if view.get('body_inference_executed') is not False or view.get('runtime_activated') is not False:
        raise PermissionError('cannot promote runtime authority')
    if view.get('a3_recomputed') is not True:
        raise ValueError('A3 verification missing')
    score, embedding = view['a4_salience'], view['a3_embedding']
    if type(score) not in (float, int) or not math.isfinite(score) or not 0 <= score <= 1:
        raise ValueError('invalid A4 score')
    if not isinstance(embedding, list) or not embedding or len(embedding) > 4096 or any(
        type(x) not in (int, float) or not math.isfinite(x) for x in embedding
    ):
        raise ValueError('invalid A3 embedding')
    segment = {
        'kind': 'timed_raw_ear', 'status': 'SHADOW', 'final': True,
        'start_ms': view['time']['start_ms'], 'end_ms': view['time']['end_ms'],
        'sample_rate_hz': view['time']['sample_rate_hz'],
        'embedding': list(embedding), 'salience': float(score),
        'acoustic': dict(view['acoustic']), 'transcript': None,
        'source_sha256': view['source_sha256'],
        'feature_sha256': view['feature_sha256'],
        'projector_revision_authenticated': False,
        'android_action_allowed': False, 'body_inference_executed': False,
    }
    result = packet('PerceptPacket', 'A5_PERCEPTION', event_id, generation_id,
                    provenance=[dict(source_ref)], source_ref=dict(source_ref),
                    segments=[segment], modality='synthetic_audio')
    return validate('PerceptPacket', result)
