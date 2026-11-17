"""Consent-gated, source-bound RAW EAR acoustic timeline; no microphone access or ASR requirement."""
import math

FEATURES = ('rms', 'pitch_hz', 'voicing', 'speech_probability')

def build_audio_percept(source_ref, frames, *, consent, source_kind='authorized_audio', final=False, teacher_text=None):
    if consent is not True:
        raise PermissionError('explicit audio observation consent required')
    if not isinstance(source_ref, dict) or not source_ref.get('source_id') or not source_ref.get('sha256'):
        raise ValueError('source-bound reference required')
    if source_kind not in ('authorized_audio', 'synthetic_fixture'):
        raise ValueError('unsupported source kind')
    if not isinstance(frames, list) or not frames:
        raise ValueError('nonempty acoustic frames required')
    out = []
    last_end = -1
    for frame in frames:
        if not isinstance(frame, dict) or not all(k in frame for k in ('start_ms', 'end_ms', *FEATURES)):
            raise ValueError('incomplete frame')
        start, end = frame['start_ms'], frame['end_ms']
        if not all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) for v in (start, end)) or start < 0 or end <= start or start < last_end:
            raise ValueError('invalid or overlapping timestamp')
        last_end = end
        values = {k: frame[k] for k in FEATURES}
        if any(not isinstance(v, (int, float)) or isinstance(v, bool) or not math.isfinite(v) for v in values.values()):
            raise ValueError('nonfinite acoustic feature')
        if values['rms'] < 0 or values['pitch_hz'] < 0 or any(not 0 <= values[k] <= 1 for k in ('voicing', 'speech_probability')):
            raise ValueError('out-of-range acoustic feature')
        out.append({'start_ms': start, 'end_ms': end, 'acoustics': values, 'non_speech': frame.get('non_speech', 'unknown')})
    if teacher_text is not None and (not isinstance(teacher_text, str) or len(teacher_text) > 4096):
        raise ValueError('invalid optional teacher transcript')
    return {'modality': 'audio', 'source_ref': dict(source_ref), 'source_kind': source_kind,
            'provenance': 'FINAL' if final else 'PROVISIONAL', 'frames': out,
            'teacher_asr': {'text': teacher_text, 'authority': 'UNVERIFIED_TEACHER_HINT'} if teacher_text is not None else None,
            'action_authority': 0, 'learning_authority': 0, 'capture_performed': False}
