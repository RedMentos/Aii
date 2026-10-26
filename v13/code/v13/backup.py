"""Checksummed snapshots and offline restore with a restart-recoverable swap journal."""
import json
import os
from pathlib import Path,PurePosixPath
import shutil
import sqlite3
import tarfile
import tempfile
from .common import uid,atomic_write,dumps,file_hash,digest
import zlib

# Store.blob_bytes has the same 64-MiB decompression ceiling.
MAX_SOURCE_BLOB_BYTES = 64 * 1024 * 1024

def _verify_live_source_blobs(stage, db):
    """Require the snapshot DB's live source hashes to be readable from this stage.

    A self-consistent archive manifest cannot prove SQLite-to-blob closure:
    a missing blob can simply be omitted from that manifest. Verify the actual
    source table independently before publishing or restoring a snapshot.
    """
    blobs = stage / 'data' / 'blobs'
    for (h,) in db.execute('SELECT DISTINCT hash FROM sources WHERE deleted=0'):
        if not isinstance(h, str) or len(h) != 64 or any(c not in '0123456789abcdef' for c in h):
            raise ValueError('Source-Blob hash invalid in snapshot database')
        plain = blobs / h
        if plain.is_file():
            try:
                good = file_hash(plain) == h
            except OSError as exc:
                raise ValueError('Source-Blob unreadable: ' + h) from exc
            if not good:
                raise ValueError('Source-Blob hash mismatch: ' + h)
            continue
        compressed = blobs / (h + '.z')
        if not compressed.is_file():
            raise ValueError('Source-Blob missing: ' + h)
        try:
            if compressed.stat().st_size > MAX_SOURCE_BLOB_BYTES + 65536:
                raise ValueError('Source-Blob compressed size exceeds bound: ' + h)
            dec = zlib.decompressobj()
            raw = dec.decompress(compressed.read_bytes(), MAX_SOURCE_BLOB_BYTES + 1)
        except (OSError, zlib.error) as exc:
            raise ValueError('Source-Blob archive unreadable: ' + h) from exc
        if (len(raw) > MAX_SOURCE_BLOB_BYTES or not dec.eof or dec.unconsumed_tail
                or dec.unused_data or digest(raw) != h):
            raise ValueError('Source-Blob archive corrupt or oversized: ' + h)

from .config import initialize
from .store import Store,SCHEMA_VERSION,migrate_database

def backup(store,destination=None):
    home=store.home;out=Path(destination) if destination else home/'backups'/('v13-'+uid('snapshot')+'.tar.gz')
    if out.exists():raise ValueError('Backup-Zieldatei existiert bereits')
    with tempfile.TemporaryDirectory(dir=home/'tmp',prefix='backup-') as tmp:
        stage=Path(tmp);db=stage/'data/db/brain.sqlite3';db.parent.mkdir(parents=True)
        # Keep the DB snapshot, blob/checkpoint/config copy and generation id
        # in one Store mutation boundary. Archive can still race outside that
        # mutex, so the copied stage is independently checked below.
        with store.mutex:
            target=sqlite3.connect(db)
            try:store.db.backup(target)
            finally:target.close()
            for name in ['data/blobs','checkpoints','config']:
                src=home/name
                if src.exists():shutil.copytree(src,stage/name)
            generation=store.generation_id
        snapshot=sqlite3.connect(db)
        try:_verify_live_source_blobs(stage,snapshot)
        finally:snapshot.close()
        hashes={str(p.relative_to(stage)):file_hash(p) for p in stage.rglob('*') if p.is_file()};atomic_write(stage/'backup_manifest.json',dumps({'format':1,'hashes':hashes,'models_included':False,'active_generation':generation}))
        out.parent.mkdir(parents=True,exist_ok=True)
        # Never reuse a predictable .partial or replace an existing backup.
        # Both names live in the destination directory, so the hardlink
        # publication is atomic and fails closed on unsupported filesystems.
        fd,pending_name=tempfile.mkstemp(prefix='.'+out.name+'.pending-',suffix='.tar.gz',dir=out.parent)
        pending=Path(pending_name)
        try:
            with os.fdopen(fd,'wb') as archive:
                with tarfile.open(fileobj=archive,mode='w:gz') as t:
                    for p in stage.rglob('*'):
                        if p.is_file():t.add(p,arcname=str(p.relative_to(stage)),recursive=False)
                archive.flush();os.fsync(archive.fileno())
            try:os.link(pending,out)
            except FileExistsError as exc:
                raise ValueError('Backup-Zieldatei existiert bereits') from exc
            # A successful backup must have both complete file bytes and a
            # persisted directory entry. Do not silently claim durability if
            # the destination filesystem rejects directory fsync.
            d=os.open(out.parent,os.O_RDONLY)
            try:os.fsync(d)
            finally:os.close(d)
        finally:pending.unlink(missing_ok=True)
    return out

def unpack_verified(path,stage,max_bytes):
    names=set();total=0
    with tarfile.open(path) as t:
        for m in t.getmembers():
            pp=PurePosixPath(m.name)
            if pp.is_absolute() or '..' in pp.parts or m.name in names or not m.isfile():raise ValueError('Unsicheres Backup-Mitglied')
            if not (m.name=='backup_manifest.json' or m.name.startswith(('data/db/','data/blobs/','checkpoints/','config/'))):raise ValueError('Unerlaubter Backup-Pfad')
            names.add(m.name);total+=m.size
            if total>max_bytes:raise ValueError('Backup überschreitet verfügbaren Speicher')
        t.extractall(stage,**({'filter':'data'} if hasattr(tarfile,'data_filter') else {}))
        # tarfile stops at the tar end marker. Drain the remaining gzip stream
        # to force CRC/ISIZE trailer verification before accepting the snapshot.
        # Bound unexpected trailing decompressed data (normal tar padding is tiny).
        trailing=0
        try:
            while True:
                chunk=t.fileobj.read(1<<20)
                if not chunk:break
                trailing+=len(chunk)
                if trailing>1<<20:raise ValueError('Backup hat unerwartete nachgestellte Daten')
        except (OSError,EOFError) as exc:
            raise ValueError('Backup-Gzip-Integrität ungültig') from exc
    m=json.loads((stage/'backup_manifest.json').read_text())
    if m.get('format')!=1 or set(m['hashes'])!=names-{'backup_manifest.json'}:raise ValueError('Backup-Manifest inkonsistent')
    for name,h in m['hashes'].items():
        if file_hash(stage/name)!=h:raise ValueError('Backup-Hash falsch: '+name)
    db=sqlite3.connect(stage/'data/db/brain.sqlite3',isolation_level=None)
    try:
        if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok' or db.execute('PRAGMA user_version').fetchone()[0] not in (1,SCHEMA_VERSION):raise ValueError('Backup-Datenbank ungültig')
        db.execute('PRAGMA foreign_keys=ON')
        # Hashes above authenticate the original archive. The verified staging copy
        # may then be upgraded transactionally before it replaces the live store.
        migrate_database(db)
        if db.execute('PRAGMA foreign_key_check').fetchall():raise ValueError('Backup-Fremdschlüssel ungültig')
        _verify_live_source_blobs(stage,db)
    finally:db.close()
    return m

def recover(home):
    journal=home/'restore_pending.json'
    if not journal.exists():return False
    j=json.loads(journal.read_text());stage=(home/j['stage']).resolve();old=(home/j['old']).resolve()
    if not stage.is_relative_to(home/'tmp') or not old.is_relative_to(home/'tmp'):raise ValueError('Restore-Journal-Pfad ungültig')
    # A journal with no staging directory is not proof that the swap finished:
    # keep it for explicit recovery instead of silently discarding intent.
    if not stage.is_dir():raise ValueError('Restore-Staging fehlt; Journal bleibt erhalten')
    names=['data/db','data/blobs','checkpoints','config']
    if not any((stage/name).exists() for name in names) and not old.is_dir():
        raise ValueError('Restore-Staging leer; Journal bleibt erhalten')
    for name in names:
        src=stage/name;dst=home/name;saved=old/name
        if not src.exists():continue
        if dst.exists() and not saved.exists():saved.parent.mkdir(parents=True,exist_ok=True);os.replace(dst,saved)
        if dst.exists():raise ValueError('Mehrdeutiger Restore-Zustand; Sicherheitskopie: '+str(old))
        dst.parent.mkdir(parents=True,exist_ok=True);os.replace(src,dst)
    journal.unlink();shutil.rmtree(stage,ignore_errors=True)
    return True

def recover_startup(home):
    if not (home/'restore_pending.json').exists():return
    # fcntl without opening/mutating a half-restored SQLite database.
    import fcntl
    with open(home/'data/coordinator.lock','a+') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);recover(home)

def restore(home,path):
    initialize(home);recover_startup(home);store=Store(home);stage=home/'tmp'/uid('restore');old=home/'tmp'/uid('pre_restore');stage.mkdir()
    try:
        unpack_verified(path,stage,shutil.disk_usage(home).free//2)
        safety=backup(store);store.close(release_lock=False)
        # Ensure empty checkpoint/blob directories are included in the swap too.
        for name in ['data/db','data/blobs','checkpoints','config']:(stage/name).mkdir(parents=True,exist_ok=True)
        atomic_write(home/'restore_pending.json',dumps({'stage':str(stage.relative_to(home)),'old':str(old.relative_to(home)),'safety_backup':str(safety)}));recover(home)
        return safety
    finally:
        store.close();
        if not (home/'restore_pending.json').exists():shutil.rmtree(stage,ignore_errors=True)
