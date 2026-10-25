"""WP-U3 F2 §5.2: a late internal offer interrupts running output.

While C3 streams the answer, one body that gave no pre-answer offer (B1 first) runs in a background thread. When its
offer arrives before the answer ends, it is compared once with the partial answer:
  RESULT_CONFLICT  the body derived numbers that are not in the source, the partial answer derived other ones, none shared
  BODY_REENTRY     the body flags a material unresolved issue (needs_reentry) and quotes the source
Modes (state LATE_WATCH, :latewatch): off | shadow (default: only records 'would interrupt at char N') | active (the
stream stops, the cut part stays marked provisional and C3 continues with the late finding, correcting or finishing).
The parallel body only starts when C3 keeps its process: body fabric on (body_residency_mb>0), C3 pinned and the body
fits next to it in the current budget, resource state NORMAL, C3 in server decode (causal streams are exclusive).
Otherwise the turn records NO_RESIDENCY and the old post-commit path (selfmodel.late_offer) stays the only late check.
An offer that arrives after the output ended goes to selfmodel.late_offer as before (gated self-message, answer kept).
"""
import re
import threading
import time

KEY='LATE_WATCH';MODES=('off','shadow','active');DEFAULT='shadow';MAX_LOG=200
MIN_CHARS=24            # never cut before the answer has said something (BOOT, not tuned)
REENTRY_CHARS=48        # needs_reentry alone is weaker evidence: cut only later
REVISION_TOKENS=160     # continuation budget after a cut
JOIN_S=2.               # how long the turn waits at most for a still running body at the end of the stream

def _state(store):return store.state(KEY)[0] or {'mode':DEFAULT,'log':[],'counts':{}}

def _mutate(store,fn):
    for attempt in (0,1):
        st,v=store.state(KEY);st=st or {'mode':DEFAULT,'log':[],'counts':{}};out=fn(st)
        try:store.set_state(KEY,st,expected=v);return out
        except ValueError:
            if attempt:raise

def mode(store):return _state(store).get('mode',DEFAULT)

def set_mode(store,m):
    if m not in MODES:raise ValueError(':latewatch off|shadow|active')
    _mutate(store,lambda st:st.__setitem__('mode',m));return m

def _record(store,row):
    def f(st):
        st['log']=(st['log']+[row])[-MAX_LOG:];c=st.setdefault('counts',{});c[row['status']]=c.get(row['status'],0)+1
    try:_mutate(store,f)
    except Exception:pass

_NUM=re.compile(r'\d+(?:[.,]\d+)?')
_THOUSANDS=re.compile(r'(?<![\d.,])\d{1,3}(?:,\d{3})+(?!\d|,\d)')  # 1,234 / 12,345,678 (groups of three) = integers
_TAIL=re.compile(r'\d[\d.,]*$')
def nums(t):
    t=_THOUSANDS.sub(lambda m:m.group(0).replace(',',''),t or '')
    return {x.replace(',','.') for x in _NUM.findall(t)}

def complete(partial):
    """The partial answer without a number that may still be growing at its end (the next check sees it whole)."""
    return _TAIL.sub('',partial or '')

def disagreement(offer,partial,source,final=False):
    """Check a late offer; only a completed stream may score its numeric tail."""
    o=(offer or {}).get('offer',{});src=nums(source)
    body_new=nums(o.get('summary',''))-src;out_new=nums(partial if final else complete(partial))-src
    if len(partial)>=MIN_CHARS and body_new and out_new and not body_new&out_new:return 'RESULT_CONFLICT'
    if len(partial)>=REENTRY_CHARS and o.get('needs_reentry') and o.get('quotes'):return 'BODY_REENTRY'
    return None

def residency(r,role):
    """Can ``role`` run next to the streaming C3 without evicting it? Returns None if yes, else a reason."""
    if r.cfg.get('c3_decode_mode','server')!='server':return 'C3_EXCLUSIVE_DECODE'
    fab=getattr(r.pool,'fabric',None)
    if fab is None or not getattr(fab,'enabled',False):return 'NO_RESIDENCY'
    try:
        from .bodies import PINNED,PRESSURE_MODE
        from .agi.residency import PRESSURE_SHARE
        st=fab.residency.box.load()[0];ex=st['experts']
        if 'C3_LANGUAGE' not in PINNED or role not in ex:return 'NO_RESIDENCY'
        if role in st['resident']:return None
        cap=st['budget_mb']*PRESSURE_SHARE[PRESSURE_MODE.get(getattr(r.guard,'state','NORMAL'),'GREEN')]
        pinned=sum(ex[x]['size_mb'] for x in st['resident'] if ex.get(x,{}).get('pinned'))
        return None if pinned+ex[role]['size_mb']<=cap else 'NO_RESIDENCY'
    except Exception:return 'NO_RESIDENCY'

class Watcher:
    """One late body offer per turn. check() runs in the token loop and must stay cheap."""
    def __init__(self,r,e,meta,m,role=None,status='OFF'):
        self.r=r;self.e=e;self.meta=meta;self.mode=m;self.role=role;self.status=status
        self.offer=None;self.error=None;self.thread=None;self.done=threading.Event();self.decided=False;self.cut=None
        self.info=meta.setdefault('late_watch',{'mode':m,'status':status,**({'role':role} if role else {})})
    def _run(self,version,offer_deadline,valid_until):
        try:self.offer=self.r.cognition.offer(self.role,self.e,version,offer_deadline,None,valid_until=valid_until)
        except BaseException as exc:self.error=type(exc).__name__
        finally:self.done.set()
    def start(self,version,offer_deadline,valid_until):
        self.thread=threading.Thread(target=self._run,args=(version,offer_deadline,valid_until),daemon=True,name='latewatch')
        self.status=self.info['status']='RUNNING';self.info['offered']=self.role;self.thread.start();return self
    def check(self,output):
        """True = stop the stream now (ACTIVE and a disagreeing offer arrived)."""
        if self.decided or self.thread is None or not self.done.is_set():return False
        if self.offer is None:self.decided=True;return False
        reason=disagreement(self.offer,output,self.r.store.read_source(self.e['source_ref']))
        if reason is None:
            if len(output)<REENTRY_CHARS:return False  # too early to judge: look again when more text exists
            self.decided=True;self._close('AGREES',len(output));return False
        self.decided=True;self.cut={'at_char':len(output),'reason':reason}
        self._close('INTERRUPTED' if self.mode=='active' else 'WOULD_INTERRUPT',len(output),reason)
        return self.mode=='active'
    def _close(self,status,at_char,reason=None):
        self.status=status;self.info.update(status=status,at_char=at_char,**({'reason':reason} if reason else {}))
        if self.offer:self.info['offer_id']=self.offer.get('packet_id')
    def finish(self,runner,messages,output,deadline,mid):
        """After the stream. ACTIVE cut: C3 continues with the late finding (appended, returned). Otherwise an offer that
        arrived too late for the stream goes the old post-commit way (gated self-message, answer kept)."""
        extra=''
        if self.thread is None:
            _record(self.r.store,{'event_id':self.e['event_id'],'status':self.status,'mode':self.mode,'ts':time.time()});return extra
        if not self.decided:
            self.done.wait(max(0.,min(JOIN_S,deadline-time.monotonic())))
            if self.offer is not None and not self.decided:
                reason=disagreement(self.offer,output,self.r.store.read_source(self.e['source_ref']),final=True)
                self._close('AFTER_OUTPUT',len(output),reason)
            elif self.offer is None:self._close('NO_OFFER' if self.done.is_set() else 'STILL_RUNNING',len(output))
            if self.error:self.info['error']=self.error
        if self.status in ('AFTER_OUTPUT','WOULD_INTERRUPT'):  # the answer stays: the old gated self-message carries the doubt
            try:
                from . import selfmodel
                selfmodel.controller(self.r).late_offer(self.e['event_id'],self.offer,output)
            except Exception as exc:self.r.store.log('self_unavailable',self.e['event_id'],{'stage':'late_offer','error':type(exc).__name__})
        if self.status=='INTERRUPTED':
            o=self.offer.get('offer',{})
            note=('(internal check, not the user) A late '+self.role+' check of the source found: '+o.get('summary','')[:300]+
                  (' Quote: '+o['quotes'][0][:120] if o.get('quotes') else '')+' Continue your answer: correct it briefly if the check shows it is wrong, otherwise finish it.')
            revise=list(messages)+[{'role':'assistant','content':output},{'role':'user','content':note}]
            head='\n\n(Revised after a late internal check) '
            from .common import safe_text
            try:
                for tok in runner.generate(revise,self.r.cancel_event,deadline,REVISION_TOKENS):
                    clean=safe_text(tok)
                    if not clean:continue
                    if not extra:self.r.store.append_message(mid,head);extra=head
                    self.r.store.append_message(mid,clean);extra+=clean
            except Exception as exc:self.info['revision_error']=type(exc).__name__
            self.info.update(provisional_chars=self.cut['at_char'],revision_chars=len(extra))
        _record(self.r.store,{'event_id':self.e['event_id'],'status':self.status,'mode':self.mode,'role':self.role,'ts':time.time(),
                              **{k:self.info[k] for k in ('at_char','reason','offer_id','provisional_chars','revision_chars') if k in self.info}})
        return extra

def start(r,e,version,offers,deadline,meta,runner,eligible=True):
    """Called right before the C3 token loop. Never raises; always returns a Watcher (inert unless a body runs)."""
    try:
        m=mode(r.store)
        if m=='off':return Watcher(r,e,meta,m,status='OFF')
        if not eligible or getattr(runner,'role',None)!='C3_LANGUAGE' or r.cfg.get('observer_mode')=='off':return Watcher(r,e,meta,m,status='NOT_ELIGIBLE')
        have={p.get('role') for p in offers if isinstance(p,dict)}
        role=next((x for x in ('B1_DETAIL','B2_GIST') if x not in have),None)
        if role is None:return Watcher(r,e,meta,m,status='ALL_BODIES_OFFERED')
        why=residency(r,role)
        if why:return Watcher(r,e,meta,m,role,status=why)
        now=time.monotonic();offer_deadline=min(deadline,now+r.cfg['observer_seconds'])
        return Watcher(r,e,meta,m,role).start(version,offer_deadline,deadline)
    except Exception as exc:
        r.store.log('latewatch_unavailable',e['event_id'],{'error':type(exc).__name__})
        return Watcher(r,e,meta,'off',status='UNAVAILABLE')

def report(r):
    st=_state(r.store)
    return {'mode':st.get('mode',DEFAULT),'counts':st.get('counts',{}),'recent':st.get('log',[])[-10:],
            'claim_limit':'Late body offers during C3 output; parallel only when C3 stays resident. Cut criteria are BOOT rules (numbers / needs_reentry), not learned salience.'}
