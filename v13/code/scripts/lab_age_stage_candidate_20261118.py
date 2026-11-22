"""Add actual owner-selected virtual Age gates to verified composed V13.

A source-bound patch of the **staged copy**, never the frozen RAW files. The
previous phone updater must still be able to migrate to this version. The
existing integrated builder verifies its own full chain before this patch.
"""
import ast
import hashlib
from pathlib import Path

# Git blob identifiers of reviewed inputs, verified independent of location.
INPUT_BLOBS = {
    "v13/age.py": "964048c47ddb5a8f11ea6706d72a1f37ab41f5d4",
    "v13/effort.py": "0ba88e4ed1d0a1e8a3e8caecccf1ac8a5e615d04",
    "v13/executive.py": "057dda1e705053047489516fc9ab10581018f5a4",
    "v13/lab_age_runtime.py": "ab72d5efcb6405323da975bd7fab707ddc3e8b7c",
    "v13/lab_age.py": "e94d081538bc47268b5b536ddcecf29b98877ee2",
}
AGE_CONTROLLER = b"""def controller(runtime):
    \"\"\"Runtime-scoped instance without touching runtime.py; reads the live config dict.\"\"\"
    a=getattr(runtime,'age',None)
    if a is None:a=runtime.age=AgeControl(runtime.store,runtime.cfg)
    return a"""
AGE_CONTROLLER_LAB = b"""def controller(runtime):
    \"\"\"Return the live, owner-selected Age gate tester; official Age is never raised.\"\"\"
    a=getattr(runtime,'age',None)
    if a is None:
        from .lab_age_runtime import LaboratoryAgeControl
        a=runtime.age=LaboratoryAgeControl(runtime.store,runtime.cfg)
    return a"""

LAB_OPERATOR = b"""        if cmd=='labage':
            from .lab_age import save, read
            a=agectl.controller(r)
            if not args or args==['status']:
                return dumps(a.view()['laboratory'])
            if len(args)==1 and args[0] in ('active','shadow','off'):
                chosen={'mode':args[0]}
            elif len(args) in (1,2) and args[0].isascii() and args[0].isdecimal():
                chosen={'stage':int(args[0]), 'mode':args[1] if len(args)==2 else 'active'}
            else:
                raise ValueError(':labage [status|0..10 [active|shadow|off]|active|shadow|off]')
            r.require_idle()
            selected=save(r.home,**chosen)
            if read(r.home)!=selected:
                raise ValueError('Laborstufe konnte nicht dauerhaft bestaetigt werden')
            return dumps(a.view()['laboratory'])
"""

AGE_HEADER = """    def header():
        from .age import controller
        a=controller(r)
        lab=a.view()['laboratory']
        return (' V13 · Age '+str(a.system_stage())+' offiziell'
                +' · LAB '+str(lab['stage'])+' '+lab['mode'].upper()
                +' · '+r.cfg['learning_mode']+' · '+r.status
                +' · Wartend: '+str(r.jobs.qsize())+' ')""".encode('utf-8')


def _replace(raw, old, new, name):
    if raw.count(old) != 1:
        raise ValueError("Lab Age staged source anchor missing/repeated: " + name)
    return raw.replace(old, new, 1)


def _replace_or_verify(raw, old, new, name):
    """Patch the original anchor or verify an already-patched exact value."""
    old_count = raw.count(old)
    new_count = raw.count(new)
    if old_count == 1 and new_count == 0:
        return raw.replace(old, new, 1)
    if old_count == 0 and new_count == 1:
        return raw
    raise ValueError("Lab Age staged source anchor missing/repeated: " + name)


def _source(code_dir, relative):
    target=code_dir / relative
    if target.is_symlink() or not target.is_file():
        raise ValueError("Lab Age source missing or symlinked: " + relative)
    raw=target.read_bytes()
    expected=INPUT_BLOBS[relative]
    blob=hashlib.sha1(b"blob "+str(len(raw)).encode("ascii")+b"\0"+raw).hexdigest()
    if blob!=expected:
        raise ValueError("Lab Age source no longer matches reviewed Git blob: " + relative)
    return raw


def apply_sources(code_dir, sources):
    code_dir=Path(code_dir)
    original={p:_source(code_dir,p) for p in INPUT_BLOBS}
    out=dict(sources)
    age=out.get("v13/age.py",original["v13/age.py"])
    if age != original["v13/age.py"]:
        raise ValueError("Lab Age requires reviewed original age.py")
    out["v13/age.py"]=_replace(age,AGE_CONTROLLER,AGE_CONTROLLER_LAB,"runtime Age controller")
    effort=out.get("v13/effort.py",original["v13/effort.py"])
    if effort!=original["v13/effort.py"]:
        raise ValueError("Lab Age requires reviewed original effort.py")
    effort=_replace_or_verify(effort,b"'stage':control.ceiling('system')",
                              b"'stage':control.system_stage()", "official stage in effort")
    effort=_replace(effort,b"'LAB_COMPUTE_ONLY_NO_NEW_RIGHTS'",
                    b"'LAB_FEATURE_GATE_TEST_WITH_INDEPENDENT_LEARNING_GUARD'", "effort lab status")
    out["v13/effort.py"]=effort
    executive=out.get("v13/executive.py",original["v13/executive.py"])
    if executive!=original["v13/executive.py"]:
        raise ValueError("Lab Age requires reviewed original executive.py")
    out["v13/executive.py"]=_replace(
        executive,b"permission_flags(AgeControl(self.s,cfg),cfg,resource_state)",
        b"permission_flags(__import__('v13.lab_age_runtime',fromlist=['LaboratoryAgeControl']).LaboratoryAgeControl(self.s,cfg),cfg,resource_state)",
        "Executive direct AgeControl permission flags")
    operator=out.get("v13/operator.py")
    if type(operator) is not bytes:
        raise ValueError("Lab Age requires composed operator source")
    operator=_replace(operator,b"        if cmd=='age':\n",LAB_OPERATOR+b"        if cmd=='age':\n","labage operator")
    operator=_replace(operator,b"'age':agectl.controller(r).system_stage()})",
        b"'age':agectl.controller(r).system_stage(), 'laboratory':agectl.controller(r).view()['laboratory']})","status field")
    operator=_replace(operator,
        b":age [freeze on|off|lower <n>|structural lock|unlock] / :stage cap 0..5",
        b":age [freeze on|off|lower <n>|structural lock|unlock] / :labage [status|0..10 [active|shadow|off]] / :stage cap 0..5",
        "unique help line only")
    # A selected laboratory stage now authorizes an *explicit* shadow
    # learning job, without ever promoting learned weights or changing the
    # owner's persisted RECORD_ONLY baseline. A thread-local overlay exists
    # only during that job; ordinary turns and post-turn agents stay RECORD_ONLY.
    operator=_replace(operator,
        b"            r.enqueue('shadow',args[0] if args else 'route');return 'Isoliertes Training gestartet; keine automatische Aktivierung.'\n",
        b"            from .lab_age import effective_stage\n"
        b"            trial=effective_stage(r.home)\n"
        b"            job=('lab_shadow' if r.cfg['learning_mode']=='RECORD_ONLY' and trial is not None and trial>=2 else 'shadow')\n"
        b"            r.enqueue(job,args[0] if args else 'route')\n"
        b"            return ('Labor-Training SHADOW angefordert; keine Gewichtsaktivierung.' if job=='lab_shadow' else 'Isoliertes Training gestartet; keine automatische Aktivierung.')\n",
        "explicit learning job gate")
    out["v13/operator.py"]=operator
    runtime=out.get("v13/runtime.py")
    if type(runtime) is not bytes:
        raise ValueError("Lab Age requires composed runtime source")
    runtime=_replace(runtime,
        b"from .config import initialize\n",
        b"from .config import initialize\nfrom .lab_age import LabConfig\n",
        "thread-scoped lab learning config")
    runtime=_replace(runtime,
        b"self.home=home;self.cfg=initialize(home);self.store=Store(home,",
        b"self.home=home;self.cfg=LabConfig(initialize(home),home);self.store=Store(home,",
        "runtime owner learning mode remains stored unchanged")
    start_marker=b"                elif kind=='shadow':\n"
    end_marker=b"                elif kind=='causal_import':"
    if runtime.count(start_marker)!=1 or runtime.count(end_marker)!=1:
        raise ValueError("Lab Age native shadow worker arm missing")
    start=runtime.index(start_marker)
    end=runtime.index(end_marker,start)
    rows=runtime[start:end].splitlines(keepends=True)
    if not rows or len(rows)<4 or any(
            line.strip() and not line.startswith(b"                    ")
            for line in rows[1:]):
        raise ValueError("Lab Age shadow worker indentation changed")
    body=b"".join((b"    "+line if line.strip() else line) for line in rows[1:])
    runtime=(
        runtime[:start]+
        b"                elif kind in ('shadow','lab_shadow'):\n"
        b"                    from contextlib import nullcontext\n"
        b"                    trial=(self.cfg.shadow_training() if kind=='lab_shadow' else nullcontext())\n"
        b"                    with trial:\n"
        +body+runtime[end:])
    out["v13/runtime.py"]=runtime
    ui=out.get("v13/ui.py")
    if type(ui) is not bytes:
        raise ValueError("Lab Age requires composed console source")
    ui=_replace(ui,
        "    def header():return ' V13 · Age 0 · '+r.cfg['learning_mode']+' · '+r.status+' · Wartend: '+str(r.jobs.qsize())+' '".encode('utf-8'),
        AGE_HEADER,"live console Age header")
    out["v13/ui.py"]=ui
    for name in ("v13/age.py","v13/effort.py","v13/executive.py","v13/operator.py","v13/runtime.py","v13/ui.py"):
        ast.parse(out[name],filename=name)
    return out
