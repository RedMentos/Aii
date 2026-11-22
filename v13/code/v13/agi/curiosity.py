"""WP-AG5 intrinsic motivation: learning progress as reward (Layer 6 M_novelty / M_surprise).

Per region (task family, domain, skill) the tracker keeps a window of prediction errors.
Learning progress LP = mean(older half) - mean(newer half): positive when V13 is getting
better there. Intrinsic value = max(0, LP) + novelty bonus for little-visited regions, so
it is drawn to where it learns, not to noise (unlearnable regions have LP≈0) and not to
what it already knows (error≈0, LP≈0). choose() picks a practice target; the Age budget
exploration_rate (0 at Age 0) and the right active_info_search bound what it may do on
its own. Blocked regions (user/hard rules) are never chosen.
"""
import random
from .base import StateBox,age_allows,budget,clamp01

KEY='G5_CURIOSITY';REVISION='g5-curiosity-v1'
WINDOW=32;NOVELTY=.2;MAX_REGIONS=256

class Curiosity:
    def __init__(self,store,age=None,rng=None):
        self.age=age;self.rng=rng or random.Random()
        self.box=StateBox(store,KEY,REVISION,lambda:{'regions':{},'blocked':[]})
    def observe(self,region,error):
        e=clamp01(error)
        def f(st):
            r=st['regions'].get(region)
            if r is None:
                if len(st['regions'])>=MAX_REGIONS:
                    old=min(st['regions'],key=lambda k:st['regions'][k]['visits']);st['regions'].pop(old)
                r=st['regions'][region]={'errors':[],'visits':0}
            r['errors']=(r['errors']+[e])[-WINDOW:];r['visits']+=1
            return self._value(r)
        return self.box.mutate(f)
    @staticmethod
    def _lp(errors):
        if len(errors)<4:return 0.
        h=len(errors)//2;old,new=errors[:h],errors[h:]
        return sum(old)/len(old)-sum(new)/len(new)
    def _value(self,r):
        lp=self._lp(r['errors']);nov=NOVELTY/(1+r['visits'])**.5
        return {'learning_progress':round(lp,6),'novelty':round(nov,6),'intrinsic':round(max(0.,lp)+nov,6),
                'error':round(r['errors'][-1],6) if r['errors'] else None}
    def block(self,region,on=True):
        def f(st):st['blocked']=sorted(set(st['blocked'])|{region}) if on else [b for b in st['blocked'] if b!=region]
        self.box.mutate(f)
    def values(self):
        st=self.box.load()[0]
        return {k:self._value(r) for k,r in st['regions'].items() if k not in st['blocked']}
    def choose(self,candidates=None,origin='SELF'):
        """Return a region to practice, or None. SELF choice needs active_info_search and exploration_rate>0."""
        vals=self.values()
        if candidates is not None:vals={k:vals.get(k,{'intrinsic':NOVELTY}) for k in candidates if k not in self.box.load()[0]['blocked']}
        if not vals:return None
        if origin!='USER':
            if not age_allows(self.age,'active_info_search',origin):return None
            if self.rng.random()>=budget(self.age,'exploration_rate',0.):return None
        return max(vals,key=lambda k:(vals[k]['intrinsic'],k))
    def modulators(self,region):
        """Typed Layer-6 signals for the learning fabric; never a global reward."""
        v=self.values().get(region)
        if v is None:return {'M_novelty':NOVELTY,'M_surprise':None}
        return {'M_novelty':v['novelty'],'M_surprise':v['error'],'M_progress':v['learning_progress']}
    def report(self):
        vals=self.values()
        top=sorted(vals.items(),key=lambda kv:-kv[1]['intrinsic'])[:8]
        return {'revision':REVISION,'regions':len(vals),'top':dict(top),'blocked':self.box.load()[0]['blocked'],
                'autonomous':age_allows(self.age,'active_info_search','SELF') and budget(self.age,'exploration_rate',0.)>0}
