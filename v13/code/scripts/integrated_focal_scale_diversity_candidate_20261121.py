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
CROSS_SCALE_RULE = "DISJOINT_SAME_SOURCE_SPANS_ONLY"

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
        b"    return (isinstance(ref,dict)\n"
        b"            and isinstance(ref.get('source_id'),str) and bool(ref.get('source_id'))\n"
        b"            and isinstance(ref.get('sha256'),str) and len(ref['sha256'])==64\n"
        b"            and isinstance(ref.get('modality'),str) and bool(ref.get('modality'))\n"
        b"            and type(ref.get('char_start')) is int and type(ref.get('char_end')) is int\n"
        b"            and ref['char_start']>=0 and ref['char_end']>ref['char_start'])\n\n"
        b"def _has_disjoint_source_evidence(candidate, admitted):\n"
        b"    left=candidate.get('source_refs');right=admitted.get('source_refs')\n"
        b"    if not isinstance(left,(list,tuple)) or not left or not isinstance(right,(list,tuple)) or not right:\n"
        b"        return False\n"
        b"    shared=False\n"
        b"    for a in left:\n"
        b"        if not _valid_source_span(a):return False\n"
        b"        for b in right:\n"
        b"            if not _valid_source_span(b):return False\n"
        b"            if a['source_id'] != b['source_id']:continue\n"
        b"            shared=True\n"
        b"            if a['sha256'] != b['sha256'] or a['modality'] != b['modality']:return False\n"
        b"            if a['char_start'] < b['char_end'] and b['char_start'] < a['char_end']:return False\n"
        b"    return shared\n\n"
        b"def _scale_aware_redundancy(candidate, admitted):\n"
        b"    overlap=relevance(candidate['text'],admitted['text'])\n"
        b"    if (candidate['source_kind'] in BODY and admitted['source_kind'] in BODY\n"
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
        b"        red=max([_scale_aware_redundancy(c,a) for a in active "
        b"if c['text'] and a['text']],default=0.)\n",
        1,
    )
    if result.count(b"_scale_aware_redundancy(c,a)") != 1:
        raise ValueError("focal redundancy consumer was not uniquely patched")
    compile(result, "v13/focal.py", "exec")
    return result
