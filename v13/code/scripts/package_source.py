#!/usr/bin/env python3
"""Create a verified, runnable source checkpoint without models or user data."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import zipfile

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',required=True);parser.add_argument('--phone-install',action='store_true',help='Runnable code/plans without historical raw proof collections');args=parser.parse_args()
    app=Path(__file__).resolve().parents[1];out=Path(args.out).expanduser().resolve()
    if out.is_relative_to(app):raise SystemExit('Keep the output ZIP outside the source tree')
    files=sorted(p for p in app.rglob('*') if p.is_file() and '__pycache__' not in p.parts and not p.name.endswith('.pyc') and not any(x.startswith('.') for x in p.relative_to(app).parts) and p.name!='WORKSPACE_FILES.json')
    if args.phone_install:
        def needed(p):
            relative=p.relative_to(app)
            return (relative.parts[0] in {'v13','scripts','tests','specs'}
                    or len(relative.parts)==1
                    or relative.parts[:2]==('docs','canon')
                    or (relative.parts[0]=='docs' and len(relative.parts)==2 and p.suffix=='.md')
                    or relative.as_posix() in {'docs/proofs/native_norm_shadow_port.cpp',
                                               'docs/proofs/native_norm_poll_policy.hpp',
                                               'docs/proofs/causal-output-lifecycle-20261009/native-fixture-proposal.json'})
        files=[p for p in files if needed(p)]
    # Freeze each file once: live proof collectors may publish a newer version
    # while this checkpoint is being packed. Hash exactly the bytes we archive.
    for capture_attempt in range(3):
        try:
            contents={str(p.relative_to(app)):p.read_bytes() for p in files}
            break
        except FileNotFoundError as exc:
            missing=Path(exc.filename)
            # SQLite removes/recreates its transient coordination files while a
            # proof finishes. Recapture the entire inventory; never silently
            # drop a source file or accept partially frozen contents.
            if (capture_attempt==2 or not missing.is_relative_to(app)
                or missing.relative_to(app).parts[:2]!=('docs','proofs')
                or not missing.name.endswith(('-shm','-wal'))):raise
            files=[p for p in files if p!=missing]
    hashes={path:hashlib.sha256(data).hexdigest() for path,data in contents.items()}
    manifest=app/'WORKSPACE_FILES.json';manifest_bytes=(json.dumps({'schema_version':1,'files':hashes},indent=2)+'\n').encode()
    if not args.phone_install:manifest.write_bytes(manifest_bytes)
    out.parent.mkdir(parents=True,exist_ok=True);tmp=out.with_suffix('.partial')
    with zipfile.ZipFile(tmp,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in files+[manifest]:
            # Source bytes are already frozen. A collector may remove a completed
            # fixture directory while compression runs; never stat live paths
            # after capture. Fixed ZIP timestamps also avoid claiming file age.
            info=zipfile.ZipInfo('V13-Phone/'+str(p.relative_to(app)));info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=(0o100755 if p.suffix=='.sh' else 0o100644)<<16
            relative=str(p.relative_to(app))
            z.writestr(info,manifest_bytes if p==manifest else contents[relative])
    with zipfile.ZipFile(tmp) as z:
        if z.testzip():raise SystemExit('ZIP CRC failed')
        for path,h in hashes.items():
            if hashlib.sha256(z.read('V13-Phone/'+path)).hexdigest()!=h:raise SystemExit('ZIP hash mismatch: '+path)
    os.replace(tmp,out)
    print(json.dumps({'zip':str(out),'files':len(files)+1,'bytes':out.stat().st_size,'sha256':hashlib.sha256(out.read_bytes()).hexdigest()}))

if __name__=='__main__':main()
