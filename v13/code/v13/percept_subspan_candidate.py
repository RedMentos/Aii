"""EXPERIMENTAL A1/A5 source-bound segmentation, not wired into runtime.

Offsets are Python text character indices, as in Store.read_source(), not
UTF-8 byte offsets or grapheme-cluster indices.  The existing segmenters see
only zero-based local spans; this wrapper verifies those spans and maps them
back into the original immutable source.  No semantic interpretation or
authority is added.
"""
import re
import sys

from .cognition import segments
from .episodes import TEXT_MAX, _units


def source_segments(store, source_ref, width=240, mode='event'):
    """Read one exact SourceRef and return losslessly tiled, absolute refs.

    The existing event segmenter raises IndexError for a long leading
    whitespace-only unit.  Detect that exact precondition and produce marked
    fixed-width source-exact chunks instead.  Normal event and fixed results
    keep their existing boundary metadata and are unchanged at offset zero.
    """
    if not isinstance(source_ref, dict):
        raise ValueError('source_ref must be a text SourceRef')
    if (not isinstance(source_ref.get('source_id'), str) or not source_ref['source_id']
            or not isinstance(source_ref.get('sha256'), str)
            or re.fullmatch(r'[0-9a-f]{64}', source_ref['sha256']) is None
            or source_ref.get('modality') != 'text'):
        raise ValueError('invalid text source identity')
    start, end = source_ref.get('char_start'), source_ref.get('char_end')
    if type(start) is not int or type(end) is not int or not 0 <= start <= end:
        raise ValueError('invalid character offsets')
    if type(width) is not int or not 0 < width <= sys.maxsize:
        raise ValueError('width must be a positive integer')
    if mode not in ('fixed', 'event'):
        raise ValueError('mode must be fixed or event')

    # Store checks deletion, complete blob digest, decoding, and upper bound.
    text = store.read_source(source_ref)
    if len(text) != end - start:
        raise ValueError('source span length mismatch')
    if not text:
        return []

    try:
        long_whitespace = mode == 'event' and any(
            b - a > width * TEXT_MAX and text[a:b].isspace()
            for a, b in _units(text)
        )
    except OverflowError as exc:
        raise ValueError('width is too large') from exc
    actual_mode = 'fixed' if long_whitespace else mode
    # Zero-based local offsets are deliberate, independently of how a future
    # segmenter might interpret nonzero original-source offsets.
    local_ref = dict(source_ref, char_start=0, char_end=len(text))
    pieces = segments(text, local_ref, width, actual_mode)
    cursor = 0
    result = []
    for piece in pieces:
        r = piece['source_ref']
        a, b = r['char_start'], r['char_end']
        if (type(a) is not int or type(b) is not int or a != cursor
                or not a < b <= len(text) or piece['text'] != text[a:b]):
            raise ValueError('segmenter did not return an exact contiguous tiling')
        chunk = dict(piece, source_ref=dict(source_ref, char_start=start+a, char_end=start+b))
        if long_whitespace:
            chunk['candidate_fallback'] = 'EVENT_LONG_WHITESPACE_FIXED'
        result.append(chunk)
        cursor = b
    if cursor != len(text):
        raise ValueError('segmenter did not cover entire source span')
    return result
