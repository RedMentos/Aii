"""A4 salience adapter for the existing consent-bound RAW EAR acoustic_window.

No PCM, transcripts or speaker identities are persisted or forwarded.
Caller must already have a consented audio_percept.acoustic_window result.
"""
import math

def modulate_audio_attention(attention, event_id, acoustic, previous=None):
    if acoustic.get('schema') != 'v13.a5.audio-acoustic/1' or acoustic.get('modality') != 'audio_raw_ear':
        raise ValueError('not an A5 acoustic observation')
    if not acoustic.get('source_ref', {}).get('source_id'):
        raise ValueError('missing source provenance')
    f = acoustic.get('features') or {}
    rms, peak = f.get('rms'), f.get('peak')
    if any(not isinstance(v, (int, float)) or not math.isfinite(v) or not 0 <= v <= 1 for v in (rms, peak)):
        raise ValueError('invalid acoustic features')
    old = (previous or {}).get('features', {}).get('rms', rms)
    if not isinstance(old, (int, float)) or not math.isfinite(old) or not 0 <= old <= 1:
        raise ValueError('invalid prior acoustic features')
    novelty = min(1., 3. * abs(rms - old))
    interrupt = min(1., peak * .5)
    return attention.modulate(event_id, sal={'novelty': novelty, 'external_interrupt': interrupt})
