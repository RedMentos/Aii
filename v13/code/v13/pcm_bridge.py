"""Deterministic PCM-to-timed-source bridge; no microphone or permission grants."""
import json
from .raw_ear_pcm import pcm16le_frames

def pcm_to_timed_source(pcm: bytes, sample_rate_hz: int, *, start_ms: int = 0, frame_ms: int = 20, final: bool = True) -> str:
    """Produce strict A3 timed-audio schema, for authorized Store insertion by caller.

    RMS and ZCR are acoustic evidence; pitch and speech probability remain 0
    (unknown), never fabricated. Features are mean RMS and mean ZCR.
    """
    if type(start_ms) is not int or not 0 <= start_ms <= 86400000:
        raise ValueError('invalid start_ms')
    if type(final) is not bool:
        raise ValueError('invalid final flag')
    frames = pcm16le_frames(pcm, sample_rate_hz, frame_ms)
    if not frames:
        raise ValueError('empty PCM observation')
    end_ms = start_ms + frames[-1].end_ms
    if end_ms > 86400000:
        raise ValueError('timestamp overflow')
    rms = sum(f.rms for f in frames) / len(frames)
    zcr = sum(f.zero_crossing_rate for f in frames) / len(frames)
    data = {'features': [rms,zcr], 'final': final, 'start_ms': start_ms,
            'end_ms': end_ms, 'sample_rate_hz': sample_rate_hz,
            'acoustic': {'rms': rms, 'pitch_hz': 0.0, 'speech_probability': 0.0}}
    return json.dumps(data, sort_keys=True, separators=(',', ':'), allow_nan=False)
