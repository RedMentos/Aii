import json
from pathlib import Path
import shlex
import shutil
from .common import dumps,atomic_write,safe_text,file_hash
from .config import KNOBS,save_config
from .models import ROLES
HELP='''Text eingeben → echte lokale Modellantwort. ::Text sendet ein führendes : als Chattext.
:help / :status / :doctor [full] / :ledger / :schemas / :resources / :models / :brain / :logs [runner]
:chats / :new / :open <Chat-ID> / :search <Text> / :export chat [json|md]
:self / :world / :components / :objectives / :plasticity [component] / :capability
:cancel / :force-report / :executive / :task [set Text|clear] / :pause / :resume / :shutdown
:feedback fact|style|preference <Korrektur> [--learn]
:feedback route simple|detail|gist|both [--learn]
:feedback wake none|detail|gist|both [--learn] / :feedback halt halt|continue [--learn]
:feedback prediction observe --learn (beobachtete native Zustände dieser Quelle)
:feedback alignment observe --learn (A3 Raw/Encoder-Paar, keine Faktenfreigabe)
:feedback world observe --learn (abgeschlossenes eigenes Action-Outcome)
:feedback retrieval <Memory-ID> relevant|irrelevant [--learn]
:remember <Thema> | <Korrektur> / :memory / :forget <Memory-ID> --confirm
:experience [Event-ID] / :choose self|teacher [Start:Ende] [--kind fact|style|preference] [--learn]
:export dataset [session|all]
:replay [Anzahl] / :replay status
:consolidate semantic|procedural / :consolidate status / :consolidate rollback <ID>
:route auto|simple|detail|gist|both / :observers background|off
:channel NO_MESSAGE|SOURCE_EXACT|CONTROL|SYMBOLIC
:tap B1_DETAIL|B2_GIST [Start:Ende] (max. 64 native Tokens, read-only)
:feedback output <gewünschter Referenztext> [--learn] (erster nativer Token)
:budget [Name Wert] / :learning record|shadow|commit / :learn [route|wake|halt|b1_predictor|b2_predictor|a3_student|world_predictor|control_calibration|memory_retrieval|output_adapter]
:requests / :approve <ID> / :reject <ID> / :rollback <Update-ID>
:rules [add <Regel>|remove <Index>] / :permissions / :age / :stage cap 0..5
:teacher on|off|compare / :teacher use B1_DETAIL|B2_GIST|C3_LANGUAGE
:dream / :probe [jef-modes|step12|body-state|sustained]
:download all|needle|language|body / :import model <Rolle> <Pfad>
:export model <Rolle> <Ziel> / :unload [Rolle] / :gc / :clear-logs
:backup / :restore <Pfad> (zeigt Offline-Befehl)
''' 
class Operator:
    def __init__(self,r):self.r=r
    def run(self,line,origin='OPERATOR_TTY'):
        if origin!='OPERATOR_TTY':raise ValueError('Nur lokale Operator-Eingaben dürfen Befehle ausführen')
        if line.startswith('::'):return self.r.submit(line[1:])
        if not line.startswith(':'):return self.r.submit(line)
        parts=shlex.split(line[1:]);cmd=parts[0].lower() if parts else 'help';args=parts[1:];r=self.r;s=r.store
        if cmd=='help':return HELP
        if cmd=='plasticity':
            if len(args)>1:raise ValueError(':plasticity [component]')
            return dumps(r.learner.plasticity.report(args[0] if args else None))
        if cmd=='shutdown':r.stop.set();r.cancel_event.set();return 'Beenden…'
        if cmd=='force-report':
            if args:raise ValueError(':force-report ohne Argumente')
            return r.force_report()
        if cmd=='executive':return dumps(r.executive.view(r.session))
        if cmd=='task':
            if not args:return dumps(r.executive.task(r.session))
            r.require_idle()
            if args==['clear']:return dumps(r.executive.task(r.session,clear=True))
            if len(args)>1 and args[0]=='set':return dumps(r.executive.task(r.session,' '.join(args[1:])))
            raise ValueError(':task [set Text|clear]')
        if cmd=='cancel':r.cancel();return 'Abbruch läuft'
        if cmd=='pause':r.pause();return 'Pausiert'
        if cmd=='resume':r.resume();return 'Fortgesetzt'
        if cmd=='status':return dumps({'session':r.session,'job':r.current,'queued':s.queue_stats()['count'],'paused':r.paused,'generation':s.generation_id,'learning':r.cfg['learning_mode'],'age':0})
        if cmd=='resources':return dumps(r.resources())
        if cmd=='brain':return dumps(s.generation())
        if cmd=='models':return dumps(r.models.installed)
        if cmd=='self':return dumps(r.world.self_state())
        if cmd=='world':return dumps(r.world.world_state())
        if cmd in {'components','objectives'}:
            from .verification import component_registry,objective_registry
            return dumps(component_registry() if cmd=='components' else objective_registry(r))
        if cmd=='doctor':
            from .verification import doctor
            return dumps(doctor(r,'full' in args))
        if cmd in {'ledger','schemas'}:
            from .verification import completion_ledger,schema_registry,write_build_artifacts
            write_build_artifacts(r)
            return dumps(completion_ledger(r) if cmd=='ledger' else schema_registry())
        if cmd=='logs':
            if args==['runner']:return '\n'.join(p.name+'\n'+safe_text(p.read_text(errors='replace')[-4000:]) for p in (r.home/'logs').glob('*.log'))
            return dumps(s.rows('SELECT * FROM telemetry ORDER BY id DESC LIMIT 20'))
        if cmd=='chats':return dumps(s.rows('SELECT * FROM sessions ORDER BY created DESC'))
        if cmd=='search':return dumps(s.rows("SELECT session_id,event_id,role,text FROM messages WHERE text LIKE ? ORDER BY id DESC LIMIT 30",('%'+' '.join(args)+'%',)))
        if cmd=='memory':return dumps(s.rows('SELECT id,kind,scope,key_text,value FROM memories WHERE active=1 AND (session_id=? OR scope=?)',(r.session,'global')))
        if cmd=='experience':
            last=r.last_answer();eid=args[0] if len(args)==1 else (last['event_id'] if not args and last else None)
            if not eid:raise ValueError(':experience [Event-ID]; erst eine Antwort erzeugen')
            return dumps(r.memory.experience(eid,r.session))
        if cmd=='replay' and args==['status']:return dumps(s.rows('SELECT * FROM replay ORDER BY created DESC LIMIT 30'))
        if cmd=='feedback':
            if len(args)<2:raise ValueError(':feedback fact|style|preference|route Text [--learn]')
            last=r.last_answer()
            if not last:raise ValueError('Erst eine Antwort abwarten')
            learn='--learn' in args;value=' '.join(x for x in args[1:] if x!='--learn')
            if r.current=='shadow':raise ValueError('Shadow-Training zuerst beenden')
            if args[0]=='output':return r.learner.output_feedback(last['event_id'],value,'learn' if learn else 'record')
            if args[0]=='retrieval':
                values=[x for x in args[1:] if x!='--learn']
                if len(values)!=2:raise ValueError(':feedback retrieval <Memory-ID> relevant|irrelevant [--learn]')
                return r.memory.retrieval_feedback(last['event_id'],values[0],values[1],'learn' if learn else 'record')
            return r.memory.feedback(last['event_id'],args[0],value,'learn' if learn else 'record')
        if cmd=='remember':
            last=r.last_answer()
            if not last or '|' not in ' '.join(args):raise ValueError(':remember Thema | Korrektur; erst eine Antwort erzeugen')
            key,value=' '.join(args).split('|',1);return r.memory.feedback(last['event_id'],'fact',value.strip(),key=key.strip())
        if cmd=='requests':return dumps({'requests':s.rows('SELECT * FROM requests ORDER BY created DESC LIMIT 20'),'updates':s.rows('SELECT * FROM updates ORDER BY created DESC LIMIT 20')})
        if cmd=='permissions':return dumps({'operator_command_origin':'TTY only','network':'explicit model setup/download only','model_tool_execution':False,'filesystem_tools_for_models':False,'weight_commit':'validated artifact + individual operator approval','latent_injection':False,'natural_language_rules':'prompt guidance, no deterministic semantic guarantee'})
        if cmd=='age':return dumps({'system_stage':0,'user_stage_cap':r.cfg['user_stage_cap'],'auto_promotion':False})
        if cmd=='budget' and not args:return dumps({k:{'value':r.cfg[k],'unit':v[1],'range':[v[2],v[3]],'status':'BOOT_ESTIMATE'} for k,v in KNOBS.items()})
        if cmd=='rules' and not args:return dumps(s.rules())
        if cmd=='export' and args and args[0]=='chat':
            fmt=args[1] if len(args)>1 else 'json'
            if fmt not in {'json','md'}:raise ValueError('json|md')
            history=s.history(r.session,100000);p=r.home/'exports'/(r.session+'.'+fmt)
            text=dumps(history) if fmt=='json' else '\n\n'.join('**'+x['role']+' · '+x['status']+'**\n\n'+x['text'] for x in history)
            atomic_write(p,text);return str(p)
        # Every mutation affecting routing/generation/files below is serialized at idle.
        r.require_idle()
        if cmd=='consolidate':
            if not args or args==['status']:return dumps(r.consolidation.report(r.session))
            if len(args)==1 and args[0] in {'semantic','procedural'}:return dumps(r.consolidation.stage(r.session,args[0]))
            if len(args)==2 and args[0]=='rollback':return r.consolidation.rollback(args[1])
            raise ValueError(':consolidate semantic|procedural|status / :consolidate rollback <ID>')
        if cmd=='tap':
            if len(args) not in (1,2) or args[0] not in {'B1_DETAIL','B2_GIST'}:raise ValueError(':tap B1_DETAIL|B2_GIST [Start:Ende]')
            last=r.last_answer()
            if not last:raise ValueError('Erst eine Eingabe/Antwort erzeugen')
            e=json.loads(s.one('SELECT packet FROM events WHERE id=?',(last['event_id'],))['packet']);ref=e['source_ref']
            if len(args)==2:
                span=args[1].split(':')
                if len(span)!=2:raise ValueError('Start:Ende, Zeichen, Ende exklusiv')
                start,end=map(int,span)
                if not 0<=start<end<=ref['char_end']:raise ValueError('Ungültiger Source-Span')
                ref=ref|{'char_start':start,'char_end':end}
            r.enqueue('tap',(e,args[0],ref));return 'Native Body-Beobachtung gestartet; Artefakt wird quellengebunden gespeichert.'
        if cmd=='export' and args and args[0]=='dataset':
            if len(args)>2 or (len(args)==2 and args[1] not in {'session','all'}):raise ValueError(':export dataset [session|all]')
            return dumps(r.memory.export_dataset(None if args==['dataset','all'] else r.session))
        if cmd=='choose':
            import argparse
            parser=argparse.ArgumentParser(prog=':choose',exit_on_error=False,add_help=False)
            parser.add_argument('lane',choices=['self','teacher']);parser.add_argument('span',nargs='?');parser.add_argument('--kind',choices=['fact','style','preference'],default='fact');parser.add_argument('--learn',action='store_true')
            try:a=parser.parse_args(args)
            except (argparse.ArgumentError,SystemExit):raise ValueError(':choose self|teacher [Start:Ende] [--kind fact|style|preference] [--learn]')
            start=end=None
            if a.span:
                spans=a.span.split(':')
                if len(spans)!=2:raise ValueError('Span: Start:Ende, Ende exklusiv')
                start,end=map(int,spans)
            last=r.last_answer()
            if not last:raise ValueError('Erst eine eigene Antwort erzeugen')
            return r.memory.select(last['event_id'],r.session,a.lane,start,end,a.kind,'learn' if a.learn else 'record')
        if cmd=='replay':
            if len(args)>1:raise ValueError(':replay [Anzahl]')
            count=int(args[0]) if args else r.cfg['replay_batch']
            if not 1<=count<=16:raise ValueError('Replay-Anzahl 1..16')
            r.enqueue('replay',count);return 'Episodic Replay gestartet; Ergebnisse bleiben in der Replay-Lane.'
        if cmd=='new':r.session=s.new_session();return r.session
        if cmd=='open':
            if len(args)!=1 or not s.one('SELECT id FROM sessions WHERE id=?',(args[0],)):raise ValueError('Chat-ID unbekannt')
            r.session=args[0];s.set_meta('last_session',r.session);r.world.recover();return r.session
        if cmd in {'route','observers','channel','learning'}:
            key={'route':'route_override','observers':'observer_mode','channel':'channel','learning':'learning_mode'}[cmd]
            if len(args)!=1:raise ValueError('Ein Wert erforderlich')
            value={'record':'RECORD_ONLY','shadow':'SHADOW_UPDATE','commit':'APPROVED_COMMIT'}.get(args[0],args[0]) if cmd=='learning' else args[0]
            cfg=r.cfg|{key:value};save_config(r.home,cfg);r.cfg.update(cfg);return key+' = '+value
        if cmd=='budget':
            if len(args)!=2 or args[0] not in KNOBS:raise ValueError(':budget Name Wert; :budget listet Bereiche')
            if args[0] in {'queue_count','queue_bytes'}:raise ValueError('Queue-Größe nur offline in config/settings.json ändern und neu starten')
            value=int(args[1]) if isinstance(KNOBS[args[0]][0],int) else float(args[1]);cfg=r.cfg|{args[0]:value};save_config(r.home,cfg);r.cfg.update(cfg);r.pool.unload()
            if args[0]=='log_retention_days':s.log_retention_days=value;s.prune_telemetry()
            return args[0]+' = '+str(value)
        if cmd=='stage' and len(args)==2 and args[0]=='cap':
            cfg=r.cfg|{'user_stage_cap':int(args[1])};save_config(r.home,cfg);r.cfg.update(cfg);return 'Obergrenze gespeichert; System bleibt Age 0.'
        if cmd=='capability':
            from .verification import native_capability_profile
            return dumps(native_capability_profile(r))
        if cmd=='learn':
            if len(args)>1 or (args and args[0] not in {'route','wake','halt','b1_predictor','b2_predictor','a3_student','world_predictor','control_calibration','memory_retrieval','output_adapter'}):raise ValueError(':learn [route|wake|halt|b1_predictor|b2_predictor|a3_student|world_predictor|control_calibration|memory_retrieval|output_adapter]')
            r.enqueue('shadow',args[0] if args else 'route');return 'Isoliertes Training gestartet; keine automatische Aktivierung.'
        if cmd=='approve':
            if len(args)!=1:raise ValueError('Konkrete Request-/Update-ID erforderlich')
            if s.one("SELECT id FROM requests WHERE id=? AND kind='RULES'",(args[0],)):return s.approve_rule(args[0],r.cfg,r.revisions())
            if s.one("SELECT id FROM requests WHERE id=? AND kind='CONSOLIDATION'",(args[0],)):return r.consolidation.approve(args[0])
            if r.cfg['learning_mode']!='APPROVED_COMMIT':raise ValueError(':learning commit erforderlich; anschließend konkrete Update-ID freigeben')
            return s.switch_generation(args[0],r.cfg,r.revisions())
        if cmd=='reject':
            if len(args)!=1:raise ValueError('ID fehlt')
            with s.tx() as c:
                n=c.execute("UPDATE requests SET status='REJECTED' WHERE id=? AND status='PENDING'",(args[0],)).rowcount
                n+=c.execute("UPDATE updates SET status='REJECTED' WHERE id=? AND status='PENDING_APPROVAL'",(args[0],)).rowcount
                if not n:raise ValueError('Keine offene ID')
            return 'Abgelehnt'
        if cmd=='rollback':
            if len(args)!=1:raise ValueError('Update-ID fehlt')
            return s.rollback(args[0])
        if cmd=='rules':
            before=s.rules();after=list(before)
            if args and args[0]=='add' and len(args)>1:after.append(' '.join(args[1:]))
            elif len(args)==2 and args[0]=='remove':after.pop(int(args[1]))
            else:raise ValueError(':rules add Text | remove Index (ab 0)')
            return s.request('RULES',{'base_rule':s.generation()['rule_version'],'before':before,'after':after})+'; :requests zeigt Diff, :approve ID übernimmt ihn'
        if cmd=='forget':
            if len(args)!=2 or args[1]!='--confirm':raise ValueError(':memory zeigt Quelle; :forget Memory-ID --confirm löscht sie ausdrücklich')
            return r.memory.forget(args[0])
        if cmd=='forget-source':
            if len(args)!=2 or args[1]!='--confirm':raise ValueError(':forget-source HUMAN_OUTPUT_REFERENCE-Source-ID --confirm')
            return r.memory.forget_output_reference(args[0])
        if cmd=='teacher':
            if len(args)==2 and args[0]=='use':
                r.pool.unload();r.models.use_reference(args[1]);return 'Separater frozen Teacher nutzt '+args[1]+'. Kein stärkeres Modell behauptet. :teacher on; danach :teacher compare.'
            if args==['compare']:r.enqueue('teacher');return 'Referenzvergleich nach eigener Antwort gestartet'
            if len(args)!=1 or args[0] not in {'on','off'}:raise ValueError('on|off|compare')
            cfg=r.cfg|{'teacher_enabled':args[0]=='on'};save_config(r.home,cfg);r.cfg.update(cfg);return 'Teacher '+args[0]
        if cmd in {'dream','probe'}:
            if args and (cmd!='probe' or args not in [['jef-modes'],['step12'],['body-state'],['sustained']]):raise ValueError(':probe [jef-modes|step12|body-state|sustained] oder :dream ohne Argumente')
            r.enqueue(cmd,args[0] if args else None);return cmd+' gestartet'
        if cmd=='download':r.enqueue('download',args[0] if args else 'all');return 'Download gestartet; Fortschritt wird angezeigt'
        if cmd=='import' and len(args)==3 and args[0]=='model':
            r.pool.unload();return r.models.import_model(args[1],args[2])+'; B1/B2 nutzen dasselbe unveränderliche Body-Gewicht, aber getrennte Zustände'
        if cmd=='export' and len(args)==3 and args[0]=='model':
            src=r.models.path_for(args[1]);dst=Path(args[2]).expanduser()
            if dst.exists():raise ValueError('Ziel existiert bereits')
            if shutil.disk_usage(dst.parent).free<src.stat().st_size:raise ValueError('Zu wenig Speicher')
            shutil.copyfile(src,dst)
            if file_hash(src)!=file_hash(dst):dst.unlink();raise ValueError('Export-Hash falsch')
            return str(dst)
        if cmd in {'unload','gc'}:
            if args and args[0]=='C2_CONTROL':r.needle.unload()
            elif args:
                if args[0] not in ROLES:raise ValueError('Unbekannte Rolle')
                if r.pool.current and r.pool.current.role==args[0]:r.pool.unload()
            else:r.pool.unload();r.needle.unload()
            return 'Native Prozesse entladen; gespeicherte Zustände bleiben erhalten'
        if cmd=='clear-logs':
            r.pool.unload();r.needle.unload()
            for p in (r.home/'logs').glob('*.log'):p.unlink()
            with s.tx() as c:c.execute('DELETE FROM telemetry')
            return 'Diagnoselogs geleert; Chat/Gedächtnis erhalten'
        if cmd=='backup':
            from .backup import backup
            return str(backup(s))
        if cmd=='restore' and len(args)==1:return 'V13 beenden, dann offline ausführen: v13 restore '+shlex.quote(str(Path(args[0]).expanduser()))+' --confirm. Erst wird automatisch ein Sicherheitsbackup erstellt.'
        raise ValueError('Unbekannter/unvollständiger Befehl. :help')
