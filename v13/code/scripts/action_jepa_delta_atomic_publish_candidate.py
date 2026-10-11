#!/usr/bin/env python3
"""Review-only atomic wrapper for the existing exact Action-JEPA delta restore.

The original verifier still owns array/NPZ/source correctness; this wrapper
only controls destination publication. Incomplete restores stay private to a
scratch directory. Never claim utility/receiver authority from storage success.
"""
import argparse
import ctypes
import errno
import json
import os
from pathlib import Path
import tempfile

AT_FDCWD=-100
RENAME_NOREPLACE=1


def rename_noreplace(src,dest):
    """Linux/Android atomic rename of a directory only if target is absent.

    Unlike os.rename, refuses even an existing empty destination directory.
    Fail closed on platforms without the primitive.
    """
    libc=ctypes.CDLL(None,use_errno=True)
    call=getattr(libc,'renameat2',None)
    if call is None:raise OSError(errno.ENOSYS,'Atomic no-replace rename unavailable')
    call.argtypes=(ctypes.c_int,ctypes.c_char_p,ctypes.c_int,ctypes.c_char_p,ctypes.c_uint)
    call.restype=ctypes.c_int
    status=call(AT_FDCWD,os.fsencode(src),AT_FDCWD,os.fsencode(dest),RENAME_NOREPLACE)
    if status:
        code=ctypes.get_errno()
        raise OSError(code,os.strerror(code),str(dest))


def restore_atomic(base,archives,destination,restore_impl=None):
    """Private full restore + validation, then single atomic directory install."""
    if not archives:raise ValueError('At least one closed delta archive required')
    destination=Path(destination).absolute()
    if destination.exists() or destination.is_symlink():
        raise ValueError('Refusing existing exact restored evidence destination')
    if destination.parent.is_symlink():
        raise ValueError('Parent symlink refused')
    destination.parent.mkdir(parents=True,exist_ok=True)
    # Existing code is imported only on a real run, never as a validation claim.
    if restore_impl is None:
        from action_jepa_delta_storage import restore as restore_impl
    with tempfile.TemporaryDirectory(prefix='.v13-delta-restore-',dir=destination.parent) as temporary:
        staging=Path(temporary)/'verified'
        result=restore_impl(base,archives,staging)
        if (not isinstance(result,dict) or result.get('exact_original_npz_bytes_restored') is not True
            or result.get('receiver_authority') != 0
            or type(result.get('completed_rows')) is not int or result['completed_rows'] <= 0
            or not staging.is_dir() or staging.is_symlink()):
            raise ValueError('Existing delta restoration did not produce verified closed state')
        for item in staging.rglob('*'):
            if item.is_symlink():raise ValueError('Symlink inside restored evidence refused')
        # Do not create partial final directory. Atomic no-replace POSIX rename.
        rename_noreplace(staging,destination)
        fd=os.open(destination.parent,os.O_RDONLY)
        try:os.fsync(fd)
        finally:os.close(fd)
    return result | {'publication':'ATOMIC_DIRECTORY_NOREPLACE',
                     'native_model_launched':False,'phone_measured':False,
                     'semantic_quality_proven':False,'canonical_gate_pass':False}


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--base-capture',required=True)
    ap.add_argument('--delta',action='append',required=True)
    ap.add_argument('--out',required=True)
    args=ap.parse_args()
    result=restore_atomic(args.base_capture,args.delta,args.out)
    print(json.dumps(result,sort_keys=True))


if __name__=='__main__':main()
