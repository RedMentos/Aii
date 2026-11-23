#!/usr/bin/env python3
"""Paired real-weight C3 benchmark; never changes the installed model manifest.

The baseline is the installed C3_LANGUAGE model. An optional candidate GGUF is run
through the same pinned llama-server/config. Results are diagnostic only: this
script does not promote a model or alter routing.
"""
import argparse, json, sys, tempfile, threading, time
from pathlib import Path

APP=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(APP))
from v13.bootstrap import initialize
from v13.common import atomic_write,dumps,file_hash
from v13.models import ModelManager,download_file
from v13.proofs import archive_previous
from v13.runners import LlamaRunner
from v13.resources import device

# WP-V9: English first; the German rows stay as the later German transfer test.
FIXTURES=[
 {'id':'en_greeting','lang':'en','system':'Answer briefly and naturally in English.','user':'Say hello briefly. What could I ask you first?','must_any':['Hello','Hi']},
 {'id':'en_rewrite','lang':'en','system':'Only rephrase the given content briefly in English. Invent nothing.','user':'Rephrase briefly: The test runs locally and uses no cloud.','must_all':['local'],'forbid':['online']},
 {'id':'en_grounded_report','lang':'en','system':'Answer only from the given sentence. Briefly, in English.','user':'Source: Project Aurora has a budget of 120 euros. Question: How large is the budget?','must_all':['120']},
 {'id':'en_abstain','lang':'en','system':'If the answer is not in the text, say briefly that it is not supported. Invent nothing.','user':'Source: Project Aurora has a budget of 120 euros. Question: Who leads Project Aurora?','must_any':['not','unknown','no ']},
 {'id':'de_greeting','lang':'de','system':'Antworte kurz und natürlich auf Deutsch.','user':'Sag kurz Hallo auf Deutsch. Was kann ich dich als Erstes fragen?','must_any':['Hallo','Hi']},
 {'id':'de_rewrite','lang':'de','system':'Formuliere nur den gegebenen Inhalt kurz auf Deutsch um. Erfinde nichts.','user':'Formuliere kurz um: Der Test läuft lokal und verwendet keine Cloud.','must_all':['lokal'],'forbid':['online']},
 {'id':'de_grounded_report','lang':'de','system':'Antworte ausschließlich aus dem gegebenen Satz. Kurz auf Deutsch.','user':'Quelle: Projekt Aurora hat ein Budget von 120 Euro. Frage: Wie hoch ist das Budget?','must_all':['120']},
 {'id':'de_abstain','lang':'de','system':'Wenn die Antwort nicht im Text steht, sage kurz, dass es nicht belegt ist. Erfinde nichts.','user':'Quelle: Projekt Aurora hat ein Budget von 120 Euro. Frage: Wer leitet Projekt Aurora?','must_any':['nicht','unbekannt','keine']},
]

def lexical_checks(text,fx):
    low=text.casefold();checks={}
    if fx.get('must_all'): checks['must_all']=all(x.casefold() in low for x in fx['must_all'])
    if fx.get('must_any'): checks['must_any']=any(x.casefold() in low for x in fx['must_any'])
    if fx.get('forbid'): checks['forbid']=not any(x.casefold() in low for x in fx['forbid'])
    return checks

def run_model(home,model,role,cfg,progress=None):
    runner=LlamaRunner(home,role,model,cfg);rows=[]
    try:
        for fx in FIXTURES:
            deadline=time.monotonic()+cfg['deadline_seconds'];out=''
            started=time.monotonic()
            try:
                
                for token in runner.generate([{'role':'system','content':fx['system']},{'role':'user','content':fx['user']}],threading.Event(),deadline,96,seed=13):out+=token
                status='FINAL'
            except Exception as exc:
                status=type(exc).__name__;out=out or ''
            checks=lexical_checks(out,fx)
            rows.append({'fixture_id':fx['id'],'status':status,'output':out,'checks':checks,'checks_pass':bool(checks) and all(checks.values()),'elapsed_s':time.monotonic()-started,'metrics':runner.last_metrics})
            if progress:progress(rows)
    finally:unload=runner.unload()
    return rows,unload

def summarize(rows):
    good=[r for r in rows if r['status']=='FINAL'];return {'final':len(good),'fixtures':len(rows),'lexical_pass':sum(r['checks_pass'] for r in rows),'median_duration_s':sorted([r['elapsed_s'] for r in good])[len(good)//2] if good else None,'peak_pss_bytes':max([r.get('metrics',{}).get('sampled_peak_pss_bytes') or 0 for r in rows] or [0]) or None}

def main():
    p=argparse.ArgumentParser();p.add_argument('--installed-home',required=True);p.add_argument('--candidate-gguf');p.add_argument('--download-candidate',action='store_true');p.add_argument('--candidate-name',default='SmolLM2-135M-Instruct');p.add_argument('--out',required=True);a=p.parse_args()
    installed=Path(a.installed_home).resolve();out=Path(a.out).resolve();out.parent.mkdir(parents=True,exist_ok=True);archive_previous(out)
    candidate_spec=None
    if a.download_candidate:
        if a.candidate_gguf:p.error('Use either --candidate-gguf or --download-candidate')
        candidate_spec=json.loads((APP/'specs/c3-benchmark.json').read_text())
        a.candidate_gguf=str(download_file(candidate_spec,installed/'benchmarks'/candidate_spec['local_name']))
    mm=ModelManager(installed);baseline=mm.path_for('C3_LANGUAGE')
    cfg=initialize(installed);cfg=dict(cfg);cfg.update(context_tokens=min(cfg['context_tokens'],2048),answer_tokens=96,history_turns=0,threads=min(cfg['threads'],4),deadline_seconds=max(30,min(cfg['deadline_seconds'],90)))
    report={'proof_kind':'C3_PAIRED_BASELINE_COMPARISON','proof_version':1,'created_wall_time':time.time(),'device':device(),'phone_measured':device()['android'],'diagnostic_only':True,'promotes_model':False,'fixtures':FIXTURES,'baseline':{'name':'installed:C3_LANGUAGE','path':str(baseline),'sha256':file_hash(baseline)},'candidate':None,'runs':{},'claim_limits':['Lexical checks are smoke criteria, not general language-quality scores.','No model-selection claim without paired target-phone runs and human/validated quality scoring.','Candidate is never installed or promoted by this script.']}
    report.update(status='RUNNING',effective_config=cfg,model_revisions={'baseline':mm.revision('C3_LANGUAGE')},candidate_spec=candidate_spec)
    def save_rows(name,rows):
        report['runs'][name]={'rows':list(rows),'summary':summarize(rows)};atomic_write(out,dumps(report))
    rows,unload=run_model(installed,baseline,'C3_BENCH_BASELINE',cfg,lambda rows:save_rows('baseline',rows));report['runs']['baseline']={'rows':rows,'summary':summarize(rows),'unload':unload}
    if a.candidate_gguf:
        candidate=Path(a.candidate_gguf).expanduser().resolve()
        if not candidate.is_file():raise SystemExit('candidate GGUF not found')
        with open(candidate,'rb') as f:
            if f.read(4)!=b'GGUF':raise SystemExit('candidate is not GGUF')
        report['candidate']={'name':a.candidate_name,'path':str(candidate),'sha256':file_hash(candidate),'size':candidate.stat().st_size}
        rows,unload=run_model(installed,candidate,'C3_BENCH_CANDIDATE',cfg,lambda rows:save_rows('candidate',rows));report['runs']['candidate']={'rows':rows,'summary':summarize(rows),'unload':unload}
        report['paired_complete']=True
    else:report['paired_complete']=False;report['missing']='candidate GGUF; baseline still measured if installed'
    report['status']='PAIRED_NATIVE_COMPLETE' if report['paired_complete'] and all(x['status']=='FINAL' and x['output'].strip() for run in report['runs'].values() for x in run['rows']) else 'COMPARISON_PARTIAL'
    atomic_write(out,dumps(report));print(json.dumps({'artifact':str(out),'paired_complete':report['paired_complete'],'summaries':{k:v['summary'] for k,v in report['runs'].items()}},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
