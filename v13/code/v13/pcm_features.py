"""CPU-only PCM16LE framing for RAW EAR; not ASR or voice detection."""
from __future__ import annotations
from array import array
from math import sqrt
import sys
from .raw_ear_contract import AcousticFrame, build_raw_ear

def extract_pcm_frames(pcm16le: bytes, sample_rate_hz: int, frame_ms: int = 20):
    """Return bounded timed RMS frames; probability fields zero mean unknown."""
    if type(frame_ms) is not int or not 10 <= frame_ms <= 100:
        raise ValueError("frame_ms must be integer 10..100")
    if type(sample_rate_hz) is not int or sample_rate_hz not in (8000, 16000, 24000, 48000):
        raise ValueError("unsupported sample rate")
    if not isinstance(pcm16le, bytes) or not pcm16le or len(pcm16le) % 2:
        raise ValueError("PCM16LE byte pairs required")
    n = len(pcm16le) // 2
    duration = n * 1000 // sample_rate_hz
    if not 1 <= duration <= 120000:
        raise ValueError("duration outside RAW EAR bounds")
    step = sample_rate_hz * frame_ms // 1000
    if (n + step - 1) // step > 4096:
        raise ValueError("too many frames")
    values = array("h")
    values.frombytes(pcm16le)
    if sys.byteorder != "little":
        values.byteswap()
    out = []
    for start in range(0, n, step):
        end = min(start + step, n)
        start_ms, end_ms = start * 1000 // sample_rate_hz, end * 1000 // sample_rate_hz
        if end_ms <= start_ms:
            continue
        chunk = values[start:end]
        rms = sqrt(sum((int(v) / 32768.0) ** 2 for v in chunk) / len(chunk))
        out.append(AcousticFrame(start_ms, end_ms, rms, None, 0.0, 0.0))
    return tuple(out)

def build_pcm_raw_ear(source_ref: str, pcm16le: bytes, sample_rate_hz: int, *,
                      frame_ms: int = 20, provisional: bool = True):
    """Source-hashed acoustic packet from PCM bytes; no capture permission implied."""
    return build_raw_ear(source_ref, pcm16le, sample_rate_hz,
                         extract_pcm_frames(pcm16le, sample_rate_hz, frame_ms),
                         provisional=provisional)
