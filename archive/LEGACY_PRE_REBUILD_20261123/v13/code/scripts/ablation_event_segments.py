"""§99-style ablation without a language model for the §102 UNTESTED_LABEL row MODULE_EPISODES (WP-N8 A1 event
segmentation inside one text, §51.2; thread L, 2026-10-12): do event segments cut at real topic changes?

Texts are built from the frozen topic sentences of `bench-results/jepa-ablation-20261010/sentences.json` (16 topics,
written by C3 earlier; read only): 3 different topics x 3-5 consecutive sentences each, joined by a single space
(`flat`: no paragraph cue) or by a blank line between topics (`para`: paragraph cue present). Gold boundary = start of
the first sentence of a new topic. Real, unchanged `episodes.text_segments(text, ref, width)`.

Arms (same texts per seed):
  event        episodes.text_segments, width 240 (default)
  fixed        legacy fixed 240-character chunks (cognition.segments mode 'fixed')
  even         same number of cuts as `event` on this text, evenly spaced over sentence starts (budget matched)
  random       same number of cuts as `event`, random sentence starts (budget matched)
Score: boundary F1 per text (a predicted cut counts if it is exactly a gold boundary after skipping whitespace), averaged over 40 texts per seed.
PREREG (fixed before the first run): primary = mean F1 on `flat` (the harder condition). "helps" only if event beats
every control in >= 4/5 seeds on flat -> SUPPORTED_SYNTHETIC; some -> PARTIAL; none -> NOT_SUPPORTED. `para` reported.
Claim limit: short synthetic topic mixtures from one corpus, lexical signals only, width 240.
"""
import json
import random
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from v13.ablation99 import SEEDS,_mean,_sd
from v13.episodes import text_segments,_units

CORPUS=Path(__file__).resolve().parents[2]/'bench-results/jepa-ablation-20261010/sentences.json'
PREREG={'schema':'ABLATION_EVENT_SEGMENTS_PREREG_V1','seeds':list(SEEDS),'texts_per_seed':40,'topics_per_text':3,'sentences_per_topic':[3,5],
        'width':240,'corpus':'bench-results/jepa-ablation-20261010/sentences.json','primary':'mean boundary F1 on flat texts (exact sentence-start match)',
        'win_rule':'event beats fixed, even and random in >=4/5 seeds on flat -> SUPPORTED_SYNTHETIC; some -> PARTIAL; none -> NOT_SUPPORTED'}
WIDTH=240;N_TEXTS=40;ARMS=('event','fixed','even','random')

def texts(seed,sep):
    rng=random.Random(seed);corpus=json.loads(CORPUS.read_text());topics=sorted(corpus);out=[]
    for _ in range(N_TEXTS):
        parts=[];gold=[];text=''
        for j,tp in enumerate(rng.sample(topics,3)):
            n=rng.randint(3,5);s=corpus[tp];i=rng.randrange(0,len(s)-n+1);chunk=' '.join(x.strip() for x in s[i:i+n])
            if j:text+=sep;gold.append(len(text))
            text+=chunk
        out.append({'text':text,'gold':gold})
    return out

def _skip_ws(text,i):
    """A cut inside the whitespace before a sentence counts at that sentence start (same rule for every arm)."""
    while i<len(text) and text[i].isspace():i+=1
    return i

def f1(pred,gold):
    pred=set(pred);gold=set(gold);tp=len(pred&gold)
    if not pred and not gold:return 1.
    p=tp/len(pred) if pred else 0.;r=tp/len(gold) if gold else 0.
    return 2*p*r/(p+r) if p+r else 0.

def cuts(arm,t,rng,n_event):
    text=t['text'];ref={'source_id':'s','sha256':'h','char_start':0,'char_end':len(text),'modality':'text'}
    if arm=='event':return [s['source_ref']['char_start'] for s in text_segments(text,ref,WIDTH)][1:]
    if arm=='fixed':return list(range(WIDTH,len(text),WIDTH))
    starts=[s for s,_ in _units(text)][1:]
    k=min(n_event,len(starts))
    if arm=='even':return [starts[round((i+1)*len(starts)/(k+1))-1] for i in range(k)] if k else []
    return sorted(rng.sample(starts,k))

def run(seed,sep):
    rng=random.Random(seed*13+5);out={a:[] for a in ARMS};ncuts={a:[] for a in ARMS}
    for t in texts(seed,sep):
        n=len(cuts('event',t,rng,0))
        for a in ARMS:
            c=[_skip_ws(t['text'],x) for x in cuts(a,t,rng,n)];out[a].append(f1(c,t['gold']));ncuts[a].append(len(set(c)))
    return {a:{'primary':round(_mean(out[a]),5),'mean_cuts':round(_mean(ncuts[a]),3)} for a in ARMS}

def run_all(seeds=SEEDS):
    res={}
    for name,sep in (('flat',' '),('para','\n\n')):
        per={s:run(s,sep) for s in seeds}
        wins={a:sum(per[s]['event']['primary']>per[s][a]['primary'] for s in seeds) for a in ARMS if a!='event'}
        res[name]={'per_seed':per,'wins_of_5':wins,'summary':{a:{k:round(_mean([per[s][a][k] for s in seeds]),4) for k in ('primary','mean_cuts')} for a in ARMS}}
    beat=[a for a,n in res['flat']['wins_of_5'].items() if n>=4]
    return {'prereg':PREREG,'conditions':res,'verdict':'SUPPORTED_SYNTHETIC' if len(beat)==3 else ('PARTIAL' if beat else 'NOT_SUPPORTED'),
            'beats_on_flat':beat,'claim_limit':'short synthetic topic mixtures from one corpus, lexical signals only, width 240'}

if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='--prereg':
        out=Path(sys.argv[2]);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(PREREG,indent=1));sys.exit(0)
    r=run_all();out=Path(sys.argv[1]);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(r,indent=1))
    print(r['verdict'])
    for k,v in r['conditions'].items():print(k,v['wins_of_5'],v['summary'])
