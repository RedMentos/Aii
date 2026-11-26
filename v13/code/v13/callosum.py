"""WP-J (model-free part) / §85.2, B3-H3 L0, B3-H9..H11, G-CALLOSUM-UTILITY-002: dynamic B3 callosum.

B3_MESSAGE (§85.2)       every MessagePacket carries salience, confidence, signed_gain (amplify / neutral / suppress
                         *proposal*, never a direct override), urgency, temporal_scope, compatibility_score and
                         utility_history. signed_gain > 0: the sender's evidence agrees with the receiver's current
                         hypothesis or flags an open issue; < 0: the sender's exact evidence contradicts it (numbers
                         or quotes differ), so the receiver is asked to damp its own claim.
Channel policy (B3-5)    per direction a learned utility for NO_MESSAGE / SOURCE_EXACT / CONTROL / SYMBOLIC. All
                         probabilities stay > 0 (B3-H9). LATENT stays at p = 0 and level `unavailable` until a trained,
                         source-disjoint receiver passes held-out utility/retention gates (B3-H3, B3-H12). A native input-effect
                         probe is diagnostic only. SHADOW (default) logs the proposal next to the configured channel;
                         ACTIVE (`:callosum active`, explicit human) uses it and passes signed_gain/urgency to the
                         receiver as CONTROL fields.
Utility (B3-H9)          task_gain (receiver offer reached the focal coalition) + uncertainty_reduction (receiver no
                         longer needs re-entry) + source_recovery_gain (receiver offer has exact evidence) - latency_cost
                         - memory_cost (bytes); human ratings add value. NO_MESSAGE is the measured baseline.
Degradation (B3-H10)     a receiver model revision change resets that direction to the configured channel; a channel
                         whose utility falls below NO_MESSAGE over the window is never chosen. The latent ladder
                         L4..L1 -> EXACT/SYMBOLIC -> NO_MESSAGE with all ten canon triggers lives in `b3degrade.py`.
:doctor (B3-H11)         per-direction report incl. latent level, calibration validity, revisions, router KL / expert
                         flip baseline+current, utility vs NO_MESSAGE/EXACT/SYMBOLIC, demotions; FAIL if latent
                         influence was active without a valid calibration.
"""
import json
import math
import re
import time
from . import b3degrade
from .common import dumps
from .neuromod import step

KEY='J_CALLOSUM';REVISION='j-callosum-v1';PATH='callosum_channel_policy'
CHANNELS=('NO_MESSAGE','SOURCE_EXACT','CONTROL','SYMBOLIC')
DIRECTIONS={('B1_DETAIL','B2_GIST'):'B1_TO_B2',('B2_GIST','B1_DETAIL'):'B2_TO_B1'}
RATE=.2;MIN_N=5;TEMP=.15;FLOOR=.05;WINDOW=20   # BOOT
LAT_S=30.;BYTES=4000.                          # BOOT normalizers for latency / memory cost
NUM=re.compile(r'\d+(?:[.,]\d+)?')

def direction(sender,receiver):return DIRECTIONS[(sender,receiver)]
def empty():return {'revision':REVISION,'mode':'SHADOW','dirs':{d:{'u':{},'revision':None,'resets':0} for d in DIRECTIONS.values()},'pending':{},'proposals':{'n':0,'same':0}}

def nums(text):return set(NUM.findall(text or ''))

def signed_gain(offer,receiver_offer):
    """Amplify/suppress proposal from the sender's offer relative to the receiver's current hypothesis."""
    o=offer['offer']
    if receiver_offer is None:return (.25 if o.get('needs_reentry') else 0.),'NO_RECEIVER_HYPOTHESIS'
    a,b=nums(o.get('summary','')),nums(receiver_offer['offer'].get('summary',''))
    qa={q for q in o.get('quotes',[]) if isinstance(q,str)};qb={q for q in receiver_offer['offer'].get('quotes',[]) if isinstance(q,str)}
    if a and b and not a&b and offer['evidence_refs']:return -.5,'EXACT_EVIDENCE_CONTRADICTS_RECEIVER'
    if (a&b) or (qa&qb):return .5,'AGREES_WITH_RECEIVER'
    return (.25 if o.get('needs_reentry') else 0.),'NEUTRAL'

class Callosum:
    def __init__(self,store,neuromod=None):self.s=store;self.n=neuromod
    def _load(self):
        st,v=self.s.state(KEY,None)
        if st is None:st=empty()
        if st.get('revision')!=REVISION:raise ValueError('Callosum state revision mismatch')
        return st,v
    def _mutate(self,fn):
        for attempt in (0,1):
            st,v=self._load();out=fn(st);dumps(st)
            try:self.s.set_state(KEY,st,expected=v);return out
            except ValueError:
                if attempt:raise
    def set_mode(self,mode,authority='SYSTEM'):
        if mode not in {'SHADOW','ACTIVE'}:raise ValueError('SHADOW|ACTIVE')
        if mode=='ACTIVE' and authority!='EXPLICIT_HUMAN':raise PermissionError('ACTIVE nur per expliziter Nutzerfreigabe (Age 0)')
        def fn(st):st['mode']=mode;return mode
        return self._mutate(fn)
    # -- policy ---------------------------------------------------------------------------------------------
    @staticmethod
    def probabilities(d):
        """Softmax over measured channel utilities with a floor: every baseline keeps p > 0 (B3-H9); LATENT = 0."""
        u={c:(d['u'].get(c) or {'v':0.,'n':0})['v'] for c in CHANNELS}
        m=max(u.values());ex={c:math.exp((u[c]-m)/TEMP) for c in CHANNELS};z=sum(ex.values())
        p={c:FLOOR+(1-FLOOR*len(CHANNELS))*ex[c]/z for c in CHANNELS};p['LATENT']=0.
        return {c:round(v,4) for c,v in p.items()}
    def choose(self,sender,receiver,configured,model_revision=None):
        """Returns (channel, proposal, applied). Degrades to the configured channel on a receiver revision change."""
        dname=direction(sender,receiver)
        def fn(st):
            d=st['dirs'][dname]
            if model_revision is not None and d['revision'] not in (None,model_revision):
                d['u']={};d['resets']+=1;self.s.log('callosum_degraded',None,{'direction':dname,'reason':'RECEIVER_REVISION_CHANGED'})
            d['revision']=model_revision
            base=(d['u'].get('NO_MESSAGE') or {'v':0.,'n':0})
            ok=[c for c in CHANNELS if (d['u'].get(c) or {'n':0})['n']>=MIN_N and (c=='NO_MESSAGE' or d['u'][c]['v']>=base['v'])]
            proposal=max(ok,key=lambda c:d['u'][c]['v']) if ok and base['n']>=MIN_N else configured
            st['proposals']['n']+=1;st['proposals']['same']+=int(proposal==configured)
            return proposal,st['mode']=='ACTIVE',bool(ok) and base['n']>=MIN_N
        proposal,active,compared=self._mutate(fn)
        b3degrade.on_receiver_revision(self.s,dname,model_revision)  # B3-H10: a latent rung falls to EXACT/SYMBOLIC at once
        if compared:
            from .authority import observe
            observe(self.s,'callosum',configured,proposal)
        return (proposal if active else configured),proposal,active
    # -- message fields (§85.2) -----------------------------------------------------------------------------
    def fields(self,offer,receiver,channel,content,receiver_offer=None):
        dname=direction(offer['role'],receiver);st,_=self._load();d=st['dirs'][dname]
        g,why=signed_gain(offer,receiver_offer);o=offer['offer']
        refs=len(offer['evidence_refs']);rej=offer.get('rejected_quotes',0)
        u=(d['u'].get(channel) or {'v':0.,'n':0,'hist':[]})
        return {'salience':1. if o.get('needs_reentry') else round(.5+.25*bool(refs),3),'confidence':round(refs/(refs+rej),3) if refs+rej else 0.,
                'signed_gain':g,'gain_reason':why,'urgency':1. if o.get('needs_reentry') else .3,'temporal_scope':'TURN',
                'compatibility_score':round(.5+.5*math.tanh(u['v']),3),'utility_history':u.get('hist',[])[-5:],'bytes':len(dumps(content)),
                'b3_level':'L0','latent_level':b3degrade.latent_level(self.s,dname)}
    def note(self,event_id,message_packet_id,sender,receiver,channel,proposal,applied,gain):
        def fn(st):
            xs=st['pending'].setdefault(event_id,[])
            xs.append({'msg':message_packet_id,'direction':direction(sender,receiver),'receiver':receiver,'channel':channel,'proposal':proposal,'applied':applied,'gain':gain})
            for k in list(st['pending'])[:-32]:del st['pending'][k]
        self._mutate(fn)
    # -- learning (B3-H9) -----------------------------------------------------------------------------------
    def _update(self,st,dname,channel,util,comp=None,sc=1.):
        d=st['dirs'][dname];q=d['u'].setdefault(channel,{'v':0.,'n':0,'hist':[],'parts':{}})
        q['n']+=1;q['v']+=(sc*RATE if q['n']>1 else 1.)*(util-q['v']);q['hist']=(q['hist']+[round(util,3)])[-WINDOW:]
        for k,v in (comp or {}).items():q['parts'][k]=round(q['parts'].get(k,v)+sc*RATE*(v-q['parts'].get(k,v)),4)
    def outcome(self,event_id,coalition_ids,status):
        """Score every message of a finished turn by what the receiver's next offer did."""
        st,_=self._load();msgs=st['pending'].get(event_id) or []
        if not msgs:return {'scored':0}
        scored=[]
        for m in msgs:
            row=self.s.one("SELECT rowid FROM packets WHERE id=?",(m['msg'],))
            off=self.s.one("SELECT payload FROM packets WHERE kind='OfferPacket' AND event_id=? AND rowid>? AND json_extract(payload,'$.role')=? ORDER BY rowid LIMIT 1",(event_id,row['rowid'] if row else 0,m['receiver']))
            if not off:continue
            p=json.loads(off['payload']);dur=(p.get('native_metrics') or {}).get('duration_s') or 0.
            msg=self.s.one("SELECT payload FROM packets WHERE id=?",(m['msg'],));nbytes=json.loads(msg['payload']).get('bytes',0) if msg else 0
            comp={'task_gain':1. if p['packet_id'] in coalition_ids else 0.,'uncertainty_reduction':0. if p['offer'].get('needs_reentry') else .5,
                  'source_recovery_gain':.25 if p['evidence_refs'] else 0.,'latency_cost':min(1.,dur/LAT_S)*.25,'memory_cost':min(1.,nbytes/BYTES)*.25}
            util=comp['task_gain']+comp['uncertainty_reduction']+comp['source_recovery_gain']-comp['latency_cost']-comp['memory_cost']-(0. if status=='FINAL' else .5)
            scored.append((m,util,comp))
        sc=step(self.n,PATH)  # WP-U6 §12.7
        def fn(st):
            for m,util,comp in scored:self._update(st,m['direction'],m['channel'],util,comp,sc)
            for m in st['pending'].get(event_id,[]):m['scored']=True
        self._mutate(fn)
        if self.n is not None and scored:
            try:self.n.touch(PATH,event_id,activity=min(1.,len(scored)/2),detail={'channels':[m['channel'] for m,_,_ in scored]})
            except Exception:pass
        return {'scored':len(scored),'utilities':[round(u,3) for _,u,_ in scored]}
    def on_rating(self,event_id,utility):
        u=max(0.,min(1.,float(utility)));sc=step(self.n,PATH)
        def fn(st):
            ms=st['pending'].get(event_id) or []
            for m in ms:self._update(st,m['direction'],m['channel'],u,None,sc)
            return len(ms)
        n=self._mutate(fn)
        if n and self.n is not None:
            try:self.n.signal(event_id,path=PATH,source_class='human_correction',task_success=u)
            except Exception:pass
        return {'updated':n}
    # -- reports --------------------------------------------------------------------------------------------
    def doctor(self,cfg,revisions=None):
        """B3-H11 fields per direction. FAIL if latent influence was active without valid calibration (b3degrade)."""
        st,_=self._load();out={}
        r=getattr(self,'r',None);deg={}
        if r is not None:  # B3-H10: evaluate the ten triggers, apply demotions, report them
            cu={dn:{c:(st['dirs'][dn]['u'].get(c) or {}).get('v') if (st['dirs'][dn]['u'].get(c) or {'n':0})['n']>=b3degrade.MIN_N else None for c in CHANNELS} for dn in DIRECTIONS.values()}
            deg=b3degrade.check(r,cu)
        for (snd,rcv),dname in DIRECTIONS.items():
            d=st['dirs'][dname];u=lambda c:(d['u'].get(c) or {}).get('v')
            vs=lambda c:None if u(c) is None or u('NO_MESSAGE' if c!='NO_MESSAGE' else c) is None else round(u(c)-u('NO_MESSAGE'),3)
            out[dname]={'latent_level':'unavailable','calibration':None,'receiver_revision':(revisions or {}).get(rcv,d['revision']),'receiver_tap_ids':[],
                        'message_rank':0,'slot_budget':0,'latent_gain':0.,'router_kl':None,'expert_flip':None,
                        'utility':{c:u(c) for c in CHANNELS},'utility_vs_no_message':{c:vs(c) for c in ('SOURCE_EXACT','CONTROL','SYMBOLIC')},
                        'experience_count':sum((d['u'].get(c) or {'n':0})['n'] for c in CHANNELS),'policy_p':self.probabilities(d),
                        'fallback_channel':cfg.get('channel'),'last_calibration':None,'hardware_proof_id':None,'resets':d['resets'],'status':'PASS'}
            g=deg.get(dname)
            if g:
                out[dname].update(latent_level=g['level'] if g['level'] in b3degrade.LATENT else 'unavailable',degradation_level=g['level'],
                                  status=g['status'],calibration_valid=g['calibration_valid'],runner_revision=g['runner_revision'],
                                  body_revisions=(revisions or (r.revisions() if hasattr(r,'revisions') else {})),router_kl=g['router_kl'],expert_flip=g['expert_flip'],
                                  degradation={k:g[k] for k in ('previous','fired','triggers','calibration_reasons','resource_mode','role_diversity','last_fail','demotions')})
                if g['level']=='NO_MESSAGE':out[dname]['fallback_channel']='NO_MESSAGE'
                try:
                    from . import b3order  # B3-H8 training order from evidence
                    o=b3order.status(r.home,dname,out[dname]['body_revisions']);out[dname]['training_order']={k:o[k] for k in ('done','next','status','violations','locked_by_canon')}
                except Exception as exc:out[dname]['training_order']={'error':type(exc).__name__}
        return out
    def report(self,cfg):
        st,_=self._load();p=st['proposals']
        native_probe={'status':'NOT_RUN','native_input_consumed':False,'input_effect_detected':False,
                      'production_route':False,'semantic_use_proven':False,'training_authority':0,'native_receiver_authority':0}
        r=getattr(self,'r',None)
        if r is not None:
            row=self.s.one(
                "SELECT p.payload FROM packets p JOIN events e ON e.id=p.event_id "
                "WHERE p.kind=? AND e.session_id=? ORDER BY p.created DESC LIMIT 1",
                ("LatentReceiverPacket",r.session),
            )
            if row:
                try:
                    saved=json.loads(row["payload"])
                    native_probe={k:saved.get(k) for k in (
                        'status','input_rows','input_dim','receiver_input_dim','runner_revision',
                        'native_input_consumed','input_effect_detected','input_effect_rms',
                        'production_route','semantic_use_proven','training_authority','native_receiver_authority',
                    )}
                except Exception:
                    native_probe['status']='INVALID_RECEIPT'
        return {'revision':REVISION,'mode':st['mode'],'proposal_agreement':round(p['same']/p['n'],3) if p['n'] else None,'directions':self.doctor(cfg),
                'native_receiver_probe':native_probe,
                'gate':'G-CALLOSUM-UTILITY-002: LATENT blocked (diagnostic native receiver only; no trained alignment/held-out utility)',
                'claim_limit':'Native input-effect diagnostic only; no learned semantic utility or production latent exchange'}

def controller(runtime):
    c=getattr(runtime,'callosum',None)
    if c is None:
        n=None
        try:
            from .neuromod import controller as nc
            n=nc(runtime)
        except Exception:n=None
        c=runtime.callosum=Callosum(runtime.store,n)
    c.r=runtime  # :doctor evaluates the B3-H10 triggers from runtime evidence
    return c

def on_rating(store,event_id,score):return Callosum(store).on_rating(event_id,(score-1)/9)



_TOKENWISE_LAB_MAX_RECORDS = 8
_TOKENWISE_LAB_MIN_AVAILABLE_BYTES = 512 * 1024 * 1024


def _tokenwise_session_ids(value, label):
    if type(value) is not str:
        raise ValueError(label + " must be a comma-separated session list")
    values = [part.strip() for part in value.split(",")]
    if len(values) < 2 or any(not item or len(item) > 160 for item in values):
        raise ValueError(label + " requires at least two bounded session IDs")
    if len(set(values)) != len(values):
        raise ValueError(label + " contains duplicate session IDs")
    return values


def _tokenwise_source_key(value):
    if not isinstance(value, dict):
        return None
    return tuple(value.get(key) for key in ("source_id", "sha256", "char_start", "char_end"))


def _fit_tokenwise_candidate(runtime, args):
    if len(args) != 5 or args[0] != "fit-tokenwise-cohort" or args[4] != "--confirm":
        raise ValueError("usage: :callosum fit-tokenwise-cohort <train-session-ids> <holdout-session-ids> <record-sha-prefix> --confirm")
    from . import native_probe_approval as approval
    approval._require_local_tty()
    runtime.require_idle()
    pending, _ = runtime.store.state(approval.KEY, None)
    if isinstance(pending, dict) and pending.get("status") == "PENDING":
        raise PermissionError("revoke the pending local probe approval before fitting a new candidate")
    if getattr(runtime, "_native_tokenwise_candidate", None) is not None:
        raise ValueError("a tokenwise candidate is already staged; probe it or clear the lab first")
    resources = runtime.resources()
    available = resources.get("mem_available_bytes") if isinstance(resources, dict) else None
    if type(available) is not int or available < _TOKENWISE_LAB_MIN_AVAILABLE_BYTES:
        raise MemoryError("tokenwise cohort fit requires at least 512 MiB available RAM")
    train = _tokenwise_session_ids(args[1], "train sessions")
    holdout = _tokenwise_session_ids(args[2], "holdout sessions")
    if set(train) & set(holdout):
        raise ValueError("train and holdout session IDs must be disjoint")
    prefix = args[3]
    if (type(prefix) is not str or not 8 <= len(prefix) <= 64
            or any(ch not in "0123456789abcdef" for ch in prefix)):
        raise ValueError("record SHA prefix must be 8..64 lowercase hexadecimal characters")
    records = getattr(runtime, "_native_tokenwise_pair_records", None)
    if not isinstance(records, list) or not 1 <= len(records) <= _TOKENWISE_LAB_MAX_RECORDS:
        raise ValueError("no bounded in-memory tokenwise pair cohort is available")
    cohort = [item for item in records if item.get("session_id") in set(train) | set(holdout)]
    matches = [
        item for item in cohort
        if item.get("session_id") in set(holdout)
        and item.get("record_sha256", "").startswith(prefix)
    ]
    if len(matches) != 1:
        raise ValueError("record SHA prefix must identify exactly one held-out in-memory record")
    heldout = matches[0]
    event, source_ref = approval._current_event(runtime)
    if (heldout.get("session_id") != runtime.session
            or heldout.get("event_id") != event.get("event_id")
            or heldout.get("brain_generation_id") != event.get("brain_generation_id")
            or _tokenwise_source_key(heldout.get("source_ref")) != _tokenwise_source_key(source_ref)):
        raise PermissionError("selected held-out record is not the current Runtime source/event/session")
    from .native_tokenwise_pair_capture import fit_native_tokenwise_pair_cohort
    fitted = fit_native_tokenwise_pair_cohort(cohort, train, holdout)
    if not isinstance(fitted, dict):
        raise ValueError("tokenwise fitter returned no candidate")
    adapter, manifest = fitted.get("adapter"), fitted.get("fit_manifest")
    if (not isinstance(adapter, dict) or adapter.get("status") != "ALIGNMENT_CANDIDATE"
            or adapter.get("projection_scope") != "TOKENWISE"
            or adapter.get("production_route") is not False
            or adapter.get("semantic_use_proven") is not False
            or adapter.get("training_authority") != 0
            or adapter.get("native_receiver_authority") != 0
            or type(adapter.get("adapter_sha256")) is not str
            or len(adapter["adapter_sha256"]) != 64
            or any(ch not in "0123456789abcdef" for ch in adapter["adapter_sha256"])
            or not isinstance(manifest, dict)
            or manifest.get("session_disjoint") is not True
            or manifest.get("source_disjoint") is not True
            or type(manifest.get("manifest_sha256")) is not str
            or len(manifest["manifest_sha256"]) != 64
            or any(ch not in "0123456789abcdef" for ch in manifest["manifest_sha256"])):
        raise ValueError("fitter did not return a source/session-disjoint authority-zero TOKENWISE candidate")
    runtime._native_tokenwise_candidate = {
        "adapter": adapter,
        "record": heldout,
        "fit_manifest": manifest,
        "cohort_records": list(cohort),
        "staged_at": time.time(),
    }
    # Keep the bounded held-out control records in memory until the matrix is
    # built or the tokenwise lab is cleared; they are never persisted.
    runtime._native_tokenwise_pair_records = list(cohort)
    return dumps({
        "schema": "v14.native-tokenwise-candidate-stage/1",
        "status": "ALIGNMENT_CANDIDATE_STAGED",
        "adapter_sha256": adapter["adapter_sha256"],
        "record_sha256": heldout["record_sha256"],
        "session_id": heldout["session_id"],
        "fit_manifest_sha256": manifest["manifest_sha256"],
        "train_record_count": manifest.get("train_record_count"),
        "holdout_record_count": manifest.get("holdout_record_count"),
        "train_pair_count": manifest.get("train_pair_count"),
        "holdout_pair_count": manifest.get("holdout_pair_count"),
        "adapter_persisted": False,
        "pair_records_persisted": False,
        "production_route": False,
        "semantic_utility_proven": False,
        "training_authority": 0,
        "native_receiver_authority": 0,
    })


def _run_tokenwise_native_probe(runtime, args):
    if args != ["native-tokenwise-probe", "--confirm"]:
        raise ValueError("usage: :callosum native-tokenwise-probe --confirm")
    from . import native_probe_approval as approval
    approval._require_local_tty()
    candidate = getattr(runtime, "_native_tokenwise_candidate", None)
    if not isinstance(candidate, dict):
        raise ValueError("no in-memory tokenwise candidate is staged")
    record = candidate.get("record")
    adapter = candidate.get("adapter")
    if not isinstance(record, dict) or not isinstance(adapter, dict):
        raise ValueError("staged tokenwise candidate is malformed")
    pending, _ = runtime.store.state(approval.KEY, None)
    if (not isinstance(pending, dict) or pending.get("status") != "PENDING"
            or pending.get("probe_kind") != "NATIVE_RECEIVER"
            or pending.get("sender_role") != record.get("sender", {}).get("role")
            or pending.get("receiver_role") != record.get("receiver", {}).get("role")
            or pending.get("session_id") != record.get("session_id")
            or pending.get("event_id") != record.get("event_id")
            or pending.get("brain_generation_id") != record.get("brain_generation_id")
            or _tokenwise_source_key(pending.get("source_ref")) != _tokenwise_source_key(record.get("source_ref"))
            or type(pending.get("expires_at")) not in (int, float)
            or time.time() >= pending["expires_at"]):
        raise PermissionError("a fresh, matching one-shot NATIVE_RECEIVER local approval is required")
    from .native_tokenwise_receiver_probe import probe_native_tokenwise_candidate
    try:
        result = probe_native_tokenwise_candidate(runtime, adapter, record)
    except BaseException:
        consumed, _ = runtime.store.state(approval.KEY, None)
        if isinstance(consumed, dict) and consumed.get("status") == "CONSUMED":
            runtime._native_tokenwise_candidate = None
        raise
    runtime._native_tokenwise_candidate = None
    runtime._native_tokenwise_pair_records = []
    return dumps(result)


def _clear_tokenwise_lab(runtime, args):
    if args != ["clear-tokenwise-lab", "--confirm"]:
        raise ValueError("usage: :callosum clear-tokenwise-lab --confirm")
    from . import native_probe_approval as approval
    approval._require_local_tty()
    runtime.require_idle()
    pending, _ = runtime.store.state(approval.KEY, None)
    if isinstance(pending, dict) and pending.get("status") == "PENDING":
        raise PermissionError("revoke the pending local probe approval before clearing the tokenwise lab")
    records = getattr(runtime, "_native_tokenwise_pair_records", [])
    candidate = getattr(runtime, "_native_tokenwise_candidate", None)
    runtime._native_tokenwise_pair_records = []
    runtime._native_tokenwise_candidate = None
    return dumps({
        "schema": "v14.native-tokenwise-pair-lab/1",
        "status": "CLEARED",
        "cleared_record_count": len(records) if isinstance(records, list) else 0,
        "cleared_candidate": isinstance(candidate, dict),
        "persisted": False,
    })

def operator_command(r,args):
    """:callosum controller plus local one-shot tokenwise and native receiver diagnostics."""
    if args and args[0] in {"arm-probe", "native-probe", "revoke-probe"}:
        from .native_probe_approval import operator_command as native_probe_command
        return native_probe_command(r,args)
    if args and type(args[0]) is str and args[0].startswith("matrix-"):
        from .native_receiver_matrix_runtime import operator_command as matrix_command
        return matrix_command(r,args)
    if args and args[0] in {"arm-input-tap", "native-input-tap", "revoke-input-tap"}:
        from .native_input_embedding_capture import operator_command as input_tap_command
        return input_tap_command(r,args)
    if args and args[0] in {"arm-tokenwise-pair", "native-tokenwise-pair", "revoke-tokenwise-pair"}:
        from .native_tokenwise_pair_capture import operator_command as pair_command
        return pair_command(r,args)
    if args and args[0] == "fit-tokenwise-cohort":
        return _fit_tokenwise_candidate(r,args)
    if args and args[0] == "native-tokenwise-probe":
        return _run_tokenwise_native_probe(r,args)
    if args and args[0] == "clear-tokenwise-lab":
        return _clear_tokenwise_lab(r,args)
    c=controller(r)
    if not args or args==['status']:return dumps(c.report(r.cfg))
    if args==['shadow']:return dumps({'mode':c.set_mode('SHADOW')})
    if args==['active']:return dumps({'mode':c.set_mode('ACTIVE','EXPLICIT_HUMAN')})
    if args==['degrade']:return dumps({d:{k:x[k] for k in ('degradation_level','status','calibration_valid','degradation')} for d,x in c.doctor(r.cfg).items()})
    if len(args)==2 and args[0]=='promote' and args[1] in b3degrade.RECEIVER:
        return dumps({'direction':args[1],'level':b3degrade.promote(r,args[1],'EXPLICIT_HUMAN')})
    raise ValueError(
        ':callosum [status|shadow|active|degrade|promote B1_TO_B2|B2_TO_B1|'
        'arm-probe <sender> <receiver> --last-source --confirm|native-probe <sender> <receiver> --last-source --confirm|'
        'arm-tokenwise-pair <sender> <receiver> --last-source --confirm|native-tokenwise-pair <sender> <receiver> --last-source --confirm|'
        'fit-tokenwise-cohort <train-sessions> <holdout-sessions> <record-sha-prefix> --confirm|'
        'native-tokenwise-probe --confirm|revoke-probe|revoke-tokenwise-pair|clear-tokenwise-lab --confirm|matrix-build <task-family> <ood-family> <entity-family> <ood-record-sha-prefix> <entity-record-sha-prefix> --confirm|matrix-status|matrix-arm --confirm|matrix-run --confirm|matrix-revoke --confirm|matrix-clear --confirm]'
    )
