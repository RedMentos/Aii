"""A4 acoustic novelty from validated A5 frames; deterministic SHADOW observation.

No speech identity, semantics, capture permission, or learning authority.
"""
from math import isfinite


def acoustic_salience(frames, *, max_events=8, threshold=0.15):
    """Select loudness onsets by positive RMS delta; preserve temporal order.

    Frames must already have passed audio_views acoustic integrity checks.
    Silence and steady tones yield no spurious onset after the first frame.
    """
    if type(max_events) is not int or not 1 <= max_events <= 32:
        raise ValueError('invalid max_events')
    if type(threshold) not in (int, float) or not isfinite(threshold) or not 0 <= threshold <= 1:
        raise ValueError('invalid threshold')
    if not isinstance(frames, list) or len(frames) > 4096:
        raise ValueError('bounded frames required')
    prev = 0.0
    candidates = []
    for i, frame in enumerate(frames):
        rms = frame['rms']
        if type(rms) not in (int, float) or not isfinite(rms) or not 0 <= rms <= 1:
            raise ValueError('invalid RMS')
        delta = max(0.0, rms-prev)
        if delta >= threshold and delta > 0:
            candidates.append((delta, i, frame))
        prev = rms
    selected = sorted(sorted(candidates, key=lambda x:(-x[0],x[1]))[:max_events],key=lambda x:x[1])
    return [{'start_ms':f['start_ms'],'end_ms':f['end_ms'],
             'onset_delta':round(delta,8),'rms':f['rms']}
            for delta,_,f in selected]
