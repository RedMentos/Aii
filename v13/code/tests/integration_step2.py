"""Real-weight STEP2 ablations of existing routes/channels, with incremental proof writes.

No inference mocks, prompt tuning, training, live chat edits or automatic gate promotion.
Run from source: python tests/integration_step2.py --installed-home ~/v13 --out proof.json
"""
import argparse
import json
from pathlib import Path
import re
import shutil
import sys
import tempfile
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from v13.common import APP,atomic_write,dumps,file_hash
from v13.config import initialize,save_config
from v13.proofs import audit_event,archive_previous
from v13.resources import device
from v13.runtime import Runtime

# WP-V9: English fixtures first; the German ones remain as the German transfer test.
FIXTURES=[
    {'id':'aurora_budget_en','lang':'en','text':'Compare the options for Project Aurora. Budget: 120 euros. Option Red costs 80 euros and takes 2 days. Option Blue costs 110 euros and takes 1 day. Constraint: local only, no cloud. State the remaining budget for each option and briefly summarise the trade-off.','expected_numbers':[40,10],'assertions':{'red_rest':r'(?is)(?:red.{0,50}40|40.{0,50}red)','blue_rest':r'(?is)(?:blue.{0,50}10|10.{0,50}blue)'}},
    {'id':'borealis_deadline_en','lang':'en','text':'Compare two plans for Project Borealis. Budget: 70 euros. Plan A costs 45 euros and takes 4 days. Plan B costs 65 euros and takes 8 days. Hard constraints: finished after 6 days at the latest; local only, no cloud. State the remaining budget for both plans and decide which plan meets the deadline.','expected_numbers':[25,5],'assertions':{'plan_a_rest':r'(?is)(?:plan\s*a.{0,50}25|25.{0,50}plan\s*a)','plan_b_rest':r'(?is)(?:plan\s*b.{0,50}5|5.{0,50}plan\s*b)','deadline_a':r'(?is)(?:plan\s*a.{0,80}(?:deadline|6\s*days?).{0,80}(?:meet|within|fits)|(?:deadline|6\s*days?).{0,80}plan\s*a)','deadline_b_rejected':r'(?is)(?:plan\s*b.{0,80}(?:not|miss|exceed).{0,80}(?:deadline|6\s*days?)|(?:deadline|6\s*days?).{0,80}(?:not|miss|exceed).{0,80}plan\s*b)'}},
    {'id':'aurora_budget','text':'Vergleiche die Optionen für Projekt Aurora. Budget: 120 Euro. Option Rot kostet 80 Euro und benötigt 2 Tage. Option Blau kostet 110 Euro und benötigt 1 Tag. Vorgabe: nur lokal, keine Cloud. Nenne die Budgetreste und fasse den Zielkonflikt knapp zusammen.','expected_numbers':[40,10],'assertions':{'rot_rest':r'(?is)(?:rot.{0,50}40|40.{0,50}rot)','blau_rest':r'(?is)(?:blau.{0,50}10|10.{0,50}blau)'}},
    {'id':'borealis_deadline','text':'Vergleiche zwei Pläne für Projekt Borealis. Budget: 70 Euro. Plan A kostet 45 Euro und dauert 4 Tage. Plan B kostet 65 Euro und dauert 8 Tage. Harte Vorgaben: Fertigstellung spätestens nach 6 Tagen; nur lokal, keine Cloud. Nenne für beide Pläne den Budgetrest und entscheide, welcher Plan die Frist einhält.','expected_numbers':[25,5],'assertions':{'plan_a_rest':r'(?is)(?:plan\s*a.{0,50}25|25.{0,50}plan\s*a)','plan_b_rest':r'(?is)(?:plan\s*b.{0,50}5|5.{0,50}plan\s*b)','deadline_a':r'(?is)(?:plan\s*a.{0,80}(?:frist|6\s*tag).{0,80}(?:ein|erfüll|hält)|(?:frist|6\s*tag).{0,80}plan\s*a)','deadline_b_rejected':r'(?is)(?:plan\s*b.{0,80}(?:nicht|verfehl|überschreit).{0,80}(?:frist|6\s*tag)|(?:frist|6\s*tag).{0,80}(?:nicht|verfehl|überschreit).{0,80}plan\s*b)'}},
]
VARIANTS=[
    ('b1_only','detail','NO_MESSAGE',{'B1_DETAIL'}),
    ('b2_only','gist','NO_MESSAGE',{'B2_GIST'}),
    ('both_none','both','NO_MESSAGE',{'B1_DETAIL','B2_GIST'}),
    ('both_exact','both','SOURCE_EXACT',{'B1_DETAIL','B2_GIST'}),
    ('both_control','both','CONTROL',{'B1_DETAIL','B2_GIST'}),
]

def run(installed,out,cycles=1,b2_control='two_body',languages=('en','de')):
    installed=Path(installed).resolve();out=Path(out).resolve();out.parent.mkdir(parents=True,exist_ok=True);archive_previous(out)
    cfg=initialize(installed)|{'b2_control':b2_control};fixtures=[f for f in FIXTURES if f.get('lang','de') in languages]
    report={'proof_kind':'STEP2_EXISTING_PATH_ABLATIONS','proof_version':1,'status':'RUNNING','device':device(),'phone_measured':device()['android'],'uses_real_weights':True,'cycles':cycles,'b2_control':b2_control,'fixtures':fixtures,'rows':[],
            'full_runner_proof':False,'complementarity_proven':False,'source_hashes':{str(p.relative_to(APP)):file_hash(p) for p in list((APP/'v13').glob('*.py'))+[Path(__file__).resolve()]},
            'method':'Fresh isolated brain and cold processes for every fixture/variant; same settings, seed, source and deadlines. B1-only/detail and B2-only/gist include their existing answer-role difference. Reentry remains at its configured limit.',
            'claim_limits':['Two small fixtures are diagnostic, not a quality benchmark.','Number presence is lexical coverage only; it does not validate assignment, reasoning or contradictions.','No winner or complementary-utility gate is inferred from these scores.','Peak RSS is sampled native-process RSS, not a total-device or sustained-memory ceiling.','Temperature/energy and target-phone long-run retention remain open.']}
    def save():atomic_write(out,json.dumps(report,ensure_ascii=False,indent=2))
    save()
    try:
        for cycle in range(cycles):
            for fixture in fixtures:
                for variant,route,channel,expected_roles in VARIANTS:
                    row={'cycle':cycle,'fixture':fixture['id'],'variant':variant};runtime=None
                    print(dumps({'starting':row}),flush=True)
                    with tempfile.TemporaryDirectory(prefix='v13-step2-') as tmp:
                        try:
                            home=Path(tmp);initialize(home);settings=cfg|{'learning_mode':'RECORD_ONLY','teacher_enabled':False,'observer_mode':'background','route_override':route,'channel':channel,'history_turns':0};save_config(home,settings)
                            for name in ['models','bin']:shutil.rmtree(home/name);(home/name).symlink_to(installed/name,target_is_directory=True)
                            shutil.copyfile(installed/'config/models.json',home/'config/models.json');runtime=Runtime(home);row['model_revisions']=runtime.revisions();before=runtime.store.generation_id
                            eid=runtime.submit(fixture['text']);end=time.monotonic()+settings['deadline_seconds']+2*settings['observer_seconds']+15
                            while not runtime.idle():
                                if time.monotonic()>end:runtime.cancel();raise TimeoutError('Integration wait budget')
                                time.sleep(.05)
                            row['audit']=audit_event(runtime.store,eid);roles={p['role'] for p in row['audit']['offers']}
                            row['checks']={'vertical':all(row['audit']['checks'].values()),'expected_roles':roles==expected_roles,'no_weight_update':before==runtime.store.generation_id,'integrity':not runtime.store.integrity(True)}
                            texts=[row['audit']['output'] or ''];offer_texts=[dumps(o['offer']) for o in row['audit']['offers']]
                            def coverage(parts):return {str(n):any(re.search(r'(?<![\d.,])'+str(n)+r'(?!\d)',text) is not None for text in parts) for n in fixture['expected_numbers']}
                            row['lexical_number_coverage']={'final':coverage(texts),'offer_union':coverage(offer_texts),'semantic_score':None};row['task_assertions']={name:re.search(pattern,texts[0]) is not None for name,pattern in fixture.get('assertions',{}).items()}
                            metrics=[o['native_metrics'] for o in row['audit']['offers']]+[row['audit']['output_metadata'].get('runner',{})]
                            row['measurements']={'turn_s':row['audit']['output_metadata']['duration_s'],'sampled_native_peak_rss_bytes':max((m['sampled_peak_rss_bytes'] for m in metrics if m.get('sampled_peak_rss_bytes') is not None),default=None),'body_state_versions':{role:runtime.store.state(role+':'+runtime.session)[1] for role in ['B1_DETAIL','B2_GIST']}}
                            row['status']='CHECKS_PASS' if all(row['checks'].values()) else 'CHECKS_PARTIAL'
                        except Exception as exc:row.update(status='INTERRUPTED',error_type=type(exc).__name__,error=str(exc)[:400])
                        finally:
                            if runtime:
                                runtime.close();row['process_releases']=list(runtime.pool.release_history)
                                if 'checks' in row:
                                    row['checks']['processes_reaped']=bool(row['process_releases']) and all(x['process_reaped'] for x in row['process_releases'])
                                    if not row['checks']['processes_reaped']:row['status']='CHECKS_PARTIAL'
                            report['rows'].append(row);save()
                    print(dumps({'finished':variant,'fixture':fixture['id'],'status':row['status']}),flush=True)
        report['all_structural_checks_passed']=all(row['status']=='CHECKS_PASS' for row in report['rows'])
        report['status']='ABLATIONS_RECORDED' if report['all_structural_checks_passed'] else 'ABLATIONS_PARTIAL'
    except BaseException as exc:
        report.update(status='INTERRUPTED',error_type=type(exc).__name__);raise
    finally:save()
    return report

def main():
    p=argparse.ArgumentParser();p.add_argument('--installed-home',required=True);p.add_argument('--out',required=True);p.add_argument('--cycles',type=int,choices=range(1,5),default=1);a=p.parse_args();report=run(a.installed_home,a.out,a.cycles)
    print(dumps({'status':report['status'],'rows':len(report['rows']),'artifact':str(Path(a.out).resolve()),'complementarity_proven':False}),flush=True)
    return 0 if report['status']=='ABLATIONS_RECORDED' else 2
if __name__=='__main__':sys.exit(main())
