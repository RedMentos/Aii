"""STEP2 + eligibility tool: B2 quotes as pointers to exact source sentences (cfg offer_quote_context_chars).

Two arms on sibling installed homes (models/bin symlinked to the measured home, so model and runner hashes are
identical), both with the B2-offer switches of thread O (b2_offer_body_state=False, offer_quote_min_chars=90):
  control   offer_quote_context_chars=0    exact-substring verification (live behaviour)
  context   offer_quote_context_chars=200  a case/whitespace-tolerant quote widens to its whole exact source
                                           sentences, up to 200 chars of the same source
Each arm runs the unchanged STEP2 harness (70 rows), then the recorded consumer messages are replayed through the
eligibility tool (scripts/step2_tool_replay.py). Preregistration: docs/proofs/continuation-20261020/step2-quote-context/PREREG.md.
Diagnosis only (Linux cloud, no Redmi); the STEP2 canonical gate is never promoted by this script.
"""
import argparse
import json
import os
import re
import shutil
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts'),str(ROOT/'tests')]

ARMS={'control':{'b2_offer_body_state':False,'offer_quote_min_chars':90,'offer_quote_context_chars':0},
      'context':{'b2_offer_body_state':False,'offer_quote_min_chars':90,'offer_quote_context_chars':200}}
B2_VARIANTS=('b2_only','both_none','both_exact','both_control','prompt_only_dual')

def sibling_home(installed,dest,enable):
    installed=Path(installed).resolve();dest=Path(dest)
    if dest.exists():raise ValueError('Arm home exists; use a fresh path')
    (dest/'config').mkdir(parents=True);(dest/'data').mkdir()
    for name in ('models','bin'):os.symlink(installed/name,dest/name,target_is_directory=True)
    for f in (installed/'config').iterdir():
        if f.is_file():shutil.copyfile(f,dest/'config'/f.name)
    s=json.loads((dest/'config/settings.json').read_text());s.update(enable);(dest/'config/settings.json').write_text(json.dumps(s))
    return dest

def rule_parts(prior):
    """Exact earlier-rule strings C3 needs in a retain episode (budget, deadline, local-only)."""
    budget=re.search(r'Budget (\d+ euros|has not been provided)\.',prior).group(0)
    return [budget,re.search(r'Deadline \d+ days\.',prior).group(0),re.search(r'Local-only requirement: (true|false)\.',prior).group(0)]

def transport(report):
    """Per verified analyst quote set reaching C3: does it carry the whole earlier rule? Counted from consumer messages."""
    fixtures={f['id']:f for f in report['fixtures']};out={}
    for mode in ('RETAIN_PRIOR_RULES','CURRENT_EXPLICIT_OVERRIDE'):
        for role in ('B2_GIST','B1_DETAIL'):
            full=partial=n=0
            for row in report['rows']:
                f=fixtures[row['fixture']]
                if f['temporal_mode']!=mode or not row.get('consumer_messages'):continue
                user=json.loads(next(m['content'] for m in row['consumer_messages'] if m['role']=='user'))
                for a in user.get('analysts',[]):
                    if a['role']!=role:continue
                    n+=1;text=' '.join(a['verified_quotes']);hits=[p in text for p in rule_parts(f['prior'])]
                    full+=all(hits);partial+=any(hits) and not all(hits)
            out[mode+':'+role]={'offers':n,'full_rule':full,'partial_rule':partial}
    return out

def run_arm(installed,work,arm):
    import integration_step2_utility as step2
    from step2_wire_rebind import diagnose
    from step2_body_state_ablation import body_state_hijack
    import step2_tool_replay as replay
    from v13.common import atomic_write
    work=Path(work);home=sibling_home(installed,work/(arm+'-home'),ARMS[arm]);out=work/('step2_'+arm+'.json')
    report=step2.run_locked(home,out)
    report['wire_arm']={'arm':'w1','note':'live wire; see producer_arm'};report['producer_arm']={'arm':'quote_context_'+arm,'enable':ARMS[arm]}
    report['wire_diagnosis']=diagnose(report);report['body_state_hijack']=body_state_hijack(report);report['rule_transport']=transport(report)
    atomic_write(out,json.dumps(report,ensure_ascii=False,indent=2))
    tool=replay.run(home,out,work/('tool_'+arm+'.json'))
    fixtures={f['id']:f for f in report['fixtures']};import calc_tool_ablation as w2
    retain=[x for x in tool['rows'] if fixtures[x['fixture']]['temporal_mode']=='RETAIN_PRIOR_RULES' and x['variant'] in B2_VARIANTS]
    summary={'arm':arm,'step2_status':report['status'],'paired':report['paired'],'rule_transport':report['rule_transport'],'tool_status':tool['status'],
             'tool_wrong_committed':sum(v['wrong_committed'] for v in tool['summary']['tool'].values()),
             'tool_retain_b2_exact':sum(w2.decision_exact(x['score']) for x in retain),'tool_retain_b2_rows':len(retain),
             'tool_summary':tool['summary']['tool'],'no_tool_summary':tool['summary']['no_tool_w1'],'hijack':report['body_state_hijack']}
    atomic_write(work/('summary_'+arm+'.json'),json.dumps(summary,ensure_ascii=False,indent=2))
    return summary

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--installed-home',required=True);p.add_argument('--work',required=True)
    p.add_argument('--arm',choices=sorted(ARMS),action='append',required=True);a=p.parse_args()
    for arm in a.arm:
        s=run_arm(a.installed_home,a.work,arm)
        print(json.dumps({k:s[k] for k in ('arm','step2_status','tool_status','tool_wrong_committed','tool_retain_b2_exact','tool_retain_b2_rows','rule_transport')},indent=1),flush=True)

if __name__=='__main__':main()
