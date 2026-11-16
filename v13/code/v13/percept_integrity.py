"""A1->A5 source-exact boundary check; no model inference or truth promotion.

A segment is only admitted when its text and character interval exactly tile
the current source. This protects B/C and memory from malformed A1 spans.
"""
import hashlib

def validate_a1_tiling(source, segments):
    if not isinstance(source, str) or not isinstance(segments, list):
        raise ValueError("A1_SOURCE_OR_SEGMENTS_INVALID")
    if not source and segments:
        raise ValueError("A1_EMPTY_SOURCE_WITH_SEGMENTS")
    pos = 0
    for seg in segments:
        if not isinstance(seg, dict) or not isinstance(seg.get("source_ref"), dict):
            raise ValueError("A1_SEGMENT_REF_INVALID")
        ref = seg["source_ref"]
        a, b = ref.get("char_start"), ref.get("char_end")
        if type(a) is not int or type(b) is not int or a != pos or b <= a or b > len(source):
            raise ValueError("A1_SEGMENT_INTERVAL_INVALID")
        if seg.get("text") != source[a:b]:
            raise ValueError("A1_SEGMENT_SOURCE_MISMATCH")
        pos = b
    if pos != len(source):
        raise ValueError("A1_SOURCE_NOT_FULLY_TILED")
    return {"status": "SOURCE_EXACT", "segments": len(segments),
            "source_chars": len(source),
            "source_sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
            "authority": "INTEGRITY_ONLY_NOT_TRUTH"}
