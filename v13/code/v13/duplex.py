"""WP-N14 Live / full-duplex in text (§4A.4 shared timeline, G10D live path, §24.30).

Input keeps flowing while V13 answers. When a new message arrives during a running answer the live path decides
at once, without waiting for A/B, memory or tools:
  CONTINUE  ordinary turn-taking: the running answer finishes, the new message is queued (default for plain input)
  INTERRUPT explicit stop/cancel cue ("stop", "wait", "never mind", "stopp", "warte"): the running answer ends now
  REVISE    correction cue with content ("no, I meant …", "actually …", "nein, …"): end now and answer the revision
duplex_mode: auto (cues as above) | interrupt (any overlapping message interrupts) | off (pure turn-taking).

Provisional vs authoritative (§4A.4): an interrupted answer keeps its text for the chat display but stays CANCELLED
and is marked `provisional` in its metadata; native history, implicit ratings and weight consolidation already take
FINAL answers only, so it is never learned as a hard experience. The next turn gets a handoff block (what was asked,
how far the answer got, how the new message relates) plus the interrupted source reference, so no valid source
state is lost across the cut. The decision is a pure function on the submit path (no I/O under the runtime lock).
Claim limit: text timeline only; audio/video streams, barge-in on speech and sub-second JEF speak/listen control
remain STEP 11.
"""
import json
import re
import time
import threading
import weakref

KEY='WP_N14_DUPLEX';REVISION='wp-n14-duplex-v1'
MODES=('auto','interrupt','off')
STOP=re.compile(r"^\s*(stop|stopp|halt|wait|hold on|cancel|never ?mind|forget it|enough|warte|moment|abbrechen|vergiss es|genug|lass das)\b[\s.!,]*$",re.I)
CORRECT=re.compile(r"^\s*(no|nope|actually|i meant|i mean|correction|sorry,? i meant|nein|doch|eigentlich|ich meinte|korrektur|falsch)\b",re.I)
PARTIAL_CHARS=600;MAX_PENDING=16
_CAS_RETRIES=32
_AUDIO_HANDOFF_LOCKS=weakref.WeakKeyDictionary()
_AUDIO_HANDOFF_LOCKS_GUARD=threading.Lock()


def audio_handoff_lock(runtime):
    """Serialize audio handoff publication with the next-turn handoff reader."""
    with _AUDIO_HANDOFF_LOCKS_GUARD:
        lock=_AUDIO_HANDOFF_LOCKS.get(runtime)
        if lock is None:
            lock=threading.RLock()
            _AUDIO_HANDOFF_LOCKS[runtime]=lock
        return lock


def _default_state():
    return {'revision':REVISION,'pending':{},'interrupted':{},
            'counters':{'CONTINUE':0,'INTERRUPT':0,'REVISE':0},'last':[]}


def _read_state(store):
    state,version=store.state(KEY,None)
    if state is None:
        state=_default_state()
    if type(state) is not dict:
        raise ValueError('duplex state is corrupt')
    defaults=_default_state()
    for key,default in defaults.items():
        state.setdefault(key,default)
        if type(state[key]) is not type(default):
            raise ValueError('duplex state is corrupt')
    return state,version

def decide(text,mode='auto'):
    """Live-path decision for a message that overlaps a running answer -> (decision, relation)."""
    if mode not in MODES:raise ValueError('duplex_mode auto|interrupt|off')
    if mode=='off':return 'CONTINUE','OVERLAP'
    if STOP.match(text):return 'INTERRUPT','STOP'
    if CORRECT.match(text):return 'REVISE','CORRECTION'
    if mode=='interrupt':return 'INTERRUPT','OVERLAP'
    return 'CONTINUE','OVERLAP'

def _load(store):
    return _read_state(store)[0]

def on_input(runtime,new_event_id,text):
    """Called from Runtime.submit while holding the runtime lock: decide and, if needed, signal the cancel. No I/O here."""
    cur=runtime.turn_event if runtime.current=='turn' else None
    if cur is None:return None
    decision,relation=decide(text,runtime.cfg.get('duplex_mode','auto'))
    if decision!='CONTINUE':runtime.cancel_event.set()
    return {'decision':decision,'relation':relation,'from_event':cur['event_id'],'to_event':new_event_id,'at':time.time(),'started':time.monotonic()}

def record(runtime,d):
    """Persist one overlap decision with CAS and first-writer target ownership."""
    if not d:return False
    s=runtime.store
    decision=d.get('decision')
    if decision not in ('CONTINUE','INTERRUPT','REVISE'):
        raise ValueError('invalid duplex decision')
    for _ in range(_CAS_RETRIES):
        st,version=_read_state(s)
        if decision!='CONTINUE':
            from_event=d.get('from_event');to_event=d.get('to_event')
            if type(from_event) is not str or not from_event or type(to_event) is not str or not to_event:
                raise ValueError('duplex target event identity is invalid')
            already_targeted=(
                from_event in st['interrupted']
                or any(type(item) is dict and item.get('from_event')==from_event
                       for item in st['pending'].values())
            )
            if already_targeted or to_event in st['pending']:
                return False
            st['pending'][to_event]={k:d[k] for k in ('decision','relation','from_event','at')}
            st['interrupted'][from_event]={'by':to_event,'relation':d['relation']}
            for key in ('pending','interrupted'):
                if len(st[key])>MAX_PENDING:
                    st[key]=dict(list(st[key].items())[-MAX_PENDING:])
        st['counters'][decision]=st['counters'].get(decision,0)+1
        st['last']=(st['last']+[
            {k:d[k] for k in ('decision','relation','from_event','to_event')}
        ])[-8:]
        try:
            s.set_state(KEY,st,expected=version)
            break
        except ValueError:
            continue
    else:
        raise RuntimeError('duplex state CAS contention')
    try:
        s.log('duplex',d['to_event'],{
            'decision':decision,'relation':d['relation'],
            'mode':runtime.cfg.get('duplex_mode','auto'),
            'latency_ms':round((time.monotonic()-d['started'])*1000,3),
        })
    except Exception:
        # Durable state is authoritative; telemetry failure must not undo it.
        pass
    return True


def rollback_record(runtime,d):
    """Remove only this call's unconsumed handoff if its target turn changed."""
    if not d:return False
    with audio_handoff_lock(runtime):
        s=runtime.store
        from_event=d['from_event'];to_event=d['to_event'];relation=d['relation']
        for _ in range(_CAS_RETRIES):
            st,version=_read_state(s)
            pending=st['pending'].get(to_event)
            interrupted=st['interrupted'].get(from_event)
            if (type(pending) is not dict or pending.get('from_event')!=from_event
                    or pending.get('relation')!=relation
                    or type(interrupted) is not dict
                    or interrupted.get('by')!=to_event
                    or interrupted.get('relation')!=relation):
                return False
            st['pending'].pop(to_event,None)
            st['interrupted'].pop(from_event,None)
            count=st['counters'].get(d['decision'],0)
            if type(count) is int and count>0:
                st['counters'][d['decision']]=count-1
            for index in range(len(st['last'])-1,-1,-1):
                item=st['last'][index]
                if item.get('from_event')==from_event and item.get('to_event')==to_event:
                    del st['last'][index]
                    break
            try:
                s.set_state(KEY,st,expected=version)
                break
            except ValueError:
                continue
        else:
            raise RuntimeError('duplex rollback CAS contention')
        try:s.log('duplex_rollback',to_event,{'decision':d['decision'],'relation':relation})
        except Exception:pass
        return True

def settle(runtime,e,meta,status):
    """Before the cut answer is finished: mark it provisional so no learner treats it as a hard experience."""
    st=_load(runtime.store);hit=st['interrupted'].get(e['event_id'])
    if hit and status!='FINAL':meta['duplex']={'interrupted_by':hit['by'],'relation':hit['relation'],'provisional':True,'authority':'PROVISIONAL_LIVE_NOT_LEARNED'}
    return meta.get('duplex')

def handoff(runtime,event_id):
    """Consume a durable handoff only after its context/source is prepared.

    A missing previous event/message, malformed packet or source-write failure
    must not silently consume the only pending handoff. The pending row remains
    retryable until every fallible read and source publication has succeeded.
    """
    with audio_handoff_lock(runtime):
        s=runtime.store
        state,_version=_read_state(s)
        h=state['pending'].get(event_id)
        if not h:return None

        # Prepare before the CAS consume. In particular, do not pop pending
        # before querying the previous turn or publishing its partial-output
        # SourceRef: either operation can fail independently.
        prev=s.one('SELECT source_id,packet FROM events WHERE id=?',(h['from_event'],))
        q=s.one("SELECT text FROM messages WHERE event_id=? AND role='user' ORDER BY id LIMIT 1",(h['from_event'],))
        a=s.one("SELECT text,status FROM messages WHERE event_id=? AND role='assistant' ORDER BY id DESC LIMIT 1",(h['from_event'],))
        if not prev or not q:return None

        packet=json.loads(prev['packet'])
        source_ref=packet.get('source_ref')
        if type(source_ref) is not dict:
            raise ValueError('duplex handoff source reference is invalid')
        partial=(a['text'] if a else '')[:PARTIAL_CHARS]
        body={'relation':h['relation'],'interrupted_question':q['text'][:PARTIAL_CHARS],'partial_answer':partial,
              'partial_answer_status':(a['status'] if a else 'NONE'),'note':'The previous answer was cut off by the user; it is provisional, not a fact.'}
        refs=[source_ref]
        if partial:refs.append(s.source(partial,'PROVISIONAL_INTERRUPTED_OUTPUT'))

        # Re-read after preparation so unrelated Store writes cannot make a
        # stale version consume a changed/replaced handoff. CAS retries reuse
        # the already-created SourceRef rather than publishing duplicates.
        for _ in range(_CAS_RETRIES):
            st,version=_read_state(s)
            if st['pending'].get(event_id)!=h:return None
            st['pending'].pop(event_id,None)
            try:
                s.set_state(KEY,st,expected=version)
                return {'body':body,'source_refs':refs}
            except ValueError:
                continue
        raise RuntimeError('duplex handoff CAS contention')


def status(runtime):
    st=_load(runtime.store)
    return {'revision':REVISION,'mode':runtime.cfg.get('duplex_mode','auto'),'counters':st['counters'],'pending_handoffs':len(st['pending']),'last':st['last'],
            'claim_limit':'Text timeline only; audio/video full duplex is STEP 11'}

def operator_command(r,args):
    if not args or args==['status']:return status(r)
    raise ValueError(':duplex [status|auto|interrupt|off]')
