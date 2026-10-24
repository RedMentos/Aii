"""Offline bootstrap from already persisted Run42/44 GitHub source artifacts.

Reads only two pinned existing project artifacts; never fetches or executes remote code.
"""
import base64
import hashlib
import io
import tarfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PARENT=ROOT.parent

def blob(data):
    return hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()

def install(dst,data,expected):
    if blob(data)!=expected:raise RuntimeError('dependency hash mismatch: '+str(dst))
    if dst.exists():
        if dst.read_bytes()!=data:raise RuntimeError('existing vendor file differs: '+str(dst))
        return
    dst.parent.mkdir(parents=True,exist_ok=True)
    dst.write_bytes(data)

def bootstrap():
    source=PARENT/'sleep-context-utility-run44/evidence/run44-source-evidence.tar.xz.b64'
    with tarfile.open(fileobj=io.BytesIO(base64.b64decode(source.read_bytes(),validate=False)),mode='r:xz') as tf:
        f=tf.extractfile('scripts/sleep_context_utility.py')
        if f is None:raise RuntimeError('Run44 source missing')
        data=f.read()
    install(ROOT/'vendor/run44/sleep_context_utility.py',data,'5b7a7a1f8db720c78feaa6e2efd9f1d0e110ad8b')
    p=PARENT/'sleep-ttt-lineage-run42/scripts/sleep_ttt_lineage_candidate.py'
    install(ROOT/'sleep-ttt-lineage-run42/scripts/sleep_ttt_lineage_candidate.py',p.read_bytes(),
            '8dcd4b36cbe58f06ea330a510f1735b37f0ad600')
    return {'run44':'5b7a7a1f8db720c78feaa6e2efd9f1d0e110ad8b','run42':'8dcd4b36cbe58f06ea330a510f1735b37f0ad600'}

if __name__=='__main__':print(bootstrap())
