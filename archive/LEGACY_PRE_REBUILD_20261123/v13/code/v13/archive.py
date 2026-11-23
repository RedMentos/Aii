"""WP-U4 §9.1 Archive / §9.5 "Exact Provenance wird günstig archiviert": cold sources are stored compressed, never lost.

A blob (data/blobs/<sha256>) is archived to data/blobs/<sha256>.z (zlib, lossless) only when every live source row
that shares its hash is cold:
  - older than ARCHIVE_DAYS,
  - of an archivable kind: a COLD_KIND (raw user turns, retrieval views, output contexts, body states, interrupted
    drafts), or a HUMAN_DECISION whose memories are all inactive (superseded/forgotten values),
  - not the value, key or event source of an active memory.
Never archived: images, fixed output rules, memory keys, human decisions still in use, unknown kinds.
The hash stays the identity: Store.read_source decompresses in memory and re-checks sha256, so SourceRefs, export,
backup (copies data/blobs) and :doctor work unchanged. Archiving is skipped when compression saves < MIN_SAVING.
Restore writes the plain blob back. Nothing here deletes content; :forget still removes both forms.
"""
import zlib
from .common import now,digest,atomic_write

KEY='U4_ARCHIVE';REVISION='u4-archive-v1'
ARCHIVE_DAYS=30.     # BOOT: a source must be this old before it may go cold
MIN_BYTES=512        # BOOT: smaller blobs are not worth a compressed copy
MIN_SAVING=.10       # BOOT: archive only when the compressed file is at least 10 % smaller
LEVEL=9;BATCH=256
COLD_KINDS=frozenset({'USER','RETRIEVAL_VIEW','C3_OUTPUT_CONTEXT','C3_SAME_CAUSAL_LIVE_OBSERVATION','BODY_STATE','PROVISIONAL_INTERRUPTED_OUTPUT'})

def _dir(store):return store.home/'data/blobs'

def _hot_ids(store):
    """Source ids an active memory still needs (its value, its key, or the event it came from)."""
    hot=set()
    for m in store.rows("SELECT m.source_id,e.source_id AS event_source FROM memories m LEFT JOIN events e ON e.id=m.event_id WHERE m.active=1"):
        hot.update(x for x in (m['source_id'],m['event_source']) if x)
    return hot  # memory keys (MEMORY_KEY) are not an archivable kind at all

def candidates(store,clock=now,limit=BATCH):
    """Hashes whose every live source row is cold, oldest first."""
    cutoff=clock()-ARCHIVE_DAYS*86400;hot=_hot_ids(store)
    inactive={r['source_id'] for r in store.rows("SELECT source_id FROM memories GROUP BY source_id HAVING MAX(active)=0")}
    out=[];seen=set()
    for r in store.rows("SELECT hash,MIN(created) AS first,MAX(created) AS last,MAX(bytes) AS bytes FROM sources WHERE deleted=0 GROUP BY hash HAVING MAX(created)<? AND MAX(bytes)>=? ORDER BY last LIMIT ?",(cutoff,MIN_BYTES,limit*4)):
        h=r['hash']
        if h in seen:continue
        seen.add(h);rows=store.rows("SELECT id,kind FROM sources WHERE hash=? AND deleted=0",(h,))
        if any(x['id'] in hot for x in rows):continue
        if not all(x['kind'] in COLD_KINDS or (x['kind']=='HUMAN_DECISION' and x['id'] in inactive) for x in rows):continue
        if not (_dir(store)/h).is_file():continue  # already archived or missing
        out.append(h)
        if len(out)>=limit:break
    return out

def archive_blob(store,h):
    p=_dir(store)/h;b=p.read_bytes()
    if digest(b)!=h:return 'HASH_MISMATCH'
    z=zlib.compress(b,LEVEL)
    if len(z)>(1-MIN_SAVING)*len(b):return 'NO_SAVING'
    zp=p.with_name(h+'.z');atomic_write(zp,z)
    if digest(zlib.decompress(zp.read_bytes()))!=h:
        zp.unlink(missing_ok=True);return 'VERIFY_FAILED'
    p.unlink();return 'ARCHIVED'

def restore(store,h):
    p=_dir(store)/h;zp=p.with_name(h+'.z')
    if p.is_file():return 'ALREADY_PLAIN'
    if not zp.is_file():raise ValueError('Kein Archiv für diese Quelle')
    b=store.blob_bytes(h)
    if digest(b)!=h:raise ValueError('Archiv-Hash falsch')
    atomic_write(p,b);zp.unlink();store.log('archive_restore',None,{'hash':h});return 'RESTORED'

def run(store,clock=now,limit=BATCH):
    """Sleep C step: archive up to `limit` cold blobs. Returns counts and saved bytes."""
    counts={};saved=0
    for h in candidates(store,clock,limit):
        size=(_dir(store)/h).stat().st_size
        try:res=archive_blob(store,h)
        except OSError:res='IO_ERROR'
        counts[res]=counts.get(res,0)+1
        if res=='ARCHIVED':saved+=size-(_dir(store)/(h+'.z')).stat().st_size
    st,v=store.state(KEY,None);st=st or {'revision':REVISION,'runs':0,'archived':0,'saved_bytes':0}
    st['runs']+=1;st['archived']+=counts.get('ARCHIVED',0);st['saved_bytes']+=saved;st['last']={'at':clock(),'counts':counts,'saved_bytes':saved}
    store.set_state(KEY,st,expected=v);store.log('archive_run',None,{'counts':counts,'saved_bytes':saved})
    return {'counts':counts,'saved_bytes':saved}

def report(store):
    d=_dir(store);plain=[p for p in d.iterdir() if p.is_file() and len(p.name)==64] if d.is_dir() else []
    arch=[p for p in d.iterdir() if p.is_file() and p.name.endswith('.z')] if d.is_dir() else []
    st=store.state(KEY,None)[0] or {}
    return {'revision':REVISION,'plain_blobs':len(plain),'archived_blobs':len(arch),'archived_bytes':sum(p.stat().st_size for p in arch),
            'history':{k:st.get(k) for k in ('runs','archived','saved_bytes','last')},
            'policy':{'archive_days':ARCHIVE_DAYS,'min_bytes':MIN_BYTES,'min_saving':MIN_SAVING,'cold_kinds':sorted(COLD_KINDS)},
            'claim_limit':'Lossless compression of cold source blobs; identity stays the sha256, nothing is deleted'}

def operator_command(r,args):
    """:archive [status|run|restore <source_id>]"""
    from .common import dumps
    if not args or args==['status']:return dumps(report(r.store))
    if args==['run']:return dumps(run(r.store))
    if args[0]=='restore' and len(args)==2:
        row=r.store.one('SELECT hash FROM sources WHERE id=?',(args[1],))
        if not row:raise ValueError('Unbekannte Quelle')
        return dumps({'status':restore(r.store,row['hash'])})
    raise ValueError(':archive [status|run|restore <Quelle>]')
