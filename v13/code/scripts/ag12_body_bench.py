"""WP-AG12 step 2: run the generality suite through the real runtime body solvers (agi/solver.py).

  V13_HOME=<installed home> python3 scripts/ag12_body_bench.py --out <dir> [c3 b1 b2 v13]

Uses the same Runtime, RunnerPool (AG13 residency) and LlamaRunner path as the phone, so the
numbers are the first points of the per-generation AG12 curves. Writes <out>/ag12-bodies.json.
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path
APP=Path(__file__).resolve().parents[1];sys.path.insert(0,str(APP))
from v13.runtime import Runtime
from v13.agi import hub
from v13.agi import solver as sv

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);ap.add_argument('solvers',nargs='*',default=['c3','b1','b2','v13'])
    a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    r=Runtime(Path(os.environ['V13_HOME']))
    try:
        g=hub(r);res={'suite_hash':g.eval.suite['hash'],'items':len(g.eval.suite['items']),'generation':r.store.generation_id,'solvers':{}}
        for name in a.solvers:
            t=time.monotonic();out=sv.run(g,r,name,label='cloud-bench')
            run=json.loads((r.home/'exports/generality-last.json').read_text()) if out['status']!='NO_SOLVER' else None
            res['solvers'][name]=out|{'seconds':round(time.monotonic()-t,1),'summary':run and run['summary'],
                                      'models':{ro:r.models.revision(ro) for ro in out.get('roles',[])}}
            print(name,out['status'],'overall',out.get('overall'),'unseen',out.get('unseen'),'ece',out.get('ece'),flush=True)
        res['metacog']=g.metacog.report()['components']
        (a.out/'ag12-bodies.json').write_text(json.dumps(res,indent=1))
    finally:r.close()

if __name__=='__main__':main()
