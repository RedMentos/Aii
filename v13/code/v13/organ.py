"""Organ checkpoint (:organ, WP-AGE0b): save and restore what belongs to ONE model organ, not only its weight file.

PR #27 point 4 (GPT, 22.10.): learning can also break heads, adapters, bridges and stored states; a copy of the GGUF
alone cannot restore them, and the existing weight rollback (Store.rollback) is LIFO over all components, so one organ
cannot be put back while another organ has newer updates.

An organ = one model role (B1_DETAIL, B2_GIST, C3_LANGUAGE, C2_CONTROL, ...). Its members:
  model       serving spec (model id, exact revision, sha256) and IH-H21 bridge key; referenced by hash, never copied
  components  active generation components whose encoder_role is the role or that depend on its revision
              (e.g. b1_predictor, b2_predictor, output_adapter, route ...), artifact copied with sha256
  bridges     b3/<SENDER>_TO_<RECEIVER>.json manifests that name the role, copied
  assets      slot assets of the role (agi/slots: kind, revision, dataset ref; metadata only)
snapshot   only while idle (best: after :stillstand), so no job writes in between.
check      per member IDENTICAL / CHANGED / MISSING / ADDED and whether the model revision is still the same.
restore    needs the same model revision as at snapshot time (else: first :body rollback, or recalibrate); writes a
           NEW generation in which only this organ's components and bridges are put back, all other organs stay as
           they are. Closes LIFO rollback (last_weight_update_id=None): an older global rollback would otherwise undo
           the organ restore silently. Not covered: optimizer state of offline trainers, GGUF files, memories
           (memory is append-only by design), states of heads that live outside the generation.
"""
import json
import contextlib
import os
import re
import shutil
import time
from pathlib import Path
from .common import atomic_write,digest,dumps,file_hash,uid
from .bodyport import bridge_key,direction_roles
from .models import ROLES,OPTIONAL_ROLES

REVISION='v13-organ-checkpoint-v1'
DIR='organs'
MODEL_ROLES=frozenset(ROLES)|frozenset(OPTIONAL_ROLES)
SNAPSHOT_ID=re.compile(r'organ_[0-9a-f]{32}\Z')


def _require_role(role):
    # The operator supplies this string. Never use arbitrary role text in a path.
    if type(role) is not str or role not in MODEL_ROLES:
        raise ValueError('Unbekannte Organ-Rolle')
    return role


def _organ_root(r):
    root=r.home/DIR
    # A symlink would redirect even a correctly spelled role outside the
    # intended checkpoint namespace.
    if root.is_symlink() or not root.resolve().is_relative_to(r.home.resolve()):
        raise ValueError('Organ-Verzeichnis außerhalb des Brain-Verzeichnisses')
    return root


def _snapshot_folder(r,role,sid):
    root=_organ_root(r);folder=root/role/sid
    if ((root/role).is_symlink() or folder.is_symlink() or
            not folder.resolve().is_relative_to(root.resolve())):
        raise ValueError('Organ-Sicherungspfad außerhalb des Organ-Verzeichnisses')
    return folder


def _spec(r,role):
    try:sp=r.bodies.ports.spec(role)
    except Exception:
        sp={'model_id':None,'revision':None,'sha256':None,'path':None}
    try:rev=r.models.revision(role)
    except Exception:rev=sp.get('revision')
    out={k:sp.get(k) for k in ('model_id','revision','sha256')}|{'revision':rev}
    try:out['bridge_key']=bridge_key(role,sp)
    except Exception:out['bridge_key']=None
    return out


def _components(r,role):
    comps=r.store.components()
    return {name:dict(e) for name,e in comps.items() if e.get('encoder_role')==role or role in (e.get('dependency_revisions') or {})}


def _bridges(r,role):
    d=r.home/'b3';out={}
    for p in sorted(d.glob('*.json')) if d.is_dir() else []:
        if role in direction_roles(p.stem):out[p.name]=file_hash(p)
    return out


def _assets(r,role):
    try:st=r.bodies.slots.box.load()[0]
    except Exception:return {}
    return {k:{x:a.get(x) for x in ('kind','revision','dataset_ref','authority')} for k,a in st.get('assets',{}).items() if a.get('slot')==role}


def members(r,role):
    role=_require_role(role)
    return {'role':role,'model':_spec(r,role),'components':_components(r,role),'bridges':_bridges(r,role),'assets':_assets(r,role)}


def _copy_new(src,dst,expected_hash):
    """Publish verified bytes only at a fresh path; never overwrite a generation's existing artifact."""
    dst.parent.mkdir(parents=True,exist_ok=True);created=False
    try:
        with src.open('rb') as source,dst.open('xb') as target:
            created=True;shutil.copyfileobj(source,target);target.flush();os.fsync(target.fileno())
        if file_hash(dst)!=expected_hash:raise RuntimeError('Kopie der Organ-Datei beschädigt')
        with contextlib.suppress(OSError):
            fd=os.open(dst.parent,os.O_RDONLY)
            try:os.fsync(fd)
            finally:os.close(fd)
    except BaseException:
        if created:dst.unlink(missing_ok=True)
        raise


def _saved_component(folder,man,name,e):
    # Additive v1 field: older snapshots used a flat basename, newer ones isolate each component.
    rel=Path(man['component_files'][name]) if 'component_files' in man else Path(e['path']).name
    base=folder/'files';path=base/rel
    if not path.resolve().is_relative_to(base.resolve()):raise RuntimeError('Ungültiger Organ-Sicherungspfad')
    return path


def snapshot(r,role,clock=time.time):
    if not r.idle():raise ValueError('Erst :stillstand (oder warten, bis nichts läuft); sonst ist die Sicherung nicht in sich stimmig.')
    role=_require_role(role)
    m=members(r,role);sid=uid('organ');folder=_snapshot_folder(r,role,sid);(folder/'files').mkdir(parents=True)
    component_files={name:'components/'+digest(name)+'.bin' for name in m['components']}
    for name,e in m['components'].items():
        src=r.home/e['path']
        if not src.is_file() or file_hash(src)!=e['sha256']:raise RuntimeError('Komponenten-Artefakt fehlt oder passt nicht: '+name)
        _copy_new(src,folder/'files'/component_files[name],e['sha256'])
    for name,h in m['bridges'].items():_copy_new(r.home/'b3'/name,folder/'files'/name,h)
    man={'revision':REVISION,'id':sid,'created':clock(),'generation':r.store.generation_id,'models_included':False,
         'component_files':component_files,**m}
    man['hash']=digest(dumps({k:v for k,v in man.items() if k!='hash'}))
    atomic_write(folder/'manifest.json',dumps(man));r.store.log('organ_snapshot',None,{'role':role,'id':sid})
    return man


def _load(r,sid):
    if type(sid) is not str or not SNAPSHOT_ID.fullmatch(sid):
        raise ValueError('Ungültige Organ-Sicherungs-ID')
    root=_organ_root(r)
    hits=list(root.glob('*/'+sid+'/manifest.json')) if root.is_dir() else []
    if len(hits)!=1:raise ValueError('Unbekannte Organ-Sicherung: '+str(sid))
    p=hits[0]
    if (p.is_symlink() or p.parent.is_symlink() or p.parent.parent.is_symlink() or
            not p.resolve().is_relative_to(root.resolve())):
        raise ValueError('Organ-Sicherungspfad außerhalb des Organ-Verzeichnisses')
    man=json.loads(p.read_text())
    if man.get('revision')!=REVISION or digest(dumps({k:v for k,v in man.items() if k!='hash'}))!=man.get('hash'):
        raise RuntimeError('Organ-Sicherung beschädigt: '+sid)
    if man.get('id')!=sid or man.get('role')!=p.parent.parent.name or man.get('role') not in MODEL_ROLES:
        raise RuntimeError('Organ-Sicherungs-Identität passt nicht zum Pfad')
    return man,p.parent


def listing(r):
    out=[];root=_organ_root(r)
    for p in sorted(root.glob('*/*/manifest.json')) if root.is_dir() else []:
        try:m=json.loads(p.read_text());out.append({k:m.get(k) for k in ('id','role','created','generation')}|{'components':sorted(m.get('components',{}))})
        except Exception:out.append({'id':p.parent.name,'error':'UNREADABLE'})
    return out


def _file_status(path,expected_hash):
    """Inspect artifact bytes, rather than treating generation metadata as proof of their existence."""
    if not path.is_file():return 'MISSING'
    try:return 'IDENTICAL' if file_hash(path)==expected_hash else 'CHANGED'
    except OSError:return 'CHANGED'


def check(r,sid):
    man,folder=_load(r,sid);now_=members(r,man['role']);parts={};backup_parts={}
    for name,e in man['components'].items():
        backup_parts['components:'+name]=_file_status(_saved_component(folder,man,name,e),e['sha256'])
    for name,h in man['bridges'].items():
        backup_parts['bridges:'+name]=_file_status(folder/'files'/name,h)
    for kind in ('components','bridges'):
        old,new=man[kind],now_[kind]
        for k in sorted(set(old)|set(new)):
            if k not in new:parts[kind+':'+k]='MISSING'
            elif kind=='components' and (actual:=_file_status(r.home/new[k]['path'],new[k]['sha256']))!='IDENTICAL':
                parts[kind+':'+k]=actual
            elif k not in old:parts[kind+':'+k]='ADDED'
            else:
                same=(old[k]['sha256']==new[k]['sha256']) if kind=='components' else old[k]==new[k]
                parts[kind+':'+k]='IDENTICAL' if same else 'CHANGED'
    model_same=man['model']['revision']==now_['model']['revision'] and man['model']['sha256']==now_['model']['sha256']
    backup_intact=all(v=='IDENTICAL' for v in backup_parts.values())
    reason=None
    if not model_same:reason='MODEL_CHANGED: erst :body rollback '+man['role']+' oder neu kalibrieren'
    elif not backup_intact:reason='BACKUP_DAMAGED: Organ-Sicherung enthält fehlende oder beschädigte Dateien'
    return {'id':sid,'role':man['role'],'model_same':model_same,'parts':parts,
            'backup_parts':backup_parts,'backup_intact':backup_intact,
            'identical':model_same and backup_intact and all(v=='IDENTICAL' for v in parts.values()),
            'restorable':model_same and backup_intact,'reason':reason}


def restore(r,sid):
    man,folder=_load(r,sid);role=man['role']
    if not r.idle():raise ValueError('Erst :stillstand (oder warten, bis nichts läuft).')
    c=check(r,sid)
    if not c['backup_intact']:raise RuntimeError('Organ-Sicherung beschädigt: '+sid)
    if not c['restorable']:raise ValueError(c['reason'])
    if c['identical']:return {'id':sid,'role':role,'status':'ALREADY_IDENTICAL','generation':r.store.generation_id}
    s=r.store;base=s.generation();comps=dict(s.components(base));hashes=dict(base['hashes'])
    for name in _components(r,role):  # take this organ's current components out ...
        hashes.pop(comps[name]['path'],None);comps.pop(name)
    # Validate the complete plan before copying ANY artifact. A later refusal must not repair/overwrite earlier files.
    from .store import COMPONENT_ENCODERS
    copies=[];original_paths=set()
    s.validate_artifacts({'hashes':hashes,'components':comps})
    for name,saved in man['components'].items():
        e=dict(saved)
        if name not in COMPONENT_ENCODERS:raise ValueError('Unbekannte Update-Komponente: '+name)
        if name in comps:raise ValueError('Komponente gehört inzwischen einem anderen Organ: '+name)
        for dep,rev in (e.get('dependency_revisions') or {}).items():
            if r.models.revision(dep)!=rev:raise ValueError('Abhängiges Modell geändert: '+dep+' (erst zurückstellen oder neu kalibrieren)')
        if e['path'] in hashes or e['path'] in original_paths:raise ValueError('Artefakt gehört bereits anderer Komponente: '+name)
        original_paths.add(e['path']);dst=r.home/e['path'];src=_saved_component(folder,man,name,e)
        if not dst.resolve().is_relative_to(r.home.resolve()):raise ValueError('Artefakt außerhalb des Brain-Verzeichnisses: '+name)
        if _file_status(dst,e['sha256'])!='IDENTICAL':
            e['path']='checkpoints/'+name+'-'+uid('organ_restore')+'.npz';dst=r.home/e['path']
            copies.append((src,dst,e['sha256']))
        comps[name]=e;hashes[e['path']]=e['sha256']
    for name,h in man['bridges'].items():
        src=folder/'files'/name
        if file_hash(src)!=h:raise RuntimeError('Gesicherte Brücke beschädigt: '+name)
    created=[];gid=None
    try:
        for src,dst,h in copies:_copy_new(src,dst,h);created.append(dst)
        s.validate_artifacts({'hashes':hashes,'components':comps})
        with s.tx() as cur:
            active=json.loads(cur.execute("SELECT value FROM meta WHERE key='active_generation'").fetchone()[0])
            if active!=base['brain_generation_id']:raise ValueError('Generation konkurrierend geändert')
            ids=[e['update_id'] for e in comps.values() if e.get('update_id')]
            gid=s._generation(cur,active,hashes,base['config'],base['rule_version'],base['models'],ids,comps,None)
    except BaseException:
        if gid is None or s.generation_id!=gid:
            for path in created:path.unlink(missing_ok=True)
        raise
    for name in _bridges(r,role):  # bridges only after the generation is written (a refused commit changes nothing)
        if name not in man['bridges']:(r.home/'b3'/name).unlink()
    for name in man['bridges']:(r.home/'b3').mkdir(exist_ok=True);shutil.copy2(folder/'files'/name,r.home/'b3'/name)
    s.log('organ_restore',None,{'role':role,'id':sid,'generation':gid})
    return {'id':sid,'role':role,'status':'RESTORED','generation':gid,'parts':c['parts'],
            'note':'Nur dieses Organ wurde zurückgestellt. Globales :rollback ist danach geschlossen; weitere Rücknahmen per :organ restore.'}


def text_check(c):
    lines=[f"Organ {c['role']} – Sicherung {c['id']}: "+('unverändert' if c['identical'] else 'geändert')]
    lines.append('  Modell: '+('gleich' if c['model_same'] else 'GEWECHSELT ('+c['reason']+')'))
    if not c['backup_intact']:lines.append('  Sicherung: BESCHÄDIGT (fehlende oder beschädigte Dateien; Wiederherstellen verweigert)')
    names={'IDENTICAL':'gleich','CHANGED':'geändert','MISSING':'fehlt jetzt','ADDED':'neu seit Sicherung'}
    for k,v in c['parts'].items():lines.append(f'  {k}: {names[v]}')
    return '\n'.join(lines)


def operator_command(r,args):
    """:organ [list|status <Rolle>|snapshot <Rolle>|check <ID>|restore <ID>]"""
    if not args or args==['list']:return dumps(listing(r))
    if len(args)==2 and args[0]=='status':return dumps(members(r,args[1]))
    if len(args)==2 and args[0]=='snapshot':
        m=snapshot(r,args[1]);return f"Organ-Sicherung {m['id']} für {m['role']}: {len(m['components'])} Köpfe/Adapter, {len(m['bridges'])} Brücken (Modelldatei nur per Prüfsumme)."
    if len(args)==2 and args[0]=='check':return text_check(check(r,args[1]))
    if len(args)==2 and args[0]=='restore':return dumps(restore(r,args[1]))
    raise ValueError(':organ [list|status <Rolle>|snapshot <Rolle>|check <ID>|restore <ID>]')
