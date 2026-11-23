"""WP-AG4 open-ended skill learning: an executable skill library plus practice at the edge of ability.

A skill is a declarative procedure: ordered steps, each either a registered tool call (AG10)
with argument templates, or a route hint for the bodies. No arbitrary code is stored or
executed (Voyager-style "skills as code" stays out until a sandbox exists, AG8).
Lifecycle (blueprint §6.2, §6.5, L5.6): CANDIDATE → SHADOW → TRUSTED → INTERNALISED | RETIRED.
Promotion needs repeated success and parity against the full route; procedural_memory
(Age 2) is required before a skill may be TRUSTED without the user. practice() proposes
tasks where success is between 30 % and 70 % (learning frontier), only from non-holdout
families (AG12 practice_items).
"""
import re
import time
from .base import StateBox,age_allows

KEY='G4_SKILLS';REVISION='g4-skills-v1'
STAGES=('CANDIDATE','SHADOW','TRUSTED','INTERNALISED','RETIRED')
PROMOTE={'CANDIDATE':3,'SHADOW':8}  # BOOT: successes needed to leave a stage
PARITY_MIN=.95;FRONTIER=(.3,.7);MAX_SKILLS=256;MAX_STEPS=16
_VAR=re.compile(r'\{(\w+)\}')

def fill(template,inputs):
    if isinstance(template,str):return _VAR.sub(lambda m:str(inputs[m.group(1)]),template)
    if isinstance(template,dict):return {k:fill(v,inputs) for k,v in template.items()}
    if isinstance(template,list):return [fill(v,inputs) for v in template]
    return template

class SkillLibrary:
    def __init__(self,store,age=None,tools=None,clock=time.time):
        self.s=store;self.age=age;self.tools=tools;self.clock=clock
        self.box=StateBox(store,KEY,REVISION,lambda:{'skills':{},'outcomes':{}})
    def propose(self,name,steps,trigger='',origin='USER',source_traces=None):
        if not re.fullmatch(r'[a-z0-9_]{2,48}',name):raise ValueError('Skill-Name a-z0-9_')
        if not steps or len(steps)>MAX_STEPS:raise ValueError('1..16 Schritte')
        for s in steps:
            if set(s)-{'tool','args','route','note'} or ('tool' in s)==('route' in s):raise ValueError('Schritt: genau tool+args oder route')
        def f(st):
            if name in st['skills'] and st['skills'][name]['stage']!='RETIRED':raise ValueError('Skill existiert')
            if len(st['skills'])>=MAX_SKILLS:raise ValueError('Skill-Speicher voll')
            st['skills'][name]={'name':name,'steps':steps,'trigger':str(trigger)[:200],'origin':origin,'stage':'CANDIDATE',
                'uses':0,'successes':0,'parity':[],'created':self.clock(),'source_traces':list(source_traces or [])[:16],'history':[['CANDIDATE',self.clock()]]}
        self.box.mutate(f);return name
    def run(self,name,inputs,origin='USER'):
        """Execute tool steps through the ToolRegistry (its gates apply); route steps are returned as hints."""
        sk=self.get(name)
        if sk['stage']=='RETIRED':raise ValueError('Skill stillgelegt')
        if self.tools is None:raise RuntimeError('Kein Werkzeug-Register')
        trace=[];value=None
        for s in sk['steps']:
            if 'route' in s:trace.append({'route':s['route']});continue
            tx=self.tools.call(s['tool'],fill(s.get('args',{}),dict(inputs,prev=value)),origin=origin,intent='skill:'+name)
            trace.append({'tool':s['tool'],'status':tx['status'],'tx':tx['id']})
            if tx['status']!='EXECUTED':return {'status':tx['status'],'trace':trace,'value':None}
            value=tx['result']
        return {'status':'DONE','trace':trace,'value':value}
    def record(self,name,success,parity=None,family=None):
        """Outcome of one use (shadow or live). parity: agreement with the full focal route on the same input."""
        def f(st):
            sk=st['skills'][name];sk['uses']+=1;sk['successes']+=int(bool(success))
            if parity is not None:sk['parity']=(sk['parity']+[float(parity)])[-32:]
            if family:
                o=st['outcomes'].setdefault(family,[0,0]);o[0]+=int(bool(success));o[1]+=1
            return self._advance(sk)
        return self.box.mutate(f)
    def _advance(self,sk):
        need=PROMOTE.get(sk['stage'])
        if need is None:return sk['stage']
        par=sum(sk['parity'])/len(sk['parity']) if sk['parity'] else 0.
        if sk['successes']>=need and par>=PARITY_MIN:
            nxt=STAGES[STAGES.index(sk['stage'])+1]
            if nxt=='TRUSTED' and sk['origin']!='USER' and not age_allows(self.age,'procedural_memory','SELF'):
                sk['pending']='TRUSTED_NEEDS_AGE_OR_USER';return sk['stage']
            sk['stage']=nxt;sk['successes']=0;sk['history'].append([nxt,self.clock()]);sk.pop('pending',None)
        return sk['stage']
    def set_stage(self,name,stage):
        """User decision: promote, internalise or retire explicitly."""
        if stage not in STAGES:raise ValueError('Stufe')
        def f(st):sk=st['skills'][name];sk['stage']=stage;sk['history'].append([stage+'_USER',self.clock()]);sk.pop('pending',None)
        self.box.mutate(f)
    def reopen(self,name,reason='failure'):
        """Novelty/failure reopens the focal route (L5.6): TRUSTED/INTERNALISED drop back to SHADOW."""
        def f(st):
            sk=st['skills'][name]
            if sk['stage'] in {'TRUSTED','INTERNALISED'}:sk['stage']='SHADOW';sk['successes']=0;sk['history'].append(['REOPENED:'+reason,self.clock()])
        self.box.mutate(f)
    def select(self,text):
        """Skill selector (§6.2) kept separate from the store: trusted skills whose trigger words all occur."""
        words=set(re.findall(r'\w+',text.casefold()));out=[]
        for sk in self.box.load()[0]['skills'].values():
            t=set(re.findall(r'\w+',sk['trigger'].casefold()))
            if sk['stage'] in {'TRUSTED','INTERNALISED'} and t and t<=words:out.append(sk['name'])
        return sorted(out)
    def practice(self,items,n=8):
        """Practice set at the learning frontier: families with success rate in FRONTIER, else least tried."""
        outc=self.box.load()[0]['outcomes'];rate=lambda f:outc[f][0]/outc[f][1] if f in outc and outc[f][1] else None
        fams=sorted({i['family'] for i in items})
        frontier=[f for f in fams if rate(f) is not None and FRONTIER[0]<=rate(f)<=FRONTIER[1]]
        pick=frontier or sorted(fams,key=lambda f:(outc.get(f,[0,0])[1],f))[:2]
        return [i for i in items if i['family'] in pick][:n]
    def get(self,name):
        sk=self.box.load()[0]['skills'].get(name)
        if sk is None:raise KeyError(name)
        return sk
    def report(self):
        st=self.box.load()[0]
        return {'revision':REVISION,'skills':{n:{'stage':s['stage'],'uses':s['uses'],'pending':s.get('pending')} for n,s in st['skills'].items()},
                'families':{f:{'success':o[0],'n':o[1]} for f,o in st['outcomes'].items()},
                'claim_limit':'Declarative tool/route procedures; no generated code; internalisation into weights goes via AG6'}
