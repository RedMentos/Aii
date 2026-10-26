"""WP-J (model-free part) / §85.2, B3-H3 L0, B3-H9..H11, G-CALLOSUM-UTILITY-002: dynamic B3 callosum.

B3_MESSAGE (§85.2)       every MessagePacket carries salience, confidence, signed_gain (amplify / neutral / suppress
                         *proposal*, never a direct override), urgency, temporal_scope, compatibility_score and
                         utility_history. signed_gain > 0: the sender's evidence agrees with the receiver's current
                         hypothesis or flags an open issue; < 0: the sender's exact evidence contradicts it (numbers
                         or quotes differ), so the receiver is asked to damp its own claim.
Channel policy (B3-5)    per direction a learned utility for NO_MESSAGE / SOURCE_EXACT / CONTROL / SYMBOLIC. All
                         probabilities stay > 0 (B3-H9). LATENT stays at p = 0 and level `unavailable` until native L1+
                         exists (B3-H3, B3-H12). SHADOW (default) logs the proposal next to the configured channel;
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
        """Score only a source-valid MessagePacket and its subsequent receiver offer."""
        st,_=self._load();msgs=[m for m in (st['pending'].get(event_id) or []) if not m.get('scored')]
        if not msgs:return {'scored':0}
        ev=self.s.one('SELECT generation_id FROM events WHERE id=?',(event_id,))
        if not ev:return {'scored':0}
        generation=ev['generation_id'];scored=[]
        for m in msgs:
            pair=next((p for p,name in DIRECTIONS.items() if name==m.get('direction')),None)
            if not pair or m.get('receiver')!=pair[1]:continue
            msg=self.s.one("SELECT rowid,kind,event_id,generation_id,payload FROM packets WHERE id=?",(m.get('msg'),))
            if not msg or msg['kind']!='MessagePacket' or msg['event_id']!=event_id or msg['generation_id']!=generation:
                continue  # never fall back to rowid=0 for a missing message
            try:
                mp=json.loads(msg['payload'])
                refs=mp['source_refs']
                if (mp['packet_id']!=m['msg'] or mp['event_id']!=event_id or
                    mp['brain_generation_id']!=generation or mp['sender']!=pair[0] or
                    mp['receiver']!=pair[1] or mp['channel']!=m['channel'] or
                    not isinstance(refs,list) or refs!=mp['provenance']):
                    continue
                for ref in refs:self.s.read_source(ref)  # deleted/digest/span must fail closed
            except (ValueError,TypeError,KeyError,AttributeError,OSError,UnicodeError):
                continue
            # SQLite json_extract over malformed payloads would abort the whole
            # cycle; inspect the first subsequent receiver offer in Python.
            offers=self.s.rows("SELECT id,generation_id,payload FROM packets WHERE kind='OfferPacket' AND event_id=? AND rowid>? ORDER BY rowid",
                               (event_id,msg['rowid']))
            for row in offers:
                try:
                    p=json.loads(row['payload'])
                    if p.get('role')!=pair[1]:continue
                    peer=p.get('peer_message_packet_id')
                    # A later offer is not evidence of a message effect unless
                    # its query explicitly consumed this exact MessagePacket.
                    # NO_MESSAGE is the intentionally unlinked control baseline.
                    if m['channel']=='NO_MESSAGE':
                        if peer is not None:continue
                    elif peer!=m['msg']:
                        continue
                    if (p['packet_id']!=row['id'] or p['event_id']!=event_id or
                        p['brain_generation_id']!=generation or row['generation_id']!=generation):
                        break
                    evidence=p['evidence_refs'];provenance=p['provenance']
                    if not isinstance(evidence,list) or not isinstance(provenance,list):break
                    for ref in evidence+provenance:self.s.read_source(ref)
                    native=p.get('native_metrics')
                    dur=native.get('duration_s') if isinstance(native,dict) else None
                    nbytes=mp.get('bytes')
                    # B3-H9: missing measurements are not zero-cost observations.
                    if type(dur) not in (int,float) or type(nbytes) is not int or nbytes<0:break
                    try:
                        if not math.isfinite(dur) or dur<0:break
                    except OverflowError:break
                    comp={'task_gain':1. if p['packet_id'] in coalition_ids else 0.,
                          'uncertainty_reduction':0. if p['offer'].get('needs_reentry') else .5,
                          'source_recovery_gain':.25 if evidence else 0.,
                          'latency_cost':min(dur,LAT_S)/LAT_S*.25,
                          'memory_cost':min(nbytes,BYTES)/BYTES*.25}
                    util=comp['task_gain']+comp['uncertainty_reduction']+comp['source_recovery_gain']-comp['latency_cost']-comp['memory_cost']-(0. if status=='FINAL' else .5)
                    scored.append((m,util,comp))
                    break
                except (ValueError,TypeError,KeyError,AttributeError,OSError,UnicodeError):
                    break  # first matching receiver offer is corrupt: no later substitution
        sc=step(self.n,PATH)  # WP-U6 §12.7
        from .callosum_outcome_once import apply_once
        def fn(st):
            pending=st['pending'].get(event_id) or []
            return apply_once(pending,scored,lambda m,u,c:self._update(st,m['direction'],m['channel'],u,c,sc))
        applied=self._mutate(fn)  # only the winning CAS may count an outcome
        if self.n is not None and applied:
            channels={m['msg']:m['channel'] for m,_,_ in scored}
            try:self.n.touch(PATH,event_id,activity=min(1.,len(applied)/2),detail={'channels':[channels[mid] for mid,_ in applied]})
            except Exception:pass
        return {'scored':len(applied),'utilities':[round(u,3) for _,u in applied]}
    def on_rating(self,event_id,utility):
        """A human rating can score each real source-bound message only once."""
        if type(utility) not in (int,float) or not math.isfinite(utility):
            raise ValueError('Callosum rating must be finite numeric utility')
        u=max(0.,min(1.,float(utility)))
        ev=self.s.one('SELECT generation_id FROM events WHERE id=?',(event_id,))
        if not ev:return {'updated':0}
        st,_=self._load();valid={}
        for m in st['pending'].get(event_id) or []:
            mid=m.get('msg')
            if m.get('rated') or not isinstance(mid,str):continue
            pair=next((p for p,name in DIRECTIONS.items() if name==m.get('direction')),None)
            if not pair or m.get('receiver')!=pair[1] or m.get('channel') not in CHANNELS:continue
            row=self.s.one('SELECT kind,event_id,generation_id,payload FROM packets WHERE id=?',(mid,))
            if not row or row['kind']!='MessagePacket' or row['event_id']!=event_id or row['generation_id']!=ev['generation_id']:
                continue
            try:
                mp=json.loads(row['payload']);refs=mp['source_refs']
                if (mp['packet_id']!=mid or mp['event_id']!=event_id or
                    mp['brain_generation_id']!=ev['generation_id'] or
                    mp['sender']!=pair[0] or mp['receiver']!=pair[1] or
                    mp['channel']!=m['channel'] or not isinstance(refs,list) or
                    refs!=mp['provenance']):
                    continue
                for ref in refs:self.s.read_source(ref)
            except (ValueError,TypeError,KeyError,AttributeError,OSError,UnicodeError):
                continue
            valid[mid]=(m['direction'],m['receiver'],m['channel'])
        if not valid:return {'updated':0}
        sc=step(self.n,PATH)
        def fn(st):
            seen=set();n=0
            for m in st['pending'].get(event_id) or []:
                mid=m.get('msg')
                if (not isinstance(mid,str) or mid not in valid or mid in seen or m.get('rated') or
                    (m.get('direction'),m.get('receiver'),m.get('channel'))!=valid[mid]):
                    continue
                self._update(st,m['direction'],m['channel'],u,None,sc)
                m['rated']=True;seen.add(mid);n+=1
            # A duplicate pending entry for the same real packet must not
            # become a second rating on the next call.
            for m in st['pending'].get(event_id) or []:
                mid=m.get('msg')
                if (isinstance(mid,str) and mid in seen and
                    (m.get('direction'),m.get('receiver'),m.get('channel'))==valid[mid]):
                    m['rated']=True
            return n
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
        return {'revision':REVISION,'mode':st['mode'],'proposal_agreement':round(p['same']/p['n'],3) if p['n'] else None,'directions':self.doctor(cfg),
                'gate':'G-CALLOSUM-UTILITY-002: LATENT blocked (no native L1 receiver path yet)','claim_limit':'Channel choice among exact/control/symbolic baselines; no latent exchange'}

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

def operator_command(r,args):
    """:callosum [status|shadow|active|degrade|promote <direction>]"""
    c=controller(r)
    if not args or args==['status']:return dumps(c.report(r.cfg))
    if args==['shadow']:return dumps({'mode':c.set_mode('SHADOW')})
    if args==['active']:return dumps({'mode':c.set_mode('ACTIVE','EXPLICIT_HUMAN')})
    if args==['degrade']:return dumps({d:{k:x[k] for k in ('degradation_level','status','calibration_valid','degradation')} for d,x in c.doctor(r.cfg).items()})
    if len(args)==2 and args[0]=='promote' and args[1] in b3degrade.RECEIVER:  # typed by the human at the operator console
        return dumps({'direction':args[1],'level':b3degrade.promote(r,args[1],'EXPLICIT_HUMAN')})
    raise ValueError(':callosum [status|shadow|active|degrade|promote B1_TO_B2|B2_TO_B1]')
