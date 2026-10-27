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
from pathlib import Path
from .common import dumps,atomic_write
from .context_os import compress

KEY='S7_DAY_DIGEST';REVISION='s7-digest-v1'
TURN_CAP=160;SESSIONS_MAX=8;TURNS_MAX=64;ENTRIES_MAX=96;TTT_MAX=256
TTT_SCHEMA='S7_TTT_CANDIDATE_V2';TTT_MAX_BYTES=2*1024*1024

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

def _live_entry(store,e):
    """Fail-closed current lineage for a previously stored digest entry."""
    if (type(e) is not dict or type(e.get('event_id')) is not str
            or type(e.get('msg')) is not int):
        return False
    row=store.one(
        "SELECT s.deleted AS deleted,m.status AS status FROM events e "
        "JOIN sources s ON s.id=e.source_id "
        "JOIN messages m ON m.id=? AND m.event_id=e.id AND m.role='assistant' "
        "WHERE e.id=?", (e['msg'],e['event_id']))
    return bool(row and not row['deleted'] and row['status']=='FINAL')


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
        new=[p for p in pairs.values() if 'assistant' in p and 'user' in p and p['assistant']['id']>d['until']]
        for p in sorted(new,key=lambda p:p['assistant']['id']):
            u,us,uok=compress(p['user']['text'],TURN_CAP);a,as_,aok=compress(p['assistant']['text'],TURN_CAP)
            d['entries'].append({'event_id':p['user']['event_id'],'user':u if uok or len(u)<=TURN_CAP*2 else u[:TURN_CAP*2],'answer':a if aok or len(a)<=TURN_CAP*2 else a[:TURN_CAP*2],
                                 'exact':us+as_,'msg':p['assistant']['id']})
            out['turns']+=1;out['compressed']+=int(uok)+int(aok)
        d['entries']=d['entries'][-ENTRIES_MAX:];d['until']=r['last'];out['sessions']+=1
    st['runs']+=1;store.set_state(KEY,st,expected=v)
    return out

def view(store,session,cap=1200):
    """Read-only digest view; deleted/missing sources must never reappear."""
    d=_load(store)[0]['sessions'].get(session)
    if not d:return None
    lines=[];n=0;visible=0
    for e in reversed(d['entries']):
        if not _live_entry(store,e):continue
        ln=line(e['user'],e['answer'])
        if n+len(ln)>cap:break
        lines.append(ln);n+=len(ln);visible+=1
    return {'session':session,'text':'\n'.join(reversed(lines)),'entries':visible,'fact_authority':0}


def context_items(store,session,exclude_ids=(),cap=1200):
    """Live digest context: verify current source and FINAL assistant on every read."""
    d=_load(store)[0]['sessions'].get(session)
    if not d:return []
    skip=set(exclude_ids);out=[];n=0
    for e in reversed(d['entries']):
        if e['event_id'] in skip or not _live_entry(store,e):continue
        ln=line(e['user'],e['answer'])
        if n+len(ln)>cap:break
        out.append(ln);n+=len(ln)
    return list(reversed(out))


def _candidate_valid(store,row,session_entries):
    """Verify target, all context SourceRefs, and exact current FINAL text."""
    if (type(row) is not dict or row.get('schema')!=TTT_SCHEMA
            or row.get('status')!='CANDIDATE_NOT_TRAINED'
            or row.get('origin')!='self' or row.get('label_source')!='own_final_answer'
            or row.get('requires')!='WP-I retention gate + human approval'
            or type(row.get('fact_authority')) is not int or row['fact_authority']!=0
            or type(row.get('event_id')) is not str
            or type(row.get('session')) is not str
            or type(row.get('target_message_id')) is not int
            or type(row.get('context_event_ids')) is not list
            or not 1<=len(row['context_event_ids'])<=4
            or any(type(eid) is not str for eid in row['context_event_ids'])
            or len(set(row['context_event_ids']))!=len(row['context_event_ids']):
        return False
    entries=session_entries.get(row.get('session'))
    if not entries:return False
    byid={e['event_id']:e for e in entries if type(e) is dict and type(e.get('event_id')) is str}
    target=byid.get(row['event_id'])
    if (not target or target.get('msg')!=row['target_message_id']
            or not _live_entry(store,target)):
        return False
    try: index=entries.index(target)
    except ValueError:return False
    context=[e for e in entries[max(0,index-4):index] if _live_entry(store,e)]
    if [e['event_id'] for e in context]!=row['context_event_ids']:
        return False
    expected='\n'.join('U: '+e['user']+' | A: '+e['answer'] for e in context)
    if row.get('context')!=expected:return False
    msg=store.one("SELECT text,metadata FROM messages WHERE id=? AND event_id=? "
                  "AND role='assistant' AND status='FINAL'",
                  (target['msg'],target['event_id']))
    user=store.one("SELECT text FROM messages WHERE event_id=? AND role='user'",
                   (target['event_id'],))
    if not msg or not user:return False
    try:generated=json.loads(msg['metadata']).get('model_generated') is True
    except (ValueError,TypeError):return False
    return bool(generated and row.get('input')==user['text'] and row.get('target')==msg['text'])


def validate_ttt_export(store,path):
    """Mandatory read gate for downstream WP-I: old/stale exports fail closed."""
    p=Path(path)
    if not p.is_file():raise ValueError('TTT candidate export must be a regular file')
    with p.open('rb') as f:raw=f.read(TTT_MAX_BYTES+1)
    if len(raw)>TTT_MAX_BYTES:raise ValueError('TTT candidate export exceeds bound')
    try:
        rows=[json.loads(line) for line in raw.decode('utf-8').splitlines() if line.strip()]
    except (ValueError,UnicodeError,TypeError) as exc:
        raise ValueError('Malformed TTT candidate export') from exc
    if len(rows)>TTT_MAX:raise ValueError('Too many TTT candidates')
    sessions={sess:d['entries'] for sess,d in _load(store)[0]['sessions'].items()}
    if any(not _candidate_valid(store,row,sessions) for row in rows):
        raise ValueError('Stale, deleted or unauthorised TTT candidate lineage')
    return {'validated':True,'candidates':len(rows),'authority':0,
            'training_performed':False,'schema':TTT_SCHEMA}


def stage_ttt(store,home,checkpoint=None):
    """Context->LoRA candidates; deleted sources are excluded, no weight update."""
    st=_load(store)[0];path=home/'exports/sleep-ttt-candidates.jsonl';rows=[]
    for sess,d in st['sessions'].items():
        ents=d['entries']
        for i,e in enumerate(ents[1:],1):
            if checkpoint and i%16==0:checkpoint()
            if not _live_entry(store,e):continue
            context=[x for x in ents[max(0,i-4):i] if _live_entry(store,x)]
            if not context:continue
            msg=store.one("SELECT text,metadata FROM messages WHERE id=? AND event_id=? "
                          "AND role='assistant' AND status='FINAL'",
                          (e['msg'],e['event_id']))
            if not msg:continue
            try:generated=json.loads(msg['metadata']).get('model_generated') is True
            except (ValueError,TypeError):continue
            if not generated:continue
            user=store.one("SELECT text FROM messages WHERE event_id=? AND role='user'",(e['event_id'],))
            if not user:continue
            rows.append({'schema':TTT_SCHEMA,'session':sess,'event_id':e['event_id'],
                         'target_message_id':e['msg'],
                         'context_event_ids':[x['event_id'] for x in context],
                         'context':'\n'.join('U: '+x['user']+' | A: '+x['answer'] for x in context),
                         'input':user['text'],'target':msg['text'],'fact_authority':0,
                         'status':'CANDIDATE_NOT_TRAINED','label_source':'own_final_answer',
                         'origin':'self','requires':'WP-I retention gate + human approval'})
    rows=rows[-TTT_MAX:]
    sessions={sess:d['entries'] for sess,d in st['sessions'].items()}
    # Recheck before the file write; deletion after staging is caught by the
    # read-only validator that any future WP-I consumer must invoke.
    rows=[row for row in rows if _candidate_valid(store,row,sessions)]
    atomic_write(path,''.join(dumps(r)+'\n' for r in rows))
    validate_ttt_export(store,path)
    return {'candidates':len(rows),'path':str(path),'schema':TTT_SCHEMA,
            'fact_authority':0,'training_performed':False}


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
