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
    """Extractive day digest per session, bounded by oldest *user* events.

    An assistant may finish after hundreds of later user rows. A message-ID
    high-water would either skip those users or permanently stall at the
    128-row scan limit. A user-event cursor never crosses an unfinished user.
    """
    from .history import native_history
    st,v=_load(store);out={'sessions':0,'turns':0,'compressed':0}
    def user_cursor(sess,d):
        if 'user_until' not in d:
            # Legacy v1 until was a safe assistant-ID high-water: all earlier
            # user rows had already been settled or source-rejected. Migrate
            # only those older users, never assume a later answer completed.
            old=d.get('until',0)
            if type(old) is not int or old<0:
                raise ValueError('S7 legacy high-water invalid')
            row=store.one(
                "SELECT COALESCE(MAX(id),0) AS last FROM messages "
                "WHERE session_id=? AND role='user' AND id<=?",(sess,old))
            d['user_until']=int(row['last'] or 0)
        return d['user_until']
    # Pending sessions are selected by user chronology, not the position of
    # FINAL assistant rows. A delayed answer cannot hide a pending user.
    candidates=store.rows(
        "SELECT session_id,MAX(id) AS last FROM messages "
        "WHERE role='user' GROUP BY session_id")
    pending=[r for r in candidates if
             r['last']>user_cursor(r['session_id'],
                st['sessions'].get(r['session_id'],{'until':0}))]
    attempts=st.setdefault('session_attempts',{})
    pending.sort(key=lambda r:(attempts.get(r['session_id'],-1),
                               user_cursor(r['session_id'],
                                   st['sessions'].get(r['session_id'],{'until':0})),
                               r['last'],r['session_id']))
    for r in pending[:SESSIONS_MAX]:
        sess=r['session_id'];attempts[sess]=st['runs']
        d=st['sessions'].setdefault(sess,{'until':0,'user_until':0,'entries':[]})
        cursor=user_cursor(sess,d)
        if r['last']<=cursor:continue
        if checkpoint:checkpoint()
        users=store.rows(
            "SELECT id,event_id,role,status FROM messages "
            "WHERE session_id=? AND role='user' AND id>? ORDER BY id LIMIT ?",
            (sess,cursor,TURNS_MAX))
        if not users:continue
        ids=[u['event_id'] for u in users]
        placeholders=','.join('?' for _ in ids)
        # Bound the event lookup even if a corrupted event has thousands of
        # duplicate assistant rows. Extra rows fail closed, never advance.
        rows=store.rows(
            "SELECT id,event_id,role,status FROM messages "
            "WHERE session_id=? AND event_id IN ("+placeholders+") "
            "ORDER BY id LIMIT ?",(sess,*ids,2*TURNS_MAX+1))
        if len(rows)>2*len(users):continue
        groups={}
        for row in rows:groups.setdefault(row['event_id'],[]).append(row)
        settled=[]
        for u in users:
            pair=groups.get(u['event_id'],[])
            if len(pair)!=2:break
            us=[x for x in pair if x['role']=='user']
            answers=[x for x in pair if x['role']=='assistant']
            if len(us)!=1 or len(answers)!=1:break
            a=answers[0]
            if (us[0]['id']!=u['id'] or u['status']!='FINAL'
                    or u['id']>=a['id']
                    or a['status'] not in ('FINAL','CANCELLED','DEADLINE','ERROR','INTERRUPTED')):
                break
            settled.append(u)
        if len(settled)<len(users):
            # Preserve the original conservative interleaving barrier:
            # a later unfinished user row cannot be crossed by an earlier
            # assistant completion. The user cursor would not lose it, but
            # existing S7 acceptance requires waiting for that predecessor.
            barrier=users[len(settled)]['id']
            if any(any(row['role']=='assistant' and row['id']>=barrier
                       for row in groups.get(u['event_id'],[]))
                   for u in settled):
                continue
        elif len(users)==TURNS_MAX:
            # A pending predecessor can sit just beyond the 64-user page.
            # If an assistant from this page finished after that user row,
            # the original barrier still applies. Check the crossed interval
            # in SQLite, without materializing unbounded source text/history.
            latest=max(row['id'] for u in settled
                       for row in groups[u['event_id']]
                       if row['role']=='assistant')
            # One grouped pass over this session, not a correlated per-user
            # scan (which is quadratic without a messages(event_id) index).
            # The CTE includes assistants beyond 'latest' so an already
            # settled crossed user is never mistaken for a pending one.
            crossed=store.one(
                "WITH event_counts AS ("
                "SELECT event_id,COUNT(*) AS n,"
                "SUM(CASE WHEN role='assistant' AND status IN "
                "('FINAL','CANCELLED','DEADLINE','ERROR','INTERRUPTED') "
                "THEN 1 ELSE 0 END) AS terminal,"
                "MIN(CASE WHEN role='assistant' THEN id END) AS assistant_id "
                "FROM messages WHERE session_id=? AND role IN ('user','assistant') "
                "GROUP BY event_id) "
                "SELECT u.id FROM messages u JOIN event_counts e ON e.event_id=u.event_id "
                "WHERE u.session_id=? AND u.role='user' AND u.id>? AND u.id<=? "
                "AND (u.status!='FINAL' OR e.n!=2 OR e.terminal!=1 "
                "OR e.assistant_id<=u.id) ORDER BY u.id LIMIT 1",
                (sess,sess,users[-1]['id'],latest))
            if crossed:continue
        if not settled:continue
        # Source/rule revocation, exact source bytes, event session, answer
        # lineage and duplicate-row counts remain enforced by native_history.
        recs,_=native_history(store,sess,'',len(settled),
                              event_ids=[u['event_id'] for u in settled])
        pairs={}
        for m in recs:pairs.setdefault(m['event_id'],{})[m['role']]=m
        for urow in settled:
            p=pairs.get(urow['event_id'])
            if not p or 'user' not in p or 'assistant' not in p:continue
            u,a=p['user'],p['assistant']
            utext,us,uok=compress(u['text'],TURN_CAP)
            atext,ans,aok=compress(a['text'],TURN_CAP)
            d['entries'].append({
                'event_id':u['event_id'],
                'user':utext if uok or len(utext)<=TURN_CAP*2 else utext[:TURN_CAP*2],
                'answer':atext if aok or len(atext)<=TURN_CAP*2 else atext[:TURN_CAP*2],
                'exact':us+ans,'msg':a['id']})
            out['turns']+=1;out['compressed']+=int(uok)+int(aok)
        d['entries']=d['entries'][-ENTRIES_MAX:]
        d['user_until']=settled[-1]['id']
        # Retain monotone legacy field for diagnostics; it is never used to
        # page future users, because assistant completion order is arbitrary.
        d['until']=max(d.get('until',0),d['user_until'])
        out['sessions']+=1
    st['session_attempts']={
        r['session_id']:attempts[r['session_id']] for r in pending
        if r['last']>user_cursor(r['session_id'],
             st['sessions'].get(r['session_id'],{'until':0}))
        and r['session_id'] in attempts}
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
    # A latest-message window drops older user rows when many FINAL answers
    # arrive in reverse order. Revalidate each retained event by exact ID,
    # still using native_history's source/rule/answer checks and bounded batches.
    # One malformed cached entry must not hide unrelated valid sources.
    # Individual entries still fail closed in the aligned checks below.
    ids=list(dict.fromkeys(e['event_id'] for e in ents
                           if isinstance(e,dict) and type(e.get('event_id')) is str
                           and e['event_id']))
    pairs={}
    for offset in range(0,len(ids),TURNS_MAX):
        batch=ids[offset:offset+TURNS_MAX]
        recs,_=native_history(store,session,'',len(batch),event_ids=batch)
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
