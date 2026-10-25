"""A2 frozen text-teacher reference consumption with immutable source binding.

A2 is a read-only reference lane backed by the pinned C2 semantic encoder in
Age-0. This validates a measured feature packet; it does not create features,
train a native encoder, grant truth authority, or establish phone proof.
"""
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import stat

TEACHER_DIM = 3072
MAX_FEATURE_BYTES = 512 * 1024


def validated_teacher_feature(store, home, reference, *, generation, encoder_revision, event_id):
    if not isinstance(reference, dict):
        raise ValueError('A2 reference must be a packet')
    if (reference.get('producer_component') != 'A2_FROZEN_REFERENCE'
            or reference.get('brain_generation_id') != generation
            or reference.get('event_id') != event_id
            or reference.get('modality') != 'text'
            or reference.get('stop_gradient') is not True
            or reference.get('teacher_truth_authority') is not False
            or reference.get('encoder_revision') != encoder_revision
            or type(reference.get('feature_dim')) is not int
            or reference['feature_dim'] != TEACHER_DIM):
        raise ValueError('A2 identity/authority/revision mismatch')
    ref = reference.get('source_ref')
    if (not isinstance(ref, dict) or reference.get('provenance') != [ref]
            or ref.get('modality') != 'text'):
        raise ValueError('A2 source lineage mismatch')
    source_text = store.read_source(ref)  # fails closed on revoked/altered source
    if not source_text:
        raise ValueError('A2 empty source')
    rel = reference.get('feature_path')
    if not isinstance(rel, str):
        raise ValueError('A2 missing feature path')
    parts = PurePosixPath(rel).parts
    if (len(parts) != 3 or parts[:2] != ('data', 'blobs')
            or not parts[2].startswith('a2_') or not parts[2].endswith('.json')
            or not all(c.isascii() and (c.isalnum() or c in '._-') for c in parts[2])
            or rel != 'data/blobs/' + parts[2] or '\\' in rel):
        raise ValueError('A2 feature path outside frozen reference lane')
    home = Path(home)
    # Open every path component relative to the preceding verified directory.
    # This avoids a parent-symlink swap between a path check and file open.
    homefd = os.open(home, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        datafd = os.open('data', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=homefd)
        try:
            blobfd = os.open('blobs', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=datafd)
            try:
                fd = os.open(parts[2], os.O_RDONLY | os.O_NOFOLLOW, dir_fd=blobfd)
                try:
                    info = os.fstat(fd)
                    if not stat.S_ISREG(info.st_mode) or not 0 < info.st_size <= MAX_FEATURE_BYTES:
                        raise ValueError('A2 feature not bounded regular file')
                    with os.fdopen(os.dup(fd), 'rb') as stream:
                        raw = stream.read(MAX_FEATURE_BYTES + 1)
                finally:
                    os.close(fd)
            finally:
                os.close(blobfd)
        finally:
            os.close(datafd)
    finally:
        os.close(homefd)
    if len(raw) > MAX_FEATURE_BYTES or hashlib.sha256(raw).hexdigest() != reference.get('feature_sha256'):
        raise ValueError('A2 feature SHA256 mismatch')
    obj = json.loads(raw)
    if not isinstance(obj, dict) or set(obj) != {'embedding'} or not isinstance(obj['embedding'], list):
        raise ValueError('A2 feature schema invalid')
    values = obj['embedding']
    if (len(values) != TEACHER_DIM or any(type(x) not in (float, int) or not math.isfinite(x) for x in values)
            or sum(float(x)*float(x) for x in values) < 1e-16):
        raise ValueError('A2 feature nonfinite, zero or wrong dimension')
    return values
