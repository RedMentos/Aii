"""STEP2 + eligibility tool with the isolated B2-offer candidate (scripts/b2_offer_candidate.py).

Loads the patched cognition in this process only, runs the unchanged STEP2 harness on a sibling installed home
whose settings enable the candidate switches (models/bin symlinked to the measured home, so model and runner
hashes are identical), then replays the recorded consumer messages through the eligibility tool.
Preregistration: docs/proofs/continuation-20261013/b2-offer-candidate/PREREG.md.
"""
import argparse
import json
import os
import shutil
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts'),str(ROOT/'tests')]
import b2_offer_candidate as candidate

def sibling_home(installed,dest):
    installed=Path(installed).resolve();dest=Path(dest)
    if dest.exists():raise ValueError('Candidate home exists; use a fresh path')
    (dest/'config').mkdir(parents=True);(dest/'data').mkdir()
    for name in ('models','bin'):os.symlink(installed/name,dest/name,target_is_directory=True)
    for f in (installed/'config').iterdir():
        if f.is_file():shutil.copyfile(f,dest/'config'/f.name)
    s=json.loads((dest/'config/settings.json').read_text());s.update(candidate.ENABLE);(dest/'config/settings.json').write_text(json.dumps(s))
    return dest

def main():
    p=argparse.ArgumentParser();p.add_argument('--installed-home',required=True);p.add_argument('--candidate-home',required=True)
    p.add_argument('--out',required=True);a=p.parse_args()
    binding=candidate.install()
    import integration_step2_utility as step2
    from step2_wire_rebind import diagnose
    from step2_body_state_ablation import body_state_hijack
    from v13.common import atomic_write
    home=sibling_home(a.installed_home,a.candidate_home)
    report=step2.run_locked(home,a.out)
    report['wire_arm']={'arm':'w1','note':'live wire; see producer_arm'};report['producer_arm']={'arm':'b2_offer_candidate','binding':binding}
    report['wire_diagnosis']=diagnose(report);report['body_state_hijack']=body_state_hijack(report)
    atomic_write(Path(a.out),json.dumps(report,ensure_ascii=False,indent=2))
    print(json.dumps({'status':report['status'],'mean_utility':report.get('paired',{}).get('mean_utility'),'hijack':report['body_state_hijack']},indent=1),flush=True)

if __name__=='__main__':main()
