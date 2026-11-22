"""Opt-in native readout proof. All labels/approvals are explicit test fixtures.

No user brain, no synthetic embedding, no fabricated body offer. Reports are
written after every collected trajectory and phase, including failed gates.
"""
import argparse
import json
from pathlib import Path
import shutil
import sys
import tempfile
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from v13.common import APP,atomic_write,dumps,file_hash
from v13.runtime import Runtime
from v13.config import initialize
from v13.cognition import scaffold_route
from v13.operator import Operator
from v13.resources import device

WAKE={
 'none':['Guten Morgen, wie geht es dir?','Guten Abend, wie geht es dir?','Guten Tag, wie geht es dir?','Gute Nacht, wie geht es dir?','Hallo, wie geht es dir heute?','Hi, wie geht es dir gerade?'],
 'detail':['Berechne die Hälfte von '+str(v)+' Euro.' for v in (60,90,150,210,270,330)],
 'gist':['Gib eine Zusammenfassung: '+s for s in ('Pflanzen brauchen Wasser.','Bäume brauchen Licht.','Blumen brauchen Pflege.','Gras braucht Feuchtigkeit.','Sträucher benötigen Regen.','Kräuter benötigen Sonne.')],
 'both':['Vergleiche die Vor- und Nachteile von '+s+'.' for s in ('Solarenergie und Windenergie','Bus und Bahn','Python und Java','Stadt und Land','Fahrrad und Auto','Holz und Stahl')]}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--installed-home',required=True);parser.add_argument('--out',required=True);parser.add_argument('--wake-only',action='store_true');a=parser.parse_args()
    installed=Path(a.installed_home).resolve();out=Path(a.out).resolve();out.parent.mkdir(parents=True,exist_ok=True)
    report={'status':'RUNNING','device':device(),'scope':'bounded observer wake and two-frozen-offer re-entry; not full executive JEPA',
            'label_authority':'explicit fixture annotations and test approvals, never user-derived automatic permission',
            'source_hashes':{str(p.relative_to(APP)):file_hash(p) for p in (APP/'v13').glob('*.py')},'checks':{},'corpus':[],'updates':[]}
    def save():atomic_write(out,json.dumps(report,ensure_ascii=False,indent=2))
    def mark(name,passed):report['checks'][name]=bool(passed);save()
    save()
    with tempfile.TemporaryDirectory(prefix='v13-readout-') as folder:
        h=Path(folder);initialize(h)
        for name in ('models','bin'):shutil.rmtree(h/name);(h/name).symlink_to(installed/name,target_is_directory=True)
        shutil.copyfile(installed/'config/models.json',h/'config/models.json');r=Runtime(h)
        try:
            r.cfg.update(learning_mode='SHADOW_UPDATE',deadline_seconds=240,observer_seconds=55,observer_tokens=96,answer_tokens=32,history_turns=0)
            config=dict(r.cfg)
            for label,texts in WAKE.items():
                for text in texts:
                    e=r.store.event(r.session,text);baseline=scaffold_route(text);baseline='none' if baseline=='simple' else baseline
                    p=r.learner.decide('wake',e,baseline,time.monotonic()+20)
                    r.memory.feedback(e['event_id'],'wake',label,'learn');r.memory.feedback(e['event_id'],'route','simple' if label=='none' else label,'learn')
                    report['corpus'].append({'kind':'wake','input':text,'label':label,'decision':p});save()
            # Keep the original route head active while adding independent components.
            before=r.store.generation_id;r.learner.shadow();route=r.store.one('SELECT * FROM updates ORDER BY created DESC LIMIT 1')
            report['updates'].append({'kind':'route','status':route['status'],'manifest':json.loads(route['manifest'])});save()
            if route['status']!='PENDING_APPROVAL':raise RuntimeError('Route gate blocked; see metrics')
            r.cfg['learning_mode']='APPROVED_COMMIT';Operator(r).run(':approve '+route['id']);route_hash=file_hash(r.learner.active())
            base=r.store.generation_id;r.learner.shadow_readout('wake');wake=r.store.one('SELECT * FROM updates ORDER BY created DESC LIMIT 1')
            report['updates'].append({'kind':'wake','status':wake['status'],'manifest':json.loads(wake['manifest'])});mark('wake_shadow_no_commit',r.store.generation_id==base)
            if wake['status']!='PENDING_APPROVAL':raise RuntimeError('Wake gate blocked; see metrics')
            Operator(r).run(':approve '+wake['id']);mark('route_preserved_by_wake',file_hash(r.learner.active())==route_hash)
            session=r.session;r.close();r=Runtime(h);r.cfg.update(config);r.cfg['learning_mode']='APPROVED_COMMIT'
            mark('restart_components',r.session==session and set(r.store.components())=={'route','wake'})
            decisions=[]
            for expected,texts in WAKE.items():
                e=r.store.event(r.session,texts[-1]);p=r.learner.decide('wake',e,'both',time.monotonic()+20)
                decisions.append(p);mark('wake_'+expected,p['learned'] and p['action']==expected)
            report['wake_after_restart']=decisions;save()
            e=r.store.event(r.session,WAKE['none'][-1]);r._turn(e);answer=r.last_answer();meta=json.loads(answer['metadata'])
            report['native_none_turn']={'status':answer['status'],'output':answer['text'],'metadata':meta}
            mark('wake_consumed_by_runtime_no_body_wake',answer['status']=='FINAL' and meta['wake_decision']['learned'] and meta['wake_decision']['action']=='none' and not r.store.rows("SELECT id FROM packets WHERE kind='OfferPacket' AND event_id=?",(e['event_id'],)))
            if not a.wake_only:
                # A fixed two-offer native trajectory is collected before fitting exit weights.
                for label in ('halt','continue'):
                    for value in (60,90,150,210,270,330):
                        text=('Vergleiche die Angaben: A nennt '+str(value)+' Euro, B nennt ebenfalls '+str(value)+' Euro. Beide Angaben stimmen exakt überein; es gibt keine offene Frage.' if label=='halt' else
                              'Vergleiche die Angaben: A nennt '+str(value)+' Euro, B nennt '+str(value+40)+' Euro. Die Angaben widersprechen sich; Datum und gültige Quelle fehlen. Prüfe den ungelösten Konflikt genauer.')
                        r.session=r.store.new_session('Fixed trajectory fixture');e=r.store.event(r.session,text);r._turn(e);answer=r.last_answer();meta=json.loads(answer['metadata'])
                        if answer['status']!='FINAL' or 'halt_decision' not in meta:raise RuntimeError('Actual two-offer runtime trajectory unavailable')
                        p=meta['halt_decision'];body_rows=r.store.rows("SELECT payload FROM packets WHERE kind='OfferPacket' AND event_id=? ORDER BY created",(e['event_id'],));actual=[json.loads(x['payload']) for x in body_rows]
                        r.memory.feedback(e['event_id'],'halt',label,'learn');report['corpus'].append({'kind':'halt','input':text,'label':label,'decision':p,'actual_offers':actual,'output':answer['text'],'duration_s':meta['duration_s']});save()
                        print('native halt trajectory',label,value,flush=True)
                base=r.store.generation_id;r.learner.shadow_readout('halt');halt=r.store.one('SELECT * FROM updates ORDER BY created DESC LIMIT 1')
                report['updates'].append({'kind':'halt','status':halt['status'],'manifest':json.loads(halt['manifest'])});mark('halt_shadow_no_commit',r.store.generation_id==base)
                if halt['status']!='PENDING_APPROVAL':raise RuntimeError('Halt gate blocked; see actual trajectory/evaluation metrics')
                Operator(r).run(':approve '+halt['id']);mark('all_components_coexist',set(r.store.components())=={'route','wake','halt'} and file_hash(r.learner.active())==route_hash)
                r.close();r=Runtime(h);r.cfg.update(config);r.cfg['learning_mode']='APPROVED_COMMIT'
                report['halt_runtime_rows']=[]
                for label in ('halt','continue'):
                    sample=[x for x in report['corpus'] if x['kind']=='halt' and x['label']==label][-1]
                    # Recreate real offers under the committed generation; no packet relabeling.
                    r.session=r.store.new_session('Native post-learning reentry');e=r.store.event(r.session,sample['input']);r._turn(e);answer=r.last_answer();meta=json.loads(answer['metadata'])
                    offers=r.store.rows("SELECT payload FROM packets WHERE kind='OfferPacket' AND event_id=? ORDER BY created",(e['event_id'],))
                    row={'expected':label,'status':answer['status'],'output':answer['text'],'offer_count':len(offers),'metadata':meta};report['halt_runtime_rows'].append(row);save()
                    decision=meta.get('halt_decision',{})
                    mark('halt_runtime_'+label,answer['status']=='FINAL' and decision.get('learned') and decision.get('action')==label and len(offers)==(2 if label=='halt' else 3))
                Operator(r).run(':rollback '+halt['id']);mark('halt_rollback_preserves_wake_route',set(r.store.components())=={'route','wake'})
            Operator(r).run(':rollback '+wake['id']);mark('wake_rollback_preserves_route',set(r.store.components())=={'route'} and file_hash(r.learner.active())==route_hash)
            Operator(r).run(':rollback '+route['id']);mark('route_final_rollback',not r.store.generation()['hashes']);mark('integrity',not r.store.integrity(True))
            report['status']='READOUT_LIFECYCLE_PASS' if all(report['checks'].values()) else 'READOUT_LIFECYCLE_PARTIAL'
        except Exception as exc:
            report.update(status='READOUT_LIFECYCLE_PARTIAL',error=type(exc).__name__+': '+str(exc));report['worker_logs']=[p.read_text()[-3000:] for p in (h/'shadow').glob('*/worker.log')]
        finally:r.close();save()
    print(dumps({'status':report['status'],'checks':report['checks'],'error':report.get('error')}));return 0 if report['status']=='READOUT_LIFECYCLE_PASS' else 2

if __name__=='__main__':sys.exit(main())
