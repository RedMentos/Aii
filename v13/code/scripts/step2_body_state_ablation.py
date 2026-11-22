"""STEP2 producer ablation: B2 offers without the WP-T5 body_state view.

Finding in the STEP2 W1 re-binding (docs/proofs/continuation-20261012/step2-wire-rebind): 41/50 B2 offers
(Qwen3.5-0.8B) summarise only the own body state ("NO_COMPLETED_OWN_DIGITAL_ACTIONS ... no prior knowledge")
although the earlier rule is in their earlier_context in 24/30 retain-prior offers. This arm runs the unchanged
STEP2 harness on the W1 wire with bodyview.body_state returning None for B2_GIST only (runtime replacement in
this wrapper; the live source is unchanged, B1 keeps its body_state). Compare with step2_w1.json (same models,
runner, fixtures, seed). Preregistration: docs/proofs/continuation-20261012/step2-body-state-ablation/PREREG.md.
"""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tests'))
from v13 import bodyview
from v13.common import atomic_write
from scripts.step2_wire_rebind import diagnose

ARM='w1_b2_without_body_state'

def set_arm():
    live=bodyview.body_state
    def without_b2(r,e,role,text):return None if role=='B2_GIST' else live(r,e,role,text)
    bodyview.body_state=without_b2
    return {'arm':ARM,'replaced':'v13.bodyview.body_state for B2_GIST -> None','wire':'WP-W1 runners.wire_json (live)'}

def body_state_hijack(report):
    """Secondary: B2 offers whose content is about the own digital-action state instead of the task."""
    n=h=0
    for r in report['rows']:
        for o in r['offers']:
            if o['role']!='B2_GIST':continue
            n+=1;t=json.dumps(o['offer']).lower();h+=('no_completed_own_digital_actions' in t) or ('digital action' in t)
    return {'b2_offers':n,'about_own_state':h}

def main():
    p=argparse.ArgumentParser();p.add_argument('--installed-home',required=True);p.add_argument('--out',required=True)
    p.add_argument('--fixtures',type=int,choices=range(1,11));p.add_argument('--resume',action='store_true')
    a=p.parse_args();arm=set_arm()
    import integration_step2_utility as step2
    report=step2.run_locked(a.installed_home,a.out,a.fixtures,a.resume)
    report['wire_arm']={'arm':'w1','note':'live wire; see producer_arm'};report['producer_arm']=arm
    report['wire_diagnosis']=diagnose(report);report['body_state_hijack']=body_state_hijack(report)
    atomic_write(Path(a.out),json.dumps(report,ensure_ascii=False,indent=2))
    print(json.dumps({'status':report['status'],'mean_utility':report.get('paired',{}).get('mean_utility'),'hijack':report['body_state_hijack'],'diagnosis':report['wire_diagnosis']},indent=1))

if __name__=='__main__':main()
