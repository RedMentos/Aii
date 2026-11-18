"""Source-bound final-stage integration of owner-selected *feature* Age rights.

The previous X10 control changed CPU/effort but never AgeControl.may(), so
tools and learning remained Age-0 gated. This candidate modifies only the
staged, hash-composed Runtime (not the raw files the old phone updater loads).
It does NOT promote earned Age, overwrite settings, auto-enable tools, bypass
per-call approvals, or automatically train model weights.
"""
import hashlib
from pathlib import Path

LAB_SHA256 = "TO_BE_PINNED"


def _replace(source, old, new, reason):
    if source.count(old) != 1:
        raise ValueError("Laboratory Age integration anchor changed: " + reason)
    return source.replace(old, new, 1)


def apply_sources(code_dir, sources):
    code_dir = Path(code_dir)
    raw = code_dir / "v13/lab_age.py"
    if raw.is_symlink() or not raw.is_file():
        raise ValueError("Laboratory Age policy source unavailable")
    if hashlib.sha256(raw.read_bytes()).hexdigest() != LAB_SHA256:
        raise ValueError("Laboratory Age policy changed without review")
    out = dict(sources)
    required = ("v13/age.py", "v13/runtime.py", "v13/operator.py", "v13/ui.py")
    if any(k not in out or not isinstance(out[k], bytes) for k in required):
        raise ValueError("Laboratory Age requires exact already composed runtime")
    age = out["v13/age.py"]
    age = _replace(age, b"        return self.ceiling(capability,st)>=RIGHTS[right]\n",
                   b"        earned=self.ceiling(capability,st)>=RIGHTS[right]\n"
                   b"        from .lab_age import right_enabled\n"
                   b"        return right_enabled(self,right,earned)\n",
                   "AgeControl effective permitted right")

    runtime = out["v13/runtime.py"]
    runtime = _replace(runtime, b"from .config import initialize\n",
                       b"from .config import initialize\nfrom .lab_age import LabConfig\n",
                       "Runtime selected lab config import")
    runtime = _replace(runtime, b"self.home=home;self.cfg=initialize(home);self.store=Store(home,",
                       b"self.home=home;self.cfg=LabConfig(initialize(home),home);self.store=Store(home,",
                       "Runtime thread-scoped experimental config")
    old_worker = (b"                elif kind=='shadow':\n"
                  b"                    if payload=='memory_retrieval':")
    new_worker = (b"                elif kind in ('shadow','lab_shadow'):\n"
                  b"                    from contextlib import nullcontext\n"
                  b"                    trial=(self.cfg.shadow_training() if kind=='lab_shadow' else nullcontext())\n"
                  b"                    with trial:\n"
                  b"                        if payload=='memory_retrieval':")
    # Reindent the existing actual dispatch arm, preserving all trainer
    # selection (and avoiding any unreviewed optimizer implementation).
    start = runtime.find(old_worker)
    if start < 0 or runtime.count(old_worker) != 1:
        raise ValueError("Laboratory Age shadow-worker entry changed")
    end_marker = b"                elif kind=='causal_import':"
    end = runtime.find(end_marker, start)
    if end < 0 or runtime.count(end_marker) != 1:
        raise ValueError("Laboratory Age shadow-worker exit changed")
    block = runtime[start:end]
    lines = block.splitlines(keepends=True)
    if not lines[1].startswith(b"                    if payload=='memory_retrieval':"):
        raise ValueError("Laboratory Age shadow branch indentation changed")
    if not all(line.startswith(b"                    ") or line.strip()==b""
               for line in lines[1:]):
        raise ValueError("Laboratory Age shadow branch has unexpected syntax")
    body = b"".join(b"    " + line if line.strip() else line for line in lines[1:])
    runtime = (runtime[:start]
               + b"                elif kind in ('shadow','lab_shadow'):\n"
               + b"                    from contextlib import nullcontext\n"
               + b"                    trial=(self.cfg.shadow_training() if kind=='lab_shadow' else nullcontext())\n"
               + b"                    with trial:\n" + body + runtime[end:])
    # LabConfig gates the job only in its executing worker thread. Ordinary
    # chat and post-turn observers still see persisted RECORD_ONLY.
    operator = out["v13/operator.py"]
    operator = _replace(operator,
        b"            r.enqueue('shadow',args[0] if args else 'route');return 'Isoliertes Training gestartet; keine automatische Aktivierung.'\n",
        b"            from .lab_age import effective_stage\n"
        b"            requested=effective_stage(r.home)\n"
        b"            trial=('lab_shadow' if r.cfg['learning_mode']=='RECORD_ONLY' and requested is not None and requested>=2 else 'shadow')\n"
        b"            r.enqueue(trial,args[0] if args else 'route')\n"
        b"            return ('Labor-Training nur SHADOW gestartet; keine automatische Aktivierung.' if trial=='lab_shadow' else 'Isoliertes Training gestartet; keine automatische Aktivierung.')\n",
        "explicit learn dispatch")
    operator = _replace(operator,
        b"        if cmd=='age':\n"
        b"            a=agectl.controller(r)\n"
        b"            if not args:return dumps(a.view())\n",
        b"        if cmd=='age':\n"
        b"            a=agectl.controller(r)\n"
        b"            if not args:\n"
        b"                from .lab_age import rights_status\n"
        b"                return dumps({'official':a.view(),'laboratory':rights_status(a)})\n",
        "age view and test permissions")
    operator = _replace(operator, b"        if cmd=='focal':\n",
        b"        if cmd=='labage':\n"
        b"            from .lab_age import view, save, read, rights_status\n"
        b"            control=agectl.controller(r)\n"
        b"            if not args or args==['status']:\n"
        b"                return dumps(rights_status(control))\n"
        b"            if len(args)==1 and args[0] in ('active','shadow','off'):\n"
        b"                setting=save(r.home,mode=args[0])\n"
        b"            elif len(args) in (1,2) and args[0].isascii() and args[0].isdecimal() and (len(args)==1 or args[1] in ('active','shadow','off')):\n"
        b"                setting=save(r.home,stage=int(args[0]),mode=args[1] if len(args)==2 else 'active')\n"
        b"            else:raise ValueError(':labage [status|0..10 [active|shadow|off]|active|shadow|off]')\n"
        b"            if read(r.home)!=setting:raise ValueError('LAB_STAGE_NOT_PERSISTED')\n"
        b"            return dumps(rights_status(control))\n"
        b"        if cmd=='focal':\n",
        "operator active laboratory stage")
    operator = _replace(operator,
        b"        if cmd=='status':return dumps({'session':r.session,'job':r.current,'queued':s.queue_stats()['count'],'paused':r.paused,'generation':s.generation_id,'learning':r.cfg['learning_mode'],'age':agectl.controller(r).system_stage()})",
        b"        if cmd=='status':\n"
        b"            from .lab_age import rights_status\n"
        b"            lab=rights_status(agectl.controller(r))\n"
        b"            return dumps({'session':r.session,'job':r.current,'queued':s.queue_stats()['count'],'paused':r.paused,'generation':s.generation_id,'learning':r.cfg['learning_mode'],'age':agectl.controller(r).system_stage(),'lab_age':lab})",
        "operator true current-age status")
    operator = _replace(operator,
        b":stage cap 0..5",
        b":labage [status|0..10 [active|shadow|off]] / :stage cap 0..5",
        "operator help discoverability")

    ui = out["v13/ui.py"]
    ui = _replace(ui,
        b"    def header():return ' V13 Â· Age 0 Â· '+r.cfg['learning_mode']+' Â· '+r.status+' Â· Wartend: '+str(r.jobs.qsize())+' '",
        b"    def header():\n"
        b"        from .lab_age import view as lab_view\n"
        b"        from .age import controller as age_controller\n"
        b"        lab=lab_view(r.home,official_stage=age_controller(r).system_stage())\n"
        b"        return (' V13 Â· offiziell Age '+str(lab['official_stage'])+' Â· Test X'+str(lab['stage'])+' '+lab['mode'].upper()+' Â· '+r.cfg['learning_mode']+' Â· '+r.status+' Â· Wartend: '+str(r.jobs.qsize())+' ')",
        "fullscreen real Age/test stage header")
    for name, value in (("v13/age.py", age),("v13/runtime.py", runtime),
                        ("v13/operator.py", operator),("v13/ui.py", ui)):
        compile(value, name, "exec")
        out[name] = value
    return out
