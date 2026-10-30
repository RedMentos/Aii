"""WP-AG9 metacognition: knowing what it does not know.

Per component (B1, B2, JEF, a tool, a skill) the tracker records (raw confidence, was it
correct) from grounded outcomes or human labels, fits a monotone histogram calibrator
(pure Python, no model), reports ECE/Brier and gives the effort policy two decisions:
second_attempt (spend more compute) and abstain (say "weiß ich nicht"). semantic_entropy
estimates uncertainty from several sampled answers without a confidence head.
The calibrated value feeds age.record(metrics['calibration']).
"""
import math
import re
from .base import StateBox,clamp01
from .generality import calibration,normalize

KEY='G9_METACOGNITION';REVISION='g9-metacog-v1'
BINS=10;WINDOW=512;MIN_SUPPORT=20
RECEIPT_HISTORY=256  # bounded per-component duplicate suppression, not permanent exactly-once
SECOND_ATTEMPT=(.35,.75)  # BOOT: retry band of calibrated confidence
ABSTAIN_BELOW=.2


def _finite_confidence(value):
    """Never map NaN/Inf/bool to plausible confidence via clamp01."""
    if type(value) is bool:
        raise ValueError("AG9_INVALID_CONFIDENCE")
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("AG9_INVALID_CONFIDENCE") from exc
    if not math.isfinite(number):
        raise ValueError("AG9_INVALID_CONFIDENCE")
    return clamp01(number)


def _binary_label(value):
    if type(value) is bool:
        return int(value)
    if type(value) is int and value in (0, 1):
        return value
    raise ValueError("AG9_INVALID_OUTCOME_LABEL")


def _component_name(value):
    if (type(value) is not str or not value or len(value) > 64
            or value != value.strip()
            or any(ord(char) < 32 or ord(char) == 127 for char in value)):
        raise ValueError("AG9_INVALID_COMPONENT")
    return value


class Metacognition:
    def __init__(self,store):
        self.box=StateBox(store,KEY,REVISION,lambda:{'components':{}})
    def record(self,component,confidence,correct,evidence=None):
        component = _component_name(component)
        c, k = _finite_confidence(confidence), _binary_label(correct)
        def f(st):
            comp=st['components'].setdefault(component,{'pairs':[],'calibrator':None})
            comp['pairs']=(comp['pairs']+[[c,k]])[-WINDOW:];comp['calibrator']=self._fit(comp['pairs'])
        self.box.mutate(f)
    def record_batch(self,component,pairs,receipt):
        """Atomically append a validated batch, fitting PAV once and deduping recent receipts."""
        component = _component_name(component)
        if (type(receipt) is not str or re.fullmatch(r'[0-9a-f]{64}',receipt) is None):
            raise ValueError('AG9_INVALID_RECEIPT')
        if type(pairs) not in (list,tuple) or not 1<=len(pairs)<=WINDOW:
            raise ValueError('AG9_INVALID_BATCH')
        validated=[]
        for pair in pairs:
            if type(pair) not in (list,tuple) or len(pair)!=2:
                raise ValueError('AG9_INVALID_BATCH_ROW')
            if type(pair[1]) is not int or pair[1] not in (0,1):
                raise ValueError('AG9_INVALID_OUTCOME_LABEL')
            validated.append([_finite_confidence(pair[0]),pair[1]])
        prior=self.box.load()[0]['components'].get(component)
        if prior and receipt in prior.get('receipts',[]):
            return {'status':'DUPLICATE','added':0}
        def f(st):
            comp=st['components'].setdefault(component,{'pairs':[],'calibrator':None})
            if receipt in comp.get('receipts',[]):
                return {'status':'DUPLICATE','added':0}
            comp['pairs']=(comp['pairs']+validated)[-WINDOW:]
            comp['calibrator']=self._fit(comp['pairs'])
            comp['receipts']=(comp.get('receipts',[])+[receipt])[-RECEIPT_HISTORY:]
            return {'status':'RECORDED','added':len(validated)}
        return self.box.mutate(f)
    @staticmethod
    def _fit(pairs):
        """Histogram binning, then pool-adjacent-violators so calibrated confidence is monotone."""
        if len(pairs)<MIN_SUPPORT:return None
        bins=[[0,0] for _ in range(BINS)]
        for c,k in pairs:b=min(BINS-1,int(c*BINS));bins[b][0]+=k;bins[b][1]+=1
        blocks=[[(s+1)/(n+2),n+2,[i]] for i,(s,n) in enumerate(bins)]  # Laplace-smoothed
        i=0
        while i<len(blocks)-1:
            if blocks[i][0]>blocks[i+1][0]:
                a,b=blocks[i],blocks[i+1];w=a[1]+b[1]
                blocks[i:i+2]=[[(a[0]*a[1]+b[0]*b[1])/w,w,a[2]+b[2]]];i=max(0,i-1)
            else:i+=1
        table=[0.]*BINS
        for v,_,idx in blocks:
            for j in idx:table[j]=round(v,6)
        return table
    def calibrated(self,component,confidence):
        try:
            _component_name(component)
        except ValueError:
            return None
        try:
            c = _finite_confidence(confidence)
        except ValueError:
            return None
        comp=self.box.load()[0]['components'].get(component)
        if not comp or not comp['calibrator']:return None  # unknown: callers must treat as uncalibrated
        return comp['calibrator'][min(BINS-1,int(c*BINS))]
    def decide(self,component,confidence):
        try:
            _component_name(component)
        except ValueError:
            return {'calibrated':None,'second_attempt':False,
                    'abstain':True,'reason':'INVALID_COMPONENT'}
        try:
            _finite_confidence(confidence)
        except ValueError:
            return {'calibrated':None,'second_attempt':False,
                    'abstain':True,'reason':'INVALID_CONFIDENCE'}
        p=self.calibrated(component,confidence)
        if p is None:return {'calibrated':None,'second_attempt':True,'abstain':False,'reason':'UNCALIBRATED'}
        return {'calibrated':p,'second_attempt':SECOND_ATTEMPT[0]<=p<SECOND_ATTEMPT[1],'abstain':p<ABSTAIN_BELOW,'reason':'CALIBRATED'}
    def report(self,component=None):
        comps=self.box.load()[0]['components'];out={}
        for name,c in comps.items():
            if component and name!=component:continue
            raw=calibration([(a,b) for a,b in c['pairs']])
            cal=calibration([(c['calibrator'][min(BINS-1,int(a*BINS))],b) for a,b in c['pairs']]) if c['calibrator'] else None
            out[name]={'n':len(c['pairs']),'raw':{'ece':raw['ece'],'brier':raw['brier']},'calibrated':cal and {'ece':cal['ece'],'brier':cal['brier']}}
        return {'revision':REVISION,'components':out}
    def age_metric(self,component):
        """1-ECE of the calibrated component, the 'calibration' metric for the Age gate (None if unsupported)."""
        r=self.report(component)['components'].get(component)
        if not r or not r['calibrated'] or r['calibrated']['ece'] is None:return None
        return round(1-r['calibrated']['ece'],4)

def semantic_entropy(answers,equivalent=None):
    """Cluster sampled answers by meaning (default: normalized equality); entropy in nats and agreement."""
    if not answers:return {'entropy':None,'clusters':0,'agreement':None}
    eq=equivalent or (lambda a,b:normalize(a)==normalize(b));clusters=[]
    for a in answers:
        for cl in clusters:
            if eq(cl[0],a):cl.append(a);break
        else:clusters.append([a])
    n=len(answers);ps=[len(c)/n for c in clusters]
    return {'entropy':round(-sum(p*math.log(p) for p in ps),6),'clusters':len(clusters),'agreement':round(max(ps),6),'majority':max(clusters,key=len)[0]}
