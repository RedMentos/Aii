import argparse
import json
import os
from pathlib import Path
import sys
import time
import unittest
from .common import APP,dumps,safe_text
from .config import home_path,initialize

def main(argv=None):
    p=argparse.ArgumentParser(description='V13 Age-0 local text runtime');p.add_argument('--home');sub=p.add_subparsers(dest='command')
    chat=sub.add_parser('chat');chat.add_argument('--plain',action='store_true');chat.add_argument('--welcome',action='store_true')
    ask=sub.add_parser('ask');ask.add_argument('text');ask.add_argument('--no-observers',action='store_true')
    doctor=sub.add_parser('doctor');doctor.add_argument('--full',action='store_true');probe_parser=sub.add_parser('probe');probe_parser.add_argument('mode',nargs='?',choices=['native','jef-modes','step12','body-state','sustained'],default='native');probe_parser.add_argument('--cycles',type=int,default=12);sub.add_parser('selftest')
    dl=sub.add_parser('download');dl.add_argument('model',nargs='?',default='all')
    restorep=sub.add_parser('restore');restorep.add_argument('path');restorep.add_argument('--confirm',action='store_true')
    a=p.parse_args(argv);home=home_path(a.home);initialize(home)
    if a.command=='selftest':
        suite=unittest.defaultTestLoader.discover(str(APP/'tests'),pattern='test_*.py');result=unittest.TextTestRunner(verbosity=2).run(suite)
        return 0 if result.testsRun>0 and result.wasSuccessful() else 1
    from .backup import recover_startup,restore
    recover_startup(home)
    if a.command=='restore':
        if not a.confirm:p.error('Restore ersetzt den aktiven Speicher: --confirm erforderlich (automatisches Sicherheitsbackup).')
        print('Wiederhergestellt. Sicherheitsbackup: '+str(restore(home,Path(a.path).expanduser())));return 0
    from .runtime import Runtime
    r=Runtime(home,lambda x:print('[V13] '+safe_text(x),file=sys.stderr,flush=True))
    try:
        if a.command=='doctor':
            from .verification import doctor
            report=doctor(r,a.full);print(json.dumps(report,ensure_ascii=False,indent=2));return 2 if report['data_integrity_errors'] else 0
        if a.command=='download':r.models.install(a.model);return 0
        if a.command=='probe':
            from .verification import probe
            if a.mode=='sustained':
                from .proofs import probe_sustained
                result=probe_sustained(r,a.cycles)
            elif a.mode=='jef-modes':
                from .proofs import probe_jef_modes
                result=probe_jef_modes(r)
            elif a.mode=='body-state':
                from .proofs import probe_body_state
                result=probe_body_state(r)
            elif a.mode=='step12':
                from .proofs import probe_step12
                result=probe_step12(r)
            else:result=probe(r)
            print(json.dumps(result,ensure_ascii=False,indent=2));return 0 if result['status'] in {'SMOKE_PASS','JEF_MODES_PASS','VERTICAL_CHECKS_PASS','BODY_STATE_CHECKS_PASS','BOUNDED_STABILITY_PASS'} else 2
        if a.command=='ask':
            if a.no_observers:r.cfg['observer_mode']='off'
            eid=r.submit(a.text);printed=0;row=None
            while not r.idle():
                row=r.store.one("SELECT * FROM messages WHERE event_id=? AND role='assistant' ORDER BY id DESC LIMIT 1",(eid,))
                if row and len(row['text'])>printed:print(safe_text(row['text'][printed:]),end='',flush=True);printed=len(row['text'])
                time.sleep(.05)
            row=r.store.one("SELECT * FROM messages WHERE event_id=? AND role='assistant' ORDER BY id DESC LIMIT 1",(eid,))
            if row:print(safe_text(row['text'][printed:]),flush=True)
            return 0 if row and row['status']=='FINAL' else 2
        from .ui import chat
        if getattr(a,'welcome',False) and not r.store.history(r.session,1):r.submit(__import__('v13.prompts',fromlist=['text']).text(r.cfg,'welcome'))
        chat(r,getattr(a,'plain',False));return 0
    except KeyboardInterrupt:r.cancel();return 130
    finally:r.close()
if __name__=='__main__':
    try:sys.exit(main())
    except Exception as exc:print('[V13 Fehler] '+safe_text(exc),file=sys.stderr);sys.exit(1)
