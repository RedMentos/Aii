"""Compose reviewed lifecycle/archiving fixes in a disposable source copy only."""
import hashlib
import importlib.util
from pathlib import Path

PINS = {
    'archive.py': 'adbdd844c2275d527a689eda789a3f247759967677e573b92bf7af7ad68404bf',
    'store.py': 'fe66f92533b20738b5ec384e9d7c0b5ac8b4b4f658c6c1ad23792d813ff29980',
    'common.py': '0bc5a2a8eb5cc246d72410cdc1e1090dc838114999ca132a4ddac0104d03262a',
    'memory.py': '391668fff0b4ad3d7c36d5d7a9823055ff74821c10f71b945e87edaa62597484',
    'vision.py': '758cfc26387bd92da6c1c73d1d53224e76827ba70289c3c9e440f62557c209e5',
    'archive_reader_guard_candidate.py': '8771f937ed58dc010ebdf42ab8efcacf3e4c86875eb89609d2118d51d3cea6fb',
    'archive_stream_range_candidate.py': 'e869eaa278bf567463f7f4bbf41b2b5f5bae51c52f7034c2edcd9250d4f917e8',
    'source_lifecycle_candidate.py': 'ce787982ce2fea28b66c618d29395c7c2cb72286d4ea9a25db2ab7f9617b94bb',
}
GUARD_SCRIPT_SHA = 'a825149f711dead291890458a30c014652cfed26a8dbe85c60ea350e86a83a72'
OLD_ARCHIVE_INTEGRATED_SHA = '3f421423ce890b90033470e15150b1ba9830642e6b5e92e61b654801602e90b4'

STORE_OLD = b'''        if not p.exists():atomic_write(p,b)
        with self.tx() as c:c.execute("INSERT INTO sources VALUES (?,?,?,?,?,?,0)",(sid,h,kind,len(b),len(text),now()))
'''
STORE_NEW = b'''        with self.tx() as c:
            from .source_lifecycle_candidate import verify_or_create_blob
            verify_or_create_blob(p,b,h)
            c.execute("INSERT INTO sources VALUES (?,?,?,?,?,?,0)",(sid,h,kind,len(b),len(text),now()))
'''
EVENT_OLD = b'''        path=self.home/'data/blobs'/h
        if not path.exists():atomic_write(path,b)
'''
EVENT_NEW = b'''        path=self.home/'data/blobs'/h
        from .source_lifecycle_candidate import verify_or_create_blob
        verify_or_create_blob(path,b,h)
'''
MEMORY_OLD = b'''        src=self.s.one('SELECT hash FROM sources WHERE id=?',(sid,))
        if not self.s.one('SELECT id FROM sources WHERE hash=? AND deleted=0',(src['hash'],)):(self.s.home/'data/blobs'/src['hash']).unlink(missing_ok=True);(self.s.home/'data/blobs'/(src['hash']+'.z')).unlink(missing_ok=True)
'''
MEMORY_NEW = b'''        from .source_lifecycle_candidate import cleanup_unreferenced
        cleanup_unreferenced(self.s,sid)
'''
VISION_OLD = b'''def ingest(store,data,cfg=DEFAULTS,label=None):
    """Store image bytes as an IMAGE source (dedup by hash) and register its regions. Returns the image record."""
    im=decode(data,cfg);w,h=im.size;sha=digest(data);st=load(store)
    for rec in st['images'].values():
        if rec['ref']['sha256']==sha:return rec
    if len(st['images'])>=cfg['max_images']:raise ValueError('Zu viele Bilder im Lab; erst :image forget')
    path=store.home/'data/blobs'/sha
    if not path.exists():atomic_write(path,data)
    sid=uid('src')
    with store.tx() as c:c.execute('INSERT INTO sources VALUES (?,?,?,?,?,?,0)',(sid,sha,'IMAGE',len(data),0,now()))
    ref={'source_id':sid,'sha256':sha,'char_start':0,'char_end':0,'modality':'image'}
    rec={'ref':ref,'size':[w,h],'label':(label or '')[:80],'regions':boxes(w,h,cfg['grid']),'captions':[],'created':now()}
    st['images'][sid]=rec;save(store,st);return rec
'''
VISION_NEW = b'''def ingest(store,data,cfg=DEFAULTS,label=None):
    from .source_lifecycle_candidate import vision_ingest
    return vision_ingest(store,data,cfg,label)
'''
VISION_FORGET_OLD = b'''def forget(store,rec):
    st=load(store);sid=rec['ref']['source_id'];st['images'].pop(sid,None)
    if st.get('projector'):st['projector']['captions']={k:v for k,v in st['projector']['captions'].items() if k.split(':')[0]!=sid}
    save(store,st)
    with store.tx() as c:c.execute('UPDATE sources SET deleted=1 WHERE id=?',(sid,))
    if not store.one('SELECT id FROM sources WHERE hash=? AND deleted=0',(rec['ref']['sha256'],)):(store.home/'data/blobs'/rec['ref']['sha256']).unlink(missing_ok=True)
    return {'forgotten':sid}
'''
VISION_FORGET_NEW = b'''def forget(store,rec):
    from .source_lifecycle_candidate import vision_forget
    return vision_forget(store,rec)
'''
VISION_STATE_OLD = b'''def load(store):return store.state(KEY,None)[0] or {'revision':REVISION,'images':{},'projector':None,'last':None}
def save(store,st):store.set_state(KEY,st)
'''
VISION_STATE_NEW = b'''def load(store):
    from .source_lifecycle_candidate import load_vision_state
    return load_vision_state(store)
def save(store,st):
    from .source_lifecycle_candidate import save_vision_state
    save_vision_state(store,st)
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
    for filename, old, new in (
            ('store.py', STORE_OLD, STORE_NEW),
            ('store.py', EVENT_OLD, EVENT_NEW),
            ('memory.py', MEMORY_OLD, MEMORY_NEW),
            ('vision.py', VISION_OLD, VISION_NEW),
            ('vision.py', VISION_FORGET_OLD, VISION_FORGET_NEW),
            ('vision.py', VISION_STATE_OLD, VISION_STATE_NEW),
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
