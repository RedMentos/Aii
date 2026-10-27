"""WP-BP7 / WP-FS8: retrieval outcome reconsolidates a memory entry (REALM idea, Song et al., arXiv 2609.16053, read 2026-10-27;
concept only, no code or numbers taken).

A stored memory is not frozen: when the human says that a retrieved entry was `relevant` or `irrelevant` for a query
(`retrieval_feedback`, the only outcome signal used; model text never labels itself), the entry's *retrieval weight* moves,
and Sleep C settles it. The entry's value, key and source are never changed, so nothing here writes a fact:

  weight = 1 + 0.5 * (H - M) / (H + M + 2)    in (0.5, 1.5); H / M = time-decayed helped / missed counts
  decay  = half-life `HALF_LIFE_DAYS` per outcome, so an old verdict fades instead of fixing the entry forever
  review = M >= 2 and M > H: listed for the user (`review_list`), never deleted or demoted to zero automatically

Mode (`reconsolidation`): off = nothing, shadow = counts and weights are kept and shown, recall order unchanged (default),
active = recall orders candidates by retrieval_score * weight (membership of the candidate set is unchanged).
"""
import json
import time
from .agi.base import StateBox

KEY='BP7_RECON';REVISION='bp7-recon-v1'
HALF_LIFE_DAYS=30.;DAY=86400.;EVENTS_MAX=32;MEMORIES_MAX=2048;MODES=('off','shadow','active')

def _empty():return {'memories':{},'cursor':0.,'seen':[],'runs':0}

class Reconsolidation:
    default_clock=staticmethod(time.time)  # simulations replace this to run weeks in seconds
    def __init__(self,store,cfg,clock=None):
        self.s=store;self.cfg=cfg;self.clock=clock or Reconsolidation.default_clock
        self.box=StateBox(store,KEY,REVISION,_empty)

    def mode(self):
        m=self.cfg.get('reconsolidation','shadow')
        if m not in MODES:raise ValueError('reconsolidation off|shadow|active')
        return m

    # outcome intake ---------------------------------------------------------------------------------------
    def _new_outcomes(self,cursor,seen):
        """Retrieval verdicts from humans newer than the cursor: (feedback id, memory id, +1/-1, time)."""
        out=[]
        for f in self.s.rows("SELECT id,event_id,source_id,value,created FROM feedback WHERE kind='retrieval' AND created>=? ORDER BY created,rowid LIMIT 512",(cursor,)):
            if f['id'] in seen or f['value'] not in ('relevant','irrelevant'):continue
            row=self.s.one("SELECT payload FROM packets WHERE kind='HumanDecision' AND event_id=? AND json_extract(payload,'$.source_ref.source_id')=?",(f['event_id'],f['source_id']))
            if not row:continue
            mid=(json.loads(row['payload']).get('selection') or {}).get('memory_id')
            if mid:out.append((f['id'],mid,1 if f['value']=='relevant' else -1,f['created']))
        return out

    def update(self):
        """Folds new human retrieval verdicts into the per-memory event lists. Idempotent (feedback ids are remembered)."""
        def go(st):
            seen=set(st['seen']);new=self._new_outcomes(st['cursor'],seen);n=0
            for fid,mid,sign,t in new:
                m=st['memories'].setdefault(mid,{'events':[]})
                m['events']=(m['events']+[[t,sign]])[-EVENTS_MAX:];seen.add(fid);st['cursor']=max(st['cursor'],t);n+=1
            st['seen']=sorted(seen)[-4096:]
            if len(st['memories'])>MEMORIES_MAX:
                for k in sorted(st['memories'],key=lambda k:max((e[0] for e in st['memories'][k]['events']),default=0))[:len(st['memories'])-MEMORIES_MAX]:del st['memories'][k]
            return n
        return self.box.mutate(go)

    # weights ----------------------------------------------------------------------------------------------
    def counts(self,events,now=None):
        now=self.clock() if now is None else now;h=m=0.
        for t,sign in events:
            w=.5**(max(0.,now-t)/(HALF_LIFE_DAYS*DAY))
            if sign>0:h+=w
            else:m+=w
        return h,m

    def weight_of(self,events,now=None):
        h,m=self.counts(events,now);return 1.+.5*(h-m)/(h+m+2.)

    def weights(self,now=None):
        st=self.box.load()[0]
        return {mid:self.weight_of(v['events'],now) for mid,v in st['memories'].items()}

    def annotate(self,candidates):
        """Adds `recon_weight` to recalled candidates; orders by score*weight only in mode `active`."""
        mode=self.mode()
        if mode=='off' or not candidates:return candidates
        w=self.weights()
        for c in candidates:c['recon_weight']=w.get(c['id'],1.)
        if mode=='active':
            return sorted(candidates,key=lambda c:(c['retrieval_score']*c['recon_weight'],c['created']),reverse=True)
        return candidates

    def review_list(self,now=None):
        """Entries the human mostly called irrelevant: for the user to look at. Nothing is changed or removed."""
        out=[]
        for mid,v in self.box.load()[0]['memories'].items():
            h,m=self.counts(v['events'],now)
            if m>h and sum(1 for e in v['events'] if e[1]<0)>=2:out.append({'memory_id':mid,'helped':round(h,3),'missed':round(m,3)})
        return sorted(out,key=lambda r:-r['missed'])

    # Sleep C ----------------------------------------------------------------------------------------------
    def sleep(self):
        """Settles the labile entries: folds new verdicts, drops events whose decayed weight is negligible."""
        if self.mode()=='off':return {'status':'OFF'}
        n=self.update();now=self.clock()
        def trim(st):
            gone=0
            for mid in list(st['memories']):
                ev=[e for e in st['memories'][mid]['events'] if .5**(max(0.,now-e[0])/(HALF_LIFE_DAYS*DAY))>=.05]
                if len(ev)!=len(st['memories'][mid]['events']):gone+=len(st['memories'][mid]['events'])-len(ev)
                if ev:st['memories'][mid]['events']=ev
                else:del st['memories'][mid]
            st['runs']+=1;return gone
        gone=self.box.mutate(trim);st=self.box.load()[0]
        w=[self.weight_of(v['events'],now) for v in st['memories'].values()]
        return {'status':'DONE','mode':self.mode(),'new_outcomes':n,'faded_events':gone,'tracked':len(w),
                'weight_min':min(w) if w else 1.,'weight_max':max(w) if w else 1.,'review':len(self.review_list(now)),'fact_write_authority':0}
