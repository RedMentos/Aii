"""WP-HX5 harness logs as learning data (Evo2 idea, arXiv 2610.13025; research/HARNESS2_AUSWERTUNG.md).

An adopted harness edit changes behaviour only while its text is in the prompt. HX5 turns the logged calls of an
edit that passed WP-HX2 into training items for the body's continual learning (LoRA, lora_trainer.LoraTrainer):
prompt = the call under the BASE harness, target = the output under the adopted edit, only where that output was
judged good. A model trained on that behaves as if the edit were present, without the extra prompt tokens.

Locked, three times:
  1. HX2 gate: the HX2 result file must report HX2_PASS for this target; its sha256 is bound into the request and
     rechecked at export (a changed file voids the request).
  2. Human: request_export() only opens a PENDING request (kind HX5_EXPORT); approve() is a human act; export()
     refuses anything not APPROVED. Nothing is trained here, ever: the output is a dataset file + manifest.
  3. Retention: retention_gate() judges a trained candidate from LlamaCppEvaluator.evaluate() (learned gain, no
     retention/unseen loss beyond tolerance, forgetting, near-miss leak, KL). Binding an adapter stays AG6/AdapterRegistry.
Items are data: texts length-capped, control characters and rule-weakening wording refused (harness.WEAKEN), protected
prompt texts (system/conduct/operator rules) never appear as a target. Authority 0 (SHADOW): no live path reads this.
"""
import json
import math
import time
from pathlib import Path
from .base import StateBox
from .harness import WEAKEN,TARGETS
from ..common import digest,dumps,atomic_write

KEY='HX5_HARNESS_DATA';REVISION='hx5-harness-data-v1'
KIND='HX5_EXPORT';PASS='HX2_PASS'
MAX_ITEMS=512;MAX_PROMPT=12000;MAX_TARGET=2000;TOLERANCE=.02

def hx2_status(path,target):
    """Read an HX2 result: (status, sha256). Unlocks only for HX2_PASS with the probed target in the chosen diff."""
    p=Path(path)
    if not p.is_file():return 'HX2_MISSING',None
    raw=p.read_bytes();sha=digest(raw)
    try:res=json.loads(raw)
    except ValueError:return 'HX2_UNREADABLE',sha
    gate=res.get('gate') or {};status=gate.get('status','HX2_UNKNOWN')
    if status==PASS and target not in (res.get('chosen_diff') or {}):status='HX2_PASS_OTHER_TARGET'
    return status,sha

def _clean(v,limit,name):
    if not isinstance(v,str) or not v.strip():raise ValueError(name+' leer')
    if len(v)>limit:raise ValueError(f'{name} länger als {limit}')
    if any(ord(c)<32 and c not in '\n\t' for c in v):raise ValueError('Steuerzeichen in '+name)
    if WEAKEN.search(v):raise PermissionError(name+' schwächt Regeln')
    return v

def item(record):
    """One capture record {'messages': base-harness messages, 'output': text, 'accepted': bool, 'task': id} -> trainer item."""
    if type(record) is not dict or type(record.get('accepted')) is not bool:
        raise ValueError('accepted muss bool sein')
    if record['accepted'] is False:return None
    msgs=record['messages']
    if not isinstance(msgs,list) or not msgs or any(type(m) is not dict or m.get('role') not in ('system','user') for m in msgs):raise ValueError('messages: system/user erwartet')
    prompt='\n\n'.join(str(m['content']) for m in msgs)
    return {'prompt':_clean(prompt,MAX_PROMPT,'prompt'),'target':_clean(record['output'],MAX_TARGET,'target'),'kind':'harness_distill',
            'answer_keys':list(record.get('answer_keys') or [])[:8],'source':{'task':str(record.get('task',''))[:80],'run':str(record.get('run',''))[:40]}}

class HarnessData:
    def __init__(self,store,clock=time.time):
        self.s=store;self.clock=clock
        self.box=StateBox(store,KEY,REVISION,lambda:{'requests':{}})
    def request_export(self,hx2_result,target):
        """Opens a PENDING human request; refuses unless the HX2 result passed for this target."""
        if target not in TARGETS:raise PermissionError('Kein Harness-Ziel: '+str(target))
        status,sha=hx2_status(hx2_result,target)
        if status!=PASS:raise PermissionError('HX5 gesperrt: '+status)
        rid=self.s.request(KIND,{'hx2_result':str(hx2_result),'hx2_sha256':sha,'target':target})
        def f(st):st['requests'][rid]={'hx2_result':str(hx2_result),'hx2_sha256':sha,'target':target,'status':'PENDING','created':self.clock()}
        self.box.mutate(f);return rid
    def approve(self,rid):
        """Human only (user command), like SelfImprovement.approve."""
        def f(st):
            r=st['requests'].get(rid)
            if not r or r['status']!='PENDING':raise ValueError('Keine offene HX5-Freigabe')
            r['status']='APPROVED';r['approved']=self.clock()
        self.box.mutate(f)
        with self.s.tx() as c:c.execute("UPDATE requests SET status='APPROVED' WHERE id=? AND kind=?",(rid,KIND))
    def export(self,rid,records,out):
        """Writes the dataset (JSON lines) + manifest; trains nothing. Every lock is rechecked here."""
        r=self.box.load()[0]['requests'].get(rid)
        if not r or r['status']!='APPROVED':raise PermissionError('HX5-Export nicht freigegeben')
        row=self.s.one("SELECT status FROM requests WHERE id=? AND kind=?",(rid,KIND))
        if not row or row['status']!='APPROVED':raise PermissionError('HX5-Freigabe fehlt in requests')
        status,sha=hx2_status(r['hx2_result'],r['target'])
        if status!=PASS or sha!=r['hx2_sha256']:raise PermissionError('HX2-Beleg geändert oder nicht bestanden: '+status)
        items=[];seen=set();refused=0
        for rec in records:
            try:it=item(rec)
            except (ValueError,PermissionError):refused+=1;continue
            if it is None:continue
            k=digest(dumps([it['prompt'],it['target']]))
            if k in seen:continue
            seen.add(k);items.append(it)
            if len(items)>=MAX_ITEMS:break
        out=Path(out);out.parent.mkdir(parents=True,exist_ok=True)
        body=''.join(json.dumps(i,ensure_ascii=False,sort_keys=True)+'\n' for i in items)
        atomic_write(out,body)
        manifest={'revision':REVISION,'request':rid,'target':r['target'],'hx2_result':r['hx2_result'],'hx2_sha256':sha,
                  'dataset':str(out),'dataset_sha256':digest(body.encode()),'items':len(items),'refused':refused,
                  'records':len(records),'authority':'TRAINING_DATA_CANDIDATE','trained':False,'created':self.clock()}
        atomic_write(out.with_suffix('.manifest.json'),json.dumps(manifest,ensure_ascii=False,indent=2))
        def f(st):st['requests'][rid]['status']='EXPORTED';st['requests'][rid]['manifest']=manifest
        self.box.mutate(f);self.s.log('hx5_exported',None,{'request':rid,'items':len(items),'dataset_sha256':manifest['dataset_sha256']})
        return manifest
    def report(self):
        rs=list(self.box.load()[0]['requests'].values())
        return {'revision':REVISION,'requests':len(rs),'by_status':{s:sum(r['status']==s for r in rs) for s in sorted({r['status'] for r in rs})},
                'claim_limit':'Dataset export behind HX2 PASS + human approval; trains nothing, no live authority (SHADOW)'}

def retention_gate(ev,tol=TOLERANCE,max_kl=None):
    """Fail closed on missing/nonfinite retention, forgetting and leak evidence.

    max_kl=None means no KL threshold was preregistered: the output explicitly
    reports kl_checked=False. A supplied KL bound must be finite and nonnegative.
    This is an evaluation-only gate; it never activates an adapter.
    """
    fails=[]
    def valid(value,unit=True):
        return (type(value) in (int,float) and math.isfinite(value)
                and value>=0 and (not unit or value<=1))
    if not valid(tol):fails.append('invalid_tolerance');tol=0.
    if max_kl is not None and not valid(max_kl,False):
        fails.append('invalid_kl_threshold')
    ev=ev if type(ev) is dict else {}
    b=ev.get('base_eval');c=ev.get('candidate_eval')
    b=b if type(b) is dict else {}
    c=c if type(c) is dict else {}
    lr,br=ev.get('learned_recall'),ev.get('base_recall')
    if not valid(lr) or not valid(br) or lr<=br:
        fails.append('no_learning_gain')
    for ax in ('overall','unseen'):
        base,candidate=b.get(ax),c.get(ax)
        if not valid(base) or not valid(candidate) or candidate<base-tol:
            fails.append('retention_'+ax)
    forgetting=c.get('forgetting')
    rate=forgetting.get('rate') if type(forgetting) is dict else None
    if not valid(rate) or rate>tol:fails.append('forgetting')
    leak=ev.get('near_miss_leak')
    if not valid(leak) or leak>tol:fails.append('near_miss_leak')
    kl=ev.get('kl_to_base')
    klv=kl.get('mean') if type(kl) is dict else kl
    if max_kl is not None:
        if not valid(klv,False) or klv>max_kl:fails.append('kl_to_base')
    elif klv is not None and not valid(klv,False):
        fails.append('kl_to_base_invalid')
    return {'status':'RETENTION_PASS' if not fails else 'RETENTION_FAIL',
            'fails':fails,'tolerance':tol,'max_kl':max_kl,
            'kl_checked':max_kl is not None}
