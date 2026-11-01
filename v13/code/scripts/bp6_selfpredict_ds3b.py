"""WP-BP6/FS4: self-prediction "would the calculator change whether I am right?" on real DS3b captures, leave-one-seed-out.
Usage: python scripts/bp6_selfpredict_ds3b.py OUTDIR in1.json ..."""
import json,os,sys
sys.path.insert(0,os.path.join(os.path.dirname(os.path.abspath(__file__)),'..'))
from v13.agi import selfpredict,selfpredictor as sp
out=sys.argv[1];rows=[]
for f in sys.argv[2:]:
    for r in json.load(open(f))['rows']:
        if r['pass3']:r['seed']=f;rows.append(r)
y=(lambda r:int((not r['pass1']['pass']) and r['pass3']['pass'])) if os.environ.get('FS4_TARGET')=='help' else (lambda r:int(r['pass1']['pass']!=r['pass3']['pass']))
models={}
for s in {r['seed'] for r in rows}:
    tr=[r for r in rows if r['seed']!=s]
    models[s]=(sp.fit([sp.state_feats(r['pass1']['features']) for r in tr],[y(r) for r in tr]),
               sp.fit([sp.input_feats(r['text'],r['nums']) for r in tr],[y(r) for r in tr]))
ids={id(r):r for r in rows}
res=selfpredict.run(rows,answer_fn=lambda r:(int(r['_orig']['pass3']['pass']) or int(r['_orig']['pass1']['pass']) if os.environ.get('FS4_TARGET')=='help' else int(r['_orig']['pass3']['pass'])) if '_orig' in r else int(r['pass1']['pass']),
  perturb_fn=lambda r:{'_orig':r},predict_fn=lambda r,p:sp.predict(models[r['seed']][0],sp.state_feats(r['pass1']['features'])),
  input_only_fn=lambda r,p:sp.predict(models[r['seed']][1],sp.input_feats(r['text'],r['nums'])))
os.makedirs(out,exist_ok=True);json.dump(res,open(os.path.join(out,'selfpredict-'+os.environ.get('FS4_TARGET','change')+'.json'),'w'),indent=1)
print({k:v for k,v in res.items() if k not in('self','input_only')});print(res['self']['perm_p'] if 'perm_p' in res['self'] else res['self'])
