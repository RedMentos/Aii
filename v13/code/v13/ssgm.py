"""WP-BP7 / WP-FS6: Sleep-D checklist before every weight update (SSGM idea, Lam et al., arXiv 2603.11768, read 2026-10-27;
concept only, no code or numbers taken).

Sleep D = the step where the nightly batch is turned into a weight-training candidate (`WeightConsolidation.stage`,
`sleep_offline.stage_ttt`). The checklist runs on the candidate items first and can only *remove* items, never add or
rewrite one and never write a memory:

  PRIVATE          mail / phone / IBAN / card / key-like strings and password words never reach weights   (hard)
  SOURCE_GONE      the exact source is deleted, archived away or no longer equals the target               (hard)
  DREAM_AS_FACT    dream / hypothesis / teacher / reference text as a fact target                          (hard)
  FACT_LEAK        a dream item that repeats a stored memory value (the Z9 finding: dream "benefit" came
                   from writing the stored fact into the weights); only policy-only dream items pass       (hard)
  CONFLICT         an active newer memory with the same key holds another value, or two batch items
                   disagree about one prompt                                                               (hard)
  SUMMARY_DRIFT    target built from a summary of a summary, or numbers / quotes not found in the source  (hard)
  AGED             the memory is older than `aged_days` and was never confirmed again                      (soft)

Hard failures are removed in mode `active`; soft ones are only reported. Mode `shadow` reports everything and removes
nothing; `off` skips the checklist. Every verdict names the check and the item so the user can read why.
"""
import json
import re
import time
from .common import digest

KEY='BP7_SLEEP_D_LOG';MODES=('off','shadow','active');AGED_DAYS=365;DAY=86400.
HARD=('PRIVATE','SOURCE_GONE','DREAM_AS_FACT','FACT_LEAK','CONFLICT','SUMMARY_DRIFT');SOFT=('AGED',)
FACT_KINDS=('fact','preference','style')
NON_HUMAN=('DREAM','HYPOTHESIS','TEACHER','REFERENCE','MODEL','REPLAY')
# Deliberately narrow, readable patterns; unmeasured, so they err towards dropping.
PRIVATE_RX=[
 ('email',re.compile(r'[\w.+-]+@[\w-]+\.[\w.-]+')),
 ('phone',re.compile(r'(?<!\d)(?:\+|00)\d[\d ()/-]{7,}\d')),
 ('iban',re.compile(r'\b[A-Z]{2}\d{2}(?: ?[A-Z0-9]{4}){3,7}(?: ?[A-Z0-9]{1,4})?\b')),
 ('card',re.compile(r'\b(?:\d[ -]?){13,19}\b')),
 ('key',re.compile(r'\b(?:sk-|ghp_|gho_|xox[bap]-|AKIA)[\w-]{8,}|\b[0-9a-f]{32,}\b|\b[A-Za-z0-9+/]{40,}={0,2}')),
 ('secret_word',re.compile(r'\b(?:passwort|kennwort|password|passwd|api[ _-]?key|token|geheimnis)\b\s*[:=]',re.I)),
]
WORD=re.compile(r'\w+',re.U)

def private_hits(text):
    return sorted({name for name,rx in PRIVATE_RX if rx.search(text or '')})

def _origin(item):
    from .guards import item_origin
    return item_origin(item)

def _norm(text):return ' '.join(WORD.findall((text or '').lower()))

def value_leaks(text,values,min_chars=4):
    """Stored memory values that appear verbatim (normalized) in `text`."""
    t=' '+_norm(text)+' ';out=[]
    for v in values:
        n=_norm(v)
        if len(n)>=min_chars and ' '+n+' ' in t:out.append(v)
    return out

def spans_missing(summary,source):
    """Exact spans (numbers, quotes, urls, code) of `summary` that the `source` text does not contain."""
    from .context_os import exact_spans
    return [s for s in exact_spans(summary) if s not in (source or '')]

class Checklist:
    def __init__(self,store,cfg,clock=time.time):
        self.s=store;self.cfg=cfg;self.clock=clock

    def mode(self):
        m=self.cfg.get('sleep_d_checklist','active')
        if m not in MODES:raise ValueError('sleep_d_checklist off|shadow|active')
        return m

    def _memory_values(self):
        return [r['value'] for r in self.s.rows("SELECT m.value FROM memories m JOIN sources s ON s.id=m.source_id WHERE m.active=1 AND s.deleted=0 AND m.kind IN ('fact','preference','style') ORDER BY m.created DESC LIMIT 1024")]

    def _read(self,ref):
        try:return self.s.read_source(ref)
        except Exception:return None

    def check_item(self,item,memory_values=None,aged_days=AGED_DAYS):
        """Returns a list of {'check','hard','detail'} for one candidate item."""
        out=[];add=lambda c,d:out.append({'check':c,'hard':c in HARD,'detail':d})
        prompt=item.get('prompt') or '';target=item.get('target') or ''
        hits=private_hits(prompt)+private_hits(target)+private_hits(item.get('context') or '')
        if hits:add('PRIVATE',sorted(set(hits)))
        origin=_origin(item);kind=item.get('kind')
        ref=item.get('source_ref') or {};label=str(ref.get('label') or item.get('source_kind') or '').upper()
        if kind in FACT_KINDS and (origin in ('dream','self') or any(w in label for w in NON_HUMAN)):add('DREAM_AS_FACT',origin)
        if origin=='dream':
            leaks=value_leaks(target+' '+prompt,memory_values if memory_values is not None else self._memory_values())
            if leaks:add('FACT_LEAK',[digest(v)[:12] for v in leaks[:4]])  # hashes only: the log must not copy the fact
        if ref.get('source_id') and ref.get('char_end') is not None:
            text=self._read(ref)
            if text is None:add('SOURCE_GONE','read failed')
            elif kind in FACT_KINDS and item.get('target') is not None and text!=target:add('SOURCE_GONE','target differs from source')
        mid=item.get('memory_id')
        if mid and not str(mid).startswith('rating:') and kind in FACT_KINDS:
            m=self.s.one("SELECT m.kind,m.key_text,m.value,m.active,m.session_id,m.scope,m.created FROM memories m WHERE m.id=?",(mid,))
            if m is None or not m['active']:add('CONFLICT','memory inactive or missing')
            else:
                newer=self.s.one("SELECT value FROM memories WHERE active=1 AND kind=? AND key_text=? AND scope=? AND session_id=? AND created>? AND value!=? LIMIT 1",
                                 (m['kind'],m['key_text'],m['scope'],m['session_id'],m['created'],m['value']))
                if newer:add('CONFLICT','a newer active memory holds another value')
                if self.clock()-m['created']>aged_days*DAY:add('AGED',int((self.clock()-m['created'])/DAY))
        depth=item.get('summary_depth',0)
        if isinstance(depth,int) and depth>1:add('SUMMARY_DRIFT','summary of a summary (depth %d)'%depth)
        if item.get('context') and target and kind not in FACT_KINDS:
            src=item.get('source_text')
            if src is not None:
                miss=spans_missing(target,src+' '+item.get('context',''))
                if miss:add('SUMMARY_DRIFT','spans not in source: %d'%len(miss))
        return out

    def run(self,items,mode=None,aged_days=AGED_DAYS):
        """Checks a candidate batch. Returns (kept items, report). Never mutates items or memories."""
        mode=mode or self.mode()
        if mode=='off':return list(items),{'mode':'off','checked':0,'dropped':0,'verdicts':[]}
        values=self._memory_values();verdicts=[];hard=set()
        by_prompt={}
        for i,it in enumerate(items):
            if it.get('kind') in FACT_KINDS and it.get('target') is not None:by_prompt.setdefault(_norm(it.get('prompt')),[]).append(i)
        batch_conflict=set()
        for idx in by_prompt.values():
            if len({_norm(items[i].get('target')) for i in idx})>1:batch_conflict.update(idx)
        for i,it in enumerate(items):
            found=self.check_item(it,values,aged_days)
            if i in batch_conflict:found.append({'check':'CONFLICT','hard':True,'detail':'batch items disagree about one prompt'})
            if found:
                verdicts.append({'memory_id':it.get('memory_id'),'event_id':it.get('event_id'),'checks':found})
                if any(f['hard'] for f in found):hard.add(i)
        drop=hard if mode=='active' else set()
        kept=[it for i,it in enumerate(items) if i not in drop]
        by={}
        for v in verdicts:
            for f in v['checks']:by[f['check']]=by.get(f['check'],0)+1
        rep={'mode':mode,'checked':len(items),'dropped':len(drop),'kept':len(kept),'by_check':by,'verdicts':verdicts[:64],'hard_failures':len(hard)}
        try:self.s.log('bp7_sleep_d',None,{'mode':mode,'checked':len(items),'dropped':len(drop),'by_check':by})
        except Exception:pass
        return kept,rep
