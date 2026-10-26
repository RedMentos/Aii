#!/usr/bin/env python3
"""Independent offline review of immutable Run507 Actions raw and safe ZIPs.

Reads only public synthetic benchmark artifacts. Does not execute models.
"""
import hashlib,json,math,zipfile,collections
from pathlib import Path

RAW=Path('/mnt/data/run507-native-raw.zip')
SAFE=Path('/mnt/data/run507-native-safe.zip')
OUT=Path('/mnt/data/run514_review.json')
EXPECTED_RAW='bae7d108bf211eb25b99694e4746f93ed0b240aeaacda3d289b1e1c051dc4227'
EXPECTED_SAFE='406c5e6467c8666e257be73842c3bbf0b5ab53c73d7b46fb7e7cc155beb6677b'
STAGES=('A_s31_p00','A_s31_p01','A_s31_p02')
VARIANTS=('b1_only','b2_only','both_none','both_exact','both_control','same_policy_dual','prompt_only_dual')
FIELDS=('project','action')+tuple(f'{e}.{k}' for e in ('A','B') for k in ('cost','remaining','days','local','eligible'))

def req(v,why):
 if not v:raise AssertionError(why)
def sha(b):return hashlib.sha256(b).hexdigest()
def canonical(o):return json.dumps(o,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode()
def js(z,n):return json.loads(z.read(n),parse_constant=lambda v:(_ for _ in ()).throw(ValueError(v)))
def manifest(z,n):
 lines=z.read(n).decode().splitlines();checked=[]
 for line in lines:
  expected,path=line.split('  ',1);path=path.removeprefix('./')
  req(path in z.namelist(),'manifest missing '+path)
  req(sha(z.read(path))==expected,'manifest hash mismatch '+path)
  checked.append(path)
 req(len(checked)==len(set(checked)),'duplicate manifest path')
 return checked

def equal(a,b):return type(a)==type(b) and a==b

def independent_score(answer,oracle):
 checks={}
 checks['project']=equal(answer.get('project'),oracle['project'])
 checks['action']=equal(answer.get('action'),oracle['action'])
 options=answer.get('options',[])
 by={x.get('entity'):x for x in options if isinstance(x,dict)} if isinstance(options,list) else {}
 req(len(by)<=2,'duplicate/unknown option entries')
 oracle_by={x['entity']:x for x in oracle['options']}
 for e in ('A','B'):
  for key in ('cost','remaining','days','local','eligible'):
   checks[f'{e}.{key}']=equal(by.get(e,{}).get(key),oracle_by[e][key])
 return checks

req(sha(RAW.read_bytes())==EXPECTED_RAW,'raw ZIP drift')
req(sha(SAFE.read_bytes())==EXPECTED_SAFE,'safe ZIP drift')
report={'schema':'V13_RUN514_INDEPENDENT_RUN507_NATIVE42_OFFLINE_AUDIT_V1','date_utc':'2026-10-26',
 'actions_run':40309409260,'actions_head':'28dbc83775ef3c764fffdbeb219fad567dff49c4',
 'raw_artifact_id':12644872590,'safe_artifact_id':12644358345,
 'raw_zip_sha256':EXPECTED_RAW,'safe_zip_sha256':EXPECTED_SAFE,
 'native_origin':'GITHUB_ACTIONS_LINUX_NATIVE_AS_RECORDED_NOT_REEXECUTED',
 'local_model_execution':False,'redmi_measured':False,
 'stage_results':{},'negative_gates':{'step2':'UTILITY_FAIL','b3_l1':'FAIL','body_jepa':'UNAVAILABLE','jepa_weight':0,'canonical_gate_pass':False}}
all_keys=[];per_variant=collections.defaultdict(list);incorrect_commits=[];total_score_rows=0
with zipfile.ZipFile(RAW) as zr,zipfile.ZipFile(SAFE) as zs:
 raw_checked=manifest(zr,'RUN507_SHA256SUMS.txt')
 safe_m=js(zs,'RUN507_SAFE_MANIFEST.json');copied=safe_m['copied']
 req(set(copied)==set(zs.namelist())-{'RUN507_SAFE_MANIFEST.json','RUN507_SAFE_AUDIT.json'},'safe manifest member set')
 for name,meta in copied.items():
  b=zs.read(name)
  req(len(b)==meta['bytes'] and sha(b)==meta['sha256'],'safe manifest drift '+name)
 req(js(zr,'RUN507_SAFE_AUDIT.json')==safe_m,'safe audit/manifest differ')
 plan=js(zr,'RUN507_BATCH_PLAN.json')
 req(plan['stage_ids']==list(STAGES) and plan['expected_rows']==42 and plan['arm']=='A' and plan['seed']==31,'frozen plan drift')
 independent=js(zr,'RUN507_INDEPENDENT_REPORT.json')
 req(independent['stage_ids']==list(STAGES) and independent['rows']==42 and independent['wrong_committed']==0,'original independent report drift')
 for stage in STAGES:
  root=f'stage_{stage}/'
  step=js(zs,root+'step2_A_s31.json')
  tool=js(zs,root+'tool_A_s31.json')
  summary=js(zs,root+'summary_A_s31.json')
  receipt=js(zs,root+'RUN500_STAGE_RESULT.json')
  fixtures={f['id']:f for f in step['fixtures']}
  req(len(fixtures)==2 and len(step['rows'])==14 and len(tool['rows'])==14,'stage row count '+stage)
  req(receipt['rows_verified']==14 and receipt['stage_id']==stage and receipt['native_execution_performed'] is True,'stage receipt '+stage)
  req(receipt['summary_sha256']==sha(zs.read(root+'summary_A_s31.json')) and receipt['tool_sha256']==sha(zs.read(root+'tool_A_s31.json')),'stage file sha '+stage)
  req(independent['stage_hashes'][stage]['summary']==receipt['summary_sha256'] and independent['stage_hashes'][stage]['tool']==receipt['tool_sha256'],'independent stage hashes '+stage)
  req(step['uses_real_weights'] is True and step['phone_measured'] is False,'stage native scope '+stage)
  req(step['installed_artifacts_unchanged'] is True and tool['installed_artifacts_unchanged'] is True,'installed artifacts drift '+stage)
  stage_keys=[];scores=collections.defaultdict(list);all_native_final=True
  for row in tool['rows']:
   key=(row['fixture'],row['variant']);stage_keys.append(key);all_keys.append((stage,*key))
   req(key[0] in fixtures and key[1] in VARIANTS and row['status']=='RECORDED','row key/status '+str(key))
   req(row['oracle_visible_to_native'] is False,'oracle exposed '+str(key))
   req(row['consumer_metrics']['status']=='FINAL','consumer nonfinal '+str(key))
   req(sha(canonical(row))==tool['row_sha256'][key[0]+':'+key[1]],'tool row hash '+str(key))
   answer=json.loads(row['answer'])
   checks=independent_score(answer,fixtures[key[0]]['oracle'])
   stored=row['score'];false_fields=[k for k,v in checks.items() if not v]
   req(checks==stored['field_checks'],'field check mismatch '+str(key))
   req(stored['contradictions']==false_fields and stored['contradiction_count']==len(false_fields),'contradictions mismatch '+str(key))
   req(stored['scored_fields']==12 and stored['exact']==all(checks.values()),'exact mismatch '+str(key))
   req(math.isclose(stored['utility'],sum(checks.values())/12,abs_tol=1e-12),'utility mismatch '+str(key))
   action=answer.get('action')
   if action not in ('UNKNOWN','NONE') and action!=fixtures[key[0]]['oracle']['action']:incorrect_commits.append((stage,*key,action))
   scores[key[1]].append(stored['utility']);per_variant[key[1]].append(stored['utility'])
   total_score_rows+=1
  req(len(set(stage_keys))==14 and set(stage_keys)=={(fid,v) for fid in fixtures for v in VARIANTS},'stage coverage '+stage)
  report['stage_results'][stage]={'fixtures':list(fixtures),'rows':14,'all_consumer_native_metrics_final':all_native_final,
    'mean_utility':{v:sum(scores[v])/len(scores[v]) for v in VARIANTS}}
 req(len(all_keys)==len(set(all_keys))==42,'global row uniqueness')
 report['raw_manifest_verified_entries']=len(raw_checked)
 report['safe_manifest_verified_entries']=len(copied)
 report['stage_count']=len(STAGES)
 report['rows_recomputed_against_oracles']=total_score_rows
 report['wrong_committed_recomputed']=len(incorrect_commits)
 report['mean_utility_42_rows']={v:sum(per_variant[v])/len(per_variant[v]) for v in VARIANTS}
 report['native_artifact_receipt_structurally_consistent']=True
 report['step2_gate_pass']=False
 report['claim_limit']='Independent offline hash/score/source review of preserved Linux-native Actions artifacts. Does not rerun models or establish STEP2/Body-JEPA/B3/Redmi success.'
 req(not incorrect_commits,'wrong committed actions found')
OUT.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
print(json.dumps({'result':'PASS','rows':total_score_rows,'raw_manifest':len(raw_checked),'safe_manifest':len(copied),'wrong_committed':len(incorrect_commits),'mean_utility':report['mean_utility_42_rows']},sort_keys=True))
print('report_sha256',sha(OUT.read_bytes()))