"""Bounded mutable PCM16 ownership and best-effort in-memory zeroization.

This clears caller-owned mutable buffers and Python-owned sample arrays. It
cannot guarantee erasure of copies inside Python, NumPy, or ONNX Runtime; the
Android capture provider must still use a native buffer lifecycle and be tested.
"""
from __future__ import annotations

from array import array
from contextlib import contextmanager
import sys


def pcm16_byte_view(pcm):
    """Return a contiguous byte view of bytes-like little-endian mono PCM16."""
    if type(pcm) not in (bytes, bytearray, memoryview):
        raise ValueError("expected PCM16 bytes, bytearray, or memoryview")
    try:
        view = memoryview(pcm)
        if view.ndim != 1 or not view.contiguous:
            raise ValueError("PCM16 buffer must be one-dimensional and contiguous")
        view = view.cast("B")
    except (TypeError, ValueError):
        raise ValueError("PCM16 buffer must be one-dimensional and contiguous") from None
    if view.nbytes % 2:
        raise ValueError("expected complete little-endian mono PCM16 samples")
    return view


@contextmanager
def pcm16_sample_buffer(pcm):
    """Yield a mutable int16 copy and overwrite it on every exit path."""
    view = pcm16_byte_view(pcm)
    samples = array("h")
    if samples.itemsize != 2:
        raise RuntimeError("this platform does not expose 16-bit array('h') samples")
    samples.frombytes(view)
    if sys.byteorder != "little":
        samples.byteswap()
    try:
        yield samples
    finally:
        if samples:
            samples[:] = array("h", [0]) * len(samples)


def pcm16_zeroization_status(pcm):
    """Describe exactly which caller-owned buffer can be overwritten."""
    if type(pcm) is bytearray:
        return "ZEROIZED_CALLER_BUFFER"
    if (type(pcm) is memoryview and not pcm.readonly
            and pcm.ndim == 1 and pcm.contiguous):
        return "ZEROIZED_WRITABLE_VIEW"
    return "IMMUTABLE_INPUT_NOT_ZEROIZED"


def zeroize_pcm16_buffer(pcm):
    """Overwrite a caller-owned bytearray or writable contiguous memoryview."""
    if type(pcm) is bytearray:
        pcm[:] = bytes(len(pcm))
        return True
    if (type(pcm) is memoryview and not pcm.readonly
            and pcm.ndim == 1 and pcm.contiguous):
        view = pcm.cast("B")
        view[:] = bytes(view.nbytes)
        return True
    return False
