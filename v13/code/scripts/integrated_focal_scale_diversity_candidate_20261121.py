"""Source-span-aware C4 redundancy for the two independent body roles.

B1_DETAIL and B2_GIST can summarize overlapping language while citing distinct
parts of the same source. Cross-scale redundancy is discounted only when both
offers carry same-source, same-digest, same-modality, non-overlapping spans.
Same-role, overlapping, cross-source and body/memory redundancy keep the full
existing penalty. This is a conservative evidence-span rule, not a semantic
calibration claim.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

SOURCE_FOCAL_GIT_BLOB = "a0588a768cc91266ef02243bcfda2e631860d8ad"
CROSS_SCALE_RULE = "DISJOINT_SAME_SOURCE_SPANS_AND_LOW_LEXICAL_OVERLAP"

BODY_MARKER = b"BODY=('B1_DETAIL','B2_GIST')\n"
REDUNDANCY_LINE = (
    b"        red=max([relevance(c['text'],a['text']) for a in active "
    b"if c['text'] and a['text']],default=0.)\n"
)
ADMIT_MARKER = b"def admit(cands,capacity,threshold,interrupt=BOOT['sal_interrupt']):\n"


def git_blob_sha1(raw: bytes) -> str:
    header = b"blob " + str(len(raw)).encode("ascii") + b"\0"
    return hashlib.sha1(header + raw).hexdigest()


def apply_staged_focal(code_dir: Path, raw: bytes) -> bytes:
    """Patch only the C4 redundancy comparison in the pinned staged FocalLoop."""
    code_dir = Path(code_dir).resolve(strict=True)
    source = code_dir / "v13" / "focal.py"
    if source.is_symlink() or not source.is_file():
        raise ValueError("frozen focal.py missing or unsafe")
    if git_blob_sha1(source.read_bytes()) != SOURCE_FOCAL_GIT_BLOB:
        raise ValueError("frozen focal.py source changed; review a new overlay")
    if b"direct_action='SOURCE_COPY'" not in raw:
        raise ValueError("base stage is not the reviewed arithmetic/C5 candidate")
    if raw.count(BODY_MARKER) != 1 or raw.count(REDUNDANCY_LINE) != 1:
        raise ValueError("focal scale-diversity anchors changed")
    if b"SCALE_AWARE_C4_RULE" in raw or b"_scale_aware_redundancy" in raw:
        raise ValueError("focal source-span rule already present")

    rule = BODY_MARKER + b"SCALE_AWARE_C4_RULE = 'DISJOINT_SAME_SOURCE_SPANS_ONLY'\n"
    result = raw.replace(BODY_MARKER, rule, 1)

    helper = (
        b"def _valid_source_span(ref):\n"
        b"    digest = ref.get('sha256') if isinstance(ref,dict) else None\n"
        b"    return (isinstance(ref,dict)\n"
        b"            and isinstance(ref.get('source_id'),str) and bool(ref['source_id'].strip())\n"
        b"            and isinstance(digest,str) and len(digest)==64\n"
        b"            and digest == digest.lower()\n"
        b"            and all(ch in '0123456789abcdef' for ch in digest)\n"
        b"            and isinstance(ref.get('modality'),str) and bool(ref['modality'].strip())\n"
        b"            and type(ref.get('char_start')) is int and type(ref.get('char_end')) is int\n"
        b"            and ref['char_start']>=0 and ref['char_end']>ref['char_start'])\n\n"
        b"def _source_signature(refs):\n"
        b"    if not isinstance(refs,(list,tuple)) or not refs:\n"
        b"        return None\n"
        b"    signature=None;spans=[]\n"
        b"    for ref in refs:\n"
        b"        if not _valid_source_span(ref):\n"
        b"            return None\n"
        b"        current=(ref['source_id'],ref['sha256'],ref['modality'])\n"
        b"        if signature is None:\n"
        b"            signature=current\n"
        b"        elif current != signature:\n"
        b"            return None\n"
        b"        spans.append((ref['char_start'],ref['char_end']))\n"
        b"    return signature,spans\n\n"
        b"def _has_disjoint_source_evidence(candidate, admitted):\n"
        b"    left=_source_signature(candidate.get('source_refs'))\n"
        b"    right=_source_signature(admitted.get('source_refs'))\n"
        b"    if left is None or right is None or left[0] != right[0]:\n"
        b"        return False\n"
        b"    return all(a_end <= b_start or b_end <= a_start\n"
        b"               for a_start,a_end in left[1]\n"
        b"               for b_start,b_end in right[1])\n\n"
        b"def _scale_aware_redundancy(candidate, admitted, threshold):\n"
        b"    overlap=relevance(candidate['text'],admitted['text'])\n"
        b"    # Disjoint evidence alone is insufficient: high lexical overlap still\n"
        b"    # competes under the original C4 penalty, even across the two body roles.\n"
        b"    if (overlap < threshold\n"
        b"            and candidate['source_kind'] in BODY and admitted['source_kind'] in BODY\n"
        b"            and candidate['source_kind'] != admitted['source_kind']\n"
        b"            and _has_disjoint_source_evidence(candidate,admitted)):\n"
        b"        return 0.0\n"
        b"    return overlap\n\n\n"
    )
    if result.count(ADMIT_MARKER) != 1:
        raise ValueError("focal admission function anchor changed")
    result = result.replace(ADMIT_MARKER, helper + ADMIT_MARKER, 1)
    result = result.replace(
        REDUNDANCY_LINE,
        b"        red=max([_scale_aware_redundancy(c,a,threshold) for a in active "
        b"if c['text'] and a['text']],default=0.)\n",
        1,
    )
    if result.count(b"_scale_aware_redundancy(c,a,threshold)") != 1:
        raise ValueError("focal redundancy consumer was not uniquely patched")
    compile(result, "v13/focal.py", "exec")
    return result
