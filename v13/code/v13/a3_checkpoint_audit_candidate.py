"""Read-only A3 checkpoint structure audit; never authorizes inference/promotion.

Bounded ZIP inspection before NumPy deserialization. This is a candidate only:
runtime remains frozen, and provenance/teacher truth cannot be inferred from an NPZ.
"""
import io
import os
import stat
import zipfile
import numpy as np

RAW_DIM = 512
LATENT_DIM = 16
TEACHER_DIM = 3072
STEM = "utf8-signed-byte-ngrams-1-3-v1"
MAX_ARCHIVE = 16 * 1024 * 1024
MAX_MEMBER = 8 * 1024 * 1024
MAX_TOTAL = 16 * 1024 * 1024
SHAPES = {
    "projector": (RAW_DIM, LATENT_DIM),
    "reconstruction_decoder": (LATENT_DIM, RAW_DIM),
    "teacher_basis": (LATENT_DIM, TEACHER_DIM),
    "teacher_mean": (TEACHER_DIM,),
    "input_mean": (RAW_DIM,),
}
REQUIRED = frozenset((*SHAPES, "support", "support_floor", "stem"))

def audit(path):
    """Return non-authoritative metadata or raise ValueError; do not load weights into runtime."""
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or not 0 < info.st_size <= MAX_ARCHIVE:
            raise ValueError("invalid checkpoint file size/type")
        with os.fdopen(fd, "rb", closefd=False) as f:
            blob = f.read(MAX_ARCHIVE + 1)
        if len(blob) != info.st_size:
            raise ValueError("checkpoint changed while reading")
    finally:
        os.close(fd)
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        names = z.namelist()
        if len(names) != len(set(names)) or set(names) != {x + ".npy" for x in REQUIRED}:
            raise ValueError("unexpected or duplicate checkpoint members")
        if any(m.file_size > MAX_MEMBER or m.file_size < 1 or m.flag_bits & 1
               for m in z.infolist()):
            raise ValueError("oversized or encrypted checkpoint member")
        if sum(m.file_size for m in z.infolist()) > MAX_TOTAL:
            raise ValueError("oversized expanded checkpoint")
    with np.load(io.BytesIO(blob), allow_pickle=False) as data:
        arrays = {name: data[name] for name in REQUIRED}
    for name, shape in SHAPES.items():
        a = arrays[name]
        if a.shape != shape or a.dtype.kind != "f" or a.dtype.itemsize not in (4, 8):
            raise ValueError("invalid A3 array shape/dtype: " + name)
        if not np.isfinite(a).all():
            raise ValueError("nonfinite A3 array: " + name)
    support = arrays["support"]
    if (support.ndim != 2 or support.shape[1] != RAW_DIM or
        not 1 <= support.shape[0] <= 2048 or support.dtype.kind != "f" or
        support.dtype.itemsize not in (4, 8) or not np.isfinite(support).all()):
        raise ValueError("invalid support matrix")
    floor = arrays["support_floor"]
    if floor.shape != () or floor.dtype.kind != "f" or not np.isfinite(floor).all() or not 0 <= float(floor) <= 1:
        raise ValueError("invalid support floor")
    stem = arrays["stem"]
    if stem.shape != () or stem.dtype.kind != "U" or str(stem) != STEM:
        raise ValueError("invalid raw stem")
    return {
        "schema": "v13.a3.checkpoint_audit/1",
        "status": "STRUCTURE_ONLY",
        "raw_dim": RAW_DIM,
        "latent_dim": LATENT_DIM,
        "teacher_dim": TEACHER_DIM,
        "support_rows": int(support.shape[0]),
        "runtime_admission_authorized": False,
        "teacher_truth_authority": False,
        "device_verified": False,
    }
