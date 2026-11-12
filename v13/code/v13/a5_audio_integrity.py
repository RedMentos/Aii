"""Strict integrity check for synthetic timed RAW EAR A5 candidates.

Non-authoritative: no Android permission, model inference, or canonical A5.
"""
import hashlib
import json
import math
from .a5_audio_source_gate import checked_audio_view
from .a3_runtime_adapter import FeatureObservation


def checked_audio_integrity_view(store, candidate, source_ref):
    """Recheck stored source and derived feature digest before SHADOW consumption."""
    view = checked_audio_view(store, candidate, source_ref)
    raw = store.read_source(source_ref)
    data = json.loads(raw, parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite JSON')))
    features = data['features']
    if not isinstance(features, list) or len(features) != 2 or any(
        type(x) not in (int, float) or not math.isfinite(x) for x in features
    ):
        raise ValueError('invalid RAW EAR feature vector')
    if not (0 <= features[0] <= 1 and 0 <= features[1] <= 1):
        raise ValueError('RAW EAR features out of range')
    if features[0] != data['acoustic']['rms']:
        raise ValueError('RMS feature and acoustic evidence mismatch')
    obs = FeatureObservation(source_ref['source_id'], 'synthetic_audio', tuple(features), True, '')
    digest = hashlib.sha256(obs.canonical_bytes()).hexdigest()
    if candidate['source']['feature_sha256'] != digest:
        raise ValueError('derived feature digest mismatch')
    embedding = candidate.get('a3', {}).get('embedding')
    if not isinstance(embedding, list) or not (1 <= len(embedding) <= 4096) or any(
        type(x) not in (int, float) or not math.isfinite(x) for x in embedding
    ):
        raise ValueError('invalid A3 embedding')
    score = candidate.get('a4', {}).get('score')
    if type(score) not in (int, float) or not math.isfinite(score) or not 0 <= score <= 1:
        raise ValueError('invalid A4 salience')
    if store.read_source(source_ref) != raw:
        raise PermissionError('source changed or revoked during integrity check')
    view['feature_sha256'] = digest
    return view
