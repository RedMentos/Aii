import json
from pathlib import Path
import shlex
import shutil
from .common import dumps,safe_text,file_hash
from .config import KNOBS,save_config
from .models import ROLES
from . import age as agectl
def obsched_names():
    from .observer_schedule import SCHEDULES
    return SCHEDULES
HELP='''Text eingeben → echte lokale Modellantwort. ::Text sendet ein führendes : als Chattext.
:befehle [Wort] (alle Befehle mit Erklärung) / :help / :status / :doctor [full] / :ledger / :schemas / :resources [modes|calibrate|reset|bodies [import <json>|reset]] / :models / :brain / :logs [runner]
:chats / :new / :open <Chat-ID> / :search <Text> / :export chat [json|md]
:self / :world / :native / :knobs / :components / :objectives / :plasticity [component]
:cancel / :force-report / :executive / :task [set Text|clear] / :pause / :resume / :shutdown
:notaus [aus|status] (stoppt sofort jedes Werkzeug und jede Freigabe) / :stillstand [aus|status] (hält alles an: Werkzeuge, Aufgaben, Lernen, Hintergrund, Alterung) / :organ [list|status <Rolle>|snapshot <Rolle>|check <ID>|restore <ID>] (Sicherung je Modell-Organ) / :verbot [liste|werkzeug <Name>|art <Risiko>|unumkehrbar|alles|weg <V-Nr>|ansage an|aus] (feste Verbote, kein Modell entscheidet)
:pause selfedit|traum|training|budget N / :resume <Klasse> / :note 1-10 [Text] / :ratings / :context
:feedback fact|style|preference <Korrektur> [--learn]
:feedback route simple|detail|gist|both [--learn]
:feedback wake none|detail|gist|both [--learn] / :feedback halt halt|continue [--learn]
:feedback skill none|skill / memory skip|recall|deep / channel NO_MESSAGE|SOURCE_EXACT|CONTROL|SYMBOLIC [--learn] (WP-T1 Fast-Köpfe)
:fastpolicy [status|focus on|off|measure|outcomes [record|learn]|lifecycle [Event-ID]] (JEF_FAST_POLICY-Köpfe, Re-entry-Frage, Ergebnis-Labels, Lebenszyklus L0–L11)
:aplane [status|student shadow|fallback|distill [Fähigkeit]] (A3-Schüler T2, Lehrer-Destillation, Reliance-Kurve)
:bodyview [status|state on|off|b4 off|shadow|on] (B1-Detailfenster, B5-Zustand als Quelle, B4 über Sessions)
:skilllive [status] (Skills im Turn: automatischer Pfad, Parität, Gewohnheiten)
:latewatch [status|off|shadow|active] (spätes Body-Offer während der Ausgabe; Standard shadow)
:feedback prediction observe --learn (beobachtete native Zustände dieser Quelle)
:feedback alignment observe --learn (A3 Raw/Encoder-Paar, keine Faktenfreigabe)
:feedback world observe --learn (abgeschlossenes eigenes Action-Outcome)
:feedback retrieval <Memory-ID> relevant|irrelevant [--learn]
:remember <Thema> | <Korrektur> / :memory / :forget <Memory-ID> --confirm
:experience [Event-ID] / :choose self|teacher [Start:Ende] [--kind fact|style|preference] [--learn]
:export dataset [session|all]
:replay [Anzahl] / :replay status
:consolidate semantic|procedural / :consolidate status / :consolidate rollback <ID>
:route auto|simple|detail|gist|both / :observers background|off|A_THEN_B_SEQUENTIAL|B_THEN_A_SEQUENTIAL|ALWAYS_BOTH_ASYNC|JEF_FIRST_THEN_BOTH|SAMPLED_OBSERVER|ON_DEMAND_REENTRY
:decode [server|same_causal_zero|same_causal] / :sampling [anti_echo|legacy] / :semantic [status|off|shadow|on|auto] / :episodes [status|list|cut|graph <id>|relation <a> <b>|forgetting] / :live / :register [summary|drift|paths|declared|<Präfix>] / :gates [summary|all|<Gate>] / :drift [status|probes|freeze <Set>|refreeze <Set> <Grund>|sdft] / :admission [status|train|active|shadow|table] / :duplex [status|auto|interrupt|off] / :fabric [report|record] / :image [status|add <Pfad>|list|describe [id] [g|rIJ|hl|hr|ht|hb]|train|look [id]|locate <id> <Text>|forget <id>] / :collapse [all]
:effort [disabled|low|adaptive|high|max] (Reasoning-Effort/Body-Wake; ohne Wert: Status)
:focal (JEF-Fokusschleife: Workspace-Slots, letzte Runden, Inquisition P1/P2, C5-Auswahl)
:import causal-output <dataset.json> <offline-trained-directory>
:channel NO_MESSAGE|SOURCE_EXACT|CONTROL|SYMBOLIC
:tap B1_DETAIL|B2_GIST [Start:Ende] (max. 64 native Tokens, read-only)
:feedback output <gewünschter Referenztext> [--learn] (erster nativer Token)
:budget [Name Wert] / :learning [status|record|shadow|commit] / :learn [route|wake|halt|b1_predictor|b2_predictor|a3_student|world_predictor|control_calibration|memory_retrieval|output_adapter]
:requests / :approve <ID> / :reject <ID> / :rollback <Update-ID>
:rules [add <Regel>|remove <Index> [weitere Indizes]] / :permissions / :age [freeze on|off|lower <n>|structural lock|unlock] / :stage cap 0..5
:rules fixed "exakte Frage" "exakte Antwort" (Diff, dann :approve ID; kein semantischer Abgleich)
:teacher on|off|compare / :teacher use B1_DETAIL|B2_GIST|C3_LANGUAGE
:dream / :probe [jef-modes|step12|body-state|sustained]
:sleep [status|digest|run full|a|b|c|wake|in <Minuten> [Modus]|policy [Name Wert]] / :scheduler (Replay/Sleep A-B-C, WP-S7 Tagesdigest + Offline-Rechenzeit, Event-Scheduler)
:growth [status|eval [run c3|b1|b2|v13 | curve <Solver> <Achse>]|teacher [status|cloud on|off|ask <Frage>|run [local|claude]|dataset]|trainer [auto|lora|sparse|none [Master-Ordner] | cfg k=v.. | cfg reset]|goals|goal <Titel>|goal status|done|abandon|reopen <ID>|subgoals <USER-ID> Kindziel 1 | Kindziel 2|consolidate|approve <Batch>|reject <Batch>|tools|enable <Werkzeug>|calc <Ausdruck>] (WP-AG1..AG12)
:neuromod [status|path <Name>|sleep|clear-veto <Name>] (WP-N10 Eligibility, Modulator-Bus, Plastizitäts-Gate)
:authority [status|review|promote <Kopf>|demote <Kopf>|<Kopf>] / :objectives (WP-T10 Beförderung gelernter Köpfe Schatten → Kandidat → aktiv, IH-H25 Lernziele)
:workspace [status|shadow|active] (WP-U8 Workspace lernt Haltedauer je Quellenart; aktiv nur durch Nutzer)
:anchor [status|shadow|active] (WP-U5 Anker-Stärke beim Gewichts-Training nach Neuheit/Stabilität; aktiv nur durch Nutzer)
:archive [status|run|restore <Quelle>] (WP-U4 kalte Quellen verlustfrei komprimiert)
:homeostasis [status|run|shadow|active] (WP-U2 Homöostase: Drift-/Sättigungs-Gate + langsame Pfad-Gains; aktiv nur durch Nutzer)
:attention [status|edge <Kante>|shadow|active] (WP-N5 Aufmerksamkeit, thalamische Gain, A4)
:ctxos [status|last|shadow|active|layout <L>|knob <N> <W>|capability <Rolle> on|off|probe <Rolle>|outcome <Event> <W>] (WP-N7 Context OS, Cache-Policy)
:callosum [status|shadow|active|degrade|promote <Richtung>] (WP-J B3-Kanal-Policy, signed_gain; WP-N19 B3-H10-Degradation) / :gist [status|shadow|active|preview <Text>|readout [fixed|text|native|hybrid]] (WP-G G1B Gist-Gruppen ~8 Token/~12 Slots; readout = nativer B2-Tap-Konsument, SHADOW) / :body [status|bridges|swap <Rolle> <gguf>|parity <Rolle> <alt.json> <neu.json>|ramp <Rolle>|rollback <Rolle>] (WP-T13 BodyPort, Bridge-Key, Body-Swap online) / :tx [status|provisional|broker|cancel <atx>|approve <Aufruf>|undo <Aufruf>] (WP-K Aktions-Transaktion, Werkzeug-Freigabe mit Vorschau, WP-T7 Output-Broker) / :toolforecast [status|shadow|off|score] (Werkzeug-Folgen-Prädiktor vor der Wirkung, SHADOW, Runden 7/8) / :delib [status|shadow|active] (WP-N2 gelernte Deliberation, Halt-Gate) / :c5 [status|shadow|active] (WP-N4 gelernte Aktionsauswahl, C6-Egress) / :ff [status|shadow|active] (WP-F Fast-Forward/Kleinhirn, Prozeduralisierung) / :reflex [status|close <Rolle>] (WP-F Reflexe)
:regeln (deine Regeln + was ich ohne Nachfrage tun würde) / :regel <Text> (Verbot oder „frag vorher“ speichern) / :regel aus|verbot|fragen|nein <Nr>
:jef [status|last|shadow|active|query|outcome <Event> <0..1>] (WP-N3 JEF-Broadcast-Cache, Offer-Nutzen, Top-down-Query)
:self [status|model|body|messages|arithmetic|world status|start|poll|stop|edit list|edit approve|reject|rollback <Id>] (WP-N9 Selbstmodell, Körpergefühl, Corollary, Self-Messages/-Edits)
:download all|needle|language|body|gist|embedding / :import model <Rolle> <Pfad>
:export model <Rolle> <Ziel> / :unload [Rolle] / :gc / :clear-logs
:backup / :restore <Pfad> (zeigt Offline-Befehl)
''' 
class Operator:
    def __init__(self,r):self.r=r
    def _implicit_feedback(self,line):
        """WP-V5: praise/criticism in chat text becomes a low-weight answer rating."""
        from . import inputs
        signal=inputs.implicit_feedback(line)
        if not signal:return
        try:
            last=self.r.last_answer()
            if last and last['status']=='FINAL':inputs.record_rating(self.r.store,last['event_id'],inputs.IMPLICIT_SCORE[signal],'IMPLICIT_CHAT',line[:240])
        except (ValueError,KeyError):pass
    def _user_rules(self,line):
        """2026-10-21: a prohibition / "ask me first" the user types is recorded by the fixed rule reader before the turn
        runs (so it already binds this turn's tools) and confirmed with a fixed notice; never via a model."""
        from . import userrules
        for text in userrules.observe(self.r.store,line):self.r.notice(text)
    def run(self,line,origin='OPERATOR_TTY'):
        if origin!='OPERATOR_TTY':raise ValueError('Nur lokale Operator-Eingaben dürfen Befehle ausführen')
        if line.startswith('::'):self._user_rules(line[1:]);return self.r.submit(line[1:])
        if not line.startswith(':'):
            self._implicit_feedback(line)
            self._user_rules(line)
            return self.r.submit(line)
        parts=shlex.split(line[1:]);cmd=parts[0].lower() if parts else 'help';args=parts[1:];r=self.r;s=r.store
        if cmd=='help':return HELP
        if cmd=='befehle':
            from .befehle import operator_command
            return operator_command(r,args)
        if cmd in {'sleep','scheduler'}:
            from .sleep import operator_command
            return operator_command(r,cmd,args)
        if cmd=='neuromod':
            from .neuromod import operator_command
            return operator_command(r,args)
        if cmd=='workspace' and (not args or args[0] in ('status','shadow','active')):
            from .workspace_learn import operator_command
            return operator_command(r,args)
        if cmd=='anchor':
            from .anchor import operator_command
            return operator_command(r,args)
        if cmd=='archive':
            from .archive import operator_command
            return operator_command(r,args)
        if cmd=='homeostasis':
            from .homeostasis import operator_command
            return operator_command(r,args)
        if cmd=='authority':
            from .authority import operator_command
            return operator_command(r,args)
        if cmd=='objectives':
            from .objectives import report as objective_report
            return dumps(objective_report(r.cfg))
        if cmd=='self' and args==['arithmetic']:
            # Local-operator-only, read-only view of the already persisted Age0d
            # arithmetic SHADOW diagnostics. No new correction/delivery rights.
            from .selfmodel import ARITH_SHADOW_KEY
            ring,_=s.state(ARITH_SHADOW_KEY,[])
            if not isinstance(ring,list):raise ValueError('Age0d shadow state invalid')
            return dumps({'status':'SHADOW_ONLY','total':len(ring),'recent':ring[-8:],
                          'user_notified':False,'learning_authorized':False,
                          'age_reopen_authorized':False})
        if cmd=='self' and args and args[0]=='world':
            # Explicit local-only read-only observation of an already existing
            # approved-tool sandbox. No automatic polling, events or authority.
            from .agi.file_world_port import SandboxWorldPort
            from .selfmodel import attribute, controller as self_controller
            root=Path(s.home)/'data'/'tool_sandbox'
            action=args[1:] or ['status']
            port=getattr(r,'_self_world_port',None)
            if action==['status']:
                ready=root.exists() and root.is_dir() and not root.is_symlink()
                return dumps({'mode':'MANUAL_POLL_ONLY','active':port is not None,
                              'sandbox_ready':bool(ready),'learning_authorized':False,
                              'age_reopen_authorized':False,'tool_authorized':False})
            if action==['stop']:
                r._self_world_port=None
                return dumps({'mode':'MANUAL_POLL_ONLY','active':False,'status':'STOPPED'})
            if action==['start']:
                # No mkdir: a real sandbox must pre-exist from a separately
                # authorized action. The port validates inode and symlinks.
                port=SandboxWorldPort(root)
                r._self_world_port=port
                return dumps({'mode':'MANUAL_POLL_ONLY','active':True,'status':'BASELINED',
                              'historical_replay':False,'learning_authorized':False})
            if action==['poll']:
                if port is None:raise ValueError('Self/World Beobachtung erst mit :self world start starten')
                # Validate persisted Self state before consuming the in-memory
                # scan baseline: a corrupt state must not silently lose changes.
                opened=list(self_controller(r)._load()[0]['open'].values())
                observations=port.poll()
                recent=[]
                for obs in observations[-8:]:
                    result=attribute(opened,obs)
                    recent.append({'channel':obs['channel'],'class':result['class'],
                                   'reason':result['reason'],'action_ids':result['action_ids']})
                return dumps({'mode':'MANUAL_POLL_ONLY','active':True,'total':len(observations),
                              'recent':recent,'packets_written':0,'learning_authorized':False,
                              'age_reopen_authorized':False,'tool_authorized':False})
            raise ValueError(':self world [status|start|poll|stop]')
        if cmd=='self' and args:  # bare :self keeps the F3 self_state view below
            from .selfmodel import operator_command
            return operator_command(r,args)
        if cmd=='callosum':
            from .callosum import operator_command
            return operator_command(r,args)
        if cmd=='gist':
            from .gist import operator_command
            return operator_command(r,args)
        if cmd=='toolforecast':
            from .toolforecast import operator_command
            return operator_command(r,args)
        if cmd=='tx':
            from .transaction import operator_command
            return operator_command(r,args)
        if cmd=='verbot':
            from .prohibitions import operator_command
            return operator_command(r,args)
        if cmd=='notaus':
            from .prohibitions import notaus_command
            return notaus_command(r,args)
        if cmd=='stillstand':
            from .standstill import operator_command
            return operator_command(r,args)
        if cmd=='organ':
            from .organ import operator_command
            return operator_command(r,args)
        if cmd=='body':
            from .bodyport import operator_command
            return operator_command(r,args)
        if cmd=='delib':
            from .deliberation import operator_command
            return operator_command(r,args)
        if cmd=='c5':
            from .actionlearn import operator_command
            return operator_command(r,args)
        if cmd=='ff':
            from .fastforward import operator_command
            return operator_command(r,args)
        if cmd=='reflex':
            from .reflex import operator_command
            return operator_command(r,args)
        if cmd=='jef':
            from .jefbridge import operator_command
            return operator_command(r,args)
        if cmd=='ctxos':
            from .context_os import operator_command
            return operator_command(r,args)
        if cmd=='attention':
            from .attention import operator_command
            return operator_command(r,args)
        if cmd in ('regel','regeln'):
            from .userrules import operator_command
            return operator_command(r,args)
        if cmd=='growth':
            from .agi import operator_command
            return operator_command(r,args)
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
        if cmd=='pause' and args:
            from . import inputs
            if args[0]=='budget' and len(args)==2:return dumps(inputs.set_burnout(s,int(args[1])))
            if len(args)==1:return dumps(inputs.set_pause(s,args[0]))
            raise ValueError(':pause [selfedit|traum|training|budget N]')
        if cmd=='resume' and args:
            from . import inputs
            if len(args)!=1:raise ValueError(':resume [selfedit|traum|training]')
            return dumps(inputs.set_pause(s,args[0],False))
        if cmd=='note':
            from . import inputs
            if not args or not args[0].isdigit():raise ValueError(':note 1-10 [Text] bewertet die letzte Antwort')
            last=r.last_answer()
            if not last:raise ValueError('Erst eine eigene Antwort erzeugen')
            return dumps(inputs.record_rating(s,last['event_id'],int(args[0]),'EXPLICIT_NOTE',' '.join(args[1:])))
        if cmd=='ratings':
            from . import inputs
            return dumps(inputs.rating_summary(s))
        if cmd=='context':
            from . import inputs
            return dumps(inputs.last_context(s,r.session) or {'status':'Noch kein Modellkontext in diesem Chat'})
        if cmd=='pause':r.pause();return 'Pausiert'
        if cmd=='resume':r.resume();return 'Fortgesetzt'
        if cmd=='status':return dumps({'session':r.session,'job':r.current,'queued':s.queue_stats()['count'],'paused':r.paused,'generation':s.generation_id,'learning':r.cfg['learning_mode'],'age':agectl.controller(r).system_stage()})
        if cmd=='resources':
            from . import resource_modes  # §97.2 GREEN/YELLOW/ORANGE/RED
            if args:return dumps(resource_modes.command(r,args))
            snap=r.resources();r.guard.update(snap);return dumps(snap|{'resource_mode':resource_modes.report(r)})
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
        if cmd=='search':
            # SQLite LIKE treats % and _ as wildcards; operator search is literal text.
            literal=' '.join(args).replace('\\','\\\\').replace('%','\\%').replace('_','\\_')
            return dumps(s.rows("SELECT session_id,event_id,role,text FROM messages WHERE text LIKE ? ESCAPE '\\' ORDER BY id DESC LIMIT 30",('%'+literal+'%',)))
        if cmd=='memory':
            rows=s.rows("SELECT m.*,s.hash,s.chars FROM memories m JOIN sources s ON s.id=m.source_id "
                        "WHERE m.active=1 AND s.deleted=0 AND (m.session_id=? OR m.scope='global')",
                        (r.session,))
            # Operator-visible facts must obey the same live human F5 authority
            # as C3 recall, C1 continuity, B4 re-entry and Sleep.
            rows=r.memory._verified_rows(rows)
            return dumps([{k:m[k] for k in ('id','kind','scope','key_text','value')} for m in rows])
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
        if cmd=='permissions':return dumps({'operator_command_origin':'TTY only','network':'explicit model setup/download only','model_tool_execution':False,'filesystem_tools_for_models':False,'registered_tools':'typed schema, user-enabled; write/network/external effects only after per-call human approval as WP-K transactions (:tx)','weight_commit':'validated artifact + individual operator approval','latent_injection':False,'natural_language_rules':'prompt guidance, no deterministic semantic guarantee','hard_prohibitions':'typed :verbot rows + :notaus, exact match, checked before and again right before every tool effect; beat per-call approval','fixed_output_rules':'operator-approved exact full-query matching only; invalid active typed rules fail closed','semantic_neural_rule_checker':False})
        if cmd=='age':
            a=agectl.controller(r)
            if not args:return dumps(a.view())
            if args[0]=='freeze' and len(args)==2 and args[1] in {'on','off'}:a.freeze(args[1]=='on');return dumps(a.view())
            if args[0]=='lower' and len(args)==2:return dumps(a.lower('system',int(args[1])))
            if args[0]=='structural' and len(args)==2 and args[1] in {'lock','unlock'}:a.lock_structural(args[1]=='lock');return dumps(a.view())
            raise ValueError(':age [freeze on|off|lower <n>|structural lock|unlock]')
        if cmd=='focal':
            from . import focal
            return dumps(focal.summary(s,r.session))
        if cmd=='effort':
            from . import effort
            if not args:return dumps(effort.summary(s))
            if len(args)!=1:raise ValueError(':effort [disabled|low|adaptive|high|max]')
            return 'reasoning_effort = '+effort.set_mode(s,args[0])+' (Deadline, Ressourcen, Observer-Schalter und Age bleiben bindend)'
        if cmd=='fabric':  # WP-T14 thin-control-fabric budget (§22.2.3)
            from .control_budget import operator_command
            return dumps(operator_command(r,args))
        if cmd=='image':  # WP-N15 vision scaffold, lab/shadow only
            from .vision import operator_command
            return dumps(operator_command(r,args))
        if cmd=='duplex':  # WP-N14 live/full-duplex text timeline
            from .duplex import operator_command,MODES
            if len(args)==1 and args[0] in MODES:
                cfg=r.cfg|{'duplex_mode':args[0]};save_config(r.home,cfg);r.cfg.update(cfg);return 'duplex_mode = '+args[0]
            return dumps(operator_command(r,args))
        if cmd=='admission':  # WP-T9 §9.5 learned memory admission (SHADOW; active only by the user)
            from .admission import operator_command
            return dumps(operator_command(r,args))
        if cmd=='drift':  # WP-S5 drift gate + SDFT data
            from .drift import operator_command
            return dumps(operator_command(r,args))
        if cmd=='register':  # WP-N12 parameter register (IH-H5)
            from .register import operator_command
            return dumps(operator_command(r,args))
        if cmd=='gates':  # WP-N12 gate graph (IH-H28, §100)
            from .gates import operator_command
            return dumps(operator_command(r,args))
        if cmd=='live':  # WP-N13 AG modules in the live turn
            from .agi.live import operator_command
            return dumps(operator_command(r,args))
        if cmd=='episodes':  # WP-N8
            from .episodes import operator_command
            return dumps(operator_command(r,args))
        if cmd=='semantic':  # WP-H semantic memory keys
            from .semantic_memory import status
            if not args or args==['status']:return dumps(status(r))
            if len(args)!=1 or args[0] not in {'off','shadow','on','auto'}:raise ValueError(':semantic [status|off|shadow|on|auto]')
            cfg=r.cfg|{'memory_embedding':args[0]};save_config(r.home,cfg);r.cfg.update(cfg);return 'memory_embedding = '+args[0]
        if cmd=='sampling':
            from .guards import C3_DECODER,LEGACY_DECODER
            if not args:return dumps({'c3_sampling':r.cfg.get('c3_sampling','anti_echo'),'anti_echo':C3_DECODER,'legacy':LEGACY_DECODER|{'temperature':r.cfg['temperature']}})
            if len(args)!=1 or args[0] not in {'anti_echo','legacy'}:raise ValueError(':sampling anti_echo|legacy')
            cfg=r.cfg|{'c3_sampling':args[0]};save_config(r.home,cfg);r.cfg.update(cfg);return 'c3_sampling = '+args[0]
        if cmd=='collapse':
            from .guards import collapse_report,store_pairs
            return dumps(collapse_report(store_pairs(s,None if args==['all'] else r.session)))
        if cmd=='decode':
            if not args:return dumps({'mode':r.cfg.get('c3_decode_mode','server'),'answer_tokens':r.cfg['answer_tokens'],'learned_head':'Individual approved same-ABI output_adapter required; otherwise zero bias'})
            if len(args)!=1 or args[0] not in {'server','same_causal_zero','same_causal'}:raise ValueError(':decode server|same_causal_zero|same_causal')
            r.require_idle()
            if args[0]!='server':
                from .causal_prepare import check_prepared
                check_prepared(r.home)
            cfg=r.cfg|{'c3_decode_mode':args[0]}
            if args[0]!='server' and cfg['answer_tokens'] not in {64,128}:cfg['answer_tokens']=64
            save_config(r.home,cfg);r.pool.unload();r.cfg.update(cfg)
            return 'c3_decode_mode = '+args[0]+'; answer_tokens = '+str(cfg['answer_tokens'])
        if cmd=='import' and len(args)==3 and args[0]=='causal-output':
            r.require_idle();r.enqueue('causal_import',{'dataset':args[1],'trained':args[2]})
            return 'Exact offline shadow verification queued; no automatic approval.'
        if cmd=='budget' and not args:return dumps({k:{'value':r.cfg[k],'unit':v[1],'range':[v[2],v[3]],'status':'BOOT_ESTIMATE'} for k,v in KNOBS.items()})
        if cmd=='rules' and not args:return dumps(s.rules())
        if cmd=='export' and args and args[0]=='chat':
            if len(args)>2:raise ValueError(':export chat [json|md]')
            from .chat_export import export_chat
            return export_chat(s,r.session,args[1] if len(args)==2 else 'json')
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
        if cmd=='learning' and (not args or args==['status']):
            # Read-only operator status. A mode setting is never a weight
            # commit approval or an Age-rights promotion.
            return dumps({'mode':r.cfg['learning_mode'],
                          'age_stage':agectl.controller(r).system_stage(),
                          'approval_required':True,
                          'approval_scope':'weight_commit',
                          'mode_is_not_approval':True})
        if cmd in {'route','observers','channel','learning'}:
            key={'route':'route_override','observers':'observer_mode','channel':'channel','learning':'learning_mode'}[cmd]
            if len(args)!=1:raise ValueError('Ein Wert erforderlich')
            value={'record':'RECORD_ONLY','shadow':'SHADOW_UPDATE','commit':'APPROVED_COMMIT'}.get(args[0],args[0]) if cmd=='learning' else args[0]
            if cmd=='observers' and args[0].upper() in obsched_names():key,value='observer_schedule',args[0].upper()  # §22.2.4 deployment knob
            cfg=r.cfg|{key:value};save_config(r.home,cfg);r.cfg.update(cfg);return key+' = '+value
        if cmd=='budget':
            if len(args)!=2 or args[0] not in KNOBS:raise ValueError(':budget Name Wert; :budget listet Bereiche')
            if args[0] in {'queue_count','queue_bytes'}:raise ValueError('Queue-Größe nur offline in config/settings.json ändern und neu starten')
            value=int(args[1]) if isinstance(KNOBS[args[0]][0],int) else float(args[1]);cfg=r.cfg|{args[0]:value};save_config(r.home,cfg);r.cfg.update(cfg);r.pool.unload()
            if args[0]=='log_retention_days':s.log_retention_days=value;s.prune_telemetry()
            return args[0]+' = '+str(value)
        if cmd=='stage' and len(args)==2 and args[0]=='cap':
            cfg=r.cfg|{'user_stage_cap':int(args[1])};save_config(r.home,cfg);r.cfg.update(cfg);agectl.controller(r).apply_cap();return 'Obergrenze gespeichert; System bleibt Age 0 bis STEP7 (Build-Obergrenze).'
        if cmd=='knobs':
            from .config import knob_specs
            return dumps(knob_specs(r.cfg))
        if cmd=='native':
            from .verification import native_capability_profile
            return dumps(native_capability_profile(r))
        if cmd=='capability':
            a=agectl.controller(r)
            if not args:return dumps(a.view()['capabilities'])
            if len(args)==3 and args[1]=='stage':return dumps(a.lower(args[0],int(args[2])))
            raise ValueError(':capability [<Name> stage <n>] (nur absenken; Anheben nur über Nachweise)')
        if cmd=='latewatch':
            from . import latewatch
            if not args or args==['status']:return dumps(latewatch.report(r))
            if len(args)==1 and args[0] in latewatch.MODES:latewatch.set_mode(r.store,args[0]);return dumps(latewatch.report(r))
            raise ValueError(':latewatch [status|off|shadow|active]')
        if cmd=='skilllive':
            from . import skilllive
            if not args or args==['status']:return dumps(skilllive.report(r))
            raise ValueError(':skilllive [status]')
        if cmd=='bodyview':
            from . import bodyview
            if not args or args==['status']:return dumps(bodyview.modes(s))
            if len(args)==2 and args[0] in ('state','b4'):return dumps(bodyview.set_mode(s,'state_source' if args[0]=='state' else 'b4',args[1]))
            raise ValueError(':bodyview [status|state on|off|b4 off|shadow|on]')
        if cmd=='aplane':
            from . import aplane
            if not args or args==['status']:return dumps(aplane.report(r))
            if len(args)==2 and args[0]=='student':return 'A3-Schüler: '+aplane.set_student_mode(s,args[1])
            if args and args[0]=='distill' and len(args)<=2:return dumps(aplane.distill(r,args[1] if len(args)==2 else None))
            raise ValueError(':aplane [status|student shadow|fallback|distill [Fähigkeit]]')
        if cmd=='fastpolicy':
            from . import fastpolicy
            if not args or args==['status']:return dumps(fastpolicy.report(r))
            if len(args)==2 and args[0]=='focus':return 'Re-entry-Frage: '+fastpolicy.set_focus_mode(s,args[1])
            if args and args[0]=='outcomes':  # WP-U1 outcome self-labels
                from . import jefoutcome
                if len(args)==1:return dumps(jefoutcome.report(r))
                if len(args)==2:return 'Ergebnis-Labels: '+jefoutcome.set_mode(s,args[1])
            if args and args[0]=='lifecycle':  # WP-U1 §14.6 experience lifecycle
                from . import jefoutcome
                return dumps(jefoutcome.lifecycle(r,args[1]) if len(args)==2 else jefoutcome.lifecycle_summary(r))
            raise ValueError(':fastpolicy [status|focus on|off|measure|outcomes [record|learn]|lifecycle [Event-ID]]')
        if cmd=='learn':
            if len(args)>1 or (args and args[0] not in {'route','wake','halt','skill','memory','channel','b1_predictor','b2_predictor','a3_student','world_predictor','control_calibration','memory_retrieval','output_adapter'}):raise ValueError(':learn [route|wake|halt|skill|memory|channel|b1_predictor|b2_predictor|a3_student|world_predictor|control_calibration|memory_retrieval|output_adapter]')
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
            from .output_policy import create,preview
            before=s.rules();after=list(before)
            if args and args[0]=='add' and len(args)>1:after.append(' '.join(args[1:]))
            elif len(args)==3 and args[0]=='fixed':after.append(create(s,args[1],args[2]))
            elif len(args)>=2 and args[0]=='remove':
                indices=[int(value) for value in args[1:]]
                if len(set(indices))!=len(indices) or any(index<0 or index>=len(after) for index in indices):raise ValueError('Eindeutige vorhandene Regel-Indizes ab 0 erforderlich')
                for index in sorted(indices,reverse=True):after.pop(index)
            else:raise ValueError(':rules add Text | fixed "exakte Frage" "exakte Antwort" | remove Index [weitere Indizes] (ab 0)')
            return s.request('RULES',{'base_rule':s.generation()['rule_version'],'before':before,'after':after,'fixed_preview':preview(s,after)})+'; :requests zeigt Diff, :approve ID übernimmt ihn'
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
