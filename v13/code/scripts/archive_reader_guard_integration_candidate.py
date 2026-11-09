"""Materialize the archive guard only against the exact reviewed frozen sources."""
import hashlib
from pathlib import Path

PINS = {
    'archive.py': 'adbdd844c2275d527a689eda789a3f247759967677e573b92bf7af7ad68404bf',
    'store.py': 'fe66f92533b20738b5ec384e9d7c0b5ac8b4b4f658c6c1ad23792d813ff29980',
    'common.py': '0bc5a2a8eb5cc246d72410cdc1e1090dc838114999ca132a4ddac0104d03262a',
}
OLD_BLOB = b'''def archive_blob(store,h):
    p=_dir(store)/h;b=p.read_bytes()
    if digest(b)!=h:return 'HASH_MISMATCH'
    z=zlib.compress(b,LEVEL)
    if len(z)>(1-MIN_SAVING)*len(b):return 'NO_SAVING'
    zp=p.with_name(h+'.z');atomic_write(zp,z)
    if digest(zlib.decompress(zp.read_bytes()))!=h:
        zp.unlink(missing_ok=True);return 'VERIFY_FAILED'
    p.unlink();return 'ARCHIVED'
'''
NEW_BLOB = b'''def archive_blob(store,h,clock=now):
    from .archive_reader_guard_candidate import archive_blob as guarded_archive_blob
    return guarded_archive_blob(store,h,clock=clock)
'''
OLD_RUN = b'''        size=(_dir(store)/h).stat().st_size
        try:res=archive_blob(store,h)
        except OSError:res='IO_ERROR'
        counts[res]=counts.get(res,0)+1
        if res=='ARCHIVED':saved+=size-(_dir(store)/(h+'.z')).stat().st_size
'''
NEW_RUN = b'''        try:
            size=(_dir(store)/h).stat().st_size
            res=archive_blob(store,h,clock=clock)
            if res=='ARCHIVED':saved+=size-(_dir(store)/(h+'.z')).stat().st_size
        except OSError:res='IO_ERROR'
        counts[res]=counts.get(res,0)+1
'''


def build_sources(source_dir):
    source_dir = Path(source_dir)
    raw = {}
    for name, expected in PINS.items():
        value = (source_dir / name).read_bytes()
        if hashlib.sha256(value).hexdigest() != expected:
            raise ValueError('unsupported archive source: ' + name)
        raw[name] = value
    for old, new in ((OLD_BLOB, NEW_BLOB), (OLD_RUN, NEW_RUN)):
        if raw['archive.py'].count(old) != 1:
            raise ValueError('ambiguous archive candidate anchor')
        raw['archive.py'] = raw['archive.py'].replace(old, new, 1)
    return {'archive.py': raw['archive.py']}
