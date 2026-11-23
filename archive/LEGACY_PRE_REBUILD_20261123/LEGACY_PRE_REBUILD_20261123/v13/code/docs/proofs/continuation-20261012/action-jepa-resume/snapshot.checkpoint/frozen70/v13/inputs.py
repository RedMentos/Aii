"""WP-V5 phone-usability input helpers (2026-10-09).

- pasted terminal logs are recognised so they stay out of later model context
- implicit praise/criticism in chat text and `:note 1-10` become stored answer ratings
- the last native model context is kept for `:context`

Ratings are human labels about an answer's quality. They carry no fact authority and
never change memories or weights by themselves; trainers (WP-I) read them explicitly.
"""
import re
import time
from .common import dumps

LOG_LINE=re.compile(r"(?x)^\s*(?:"
    r"\$\s|\#\s|~\s?\$|[\w.-]+@[\w.-]+:.*[$#]\s|"                    # shell prompts
    r"\[?\d{4}-\d\d-\d\d[ T]\d\d:\d\d|\[\d\d:\d\d:\d\d\]|\[bench\s|"  # timestamps
    r"Traceback\ \(most|File\ \".*\",\ line\ \d+|\w*(?:Error|Exception):\s|"
    r"(?:INFO|WARN|WARNING|ERROR|DEBUG|FATAL)[\s:\]]|"
    r"(?:Ran\ \d+\ tests|OK$|FAILED\ \()|"
    r"pkg\ |apt\ |pip\ |python3?\ |bash\ |cd\ |ls\ |termux-"
    r")")

def looks_like_terminal_log(text,min_lines=3,share=.5):
    """True for pasted terminal output: several lines, most of them log/prompt shaped."""
    lines=[l for l in (text or '').splitlines() if l.strip()]
    if len(lines)<min_lines:return False
    hits=sum(bool(LOG_LINE.search(l)) for l in lines)
    return hits/len(lines)>=share

PRAISE=re.compile(r"(?i)\b(danke|super|perfekt|genau( so)?|(?<!nicht )richtig|stimmt(?! nicht)|gut gemacht|klasse|top|thanks?|thank you|great|perfect|exactly|(?<!not )correct|well done|nice)\b")
CRITICISM=re.compile(r"(?i)\b(falsch|stimmt nicht|quatsch|unsinn|nein,? das|schlecht|wiederholst|nicht gefragt|wrong|incorrect|nonsense|that'?s not|bad answer|you repeated|not what i asked|nicht richtig)\b")

def implicit_feedback(text):
    """'praise' | 'criticism' | None. Mixed or long messages count as no signal."""
    t=(text or '').strip()
    if not t or len(t)>280 or looks_like_terminal_log(t):return None
    p=bool(PRAISE.search(t));c=bool(CRITICISM.search(t))
    if p==c:return None
    return 'praise' if p else 'criticism'

RATINGS_KEY='ANSWER_RATINGS'
MAX_RATINGS=4096
IMPLICIT_SCORE={'praise':8,'criticism':3}

def record_rating(store,event_id,score,origin,note=''):
    if isinstance(score,bool) or not isinstance(score,int) or not 1<=score<=10:raise ValueError(':note 1..10')
    if origin not in ('EXPLICIT_NOTE','IMPLICIT_CHAT'):raise ValueError('origin')
    if not store.one("SELECT id FROM messages WHERE event_id=? AND role='assistant' AND status='FINAL'",(event_id,)):raise ValueError('Keine fertige Antwort zum Bewerten')
    st,v=store.state(RATINGS_KEY,{'ratings':[]})
    # One rating per answer and origin: a later explicit note replaces the earlier one.
    st['ratings']=[x for x in st['ratings'] if not (x['event_id']==event_id and x['origin']==origin)]
    st['ratings'].append({'event_id':event_id,'score':score,'origin':origin,'note':note[:240],'created':time.time(),'authority':'HUMAN_QUALITY_LABEL_NOT_FACT'})
    del st['ratings'][:-MAX_RATINGS]
    store.set_state(RATINGS_KEY,st,expected=v)
    store.log('answer_rating',event_id,{'kind':'rating','origin':origin,'status':str(score)})
    try:
        from .agi.live import on_rating
        on_rating(store,event_id,score)  # WP-N13 AG9 label
    except Exception as exc:store.log('agi_live_unavailable',event_id,{'stage':'rating','error':type(exc).__name__})
    try:
        from .jefbridge import on_rating as jef_rating
        jef_rating(store,event_id,score)  # WP-N3 offer-utility label
        from .actionlearn import on_rating as c5_rating
        c5_rating(store,event_id,score)  # WP-N4 human approval/correction of the taken action
        from .deliberation import on_rating as delib_rating
        delib_rating(store,event_id,score)  # WP-N2 value of the turn's deliberation modes
        from .callosum import on_rating as callosum_rating
        callosum_rating(store,event_id,score)  # WP-J B3-H9 human value of the turn's callosum channels
    except Exception as exc:store.log('jef_bridge_unavailable',event_id,{'stage':'rating','error':type(exc).__name__})
    return st['ratings'][-1]

def ratings(store):return store.state(RATINGS_KEY,{'ratings':[]})[0]['ratings']

def rating_summary(store):
    rows=ratings(store);explicit=[r for r in rows if r['origin']=='EXPLICIT_NOTE']
    return {'count':len(rows),'explicit':len(explicit),'implicit':len(rows)-len(explicit),
            'mean_score':sum(r['score'] for r in rows)/len(rows) if rows else None,'latest':rows[-5:]}

CONTEXT_KEY='LAST_NATIVE_CONTEXT:'
MAX_CONTEXT_CHARS=16000

def save_context(store,session,event_id,role,messages):
    """Exact messages handed to the native model for the latest turn (bounded copy)."""
    text=dumps(messages)
    store.set_state(CONTEXT_KEY+session,{'event_id':event_id,'role':role,'messages':messages if len(text)<=MAX_CONTEXT_CHARS else None,
                                         'truncated':len(text)>MAX_CONTEXT_CHARS,'chars':len(text),'preview':text[:MAX_CONTEXT_CHARS]})

def last_context(store,session):return store.state(CONTEXT_KEY+session,None)[0]

# :pause selfedit|traum|training and the "burn-out" budget (WP-V5). Both only
# hold background work; user commands and user turns are never blocked.
PAUSE_KEY='BACKGROUND_PAUSES'
PAUSE_ACTIONS={'traum':{'sleep_b'},'training':{'growth_consolidate','growth_practice'},'selfedit':{'growth_goal'}}
BURNOUT_DEFAULT=12  # BOOT: background dispatches allowed per period without user input

def pauses(store):return store.state(PAUSE_KEY,{'paused':[],'burnout_budget':BURNOUT_DEFAULT})[0]

def set_pause(store,name,on=True):
    if name not in PAUSE_ACTIONS:raise ValueError(':pause selfedit|traum|training')
    st,v=store.state(PAUSE_KEY,{'paused':[],'burnout_budget':BURNOUT_DEFAULT})
    st['paused']=sorted(set(st['paused'])|{name} if on else set(st['paused'])-{name});store.set_state(PAUSE_KEY,st,expected=v);return st

def set_burnout(store,value):
    if isinstance(value,bool) or not isinstance(value,int) or not 0<=value<=1000:raise ValueError(':pause budget 0..1000')
    st,v=store.state(PAUSE_KEY,{'paused':[],'burnout_budget':BURNOUT_DEFAULT});st['burnout_budget']=value;store.set_state(PAUSE_KEY,st,expected=v);return st

def paused(store,name):return name in pauses(store)['paused']

def background_blocked(store,action,dispatched_since_input):
    """Reason string when a background action must wait, else None."""
    st=pauses(store)
    for name in st['paused']:
        if action in PAUSE_ACTIONS[name]:return 'PAUSED_'+name.upper()
    if dispatched_since_input>=st['burnout_budget']:return 'BURNED_OUT_WAITING_FOR_INPUT'
    return None
