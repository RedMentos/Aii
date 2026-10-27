"""WP-HX1 harness ("Drumherum") as an AG8 proposal kind (research/HARNESS2_AUSWERTUNG.md, Harness² arXiv 2610.14224).

The harness is the text and rule data around frozen weights: body prompt pieces, tool hints, parser rule sets,
recipe templates. Only targets on the fixed allow-list below are editable; everything else, above all safety and
moral texts (prompts 'system'/'conduct', operator rules, prohibitions, user rules, Age, channel), is never a target.
A harness change goes the same AG8 way as a knob: sandbox evaluator, regression shield, PENDING_USER, human approve,
then HarnessLibrary.apply(). Each apply keeps the previous value and the base generation as its rollback point.

Authority 0: no live consumer reads an override yet (SHADOW). resolve() serves evaluators/benches only; wiring a live
prompt path needs the HX2 gate PASS and the user. Defaults are read from the live modules, which stay unchanged.
"""
import re
import time
from .base import StateBox
from ..common import digest,dumps

KEY='G8_HARNESS';REVISION='hx1-harness-v1'
MAX_TEXT=600;MAX_RULES=32;MAX_PATTERN=200;HISTORY=64
LIST_OPS=('total','difference_max_min')  # listarith operations a parser rule may map to
# Never editable, whatever the target name says (also checked on the text: a harness edit may not talk the body out of its rules).
PROTECTED_PROMPTS=('system','conduct','operator_rules','replay_rules','user_model','memories','replay_memories')
# Second net only (wording heuristic, gaps possible); the real protection is the allow-list plus human approval.
WEAKEN=re.compile(r'(?i)\b(?:ignore|disregard|override|bypass|forget|skip|disable|drop|never mind|ignorier\w*|missacht\w*|umgeh\w*|übergeh\w*|vergiss)\b'
                  r'[^.]{0,60}\b(?:rules?|instructions?|safety|guard\w*|conduct|prohibition\w*|verbot\w*|operator|harm|limits?|regeln?|anweisung\w*|sicherheit\w*|grenzen?)\b'
                  r'|\b(?:rules?|instructions?|limits?|regeln|grenzen)\b[^.]{0,30}\b(?:do not|don\'t|no longer|never) apply\b|\b(?:regeln|grenzen)\b[^.]{0,30}\bgelten nicht\b'
                  r'|\b(?:no|without|ohne)\s+(?:rules|limits|safety|restrictions|regeln|grenzen)\b|\bjailbreak|\bdeveloper mode\b')

def _prompt(lang,key):
    def f():
        from .. import prompts
        return prompts.TEXT[lang][key]
    return f
def _attr(mod,name):
    def f():
        import importlib
        return getattr(importlib.import_module('v13.'+mod),name)
    return f
def _listarith_extra():
    from . import listarith
    return [[p.pattern,op] for p,op in listarith.EXTRA]

def _text(v,required=()):
    if not isinstance(v,str) or not v.strip():raise ValueError('Text erwartet')
    if len(v)>MAX_TEXT:raise ValueError(f'Text länger als {MAX_TEXT}')
    if any(ord(c)<32 and c not in '\n\t' for c in v):raise ValueError('Steuerzeichen im Text')
    for r in required:
        if r not in v:raise ValueError('Platzhalter fehlt: '+r)
    return v
def _rules(v):
    if not isinstance(v,list) or not 0<len(v)<=MAX_RULES:raise ValueError(f'1..{MAX_RULES} Regeln erwartet')
    out=[]
    for r in v:
        if not (isinstance(r,(list,tuple)) and len(r)==2 and isinstance(r[0],str) and r[1] in LIST_OPS):raise ValueError('Regel = [Muster, '+'|'.join(LIST_OPS)+']')
        if not r[0] or len(r[0])>MAX_PATTERN:raise ValueError('Muster leer oder zu lang')
        try:re.compile(r[0])
        except re.error as exc:raise ValueError('Muster ungültig: '+str(exc)) from None
        out.append([r[0],r[1]])
    return out

# target -> (category, default getter, validator). The allow-list is the code; a proposal cannot add targets.
TARGETS={}
for _lang in ('en','de'):
    for _k in ('answer_rules','digest','task_context','hypotheses','clarify','replay','duplex_handoff','welcome'):
        TARGETS[f'prompt.{_lang}.{_k}']=('body_prompt',_prompt(_lang,_k),_text)
TARGETS['tool_hint.list_note']=('tool_hint',_attr('toolstep','LIST_NOTE'),_text)
TARGETS['tool_hint.eligibility_note']=('tool_hint',_attr('agi.eligibility','LIVE_NOTE'),_text)
TARGETS['parser.listarith_extra']=('parser_rules',_listarith_extra,_rules)
TARGETS['recipe.list_result']=('recipe_template',lambda:'{label} = {result}',lambda v:_text(v,('{result}',)))
CATEGORIES=tuple(sorted({c for c,_,_ in TARGETS.values()}))

def _weakens(v):
    return isinstance(v,str) and bool(WEAKEN.search(v))  # parser rules are patterns the body never reads; ops are allow-listed

def candidate(diff):
    """Validate a harness diff {target: value}; raises PermissionError for anything off the allow-list."""
    if not isinstance(diff,dict) or not diff:raise ValueError('Harness-Diff {Ziel: Wert} erwartet')
    bad=sorted(t for t in diff if t not in TARGETS)
    if bad:raise PermissionError('Nicht vorschlagbar (Harness): '+', '.join(bad))
    out={}
    for t,v in diff.items():
        v=TARGETS[t][2](v)
        if _weakens(v):raise PermissionError('Harness-Text schwächt Regeln: '+t)
        out[t]=v
    return out

def default(target):
    if target not in TARGETS:raise KeyError(target)
    return TARGETS[target][1]()

class HarnessLibrary:
    """Active harness overrides with history. apply() only takes an APPROVED AG8 'harness' proposal."""
    def __init__(self,store,clock=time.time):
        self.s=store;self.clock=clock
        self.box=StateBox(store,KEY,REVISION,lambda:{'active':{},'history':[]})
    def resolve(self,target):
        """Override if applied, else the live default. For evaluators/benches; no live consumer yet (authority 0)."""
        a=self.box.load()[0]['active'].get(target)
        return a['value'] if a else default(target)
    def overlay(self,diff=None):
        """Settings for an evaluator: every target resolved, with an optional candidate diff on top (sandbox, nothing stored)."""
        out={t:self.resolve(t) for t in TARGETS}
        if diff:out|=candidate(diff)
        return out
    def apply(self,proposal,settings):
        if proposal.get('kind')!='harness' or proposal.get('status')!='APPROVED':raise PermissionError('Nur freigegebene Harness-Vorschläge')
        if not (proposal.get('shield') or {}).get('passed'):raise PermissionError('Regressionsschild nicht bestanden')
        settings=candidate(settings)
        if settings!=candidate(proposal['diff']):raise ValueError('Werte weichen vom freigegebenen Vorschlag ab')
        def f(st):
            if any(h['proposal']==proposal['id'] and h['op']=='apply' for h in st['history']):raise ValueError('Schon angewendet')
            for t,v in settings.items():
                prev=st['active'].get(t);ver=(prev or {}).get('version',0)+1
                st['active'][t]={'value':v,'version':ver,'proposal':proposal['id'],'applied':self.clock(),'generation':self.s.generation_id}
                st['history'].append({'op':'apply','target':t,'proposal':proposal['id'],'version':ver,'previous':prev,
                                      'rollback_generation':proposal.get('base_generation'),'time':self.clock()})
            st['history']=st['history'][-HISTORY:]
            return self._hash(st)
        h=self.box.mutate(f);self.s.log('harness_applied',None,{'proposal':proposal['id'],'targets':sorted(settings),'harness_hash':h})
        return {'targets':sorted(settings),'harness_hash':h}
    def rollback(self,target):
        """Human act: back to the value before the last apply of this target (or the live default)."""
        def f(st):
            last=next((h for h in reversed(st['history']) if h['target']==target and h['op']=='apply' and not h.get('undone')),None)
            if last is None:raise ValueError('Nichts zurückzunehmen: '+target)
            last['undone']=True
            if last['previous']:st['active'][target]=last['previous']
            else:st['active'].pop(target,None)
            st['history'].append({'op':'rollback','target':target,'proposal':last['proposal'],'version':last['version'],'time':self.clock()})
            st['history']=st['history'][-HISTORY:]
            return last['proposal']
        pid=self.box.mutate(f);self.s.log('harness_rollback',None,{'target':target,'proposal':pid});return pid
    def _hash(self,st):return digest(dumps({t:a['value'] for t,a in sorted(st['active'].items())}))
    def manifest_fields(self):
        st=self.box.load()[0]
        return {'harness_hash':self._hash(st),'harness_targets':{t:a['version'] for t,a in sorted(st['active'].items())}}
    def report(self):
        st=self.box.load()[0]
        return {'revision':REVISION,'categories':list(CATEGORIES),'targets':len(TARGETS),'active':sorted(st['active']),
                'live_consumers':0,'harness_hash':self._hash(st),
                'claim_limit':'Allow-listed harness edits behind the AG8 shield and human approval; overrides not read by the live path yet (SHADOW)'}
