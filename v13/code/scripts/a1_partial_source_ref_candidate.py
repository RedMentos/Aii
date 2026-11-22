"""Frozen-safe A1 excerpt SourceRef candidate; SHADOW software adapter only.

The current production A1 segmenters emit offsets relative to their input text.
This adapter preserves their exact segmentation while translating validated
excerpt-local spans into original Store SourceRef coordinates. It intentionally
does not modify frozen cognition.py/episodes.py or register a Runtime consumer.
"""
from v13.cognition import segments as _segments
from v13.episodes import text_segments as _text_segments


def _validate(text, ref, width):
    if type(text) is not str or type(ref) is not dict:
        raise ValueError("text must be str and source_ref must be dict")
    if type(width) is not int or width <= 0:
        raise ValueError("segment width must be a positive integer")
    start, end = ref.get("char_start"), ref.get("char_end")
    if type(start) is not int or type(end) is not int or start < 0 or end < start:
        raise ValueError("invalid excerpt SourceRef bounds")
    if end - start != len(text):
        raise ValueError("excerpt text length differs from SourceRef span")
    for key in ("source_id", "sha256", "modality"):
        if not isinstance(ref.get(key), str) or not ref[key]:
            raise ValueError("incomplete excerpt SourceRef provenance")
    return start


def _translate(text, ref, width, mode):
    start = _validate(text, ref, width)
    if mode not in ("fixed", "event"):
        raise ValueError("unknown A1 segment mode")
    # Existing frozen functions are used without altering their bytes or
    # leaking the parent offset into their local segmentation heuristics.
    local_ref = dict(ref, char_start=0, char_end=len(text))
    pieces = (_text_segments(text, local_ref, width) if mode == "event"
              else _segments(text, local_ref, width, "fixed"))
    result = []
    cursor = 0
    for piece in pieces:
        local = piece["source_ref"]
        lo, hi = local["char_start"], local["char_end"]
        if (type(lo) is not int or type(hi) is not int or
                lo != cursor or hi <= lo or hi > len(text) or
                piece["text"] != text[lo:hi]):
            raise ValueError("A1 segmenter produced non-contiguous source spans")
        translated = dict(piece)
        translated["source_ref"] = dict(ref, char_start=start + lo, char_end=start + hi)
        result.append(translated)
        cursor = hi
    if cursor != len(text):
        raise ValueError("A1 segmenter failed to tile the excerpt")
    return result


def segment_excerpt(text, ref, width, mode="fixed"):
    """Candidate A1 fixed/event segmentation with absolute Store offsets."""
    return _translate(text, ref, width, mode)


def event_segments_excerpt(text, ref, width=240):
    """Candidate direct event segmenter with absolute Store offsets."""
    return _translate(text, ref, width, "event")
