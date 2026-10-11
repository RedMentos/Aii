"""WP-G G1B: boundary-aware vs fixed gist grouping on a fixed text set (model-free).

Metrics per mode: groups, boundary rate (groups ending at a sentence/clause end), mean/CV of group size in
token-equivalents, exact spans (numbers, dates, code, URLs) split across two groups, and lossless coverage
(every non-space character lies in exactly one slot). Usage: python3 scripts/gist_grouping_bench.py [out.json]
"""
import json
import statistics
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from v13 import gist as G
from v13.context_os import exact_spans

TEXTS={
 'en_plan':'We move on 2026-11-02. The van is booked for 8:00, and Tom brings boxes. Before that, cancel the internet contract (number 55-1209) and forward the mail. After the move, register at the town hall within two weeks; bring the passport and the rental agreement.',
 'de_alltag':'Morgen um 9 Uhr ist der Zahnarzttermin. Danach muss ich zur Bank, weil die Karte am 31.10. abläuft. Am Nachmittag kommt Lisa vorbei, wir wollen den Garten winterfest machen: Rosen schneiden, Laub sammeln und die Pumpe ausbauen.',
 'code':'To fix it, change `max_tokens` in config.json from 128 to 256, then run `python3 -m v13 doctor`. If the error persists, def check(x): return x>0 must be called before load().',
 'long_story':' '.join(['The committee met again on day %d and discussed the budget, the schedule and the risks; nobody agreed on the final number, so they postponed the vote.'%i for i in range(1,9)]),
 'list':'Shopping: milk, eggs, bread, butter, cheese, apples, pears, rice, pasta, tomatoes, onions, garlic, coffee, tea, sugar, salt, pepper, oil, vinegar, flour.',
}

def measure(text,mode,size=8,slots=12):
    ref={'source_id':'bench','sha256':'0'*64,'char_start':0,'char_end':len(text),'modality':'text'}
    raw=G.group(text,ref,size,mode);p=G.plan(text,ref,{'tokens_per_group':size,'slots':slots},mode)
    sizes=[g['units'] for g in raw];cuts={g['source_ref']['char_end'] for g in raw[:-1]}
    split=sum(any(text.find(s)<c<text.find(s)+len(s) for c in cuts) for s in exact_spans(text) if text.find(s)>=0)
    cover=[0]*len(text)
    for s in p['slots']:
        for i in range(s['source_ref']['char_start'],s['source_ref']['char_end']):cover[i]+=1
    lossless=all(cover[i]==1 for i,ch in enumerate(text) if not ch.isspace())
    return {'groups':len(raw),'slots':len(p['slots']),'coarsened':p['coarsened'],'boundary_rate':round(sum(g['boundary']>=.7 for g in raw)/len(raw),3),
            'mean_units':round(statistics.mean(sizes),2),'cv_units':round(statistics.pstdev(sizes)/statistics.mean(sizes),3),'exact_spans_split':split,'lossless':lossless}

def main(out=None):
    rep={'kind':'G1B_GIST_GROUPING_BENCH','size':8,'slots':12,'texts':{}}
    for name,t in TEXTS.items():rep['texts'][name]={m:measure(t,m) for m in ('boundary','fixed')}
    for m in ('boundary','fixed'):
        rows=[v[m] for v in rep['texts'].values()]
        rep[m]={'boundary_rate':round(statistics.mean(r['boundary_rate'] for r in rows),3),'exact_spans_split':sum(r['exact_spans_split'] for r in rows),
                'cv_units':round(statistics.mean(r['cv_units'] for r in rows),3),'all_lossless':all(r['lossless'] for r in rows)}
    rep['claim_limit']='Structural readout metrics only; whether B2 answers improve needs the model bench (WP-N12)'
    s=json.dumps(rep,indent=1,ensure_ascii=False)
    if out:Path(out).parent.mkdir(parents=True,exist_ok=True);Path(out).write_text(s)
    print(json.dumps({m:rep[m] for m in ('boundary','fixed')}))
    return rep

if __name__=='__main__':main(sys.argv[1] if len(sys.argv)>1 else None)
