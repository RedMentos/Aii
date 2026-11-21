"""Scale-aware C4 redundancy for the two independent body roles.

The existing FocalLoop admits B1_DETAIL and B2_GIST into one bounded coalition.
They operate at different representational scales; lexical overlap between
their summaries is therefore weaker evidence of duplication than overlap
between two offers from the same role. Same-role and body/memory redundancy
remain unchanged.

This is a staged candidate only. It never edits the historical V13 source.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

SOURCE_FOCAL_GIT_BLOB = "a0588a768cc91266ef02243bcfda2e631860d8ad"
CROSS_SCALE_REDUNDANCY_FACTOR = 0.15

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
    if b"CROSS_SCALE_REDUNDANCY_FACTOR" in raw or b"_scale_aware_redundancy" in raw:
        raise ValueError("focal scale-diversity overlay already present")

    constant = (
        BODY_MARKER
        + b"CROSS_SCALE_REDUNDANCY_FACTOR = 0.15  # ENG: uncalibrated cross-scale discount\n"
    )
    result = raw.replace(BODY_MARKER, constant, 1)

    helper = (
        b"def _scale_aware_redundancy(candidate, admitted):\n"
        b"    overlap=relevance(candidate['text'],admitted['text'])\n"
        b"    if (candidate['source_kind'] in BODY and admitted['source_kind'] in BODY\n"
        b"            and candidate['source_kind'] != admitted['source_kind']):\n"
        b"        return overlap * CROSS_SCALE_REDUNDANCY_FACTOR\n"
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
