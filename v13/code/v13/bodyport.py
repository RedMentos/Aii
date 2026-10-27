"""WP-T13 / IH-H8, IH-H21, G2, G11: BodyPort objects in the run path, live bridge-key check, online body swap with rollback.

IH-H8 BodyPort       one port per body role (B1_DETAIL, B2_GIST, C3_LANGUAGE, ...). The RunnerPool reports every
                     lifecycle transition: ASSIGNED (runner object, no process yet) -> READY (process alive) ->
                     RELEASED; a different weight file for a role is a MODEL_CHANGE (old runner released, new one
                     assigned) and a failed probe is FAILED. A port knows its serving spec (path, revision, sha256,
                     capabilities) and its bridge compatibility key. Hits (same runner reused) are not persisted.
IH-H21 bridge key    sha256 over role, model id, exact revision, weight-file sha256, dims, tokenizer and capabilities.
                     Bridges and latent paths are valid only for the exact keys/revisions they were trained on.
                     Before a role serves a different file the key is recomputed live; every B3 bridge manifest
                     (b3/<SENDER>_TO_<RECEIVER>.json) and every slot asset of kind bridge/latent_path that names the old
                     revision is marked stale (authority SHADOW_RECALIBRATE). Stale bridges fall back to the configured
                     SOURCE/EXACT channel; nothing is retried with old weights.
G11 online swap      propose (GGUF magic + sha256, copied to models/swap/) -> SHADOW -> parity (AG12 axes) -> RAMP
                     0.1 -> 0.5 -> 1.0 -> ACTIVE. Every stage change takes effect on the next turn without a restart:
                     ModelManager.path_for asks the slot (bodies.BodyFabric.path_override), the pool notices the
                     different file and swaps the runner. After the last ramp step a health probe loads the new
                     body; a failed probe rolls back automatically. rollback() works from any stage, also after
                     ACTIVE (previous model), and also without a restart.
A swap is the user's decision (origin USER); V13's own proposal needs the Age right body_swap (agi/slots.py).
Claim limit: the probe proves that the new file loads and answers /health, not that it answers well; quality is the
parity gate's job (AG12 eval), and Redmi load times remain a phone measurement.
"""
import json
import re
import shutil
import time
from pathlib import Path
from .common import digest,dumps,file_hash

KEY='T13_BODY_PORTS';REVISION='t13-bodyport-v1';HISTORY=96
BRIDGE_KEY='T13_BRIDGE_KEYS'
SHORT={'B1':'B1_DETAIL','B2':'B2_GIST','C3':'C3_LANGUAGE'}
BRIDGE_ASSETS=('bridge','latent_path')

def bridge_key(role,spec):
    """IH-H21 compatibility key of one serving spec."""
    keep={k:spec.get(k) for k in ('model_id','revision','sha256','dims','tokenizer')}
    return digest(dumps({'role':role,'capabilities':sorted(spec.get('capabilities') or []),**keep}))

def direction_roles(direction):
    """'B1_TO_B2' -> ('B1_DETAIL','B2_GIST'); unknown names -> (None, None)."""
    a,_,b=str(direction).upper().partition('_TO_')
    return SHORT.get(a),SHORT.get(b)

class Ports:
    """Persistent lifecycle table + live bridge-key check. Attached as runtime.bodies.ports (see bodies.attach)."""
    def __init__(self,runtime,clock=time.time):
        self.r=runtime;self.s=runtime.store;self.clock=clock;self.live={}
    def _mutate(self,key,fn,default):
        for attempt in (0,1):
            st,v=self.s.state(key,None);st=st or default()
            out=fn(st)
            try:self.s.set_state(key,st,expected=v);return out
            except ValueError:
                if attempt:raise
    def _default(self):return {'revision':REVISION,'ports':{},'history':[]}
    # -- serving spec --------------------------------------------------------------------------------------
    def spec(self,role,path=None):
        """What serves `role` now (or what `path` would be): slot spec if the slot owns that file, else the installed entry."""
        from .models import model_key
        m=self.r.models;path=Path(path) if path else m.path_for(role)
        sl=self.r.bodies.slots.box.load()[0]['slots'].get(role) if getattr(self.r,'bodies',None) else None
        for cand in ([sl.get('candidate'),sl.get('active'),sl.get('previous')] if sl else []):
            if cand and cand.get('path') and self._abs(cand['path'])==path.resolve():
                return {'model_id':cand['model_id'],'revision':cand['revision'],'sha256':cand.get('sha256') or cand['revision'],'dims':cand.get('dims'),
                        'tokenizer':cand.get('tokenizer'),'capabilities':cand.get('capabilities') or [],'path':str(path)}
        e=m.installed.get(model_key(role,m.b2_control)) or {}
        f=(e.get('files') or {}).get(e.get('main_file')) or {}
        return {'model_id':e.get('model_id'),'revision':e.get('exact_revision'),'sha256':f.get('sha256'),'dims':None,'tokenizer':None,
                'capabilities':['CAN_NATIVE_DECODE'],'path':str(path)}
    def _abs(self,p):
        p=Path(p);return (p if p.is_absolute() else self.r.models.home/p).resolve()
    # -- lifecycle events from the RunnerPool ------------------------------------------------------------------
    def event(self,role,state,path=None,detail=None):
        """ASSIGNED | READY | RELEASED | MODEL_CHANGE | FAILED. Persisted with the serving spec and its bridge key."""
        try:sp=self.spec(role,path) if path or state!='RELEASED' else None
        except Exception:sp=None
        key=bridge_key(role,sp) if sp else None
        self.live[role]={'state':state,'path':sp and sp['path'],'key':key,'at':self.clock()}
        def f(st):
            p=st['ports'].setdefault(role,{'state':'UNLOADED','loads':0,'changes':0,'failures':0})
            p['state']=state;p['since']=self.clock()
            if sp:p.update(path=sp['path'],revision=sp['revision'],model_id=sp['model_id'],bridge_key=key)
            if state=='ASSIGNED':p['loads']+=1
            if state=='MODEL_CHANGE':p['changes']+=1
            if state=='FAILED':p['failures']+=1;p['last_error']=(detail or {}).get('error')
            st['history']=(st['history']+[{'role':role,'state':state,'revision':sp and sp['revision'],'at':round(self.clock(),3),**({'detail':detail} if detail else {})}])[-HISTORY:]
        self._mutate(KEY,f,self._default)
        return key
    def model_change(self,role,old_path,new_path):
        """Called by the pool before a role serves a different weight file: live IH-H21 check, then the event."""
        old=self.spec(role,old_path) if old_path else None;new=self.spec(role,new_path)
        res=self.check_bridges(role,old,new)
        self.event(role,'MODEL_CHANGE',new_path,{'from':old and old['revision'],'to':new['revision'],'stale_bridges':res['stale']})
        return res
    def check_bridges(self,role,old,new):
        """IH-H21: bridges trained for any other revision of `role` lose authority before the new body serves."""
        nk=bridge_key(role,new);stale=[]
        old_key=bridge_key(role,old) if old is not None else None
        identity_changed=old_key is not None and old_key!=nk
        from .b3bridge import bridge_dir
        d=bridge_dir(self.r.home)
        for p in sorted(d.glob('*.json')) if d.is_dir() else []:
            try:man=json.loads(p.read_text())
            except Exception:continue
            snd,rcv=direction_roles(man.get('direction') or p.stem)
            for side,key_field,r_ in (('sender_revision','sender_bridge_key',snd),
                                      ('receiver_revision','receiver_bridge_key',rcv)):
                if r_==role and (man.get(side)!=new.get('revision') or man.get(key_field)!=nk):
                    stale.append({'bridge':p.stem,'side':side,'trained_for':man.get(side),
                                  'bridge_key_match':man.get(key_field)==nk})
        slots=self.r.bodies.slots
        def f(st):
            for k,a in st['assets'].items():
                if (a['slot']==role and a['kind'] in BRIDGE_ASSETS and
                        (a['revision']!=new['revision'] or identity_changed)):
                    a['authority']='SHADOW_RECALIBRATE'
                    stale.append({'asset':k,'trained_for':a['revision'],
                                  'identity_changed':identity_changed})
        slots.box.mutate(f)
        def g(st):
            prev=st.get(role);st[role]={'key':nk,'revision':new['revision'],'checked':self.clock(),'previous_key':prev and prev['key'],
                                        'stale':[x.get('bridge') or x.get('asset') for x in stale]}
        self._mutate(BRIDGE_KEY,g,dict)
        self.s.log('bridge_key_check',None,{'role':role,'stale':len(stale)})
        return {'role':role,'key':nk,'previous_key':bridge_key(role,old) if old else None,'stale':stale}
    def bridge_binding(self,direction):
        """Exact live serving identities for Bridge.save(extra=...), not an L1 approval.

        A revision string alone cannot bind a learned bridge to model bytes.
        Unhashed/uninstalled specs are not safe inputs for a bridge manifest.
        """
        snd,rcv=direction_roles(direction)
        if not snd or not rcv or direction not in ('B1_TO_B2','B2_TO_B1'):
            raise ValueError('unknown B3 bridge direction')
        left,right=self.spec(snd),self.spec(rcv)
        for spec in (left,right):
            if (not isinstance(spec.get('sha256'),str) or
                    re.fullmatch(r'[a-f0-9]{64}',spec['sha256']) is None or
                    not isinstance(spec.get('revision'),str) or not spec['revision'] or
                    not isinstance(spec.get('model_id'),str) or not spec['model_id']):
                raise ValueError('unbound B3 serving model identity')
        return {'sender_revision':left['revision'],'receiver_revision':right['revision'],
                'sender_bridge_key':bridge_key(snd,left),
                'receiver_bridge_key':bridge_key(rcv,right)}

    def bridge_valid(self,direction):
        """Only exact live model-byte/bridge-key-bound manifests may be valid.

        Legacy revision-only manifests intentionally fail closed until retrained
        or explicitly rebound to current bytes; no B3 L1 authority is granted.
        """
        from .b3bridge import bridge_dir
        if direction not in ('B1_TO_B2','B2_TO_B1'):
            return False
        p=bridge_dir(self.r.home)/(direction+'.json')
        try:
            man=json.loads(p.read_text())
            if not isinstance(man,dict) or man.get('direction')!=direction:
                return False
            expected=self.bridge_binding(direction)
            return all(man.get(k)==v for k,v in expected.items())
        except (OSError,ValueError,TypeError,KeyError):
            return False
    def report(self):
        st=self.s.state(KEY,None)[0] or self._default();keys=self.s.state(BRIDGE_KEY,None)[0] or {}
        return {'revision':REVISION,'ports':st['ports'],'live':self.live,'bridge_keys':keys,'recent':st['history'][-12:],
                'claim_limit':'Lifecycle bookkeeping of real runner transitions; READY means the process answered /health, not quality'}

class BodySwap:
    """G11 online swap driver over agi/slots.ModelSlots (the gates) and the live pool (the effect)."""
    def __init__(self,runtime,probe=None):
        self.r=runtime;self.slots=runtime.bodies.slots;self.ports=runtime.bodies.ports;self.probe_fn=probe or self._probe
    def propose(self,role,gguf,origin='USER',model_id='operator-swap',dims=None,tokenizer=None):
        src=Path(gguf).expanduser().resolve()
        with open(src,'rb') as f:
            if f.read(4)!=b'GGUF':raise ValueError('Nur GGUF tauschbar')
        h=file_hash(src);dest=self.r.models.home/'models'/'swap'/(h[:16]+'.gguf');dest.parent.mkdir(parents=True,exist_ok=True)
        if not dest.exists():
            tmp=dest.with_suffix('.partial');shutil.copyfile(src,tmp)
            if file_hash(tmp)!=h:tmp.unlink(missing_ok=True);raise IOError('Kopie beschädigt')
            tmp.replace(dest)
        old=self.ports.spec(role)
        spec=self.slots.spec(model_id,h,old.get('capabilities') or ('CAN_NATIVE_DECODE',),dims=dims,tokenizer=tokenizer,path=str(dest.relative_to(self.r.models.home)))|{'sha256':h}
        plan=self.slots.propose_swap(role,spec,origin)
        self.slots.start_shadow(role)
        self.r.store.log('body_swap',None,{'role':role,'stage':'SHADOW','to':h[:16]})
        return {'role':role,'stage':'SHADOW','candidate':h,'plan':plan,'bridge_key_new':bridge_key(role,dict(spec,revision=h))}
    def parity(self,role,old_eval,new_eval,skills_parity=None,provenance_ok=True):
        sl=self.slots.parity(role,old_eval,new_eval,skills_parity,provenance_ok)
        return {'role':role,'stage':sl['stage'],'parity':sl['parity']}
    def ramp(self,role):
        sl=self.slots.ramp(role);out={'role':role,'stage':sl['stage'],'share':sl['share']}
        if sl['stage']=='ACTIVE':
            ok,detail=self._safe_probe(role)
            out['probe']=detail
            if not ok:
                self.rollback(role,reason='PROBE_FAILED');out['stage']='ROLLED_BACK'
        self.r.store.log('body_swap',None,{'role':role,'stage':out['stage'],'share':out.get('share')})
        return out
    def rollback(self,role,reason='USER'):
        self.slots.rollback(role)
        self.r.pool.unload(role)  # the next get() loads whatever the slot serves now; no restart
        self.ports.event(role,'RELEASED',None,{'rollback':reason})
        self.r.store.log('body_swap',None,{'role':role,'stage':'ROLLBACK','reason':reason})
        return {'role':role,'stage':'ACTIVE','serving':self.ports.spec(role)['revision'],'reason':reason}
    def _safe_probe(self,role):
        try:
            d=self.probe_fn(role);ok=bool(d.get('ok'))
        except Exception as exc:ok,d=False,{'ok':False,'error':type(exc).__name__+': '+str(exc)[:160]}
        if not ok:self.ports.event(role,'FAILED',None,{'error':d.get('error','probe')})
        return ok,d
    def _probe(self,role,seconds=120.):
        """Default health probe: obtain the runner for the new file and wait for /health (real load, no generation)."""
        import threading
        runner=self.r.pool.get(role);runner.load(threading.Event(),time.monotonic()+seconds)
        alive=bool(runner.pids())
        if alive:self.ports.event(role,'READY',getattr(runner,'model',None))
        return {'ok':alive,'model':str(getattr(runner,'model','')),'pids':len(runner.pids())}

def operator_command(r,args):
    """:body [status|bridges|swap <Rolle> <gguf>|parity <Rolle> <alt.json> <neu.json>|ramp <Rolle>|rollback <Rolle>]"""
    ports=r.bodies.ports
    if not args or args==['status']:return dumps(ports.report()|{'slots':r.bodies.slots.report()['slots']})
    if args==['bridges']:return dumps(ports.report()['bridge_keys'])
    sw=BodySwap(r)
    if len(args)==3 and args[0]=='swap':return dumps(sw.propose(args[1],args[2]))
    if len(args)==4 and args[0]=='parity':return dumps(sw.parity(args[1],json.loads(Path(args[2]).read_text()),json.loads(Path(args[3]).read_text())))
    if len(args)==2 and args[0]=='ramp':return dumps(sw.ramp(args[1]))
    if len(args)==2 and args[0]=='rollback':return dumps(sw.rollback(args[1]))
    raise ValueError(':body [status|bridges|swap <Rolle> <gguf>|parity <Rolle> <alt.json> <neu.json>|ramp <Rolle>|rollback <Rolle>]')
