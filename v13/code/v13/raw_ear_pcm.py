"""Bounded nonsemantic PCM16LE frame features; no microphone/ASR/permission."""
from array import array
from dataclasses import dataclass
import math
import sys

@dataclass(frozen=True)
class AcousticFrame:
    start_ms: int
    end_ms: int
    rms: float
    peak: float
    zero_crossing_rate: float
    sample_count: int

def pcm16le_frames(pcm: bytes, sample_rate_hz: int, frame_ms: int = 20,
                   *, max_duration_ms: int = 60000) -> tuple[AcousticFrame, ...]:
    """Mono signed PCM16LE, bounded and frame-aligned; relative timestamps."""
    if type(sample_rate_hz) is not int or not 8000 <= sample_rate_hz <= 192000:
        raise ValueError("sample_rate_hz out of range")
    if type(frame_ms) is not int or not 5 <= frame_ms <= 100:
        raise ValueError("frame_ms out of range")
    if type(max_duration_ms) is not int or not 1 <= max_duration_ms <= 60000:
        raise ValueError("max_duration_ms out of range")
    if sample_rate_hz * frame_ms % 1000:
        raise ValueError("frame duration must be sample-aligned")
    if not isinstance(pcm, bytes) or len(pcm) % 2:
        raise ValueError("PCM must be complete signed 16-bit bytes")
    samples_per_frame = sample_rate_hz * frame_ms // 1000
    if len(pcm) > 2 * (sample_rate_hz * max_duration_ms // 1000):
        raise ValueError("PCM duration exceeds limit")
    if len(pcm) % (2 * samples_per_frame):
        raise ValueError("partial PCM frame")
    samples = array('h')
    samples.frombytes(pcm)
    if sys.byteorder != 'little':
        samples.byteswap()
    frames = []
    for offset in range(0, len(samples), samples_per_frame):
        chunk = samples[offset:offset + samples_per_frame]
        rms = math.sqrt(sum((x / 32768.0) ** 2 for x in chunk) / len(chunk))
        peak = max(abs(x / 32768.0) for x in chunk)
        crossings = sum((a < 0) != (b < 0) for a, b in zip(chunk, chunk[1:]))
        index = offset // samples_per_frame
        frames.append(AcousticFrame(index * frame_ms, (index + 1) * frame_ms,
                                    rms, peak, crossings / max(1, len(chunk) - 1),
                                    len(chunk)))
    return tuple(frames)
