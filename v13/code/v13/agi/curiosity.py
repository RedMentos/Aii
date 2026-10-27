"""WP-AG5 intrinsic motivation: learning progress as reward (Layer 6 M_novelty / M_surprise).

Per region (task family, domain, skill) the tracker keeps a window of prediction errors.
Learning progress LP = mean(older half) - mean(newer half): positive when V13 is getting
better there. Intrinsic value = max(0, LP) + novelty bonus for little-visited regions, so
it is drawn to where it learns, not to noise (unlearnable regions have LP≈0) and not to
what it already knows (error≈0, LP≈0). choose() picks a practice target; the Age budget
exploration_rate (0 at Age 0) and the right active_info_search bound what it may do on
its own. Blocked regions (user/hard rules) are never chosen.
"""
import json
import math
import random
from ..common import dumps
from .base import StateBox,age_allows,budget,clamp01

KEY='G5_CURIOSITY';REVISION='g5-curiosity-v1'
WINDOW=32;NOVELTY=.2;MAX_REGIONS=256

class Curiosity:
    def __init__(self,store,age=None,rng=None):
        self.age=age;self.rng=rng or random.Random()
        self.box=StateBox(store,KEY,REVISION,lambda:{'regions':{},'blocked':[]})
    def observe(self,region,error):
        # An invalid prediction error is not evidence of zero error (success).
        # Shared clamp01 deliberately maps nonfinite *confidence* to zero;
        # learning-error evidence must instead fail closed before that clamp.
        if type(error) not in (int,float):raise ValueError('Prediction error must be numeric')
        try:finite=math.isfinite(error)
        except (OverflowError,ValueError,TypeError):finite=False
        if not finite:raise ValueError('Prediction error must be finite')
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
    def observe_once(self,region,error,event_id,session_id):
        """One durable AG5 learning-error observation per source event.

        The region update and receipt are a single SQLite transaction, so
        neither a crash nor a repeated terminal hook creates a second visit.
        Unbound synthetic observations still use observe() unchanged.
        """
        if type(error) not in (int,float):
            raise ValueError('Prediction error must be numeric')
        try:finite=math.isfinite(error)
        except (OverflowError,ValueError,TypeError):finite=False
        if not finite:
            raise ValueError('Prediction error must be finite')
        if not isinstance(region,str) or not 0<len(region)<=200:
            raise ValueError('region: required bounded name')
        if not isinstance(event_id,str) or not 0<len(event_id)<=128:
            raise ValueError('event_id: required bounded source ID')
        if not isinstance(session_id,str) or not 0<len(session_id)<=128:
            raise ValueError('session_id: required bounded source ID')
        e=clamp01(error)
        key='G5_EVENT:'+event_id
        with self.box.s.tx() as c:
            event=c.execute('SELECT session_id FROM events WHERE id=?',(event_id,)).fetchone()
            if event is None or event['session_id']!=session_id:
                raise ValueError('curiosity outcome event/session mismatch')
            old=c.execute('SELECT payload FROM states WHERE key=?',(key,)).fetchone()
            if old is not None:
                receipt=json.loads(old['payload'])
                if not isinstance(receipt,dict) or receipt.get('region')!=region or receipt.get('session_id')!=session_id:
                    raise ValueError('curiosity receipt already bound to another region/session')
                return False
            row=c.execute('SELECT payload,version FROM states WHERE key=?',(KEY,)).fetchone()
            st=json.loads(row['payload']) if row else {'regions':{},'blocked':[],'revision':REVISION}
            if st.get('revision')!=REVISION:
                raise ValueError('curiosity state revision mismatch')
            r=st['regions'].get(region)
            if r is None:
                if len(st['regions'])>=MAX_REGIONS:
                    least=min(st['regions'],key=lambda k:st['regions'][k]['visits'])
                    st['regions'].pop(least)
                r=st['regions'][region]={'errors':[],'visits':0}
            r['errors']=(r['errors']+[e])[-WINDOW:]
            r['visits']+=1
            if row:
                cursor=c.execute('UPDATE states SET payload=?,version=? WHERE key=? AND version=?',
                                 (dumps(st),row['version']+1,KEY,row['version']))
                if cursor.rowcount!=1:
                    raise ValueError('stale curiosity state')
            else:
                c.execute('INSERT INTO states VALUES (?,?,?)',(KEY,1,dumps(st)))
            c.execute('INSERT INTO states VALUES (?,?,?)',
                      (key,1,dumps({'region':region,'session_id':session_id,'error':e})))
        return True

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
