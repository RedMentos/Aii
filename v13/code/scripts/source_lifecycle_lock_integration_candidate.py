"""Compose reviewed lifecycle/archiving fixes in a disposable source copy only."""
import hashlib
import importlib.util
from pathlib import Path

PINS = {
    'archive.py': 'adbdd844c2275d527a689eda789a3f247759967677e573b92bf7af7ad68404bf',
    'store.py': '40a387e24f8c4d9533bde484c1c82c1dd700517fa652469b4eea7b8b21a471bb',
    'common.py': '0bc5a2a8eb5cc246d72410cdc1e1090dc838114999ca132a4ddac0104d03262a',
    'memory.py': '8512bf0acd13b53970dba69e4a0fe30e81b1b3562fbe09b7771e4132e421fed8',
    'vision.py': 'd204393a1c17e9fbe068b11a096ae6977438c9fc3091474b45b28162d2b00e41',
    'archive_reader_guard_candidate.py': '84c06a9f5c0b6054f836615023822ff577984d3efe9ddfb07cae569ec124f438',
    'archive_stream_range_candidate.py': 'd2d021adcc844c1f321312cbfa60a4affb0a6b7fddc09e41a234cdf83f1eec98',
    'source_lifecycle_candidate.py': '3ace74b802d3e3e7340eabcccb03275d348deae2297fe8a1b4d2e1eab17d62b0',
}
GUARD_SCRIPT_SHA = '69a20b1c9e10882f80086c0620e8f87575c4559e7113ed19fd53002330be8747'
OLD_ARCHIVE_INTEGRATED_SHA = '3f421423ce890b90033470e15150b1ba9830642e6b5e92e61b654801602e90b4'

STORE_OLD = b'''        with self.mutex:
            if not p.exists():atomic_write(p,b)
            with self.tx() as c:c.execute("INSERT INTO sources VALUES (?,?,?,?,?,?,0)",(sid,h,kind,len(b),len(text),now()))
'''
STORE_NEW = b'''        with self.mutex:
            from .source_lifecycle_candidate import verify_or_create_blob
            verify_or_create_blob(p,b,h)
            with self.tx() as c:c.execute("INSERT INTO sources VALUES (?,?,?,?,?,?,0)",(sid,h,kind,len(b),len(text),now()))
'''
RECOVER_OLD = b'''    def _recover(self):
        with self.tx() as c:
'''
RECOVER_NEW = b'''    def _recover(self):
        # Both file publication and forget use the global Store write lock.
        # Recover privately staged crash leftovers before any sources are read.
        from .source_lifecycle_candidate import cleanup_pending
        cleanup_pending(self.home / 'data/blobs')
        with self.tx() as c:
'''

EVENT_OLD = b'''        path=self.home/'data/blobs'/h
        if not path.exists():atomic_write(path,b)
'''
EVENT_NEW = b'''        path=self.home/'data/blobs'/h
        from .source_lifecycle_candidate import verify_or_create_blob
        verify_or_create_blob(path,b,h)
'''
READ_SOURCE_OLD = b'''    def read_source(self,ref):
        r=self.one("SELECT * FROM sources WHERE id=?",(ref.get("source_id"),))
        if not r or r["deleted"] or r["hash"]!=ref.get("sha256"):raise ValueError("Dangling/gel\xc3\xb6schter SourceRef")
        b=self.blob_bytes(r["hash"])
        if digest(b)!=r["hash"]:raise ValueError("Source-Hash falsch")
        txt=b.decode()
        if not 0<=ref["char_start"]<=ref["char_end"]<=len(txt):raise ValueError("SourceRef au\xc3\x9ferhalb Text")
        return txt[ref["char_start"]:ref["char_end"]]
'''
READ_SOURCE_NEW = b'''    def read_source(self,ref):
        # Linearize the read against forget: validate the row and acquire the
        # exact file descriptor under the same Store lock used by revocation.
        # The potentially large read/decompression then happens outside the lock.
        with self.mutex:
            r=self.one("SELECT * FROM sources WHERE id=?",(ref.get("source_id"),))
            if not r or r["deleted"] or r["hash"]!=ref.get("sha256"):raise ValueError("Dangling/deleted SourceRef")
            if not all(hasattr(os,name) for name in ("O_DIRECTORY","O_NOFOLLOW","O_NONBLOCK")):
                raise OSError("safe source read primitives unavailable")
            directory=self.home/"data/blobs"
            dir_fd=os.open(directory,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
            fd=None
            try:
                try:
                    fd=os.open(r["hash"],os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=dir_fd)
                    compressed=False
                except FileNotFoundError:
                    try:
                        fd=os.open(r["hash"]+".z",os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=dir_fd)
                        compressed=True
                    except FileNotFoundError:
                        raise FileNotFoundError(str(directory/r["hash"]))
                import stat
                if not stat.S_ISREG(os.fstat(fd).st_mode):
                    raise ValueError("Source blob is not a regular file")
                source_file=os.fdopen(fd,"rb")
                fd=None
            finally:
                if fd is not None:os.close(fd)
                os.close(dir_fd)
        with source_file:
            raw=source_file.read()
        if compressed:
            import zlib
            d=zlib.decompressobj()
            try:b=d.decompress(raw,64*1024*1024)
            except zlib.error as exc:raise ValueError("Archive blob corrupt") from exc
            if d.unconsumed_tail or not d.eof:raise ValueError("Archive blob corrupt or too large")
        else:
            b=raw
        if digest(b)!=r["hash"]:raise ValueError("Source-Hash falsch")
        txt=b.decode()
        if not 0<=ref["char_start"]<=ref["char_end"]<=len(txt):raise ValueError("SourceRef out of bounds")
        return txt[ref["char_start"]:ref["char_end"]]
'''
MEMORY_OLD = b'''                source=self.s.one('SELECT hash FROM sources WHERE id=?',(sid,))
                if source and not self.s.one('SELECT id FROM sources WHERE hash=? AND deleted=0',(source['hash'],)):
                    (self.s.home/'data/blobs'/source['hash']).unlink(missing_ok=True)
                    (self.s.home/'data/blobs'/(source['hash']+'.z')).unlink(missing_ok=True)
'''
MEMORY_NEW = b'''                from .source_lifecycle_candidate import cleanup_unreferenced
                cleanup_unreferenced(self.s,sid)
'''
RESTORE_OLD = '''def restore(store,h):
    p=_dir(store)/h;zp=p.with_name(h+'.z')
    if p.is_file():return 'ALREADY_PLAIN'
    if not zp.is_file():raise ValueError('Kein Archiv für diese Quelle')
    b=store.blob_bytes(h)
    if digest(b)!=h:raise ValueError('Archiv-Hash falsch')
    atomic_write(p,b);zp.unlink();store.log('archive_restore',None,{'hash':h});return 'RESTORED'
'''.encode('utf-8')
RESTORE_NEW = b'''def restore(store,h):
    from .source_lifecycle_candidate import restore as guarded_restore
    return guarded_restore(store,h)
'''


def _replace_once(raw, old, new, label):
    if raw.count(old) != 1:
        raise ValueError('ambiguous lifecycle candidate anchor: ' + label)
    return raw.replace(old, new, 1)


def build_sources(source_dir):
    source_dir = Path(source_dir)
    raw = {}
    for name, expected in PINS.items():
        data = (source_dir / name).read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise ValueError('unsupported lifecycle source: ' + name)
        raw[name] = data
    script = source_dir.parent / 'scripts/archive_reader_guard_integration_candidate.py'
    if hashlib.sha256(script.read_bytes()).hexdigest() != GUARD_SCRIPT_SHA:
        raise ValueError('unsupported archive materializer')
    spec = importlib.util.spec_from_file_location('reviewed_archive_materializer', script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    raw['archive.py'] = module.build_sources(source_dir)['archive.py']
    if hashlib.sha256(raw['archive.py']).hexdigest() != OLD_ARCHIVE_INTEGRATED_SHA:
        raise ValueError('unexpected materialized archive revision')
    # The pinned V14 vision.py already owns transactional image-source publication,
    # registry updates and projector invalidation. Preserve those exact bytes instead
    # of replaying legacy V13 anchors that no longer exist in this source revision.
    for filename, old, new in (
            ('store.py', STORE_OLD, STORE_NEW),
            ('store.py', RECOVER_OLD, RECOVER_NEW),
            ('store.py', EVENT_OLD, EVENT_NEW),
            ('store.py', READ_SOURCE_OLD, READ_SOURCE_NEW),
            ('memory.py', MEMORY_OLD, MEMORY_NEW),
            ('archive.py', RESTORE_OLD, RESTORE_NEW)):
        raw[filename] = _replace_once(raw[filename], old, new, filename)
    archive_sha = hashlib.sha256(raw['archive.py']).hexdigest().encode()
    store_sha = hashlib.sha256(raw['store.py']).hexdigest().encode()
    guard = raw['archive_reader_guard_candidate.py']
    guard = _replace_once(guard, OLD_ARCHIVE_INTEGRATED_SHA.encode(), archive_sha, 'archive pin')
    guard = _replace_once(guard, PINS['store.py'].encode(), store_sha, 'guard store pin')
    raw['archive_reader_guard_candidate.py'] = guard
    raw['archive_stream_range_candidate.py'] = _replace_once(
        raw['archive_stream_range_candidate.py'], PINS['store.py'].encode(), store_sha, 'stream store pin')
    return {name: raw[name] for name in ('archive.py', 'store.py', 'memory.py', 'vision.py',
                                         'archive_reader_guard_candidate.py', 'archive_stream_range_candidate.py',
                                         'source_lifecycle_candidate.py')}
