"""WP-BP10 / WP-FS10: mark stale hypotheses in the executive's open questions (AEWM "task-state contamination" idea,
read 2026-10-27; concept only; link to Z5c: old unresolved hypotheses of earlier tasks hurt long sessions).

An open question (`executive.open_questions`, shown to the bodies as `unresolved_observer_hypotheses`) is a fallible note from an
earlier turn. It is STALE when the situation it was written for no longer holds. Reasons, each cheap and source-based:

  TOPIC_SHIFT       the current request shares (almost) no terms with the question's own request
  ANSWERED_LATER    a later turn in the session restated the question and got a FINAL answer
  CORRECTED_SINCE   a human correction on the question's topic was stored after the question was written
  TOO_OLD           more than `MAX_TURNS` user turns have passed since the question
  SOURCE_GONE       the question's source can no longer be read

Mode `hypothesis_stale` (cfg): off | shadow (default: counts and reasons are logged, nothing changes) | active (stale notes are not
shown to the bodies). Nothing is deleted and no memory is written; a stale note simply stops being offered as current.
"""
import json
from .memory import terms

MODES=('off','shadow','active')
TOPIC_MIN=.12;MAX_TURNS=6;SAME_TOPIC=.5

def _overlap(a,b):
    ta,tb=terms(a),terms(b)
    return len(ta&tb)/max(1,min(len(ta),len(tb))) if ta and tb else 0.

def mode(cfg):
    m=cfg.get('hypothesis_stale','shadow')
    if m not in MODES:raise ValueError('hypothesis_stale off|shadow|active')
    return m

def classify(store,session,item,current_text):
    """Reasons why one open question is stale; empty list = fresh."""
    try:text=store.read_source(item['source_ref'])
    except Exception:return ['SOURCE_GONE']
    src=store.one("SELECT e.id,e.created FROM events e JOIN sources s ON s.id=e.source_id WHERE s.id=? AND e.session_id=? ORDER BY e.created LIMIT 1",(item['source_ref']['source_id'],session))
    if not src:return ['SOURCE_GONE']
    out=[]
    if current_text and _overlap(text,current_text)<TOPIC_MIN:out.append('TOPIC_SHIFT')
    later=store.rows("SELECT e.id,e.source_id FROM events e WHERE e.session_id=? AND e.created>? ORDER BY e.created",(session,src['created']))
    if len(later)>MAX_TURNS:out.append('TOO_OLD')
    for ev in later:
        try:t=store.read_source({'source_id':ev['source_id'],'sha256':store.one('SELECT hash FROM sources WHERE id=?',(ev['source_id'],))['hash'],'char_start':0,
                                 'char_end':store.one('SELECT chars FROM sources WHERE id=?',(ev['source_id'],))['chars'],'modality':'text'})
        except Exception:continue
        if _overlap(text,t)>=SAME_TOPIC and store.one("SELECT id FROM messages WHERE event_id=? AND role='assistant' AND status='FINAL'",(ev['id'],)):
            out.append('ANSWERED_LATER');break
    for m in store.rows("SELECT key_text FROM memories WHERE active=1 AND created>? AND session_id=?",(src['created'],session)):
        if _overlap(text,m['key_text'])>=SAME_TOPIC:out.append('CORRECTED_SINCE');break
    return out

def filter_questions(store,cfg,session,questions,current_text):
    """Returns (questions to show, report). Only mode `active` removes stale ones; `shadow` only reports."""
    m=mode(cfg)
    if m=='off' or not questions:return questions,{'mode':m,'checked':0,'stale':0}
    keep=[];stale=[]
    for q in questions:
        r=classify(store,session,q,current_text)
        (stale if r else keep).append((q,r))
    rep={'mode':m,'checked':len(questions),'stale':len(stale),'reasons':sorted({x for _,r in stale for x in r})}
    try:store.log('bp10_hypothesis_stale',None,rep)
    except Exception:pass
    return ([q for q,_ in keep] if m=='active' else questions),rep
