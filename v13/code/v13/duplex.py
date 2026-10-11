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

KEY='WP_N14_DUPLEX';REVISION='wp-n14-duplex-v1'
MODES=('auto','interrupt','off')
STOP=re.compile(r"^\s*(stop|stopp|halt|wait|hold on|cancel|never ?mind|forget it|enough|warte|moment|abbrechen|vergiss es|genug|lass das)\b[\s.!,]*$",re.I)
CORRECT=re.compile(r"^\s*(no|nope|actually|i meant|i mean|correction|sorry,? i meant|nein|doch|eigentlich|ich meinte|korrektur|falsch)\b",re.I)
PARTIAL_CHARS=600;MAX_PENDING=16

def decide(text,mode='auto'):
    """Live-path decision for a message that overlaps a running answer -> (decision, relation)."""
    if mode not in MODES:raise ValueError('duplex_mode auto|interrupt|off')
    if mode=='off':return 'CONTINUE','OVERLAP'
    if STOP.match(text):return 'INTERRUPT','STOP'
    if CORRECT.match(text):return 'REVISE','CORRECTION'
    if mode=='interrupt':return 'INTERRUPT','OVERLAP'
    return 'CONTINUE','OVERLAP'

def _load(store):return store.state(KEY,None)[0] or {'revision':REVISION,'pending':{},'interrupted':{},'counters':{'CONTINUE':0,'INTERRUPT':0,'REVISE':0},'last':[]}

def on_input(runtime,new_event_id,text):
    """Called from Runtime.submit while holding the runtime lock: decide and, if needed, signal the cancel. No I/O here."""
    cur=runtime.turn_event if runtime.current=='turn' else None
    if cur is None:return None
    decision,relation=decide(text,runtime.cfg.get('duplex_mode','auto'))
    if decision!='CONTINUE':runtime.cancel_event.set()
    return {'decision':decision,'relation':relation,'from_event':cur['event_id'],'to_event':new_event_id,'at':time.time(),'started':time.monotonic()}

def record(runtime,d):
    """Persist the decision after the lock is released (handoff for the next turn, provisional mark for the cut one)."""
    if not d:return
    s=runtime.store;st=_load(s)
    st['counters'][d['decision']]=st['counters'].get(d['decision'],0)+1
    if d['decision']!='CONTINUE':
        st['pending'][d['to_event']]={k:d[k] for k in ('decision','relation','from_event','at')}
        st['interrupted'][d['from_event']]={'by':d['to_event'],'relation':d['relation']}
        for k in ('pending','interrupted'):
            if len(st[k])>MAX_PENDING:st[k]=dict(list(st[k].items())[-MAX_PENDING:])
    st['last']=(st['last']+[{k:d[k] for k in ('decision','relation','from_event','to_event')}])[-8:]
    s.set_state(KEY,st)
    s.log('duplex',d['to_event'],{'decision':d['decision'],'relation':d['relation'],'mode':runtime.cfg.get('duplex_mode','auto'),
                                   'latency_ms':round((time.monotonic()-d['started'])*1000,3)})

def settle(runtime,e,meta,status):
    """Before the cut answer is finished: mark it provisional so no learner treats it as a hard experience."""
    st=_load(runtime.store);hit=st['interrupted'].get(e['event_id'])
    if hit and status!='FINAL':meta['duplex']={'interrupted_by':hit['by'],'relation':hit['relation'],'provisional':True,'authority':'PROVISIONAL_LIVE_NOT_LEARNED'}
    return meta.get('duplex')

def handoff(runtime,event_id):
    """Handoff block for the turn that cut in: question, partial answer and relation; consumed once."""
    s=runtime.store;st=_load(s);h=st['pending'].pop(event_id,None)
    if not h:return None
    prev=s.one('SELECT source_id,packet FROM events WHERE id=?',(h['from_event'],))
    q=s.one("SELECT text FROM messages WHERE event_id=? AND role='user' ORDER BY id LIMIT 1",(h['from_event'],))
    a=s.one("SELECT text,status FROM messages WHERE event_id=? AND role='assistant' ORDER BY id DESC LIMIT 1",(h['from_event'],))
    s.set_state(KEY,st)
    if not prev or not q:return None
    partial=(a['text'] if a else '')[:PARTIAL_CHARS]
    body={'relation':h['relation'],'interrupted_question':q['text'][:PARTIAL_CHARS],'partial_answer':partial,
          'partial_answer_status':(a['status'] if a else 'NONE'),'note':'The previous answer was cut off by the user; it is provisional, not a fact.'}
    refs=[json.loads(prev['packet'])['source_ref']]
    if partial:refs.append(s.source(partial,'PROVISIONAL_INTERRUPTED_OUTPUT'))
    return {'body':body,'source_refs':refs}

def status(runtime):
    st=_load(runtime.store)
    return {'revision':REVISION,'mode':runtime.cfg.get('duplex_mode','auto'),'counters':st['counters'],'pending_handoffs':len(st['pending']),'last':st['last'],
            'claim_limit':'Text timeline only; audio/video full duplex is STEP 11'}

def operator_command(r,args):
    if not args or args==['status']:return status(r)
    raise ValueError(':duplex [status|auto|interrupt|off]')
