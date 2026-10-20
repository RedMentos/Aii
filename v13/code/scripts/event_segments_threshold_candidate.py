"""Isolated candidate (thread L, 2026-10-12) after `ablation_event_segments.py` (PARTIAL): cuts follow length because the
length prior (.40) plus a sentence end (.25) already reach the cut threshold .5. Candidate: same unchanged
`episodes.text_segments`, only a higher `threshold` argument, so a cut needs paragraph or topic-shift evidence.

PREREG (fixed before the first run):
  threshold grid {.6, .65, .7, .75, .8}; chosen on calibration seeds 101-105 (flat texts, max mean F1; ties -> lower).
  Test seeds 13-17, same text generator, scoring and controls as the ablation; `even`/`random` use the candidate's count.
  PASS only if on flat the candidate beats (a) the current threshold .5 and (b) evenly spaced sentence cuts of the same
  count in >= 4/5 seeds each, and on para it is not worse than .5 in more than 1/5 seeds. Otherwise FAIL.
Claim limit: as the ablation (short synthetic topic mixtures, lexical signals, width 240). episodes.py unchanged.
"""
import json
import random
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from v13.ablation99 import _mean
from v13.episodes import text_segments,_units
import ablation_event_segments as E

GRID=(.6,.65,.7,.75,.8);CAL=(101,102,103,104,105);TEST=(13,14,15,16,17)
PREREG={'schema':'EVENT_SEGMENTS_THRESHOLD_PREREG_V1','grid':list(GRID),'calibration_seeds':list(CAL),'test_seeds':list(TEST),
        'selection':'max mean F1 on flat calibration texts; ties -> lower threshold',
        'pass':['flat: beats threshold .5 in >=4/5 test seeds','flat: beats even cuts of the same count in >=4/5 test seeds','para: worse than .5 in at most 1/5 seeds']}

def event_cuts(text,th):
    ref={'source_id':'s','sha256':'h','char_start':0,'char_end':len(text),'modality':'text'}
    return [s['source_ref']['char_start'] for s in text_segments(text,ref,E.WIDTH,threshold=th)][1:]

def score(seed,sep,th):
    rng=random.Random(seed*13+5);r={'cand':[],'base':[],'even':[],'random':[]};n=[]
    for t in E.texts(seed,sep):
        c=sorted({E._skip_ws(t['text'],x) for x in event_cuts(t['text'],th)});b=sorted({E._skip_ws(t['text'],x) for x in event_cuts(t['text'],.5)})
        k=len(c);starts=[s for s,_ in _units(t['text'])][1:];k=min(k,len(starts))
        ev=[E._skip_ws(t['text'],starts[round((i+1)*len(starts)/(k+1))-1]) for i in range(k)] if k else []
        rd=[E._skip_ws(t['text'],x) for x in sorted(rng.sample(starts,k))]
        for name,cut in (('cand',c),('base',b),('even',ev),('random',rd)):r[name].append(E.f1(cut,t['gold']))
        n.append(len(c))
    return {k:round(_mean(v),5) for k,v in r.items()}|{'cand_cuts':round(_mean(n),3)}

def run():
    cal={th:_mean([score(s,' ',th)['cand'] for s in CAL]) for th in GRID}
    best=max(GRID,key=lambda th:(round(cal[th],6),-th))
    test={name:{s:score(s,sep,best) for s in TEST} for name,sep in (('flat',' '),('para','\n\n'))}
    f,p=test['flat'],test['para']
    a=sum(f[s]['cand']>f[s]['base'] for s in TEST);b=sum(f[s]['cand']>f[s]['even'] for s in TEST);c=sum(p[s]['cand']<p[s]['base'] for s in TEST)
    means={n:{k:round(_mean([test[n][s][k] for s in TEST]),4) for k in ('cand','base','even','random','cand_cuts')} for n in test}
    return {'prereg':PREREG,'calibration':{str(k):round(v,5) for k,v in cal.items()},'threshold':best,'test':test,'means':means,
            'criteria':{'flat_beats_base':a,'flat_beats_even':b,'para_worse_than_base':c},'verdict':'PASS' if a>=4 and b>=4 and c<=1 else 'FAIL'}

if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='--prereg':
        out=Path(sys.argv[2]);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(PREREG,indent=1));sys.exit(0)
    r=run();out=Path(sys.argv[1]);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(r,indent=1))
    print(r['verdict'],'threshold',r['threshold'],r['criteria'],r['calibration']);print(json.dumps(r['means'],indent=1))
