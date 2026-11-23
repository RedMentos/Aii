"""WP-S5 drift gate and self-distillation data (STEP5 regression shield, RL's Razor).

Forgetting tracks how far a fine-tuned model moves from its base (RL's Razor), so every adapter update is measured
on a FROZEN probe set before `:approve`:
- language adapters (LoRA, output adapters): mean KL(base || candidate) on fixed generic prompts
  (specs/drift-probes.json; no user data, never trained on). The evaluator is duck-typed: anything with
  `kl(prompts) -> float` (lora_trainer.LlamaCppEvaluator does this).
- decision heads (route/wake/halt and other readouts): share of frozen protected human decisions the candidate flips.
Probe sets freeze on first use (sha256 in state). A changed probe file or a new decision set needs an explicit
`refreeze` with a reason, and the history is kept, so the bar cannot move silently between two measurements.
`record()` writes the result into the update manifest; guards.stability_envelope refuses `:approve` above the caps
(drift_kl_max, drift_flip_max). With drift_required=1 an update without a drift measurement is refused as well.

SDFT (self-distillation fine-tuning) for human corrections: instead of SFT on the correction text, the model itself
answers the original question with the correction in context (teacher) and is trained to give that answer without
the context (student). This module only builds that dataset; the trainer (lora_trainer) generates the teacher
answers and still has to pass the AG6 retention gate (arXiv 2607.01763 counter-finding: no gate, no SDFT).
"""
import json
import math
import time
from .common import APP,digest,dumps

KEY='WP_S5_DRIFT';REVISION='wp-s5-drift-v1'
PROBE_FILE=APP/'specs/drift-probes.json'
DECISION_KINDS={'route':('route',),'wake':('wake',),'halt':('halt',)}  # component -> human feedback kinds that label it
CORRECTION_KINDS=('fact','style','preference')
MAX_DECISIONS=64;MAX_HISTORY=32
TEACHER_TEMPLATE=('{question}\n\nA user corrected an earlier answer to this question: "{correction}". '
                  'Answer the question again, taking the correction into account.')

def kl(p,q,eps=1e-6):
    """KL(p || q) for two distributions given as dicts (token -> prob) or equal-length lists; missing mass smoothed with eps."""
    if isinstance(p,dict):keys=sorted(set(p)|set(q));p=[p.get(k,0.) for k in keys];q=[q.get(k,0.) for k in keys]
    if len(p)!=len(q) or not p:raise ValueError('KL: Verteilungen passen nicht')
    sp=sum(p)+eps*len(p);sq=sum(q)+eps*len(q)
    return max(0.,sum(((a+eps)/sp)*math.log(((a+eps)/sp)/((b+eps)/sq)) for a,b in zip(p,q)))

def flip_rate(base,cand):
    """Share of probes where the candidate decision differs from the base decision."""
    if len(base)!=len(cand):raise ValueError('flip_rate: Längen passen nicht')
    return sum(a!=b for a,b in zip(base,cand))/len(base) if base else 0.

def _probe_doc():
    text=PROBE_FILE.read_text(encoding='utf-8');doc=json.loads(text)
    if doc.get('schema')!='V13_DRIFT_PROBES_V1' or not doc.get('probes'):raise ValueError('Drift-Probe-Datei ungültig')
    return doc,digest(text)

class Drift:
    def __init__(self,store,cfg,clock=time.time):self.s=store;self.cfg=cfg;self.clock=clock
    def _load(self):
        st=self.s.state(KEY,None)[0] or {'revision':REVISION,'sets':{},'history':[],'measurements':[]}
        if st.get('revision')!=REVISION:raise ValueError(KEY+': state revision mismatch')
        return st
    def _save(self,st):self.s.set_state(KEY,st)
    # frozen probe sets -----------------------------------------------------------------------------
    def lm_probes(self):
        """Fixed generic prompts. First use freezes the file hash; a later file change is refused until refreeze('lm')."""
        doc,sha=_probe_doc();st=self._load();cur=st['sets'].get('lm')
        if cur is None:
            st['sets']['lm']={'sha256':sha,'n':len(doc['probes']),'frozen_at':self.clock(),'source':str(PROBE_FILE.relative_to(APP))};self._save(st)
        elif cur['sha256']!=sha:raise ValueError('Drift-Probe-Datei geändert; :drift refreeze lm <Grund> nötig')
        return [p['prompt'] for p in doc['probes']],sha
    def _decision_rows(self,component):
        kinds=DECISION_KINDS.get(component)
        if not kinds:raise ValueError('Keine menschlichen Entscheidungs-Labels für '+component)
        rows=self.s.rows('SELECT f.event_id,f.value,f.created FROM feedback f JOIN sources s ON s.id=f.source_id WHERE s.deleted=0 AND f.kind IN (%s) ORDER BY f.created,f.id'
                         %','.join('?'*len(kinds)),kinds)
        last={}
        for r in rows:last[r['event_id']]=r['value']  # the latest human label per event counts
        return [{'event_id':e,'label':v} for e,v in list(last.items())[:MAX_DECISIONS]]
    def decision_probes(self,component):
        """Frozen protected decisions (oldest human labels first). Frozen once; new labels join only through refreeze."""
        st=self._load();cur=st['sets'].get(component)
        if cur is None:
            items=self._decision_rows(component)
            if not items:raise ValueError('Noch keine menschlichen '+component+'-Labels zum Einfrieren')
            cur={'items':items,'sha256':digest(dumps(items)),'n':len(items),'frozen_at':self.clock()};st['sets'][component]=cur;self._save(st)
        elif digest(dumps(cur['items']))!=cur['sha256']:raise ValueError('Eingefrorene Probe-Menge beschädigt: '+component)
        return cur['items'],cur['sha256']
    def refreeze(self,name,reason):
        if not reason or not reason.strip():raise ValueError('refreeze braucht einen Grund')
        st=self._load();old=st['sets'].pop(name,None)
        st['history']=(st['history']+[{'set':name,'old_sha256':old and old['sha256'],'reason':reason.strip()[:240],'at':self.clock()}])[-MAX_HISTORY:]
        self._save(st)
        return self.lm_probes()[1] if name=='lm' else self.decision_probes(name)[1]
    # measurements -----------------------------------------------------------------------------------
    def measure_lm(self,component,evaluator):
        prompts,sha=self.lm_probes();value=float(evaluator.kl(prompts))
        return self._report(component,'LM_KL',value,float(self.cfg['drift_kl_max']),len(prompts),sha)
    def measure_decisions(self,component,base_fn,cand_fn):
        """base_fn/cand_fn: event_id -> decision of the active head / the candidate head on that frozen event."""
        items,sha=self.decision_probes(component);ids=[i['event_id'] for i in items]
        value=flip_rate([base_fn(e) for e in ids],[cand_fn(e) for e in ids])
        return self._report(component,'DECISION_FLIP',value,float(self.cfg['drift_flip_max']),len(ids),sha)
    def _report(self,component,measure,value,cap,n,sha):
        rep={'component':component,'measure':measure,'value':round(value,6),'cap':cap,'n':n,'probes_sha256':sha,'passed':value<=cap,'at':self.clock(),'revision':REVISION}
        st=self._load();st['measurements']=(st['measurements']+[rep])[-MAX_HISTORY:];self._save(st)
        self.s.log('drift_gate',None,{k:rep[k] for k in ('component','measure','value','cap','n','passed','probes_sha256')})
        return rep
    def record(self,update_id,rep):
        """Attach a measurement to a pending update; :approve then checks it (guards.stability_envelope)."""
        with self.s.tx() as c:
            row=c.execute('SELECT manifest,status FROM updates WHERE id=?',(update_id,)).fetchone()
            if not row:raise ValueError('Update unbekannt')
            m=json.loads(row[0]);m['drift']={k:rep[k] for k in ('component','measure','value','cap','n','probes_sha256','passed')}
            c.execute('UPDATE updates SET manifest=? WHERE id=?',(dumps(m),update_id))
        return m['drift']
    # SDFT -------------------------------------------------------------------------------------------
    def sdft_dataset(self,limit=256):
        """Self-distillation items from human corrections marked `learn`. Teacher answers are generated later by the
        model itself (on-policy); no correction text is ever used as a direct training target."""
        rows=self.s.rows("SELECT f.id,f.event_id,f.kind,f.value,f.source_id,s.hash FROM feedback f JOIN sources s ON s.id=f.source_id "
                         "WHERE s.deleted=0 AND f.permission='learn' AND f.kind IN (?,?,?) ORDER BY f.created,f.id",CORRECTION_KINDS)
        out=[]
        for r in rows:
            q=self.s.one("SELECT text FROM messages WHERE event_id=? AND role='user' ORDER BY id LIMIT 1",(r['event_id'],))
            if not q or not q['text'].strip():continue
            out.append({'item_id':'sdft:'+r['id'],'event_id':r['event_id'],'kind':r['kind'],'student_prompt':q['text'],
                        'teacher_prompt':TEACHER_TEMPLATE.format(question=q['text'],correction=r['value']),'target':None,'correction':r['value'],
                        'target_policy':'SELF_TEACHER_IN_CONTEXT','gate':'AG6_RETENTION_REQUIRED','origin':'human_replay',  # data mix: content is the human correction, the model only voices it
                        'source_ref':{'source_id':r['source_id'],'sha256':r['hash'],'modality':'text','label':'HUMAN_CORRECTION'}})
            if len(out)>=limit:break
        return out
    def status(self):
        st=self._load()
        return {'revision':REVISION,'sets':{k:{x:v[x] for x in ('sha256','n','frozen_at')} for k,v in st['sets'].items()},'history':st['history'][-5:],
                'last':st['measurements'][-5:],'caps':{'kl':self.cfg['drift_kl_max'],'flip':self.cfg['drift_flip_max']},'required':bool(self.cfg['drift_required']),
                'sdft_items':len(self.sdft_dataset()),'claim_limit':'Gate on frozen probes; KL needs a model evaluator, decision drift needs both heads callable'}

def gate(manifest,cfg):
    """Violations for guards.stability_envelope. Caps come from the current config, not from the measurement."""
    d=manifest.get('drift')
    if not isinstance(d,dict):return ['DRIFT_NOT_MEASURED'] if cfg.get('drift_required') else []
    cap={'LM_KL':cfg.get('drift_kl_max',.05),'DECISION_FLIP':cfg.get('drift_flip_max',.10)}.get(d.get('measure'))
    if cap is None or not isinstance(d.get('value'),(int,float)):return ['DRIFT_INVALID']
    return ['DRIFT_ABOVE_CAP'] if d['value']>cap else []

def operator_command(r,args):
    d=Drift(r.store,r.cfg)
    if not args or args==['status']:return d.status()
    if args==['probes']:return {'prompts':d.lm_probes()[0]}
    if len(args)==2 and args[0]=='freeze':return {'set':args[1],'sha256':(d.lm_probes() if args[1]=='lm' else d.decision_probes(args[1]))[1]}
    if len(args)>=3 and args[0]=='refreeze':return {'set':args[1],'sha256':d.refreeze(args[1],' '.join(args[2:]))}
    if args==['sdft']:return d.sdft_dataset()
    raise ValueError(':drift [status|probes|freeze <lm|route|wake|halt>|refreeze <Set> <Grund>|sdft]')
