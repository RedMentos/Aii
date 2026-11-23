"""WP-AG11 social model: an "Other-Model" of the user next to the Self-Model in F3 (§7.3).

Beliefs about the user (preferences, knowledge per topic, open intentions, style) are
stored as claims with evidence refs, a confidence and a time; repeated evidence raises
confidence, contradicting evidence replaces the value, unused beliefs decay. Only explicit
evidence counts (feedback, corrections, stated facts); nothing is inferred about protected
attributes (health, religion, politics, sexuality, ethnicity, finances). The user can view,
correct and delete everything (forget()).
"""
import time
from .base import StateBox,clamp01

KEY='G11_USER_MODEL';REVISION='g11-user-model-v1'
ASPECTS=('preference','knowledge','intention','style','correction_pattern')
PROTECTED=('health','gesundheit','religion','politik','politics','sexual','ethni','herkunft','finanz','finance','krankheit')
MAX_BELIEFS=512;HALF_LIFE_DAYS=90.

class UserModel:
    def __init__(self,store,clock=time.time):
        self.s=store;self.clock=clock
        self.box=StateBox(store,KEY,REVISION,lambda:{'users':{}})
    def observe(self,aspect,topic,value,evidence_ref,user='owner',strength=.5):
        if aspect not in ASPECTS:raise ValueError('aspect '+'|'.join(ASPECTS))
        if not evidence_ref:raise ValueError('Nur mit Beleg (evidence_ref)')
        t=str(topic).casefold()
        if any(p in t or p in str(value).casefold() for p in PROTECTED):raise PermissionError('Geschütztes Merkmal wird nicht modelliert')
        def f(st):
            u=st['users'].setdefault(user,{'beliefs':{}});k=aspect+':'+t;b=u['beliefs'].get(k)
            if b is None or b['value']!=value:
                if b is None and len(u['beliefs'])>=MAX_BELIEFS:
                    u['beliefs'].pop(min(u['beliefs'],key=lambda x:u['beliefs'][x]['updated']))
                prev=b and {'value':b['value'],'confidence':b['confidence']}
                b=u['beliefs'][k]={'aspect':aspect,'topic':t,'value':value,'confidence':clamp01(strength),'evidence':[],'updated':self.clock(),'replaced':prev}
            else:b['confidence']=round(1-(1-b['confidence'])*(1-clamp01(strength)),4)
            b['evidence']=(b['evidence']+[evidence_ref])[-8:];b['updated']=self.clock();return dict(b)
        return self.box.mutate(f)
    def _decayed(self,b):
        age_days=(self.clock()-b['updated'])/86400.
        return round(b['confidence']*.5**(age_days/HALF_LIFE_DAYS),4)
    def beliefs(self,user='owner',aspect=None,min_confidence=0.):
        u=self.box.load()[0]['users'].get(user,{'beliefs':{}})
        out=[dict(b,confidence=self._decayed(b)) for b in u['beliefs'].values() if aspect in (None,b['aspect'])]
        return sorted([b for b in out if b['confidence']>=min_confidence],key=lambda b:-b['confidence'])
    def context(self,user='owner',limit=6):
        """Compact, source-bound context for C1/JEF: the strongest current beliefs, labelled as beliefs."""
        return [{'aspect':b['aspect'],'topic':b['topic'],'value':b['value'],'confidence':b['confidence'],'authority':'BELIEF_NOT_FACT'}
                for b in self.beliefs(user,min_confidence=.3)[:limit]]
    def forget(self,user='owner',aspect=None,topic=None):
        def f(st):
            u=st['users'].get(user)
            if not u:return 0
            keep={k:b for k,b in u['beliefs'].items() if not ((aspect in (None,b['aspect'])) and (topic is None or b['topic']==str(topic).casefold()))}
            n=len(u['beliefs'])-len(keep);u['beliefs']=keep;return n
        return self.box.mutate(f)
    def report(self,user='owner'):
        bs=self.beliefs(user)
        return {'revision':REVISION,'beliefs':len(bs),'by_aspect':{a:sum(b['aspect']==a for b in bs) for a in ASPECTS},'top':self.context(user),
                'claim_limit':'Explicit-evidence belief store; no learned theory-of-mind model'}
