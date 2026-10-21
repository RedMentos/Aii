#!/usr/bin/env python3
"""Create a verified, runnable source checkpoint without models or user data.

Integrated 2026-10-12 from the reviewed streaming candidate
(`package_source_streaming_candidate.py`, 56 focused tests, file-selection
parity 908/908 full and 527/527 phone on the then-current tree). Streams in
1 MiB blocks instead of holding every file in memory, rejects symlinks and
source changes during packing, and never replaces an existing archive.
Preserves the `V13-Phone/` prefix and the `WORKSPACE_FILES.json` schema.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile
import zipfile

CHUNK=1 << 20
SKIP_EXT={'.gguf','.safetensors','.sqlite','.sqlite3','.db','.pyc','.ggml'}
SKIP_DIRS={'__pycache__','.git','.venv','venv','data','model-cache','models','cache'}
SKIP_NAMES={'WORKSPACE_FILES.json','.env','.netrc','credentials.json','token.json'}
PHONE_REQUIRED_FIXTURES={
    'docs/proofs/continuation-20261011/source-handoff-baseline/'+x
    for x in ('bodyview.py','cognition.py','runtime.py','manifest.json')
}
PHONE_REQUIRED_FIXTURES.update(
    'docs/proofs/continuation-20261011/native-firing-runtime-baseline/'+x
    for x in ('runners.py','memory_server.py','runtime.py','store.py','manifest.json'))
PHONE_REQUIRED_FIXTURES.update(
    'docs/proofs/continuation-20261011/approval-reader-runtime-baseline/'+x
    for x in ('runners.py','runtime.py','manifest.json'))
# Read by the phone selftest (test_b2_offer_candidate, test_calc_tool_producer_ablation); missing in the
# 2026-10-20 phone ZIP, which made setup.sh stop at selftest.
PHONE_REQUIRED_FIXTURES.update({
    'docs/proofs/continuation-20261013/b2-offer-candidate/cognition.patch',
    'docs/proofs/continuation-20261012/rule-transport-ablation/report.json'})


def _sha_stream(stream):
    h=hashlib.sha256()
    while block:=stream.read(CHUNK):h.update(block)
    return h.hexdigest()


def _fingerprint(stat):
    return (stat.st_dev,stat.st_ino,stat.st_size,stat.st_mtime_ns,stat.st_ctime_ns)


def eligible(root,p):
    relative=p.relative_to(root)
    if (any(part in SKIP_DIRS or part.startswith('.') or part.endswith('.checkpoint')
            or '.checkpoint.previous-' in part for part in relative.parts[:-1])
        or p.name in SKIP_NAMES or p.name.startswith('.') or p.suffix in SKIP_EXT
        or p.name.endswith(('-wal','-shm'))):return False
    if p.is_symlink():
        raise ValueError('Source tree contains symlinked candidate: '+str(relative))
    return p.is_file()


def phone_needed(p):
    relative=p.as_posix();parts=p.parts
    return (parts[0] in {'v13','scripts','tests','specs'}
            or len(parts)==1 or parts[:2]==('docs','canon')
            or (parts[0]=='docs' and len(parts)==2 and p.suffix=='.md')
            or relative in PHONE_REQUIRED_FIXTURES
            or relative in {'docs/proofs/native_norm_shadow_port.cpp',
                             'docs/proofs/native_norm_poll_policy.hpp',
                             'docs/proofs/causal-output-lifecycle-20261009/native-fixture-proposal.json'})


def inventory(root,phone_install):
    files=[p for p in root.rglob('*') if eligible(root,p)]
    if phone_install:
        missing=sorted(rel for rel in PHONE_REQUIRED_FIXTURES if not (root/rel).is_file())
        if missing:raise ValueError('Phone-install required fixture missing: '+', '.join(missing))
        files=[p for p in files if phone_needed(p.relative_to(root))]
    return sorted(files,key=lambda p:p.relative_to(root).as_posix())


def package(root,out,*,phone_install=False):
    root=Path(root)
    if root.is_symlink() or not root.is_dir():raise ValueError('Invalid source root')
    root=root.resolve();out=Path(out).absolute()
    if out.resolve().is_relative_to(root):raise ValueError('Output inside source tree')
    if out.exists() or out.is_symlink():raise ValueError('Refusing to replace existing archive')
    if out.parent.is_symlink():raise ValueError('Output directory must not be symlink')
    files=inventory(root,phone_install)
    if not files:raise ValueError('No source files to checkpoint')
    out.parent.mkdir(parents=True,exist_ok=True)
    tmp=None
    hashes={}
    source_states={}
    try:
        with tempfile.NamedTemporaryFile(dir=out.parent,delete=False,suffix='.partial') as staged:
            tmp=Path(staged.name)
        with zipfile.ZipFile(tmp,'w',zipfile.ZIP_DEFLATED,compresslevel=6,allowZip64=True) as archive:
            for p in files:
                rel=p.relative_to(root).as_posix()
                if not p.resolve().is_relative_to(root):raise ValueError('Source path escape')
                before=p.stat();h=hashlib.sha256()
                info=zipfile.ZipInfo('V13-Phone/'+rel)
                info.compress_type=zipfile.ZIP_DEFLATED
                info.external_attr=((0o100755 if p.suffix=='.sh' else 0o100644)<<16)
                with p.open('rb') as source,archive.open(info,'w',force_zip64=True) as dest:
                    while block:=source.read(CHUNK):
                        h.update(block);dest.write(block)
                after=p.stat()
                if _fingerprint(before)!=_fingerprint(after):
                    raise ValueError('Source changed during checkpoint: '+rel)
                source_states[rel]=_fingerprint(after)
                hashes[rel]=h.hexdigest()
            contents=(json.dumps({'schema_version':1,'files':hashes},indent=2)+'\n').encode()
            info=zipfile.ZipInfo('V13-Phone/WORKSPACE_FILES.json');info.compress_type=zipfile.ZIP_DEFLATED
            archive.writestr(info,contents)
        # Any added/removed files could make the ZIP look like a complete source tree.
        if [p.relative_to(root).as_posix() for p in inventory(root,phone_install)]!=list(hashes):
            raise ValueError('Source inventory changed during checkpoint')
        with zipfile.ZipFile(tmp) as archive:
            if archive.testzip() is not None:raise ValueError('ZIP CRC failure')
            for rel,expected in hashes.items():
                with archive.open('V13-Phone/'+rel) as source:
                    if _sha_stream(source)!=expected:
                        raise ValueError('ZIP source checksum mismatch: '+rel)
            if archive.read('V13-Phone/WORKSPACE_FILES.json')!=contents:
                raise ValueError('ZIP manifest mismatch')
        # Recheck just before the immutable publish, after ZIP validation: the
        # source tree can change while compressed bytes are being reread.
        if [p.relative_to(root).as_posix() for p in inventory(root,phone_install)]!=list(hashes):
            raise ValueError('Source inventory drifted during ZIP verification')
        for rel,expected_state in source_states.items():
            if _fingerprint((root/rel).stat())!=expected_state:
                raise ValueError('Source changed during ZIP verification: '+rel)
        # Crash-consistent local immutable checkpoint. Never overwrite a prior save.
        with tmp.open('rb') as source:os.fsync(source.fileno())
        os.link(tmp,out)
        out_hash=None
        with out.open('rb') as stream:out_hash=_sha_stream(stream)
        dir_fd=os.open(out.parent,os.O_RDONLY)
        try:os.fsync(dir_fd)
        finally:os.close(dir_fd)
        return {'status':'SOURCE_CHECKPOINT_LOCAL_ONLY','zip':str(out),'files':len(hashes)+1,
                'bytes':out.stat().st_size,'sha256':out_hash,
                'native_models_launched':False,'phone_measured':False,
                'canonical_gate_pass':False}
    finally:
        if tmp is not None:tmp.unlink(missing_ok=True)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);ap.add_argument('--out',required=True,type=Path)
    ap.add_argument('--phone-install',action='store_true');args=ap.parse_args()
    try:result=package(args.root,args.out,phone_install=args.phone_install)
    except ValueError as exc:raise SystemExit(str(exc))
    print(json.dumps(result,sort_keys=True))

if __name__=='__main__':main()
