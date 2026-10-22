"""WP-Z5d: live context fit for long sessions (Z5c follow-up).

Z5c (bench-results/z5c-focal-session-20261022) found that the shipped live turn overflows the native window in a long
session (41/300): pinned rules + hypotheses + the executive task context (which carries up to 8 unresolved observer
hypotheses of *earlier* tasks) + the user message no longer fit; the runner can only drop history turns, so with
history_turns 0 it raised Limits and the user got a system report instead of an answer.

This guard runs on the volatile layers before the answer message is built. It acts only when the prompt does not fit
(exact token count from the runner when it can tokenize, otherwise the conservative Context-OS char estimate), and
removes material in a fixed order, least valuable and oldest first, re-checking after every step:

  1 TASK_DUPLICATE   task_request that repeats the current user message verbatim -> pointer (lossless)
  2 OLD_QUESTIONS    unresolved observer hypotheses of earlier turns, oldest first
  3 DIGEST           day-digest lines of earlier turns, oldest first
  4 QUOTES           verified quotes beyond the first per hypothesis (the user message is in the prompt anyway)
  5 HYPOTHESES       lowest-ranked current hypotheses (the last ones), at least one stays
  6 MEMORIES         recalled memories beyond the first, last first

Sources are never changed; every dropped item stays in the answer lineage (context_source_refs are built from the
uncompacted selection). Modes (cfg ``context_fit``): ``active`` (default: it can only change a turn that would
otherwise fail with a system report), ``shadow`` (compute and log the steps, keep the overflowing view), ``off``.
"""
import copy

from .common import dumps

CHARS_PER_TOKEN=3.0  # same BOOT estimate as context_os; only used when the runner cannot count tokens
SURE_CHARS_PER_TOKEN=1.5  # below limit*1.5 chars a prompt fits for any of the pinned tokenizers: no native count needed
MODES=('off','shadow','active')
TASK_POINTER='(same as the current user message)'

def budget(cfg,reserve=None):
    """Prompt tokens the runner accepts: same rule as LlamaRunner._prompt."""
    return int(cfg['context_tokens'])-int(reserve or cfg['answer_tokens'])-16

def build(stable,volatile,history,text):
    return [{'role':'system','content':stable+''.join(h+dumps(p) for _,h,p in volatile)}]+list(history)+[{'role':'user','content':text}]

def estimate(messages):
    return int(sum(len(m['content']) for m in messages)/CHARS_PER_TOKEN)+8*len(messages)

def _layer(vol,name):
    return next((i for i,(layer,_,_) in enumerate(vol) if layer==name),None)

def _steps(vol,text):
    """Yield (step, detail) after each single in-place reduction of ``vol``; stops when nothing is left to cut."""
    i=_layer(vol,'LATENT_STATE')
    if i is not None:
        task=(vol[i][2] or {}).get('task_request')
        if isinstance(task,dict) and isinstance(task.get('exact_request'),str) and task['exact_request'] and text.startswith(task['exact_request']):
            task['exact_request']=TASK_POINTER;yield 'TASK_DUPLICATE',1
        qs=(vol[i][2] or {}).get('unresolved_observer_hypotheses')
        while isinstance(qs,list) and qs:
            qs.pop(0);yield 'OLD_QUESTIONS',1
    i=_layer(vol,'COMPRESSED')
    while i is not None and isinstance(vol[i][2],list) and vol[i][2]:
        vol[i][2].pop(0)
        if not vol[i][2]:del vol[i]
        yield 'DIGEST',1
        i=_layer(vol,'COMPRESSED')
    i=_layer(vol,'HYPOTHESES')
    if i is not None and isinstance(vol[i][2],list):
        for item in reversed(vol[i][2]):
            q=item.get('verified_quotes') if isinstance(item,dict) else None
            while isinstance(q,list) and len(q)>1:
                q.pop();yield 'QUOTES',1
        while len(vol[i][2])>1:
            vol[i][2].pop();yield 'HYPOTHESES',1
    i=_layer(vol,'ACTIVE_VIEW')
    if i is not None and isinstance(vol[i][2],list):
        while len(vol[i][2])>1:
            vol[i][2].pop();yield 'MEMORIES',1

def fit(mode,stable,volatile,history,text,count,limit,sure=SURE_CHARS_PER_TOKEN):
    """Return (volatile to use, report). ``count(messages)`` -> prompt tokens; ``limit`` = allowed prompt tokens."""
    if mode not in MODES:raise ValueError('context_fit '+'|'.join(MODES))
    report={'mode':mode,'limit_tokens':limit,'applied':False,'fits':None,'steps':{}}
    if mode=='off':return volatile,report
    if sum(len(m['content']) for m in build(stable,volatile,history,text))<=limit*sure:
        report.update(fits=True,quick=True);return volatile,report
    before=count(build(stable,volatile,history,text));report['tokens_before']=before
    if before<=limit:report.update(fits=True,tokens_after=before);return volatile,report
    work=[(layer,head,copy.deepcopy(body)) for layer,head,body in volatile];now=before
    for step,n in _steps(work,text):
        report['steps'][step]=report['steps'].get(step,0)+n
        now=count(build(stable,work,history,text))
        if now<=limit:break
    report.update(fits=now<=limit,tokens_after=now)
    if mode=='active' and report['steps']:
        report['applied']=True;return work,report
    return volatile,report

def counter(runner,cancel,deadline):
    """Exact token count through the runner's own template + tokenizer when available, else the char estimate."""
    exact=getattr(runner,'prompt_tokens',None)
    if exact is None:return estimate,'ESTIMATE'
    def count(messages):
        try:return exact(messages,cancel,deadline)
        except Exception:
            if cancel.is_set():raise
            return estimate(messages)  # no native count (runner unavailable, HTTP error): conservative estimate
    return count,'EXACT'
