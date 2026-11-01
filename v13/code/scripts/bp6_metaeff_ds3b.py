"""WP-BP6/FS3: meta_i on real DS3b captures (C3 alone, pass1). Usage: python scripts/bp6_metaeff_ds3b.py OUTDIR in1.json ..."""
import json,math,os,sys
sys.path.insert(0,os.path.join(os.path.dirname(os.path.abspath(__file__)),'..'))
from v13.agi import metaeff
from v13.agi.generality import calibration
out=sys.argv[1];files=sys.argv[2:]
rows=[r for f in files for r in json.load(open(f))['rows']]
src={'mean_logprob':lambda x:math.exp(x['mean_logprob']),'min_logprob':lambda x:math.exp(x['min_logprob']),
     'p10_logprob':lambda x:math.exp(x['p10_logprob']),'digit_min_logprob':lambda x:math.exp(x['digit_min_logprob']),
     'share_above_half':lambda x:1-x['share_below_half']}
res={'n':len(rows),'correct':sum(bool(r['pass1']['pass']) for r in rows),'sources':{}}
for k,fn in src.items():
    pairs=[(fn(r['pass1']['features']),int(bool(r['pass1']['pass']))) for r in rows]
    res['sources'][k]={'ece':calibration(pairs)['ece'],'meta':metaeff.report(pairs),'abstain':metaeff.abstain_utility(pairs)}
os.makedirs(out,exist_ok=True);json.dump(res,open(os.path.join(out,'report.json'),'w'),indent=1)
for k,v in res['sources'].items():print(k,'ece',round(v['ece'],3),'meta_i',v['meta'].get('meta_i'),'auroc',v['meta'].get('auroc2'),'abst',v['abstain'])
print(res['n'],res['correct'])
