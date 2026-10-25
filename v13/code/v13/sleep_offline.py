"""WP-S7: Sleep with offline compute (extension of WP-E Sleep A; sleep-time compute idea, arXiv 2605.26099).

Runs inside a full / a sleep after replay, between checkpoints (user input cancels it, RED = no sleep, YELLOW = skipped):
  1. Re-encode the day: per session an extractive digest of the turns since the last digest (context_os.compress,
     exact spans pinned, lineage-checked through history.native_history so deleted sources never appear).
     The digest is a warm, source-anchored context aid with fact authority 0; `:sleep digest` shows it.
  2. Predictor updates: low-rate extra passes of the cerebellar fast-forward predictor (WP-F) over stored outcomes,
     kept only when the held-out error does not rise.
  3. Context -> LoRA (TTT) candidates: digest-conditioned (context, answer) pairs from FINAL turns are *staged* to
     exports/sleep-ttt-candidates.jsonl for the WP-I train runner. No weight update here; `:pause training` and the
     Age right `small_shadow_update` gate staging for system-initiated sleeps.
"""
import json
from .common import dumps,atomic_write
from .context_os import compress

KEY='S7_DAY_DIGEST';REVISION='s7-digest-v1'
TURN_CAP=160;SESSIONS_MAX=8;TURNS_MAX=64;ENTRIES_MAX=96;TTT_MAX=256

def empty():return {'revision':REVISION,'sessions':{},'runs':0}

def line(user,answer):
    """One digest line. Short answers without exact content are left out: in the cloud bench a repeated
    'A: Noted ...' made small bodies copy the acknowledgement instead of answering (digest-context-20261009)."""
    from .context_os import exact_spans
    keep=bool(exact_spans(answer)) or len(answer)>60
    return '- user: '+user+('  (answer: '+answer+')' if keep else '')

def _load(store):
    st,v=store.state(KEY,None)
    if st is None:st=empty()
    if st.get('revision')!=REVISION:raise ValueError('Digest state revision mismatch')
    return st,v

def digest(store,checkpoint=None):
    """Extractive day digest per session; only turns newer than the last digest."""
    from .history import native_history
    st,v=_load(store);out={'sessions':0,'turns':0,'compressed':0}
    rows=store.rows("SELECT session_id,MAX(id) AS last FROM messages WHERE role='assistant' AND status='FINAL' GROUP BY session_id ORDER BY last DESC LIMIT ?",(SESSIONS_MAX,))
    for r in rows:
        sess=r['session_id'];d=st['sessions'].setdefault(sess,{'until':0,'entries':[]})
        if r['last']<=d['until']:continue
        if checkpoint:checkpoint()
        recs,_=native_history(store,sess,'',TURNS_MAX)
        pairs={}
        for m in recs:pairs.setdefault(m['event_id'],{})[m['role']]=m
        new=[p for p in pairs.values() if p['assistant']['id']>d['until']]
        for p in sorted(new,key=lambda p:p['assistant']['id']):
            u,us,uok=compress(p['user']['text'],TURN_CAP);a,as_,aok=compress(p['assistant']['text'],TURN_CAP)
            d['entries'].append({'event_id':p['user']['event_id'],'user':u if uok or len(u)<=TURN_CAP*2 else u[:TURN_CAP*2],'answer':a if aok or len(a)<=TURN_CAP*2 else a[:TURN_CAP*2],
                                 'exact':us+as_,'msg':p['assistant']['id']})
            out['turns']+=1;out['compressed']+=int(uok)+int(aok)
        d['entries']=d['entries'][-ENTRIES_MAX:];d['until']=r['last'];out['sessions']+=1
    st['runs']+=1;store.set_state(KEY,st,expected=v)
    return out

def view(store,session,cap=1200):
    """Digest text for a session (warm context aid; authority 0)."""
    d=_load(store)[0]['sessions'].get(session)
    if not d:return None
    # The operator-visible digest is also an information output. A persisted
    # cache is not source authority: apply the same live history/source checks
    # as the C3 context and sleep-time TTT staging paths before showing text.
    checked=_checked_digest_entries(store,session,d.get('entries'))
    valid=[e for item in checked if item is not None for e,_,_ in (item,)]
    lines=[];n=0
    for e in reversed(valid):
        ln=line(e['user'],e['answer'])
        if n+len(ln)>cap:break
        lines.append(ln);n+=len(ln)
    return {'session':session,'text':'\n'.join(reversed(lines)),'entries':len(valid),'fact_authority':0}

def _checked_digest_entries(store,session,entries):
    """Validate a persisted digest against the live, source-bound history path.

    Return aligned entries or None. A deleted query, revoked answer dependency,
    wrong event/message ID, cross-session row, or altered digest is not context.
    """
    from .history import native_history
    if not isinstance(entries,list):return []
    ents=entries[-ENTRIES_MAX:]
    if not ents:return []
    recs,_=native_history(store,session,'',max(TURNS_MAX,len(ents)+1))
    pairs={}
    for m in recs:
        pairs.setdefault(m['event_id'],{})[m['role']]=m
    def packed(text):
        value,_,ok=compress(text,TURN_CAP)
        return value if ok or len(value)<=TURN_CAP*2 else value[:TURN_CAP*2]
    checked=[]
    for e in ents:
        if (not isinstance(e,dict) or type(e.get('event_id')) is not str
                or type(e.get('msg')) is not int):
            checked.append(None);continue
        pair=pairs.get(e['event_id'],{})
        u=pair.get('user');a=pair.get('assistant')
        if not u or not a or a['id']!=e['msg']:
            checked.append(None);continue
        if e.get('user')!=packed(u['text']) or e.get('answer')!=packed(a['text']):
            checked.append(None);continue
        checked.append((e,u,a))
    return checked

def context_items(store,session,exclude_ids=(),cap=1200):
    """Source-verified compressed history for the live C3 context (§8.3).

    The digest state has no independent fact authority. The same history
    source/rule revocation and exact-text checks apply as to native_history.
    """
    d=_load(store)[0]['sessions'].get(session)
    if not d:return []
    checked=_checked_digest_entries(store,session,d.get('entries'))
    skip=set(exclude_ids);out=[];n=0
    for entry in reversed(checked):
        if entry is None:continue
        e,_,_=entry
        if e['event_id'] in skip:continue
        ln=line(e['user'],e['answer'])
        if n+len(ln)>cap:break
        out.append(ln);n+=len(ln)
    return list(reversed(out))

def stage_ttt(store,home,checkpoint=None):
    """Stage context->LoRA candidates only from currently source-valid FINAL turns.

    A digest is an untrusted, revocable context cache, never a training label.
    Recheck the actual native-history source/answer lineage and recompute its
    extractive compression before reusing a persisted digest entry. This is a
    staging-time check, NOT authorization to train a later stale export.
    """
    st=_load(store)[0];path=home/'exports/sleep-ttt-candidates.jsonl';rows=[]
    for sess,d in st['sessions'].items():
        checked=_checked_digest_entries(store,sess,d.get('entries'))
        for i,entry in enumerate(checked[1:],1):
            if checkpoint and i%16==0:checkpoint()
            if entry is None:continue
            prior=[x[0] for x in checked[max(0,i-4):i] if x is not None]
            if not prior:continue  # a context-conditioned example needs valid earlier context
            e,u,a=entry
            try:
                if not json.loads(a['metadata']).get('model_generated'):continue
            except (TypeError,ValueError):continue
            ctx='\n'.join('U: '+x['user']+' | A: '+x['answer'] for x in prior)
            rows.append({'session':sess,'event_id':e['event_id'],'context':ctx,'input':u['text'],'target':a['text'],
                         'status':'CANDIDATE_NOT_TRAINED','label_source':'own_final_answer','origin':'self','requires':'WP-I retention gate + human approval'})
    rows=rows[-TTT_MAX:]
    atomic_write(path,''.join(dumps(r)+'\n' for r in rows))
    return {'candidates':len(rows),'path':str(path)}

def run(cycle,state,cancel,deadline,resource,origin):
    """Sleep phase SLEEP_A_OFFLINE. cycle is the SleepCycle (store, home, checkpoints, Age rights)."""
    rep={'phase':'SLEEP_A_OFFLINE','status':'DONE','fact_write_authority':0,'weight_updates':False}
    cp=lambda:cycle._checkpoint(cancel,deadline,resource)
    try:
        cp();rep['digest']=digest(cycle.s,cp)
        try:
            from .fastforward import FastForward
            cp();rep['predictor']=FastForward(cycle.s).consolidate(checkpoint=cp)
        except (ImportError,ValueError) as exc:rep['predictor']={'status':'UNAVAILABLE','error':type(exc).__name__}
        from .inputs import paused
        if paused(cycle.s,'training'):rep['ttt']={'status':'SKIPPED_PAUSED_TRAINING'}
        elif origin!='USER' and not cycle._allowed('small_shadow_update',state):rep['ttt']={'status':'SKIPPED_AGE_RIGHT','right':'small_shadow_update'}
        else:cp();rep['ttt']=stage_ttt(cycle.s,cycle.home,cp)
    except Exception as exc:
        from .common import Cancelled
        if isinstance(exc,(Cancelled,TimeoutError,ResourceWarning)):rep['status']='INTERRUPTED';rep['reason']=type(exc).__name__
        else:rep['status']='ERROR';rep['error']=type(exc).__name__+': '+str(exc)[:200]
    return rep
