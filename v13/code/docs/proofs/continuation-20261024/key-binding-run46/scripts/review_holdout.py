"""Post-hoc independent holdout robustness check; not part of preregistered PASS."""
import json
import torch
import key_binding as R

def review():
    torch.set_num_threads(1);torch.manual_seed(R.SEED)
    rows=R.data_builder()(R.SEED,512,'train')
    m=R.KeyBinding();R.fit(m,rows)
    results=[]
    for seed in (20261026,20261027,20261028):
        test=R.data_builder()(seed,256,'review')
        results.append({'seed':seed,'context':R.acc(m,test),'shuffled':R.acc(m,test,shuffle=True),
                        'uniform':R.acc(m,test,uniform=True)})
    return {'scope':'POSTHOC_INDEPENDENT_SYNTHETIC_HOLDOUT','results':results}
if __name__=='__main__':print(json.dumps(review(),indent=2,sort_keys=True))
