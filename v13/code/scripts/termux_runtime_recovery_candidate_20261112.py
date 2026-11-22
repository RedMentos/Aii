"""Compose phone recovery into the existing pinned integrated review tree.

Frozen source files are only read. The ordinary stager writes the complete
review copy, with its source manifest, before any explicit local activation.
"""
import hashlib
import importlib.util
from pathlib import Path

BUILDERS = {
    'scripts/integrated_world_training_resume_candidate_20261111.py': '1cbbafe0e2f3e6bcc959be3c707218ce0446d065c37c8aec8b07c9b0142f7b44',
    'scripts/termux_probe_recovery_candidate_20261112.py': '27aec15dc1f003fd2c90d3d5a08d5a4a9af223ab57c188720ea9cd18aebc1b2b',
    'scripts/termux_chat_recovery_candidate_20261112.py': '6ae1f52595660b12bbb7f6684cc5c0b090614df5fe538f075a3256bd6995645f',
    'scripts/termux_idle_recovery_candidate_20261112.py': '4920cc600fd184ff9a536807dec3d63571db8029379828334bb4cf1c635be36a',
}


def load(code_dir, relative, expected):
    path = code_dir / relative
    if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise ValueError('Termux recovery builder source changed: ' + relative)
    spec = importlib.util.spec_from_file_location('recovery_' + path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build_sources(code_dir, *, include_postcommit=True):
    code_dir = Path(code_dir)
    modules = [load(code_dir, name, pin) for name, pin in BUILDERS.items()]
    base, probe, chat, idle = modules
    result = base.build_sources(code_dir)
    for name, raw in probe.build_sources(code_dir).items():
        if name in result:
            raise ValueError('Upstream probe source changed; review composition')
        result[name] = raw
    chat.build_sources(code_dir)  # validate frozen inputs as well as anchors
    composed = {name: result.get(name, (code_dir / name).read_bytes())
                for name in chat.SOURCE_PINS}
    result.update(chat.apply_sources(composed))
    result = idle.apply_sources(code_dir, result)
    arithmetic = load(code_dir, 'scripts/integrated_arithmetic_candidate_20261116.py',
                      '72bf8a829a7de064e7703271228bcdf02632108418c41c571126fbd8c05d5567')
    result = arithmetic.apply_sources(code_dir, result)
    arithmetic_outcome = load(code_dir, 'scripts/integrated_arithmetic_outcome_candidate_20261116.py',
                              'c65d6ac26c72dbd7c9563cca3dfc165d6336320624f5a6083bc7b707dbc7c1b3')
    result = arithmetic_outcome.apply_sources(code_dir, result)
    observers = load(code_dir, 'scripts/integrated_observer_fair_budget_candidate_20261116.py',
                     '44216ae22cc92e638ca36b71a9e62f95b130cf21ce0c2b550a6ecdc3ccca9a94')
    result = observers.apply_sources(code_dir, result)
    # Apply only the reviewed ContextOS input and the exact checked builder.
    # The dependent recall module pins ContextOS, so rebind that one pin.
    path = code_dir / 'scripts/context_offer_budget_candidate_20261116.py'
    if path.is_symlink() or not path.is_file():
        raise ValueError('Context budget builder missing or unsafe')
    candidate = path.read_bytes()
    if hashlib.sha256(candidate).hexdigest() != 'e904eba285af6c5079a91e886e7b6d9b9a6c2ecbcd352adcd351ddef3b150fa7':
        raise ValueError('Context budget builder source changed')
    namespace = {'__name__': 'v13_checked_context_budget', '__file__': str(path)}
    exec(compile(candidate, str(path), 'exec'), namespace)
    context = result['v13/context_os.py']
    if hashlib.sha256(context).hexdigest() != 'a35966dbe77a603470d73285eac9c8087163d8cf675a1b8516e3b9f38b267232':
        raise ValueError('Integrated ContextOS source changed')
    context = namespace['apply_source'](context)
    if hashlib.sha256(context).hexdigest() != 'e4962d932294490b8f4b63a79115212a7000285290444484ec3bf7e50b243cad':
        raise ValueError('Integrated ContextOS output changed')
    recall = result['v13/context_source_recall_candidate.py']
    if hashlib.sha256(recall).hexdigest() != '7f73ec6c4a15e6790a40e7f94d4a0bc5f2fba63bfc23c9368286aa2d83457d7c':
        raise ValueError('Integrated source recall changed')
    old_pin = b'a35966dbe77a603470d73285eac9c8087163d8cf675a1b8516e3b9f38b267232'
    if recall.count(old_pin) != 1:
        raise ValueError('Integrated source recall ContextOS pin changed')
    result['v13/context_os.py'] = context
    result['v13/context_source_recall_candidate.py'] = recall.replace(
        old_pin, b'e4962d932294490b8f4b63a79115212a7000285290444484ec3bf7e50b243cad', 1)
    if include_postcommit:
        path = code_dir / 'scripts/postcommit_observer_candidate_20261116.py'
        if path.is_symlink() or not path.is_file():
            raise ValueError('Postcommit observer builder missing or unsafe')
        raw_candidate = path.read_bytes()
        if hashlib.sha256(raw_candidate).hexdigest() != '0fec24d5b5bf7c1d270a3143811a4e62da65893beae84c3b8ce72baf3765e670':
            raise ValueError('Postcommit observer builder source changed')
        namespace = {'__name__': 'v13_checked_postcommit', '__file__': str(path)}
        exec(compile(raw_candidate, str(path), 'exec'), namespace)
        runtime = result['v13/runtime.py']
        if hashlib.sha256(runtime).hexdigest() != 'd3fac6289d2898806d0126a462b8224b1f945fdf0bd87b7cc5715206974334c2':
            raise ValueError('Integrated observer Runtime source changed')
        runtime = namespace['apply_source'](runtime)
        # LateWatch runs during C3 streaming and must obey the same resolved
        # per-turn body selection as the foreground and post-answer schedules.
        old_call = b"latewatch.start(self,e,version,offers,deadline,meta,runner,eligible=not direct and state=='NORMAL')"
        new_call = b"latewatch.start(self,e,version,offers,deadline,meta,runner,eligible=not direct and state=='NORMAL',allowed_roles=effort.roles(wake_route))"
        if runtime.count(old_call) != 1:
            raise ValueError('LateWatch Runtime anchor changed')
        result['v13/runtime.py'] = runtime.replace(old_call, new_call, 1)
        late_path = code_dir / 'v13/latewatch.py'
        if late_path.is_symlink() or not late_path.is_file():
            raise ValueError('LateWatch source missing or unsafe')
        late = late_path.read_bytes()
        if hashlib.sha256(late).hexdigest() != 'fc2e86be3f2f3e629a9e54c3f1c31266f495060e60a42e636f7a924f5ffadfc0':
            raise ValueError('LateWatch source changed')
        old_sig = b"def start(r,e,version,offers,deadline,meta,runner,eligible=True):\n"
        new_sig = b"def start(r,e,version,offers,deadline,meta,runner,eligible=True,allowed_roles=None):\n"
        old_roles = b'''        have={p.get('role') for p in offers if isinstance(p,dict)}
        role=next((x for x in ('B1_DETAIL','B2_GIST') if x not in have),None)
        if role is None:return Watcher(r,e,meta,m,status='ALL_BODIES_OFFERED')
'''
        new_roles = b'''        valid=('B1_DETAIL','B2_GIST')
        if allowed_roles is None:
            allowed=set(valid)
        elif type(allowed_roles) in (list,tuple,set,frozenset) and all(x in valid for x in allowed_roles):
            allowed=set(allowed_roles)
        else:
            return Watcher(r,e,meta,m,status='INVALID_ROLE_LIMIT')
        have={p.get('role') for p in offers if isinstance(p,dict)}
        role=next((x for x in valid if x in allowed and x not in have),None)
        if role is None:
            status='ALL_BODIES_OFFERED' if allowed and allowed.issubset(have) else 'NO_ELIGIBLE_BODY'
            return Watcher(r,e,meta,m,status=status)
'''
        if late.count(old_sig) != 1 or late.count(old_roles) != 1:
            raise ValueError('LateWatch role anchor changed')
        late = late.replace(old_sig, new_sig, 1).replace(old_roles, new_roles, 1)
        if hashlib.sha256(late).hexdigest() != '841aeaa9d7d0b0950b6c3ad799d2b8f8dd44fcee93159bd2a48c66f341460b12':
            raise ValueError('LateWatch output changed')
        result['v13/latewatch.py'] = late
        control_guard = load(code_dir, 'scripts/record_only_controller_guard_20261116.py',
                             '01e034e478eea9d7ec6c034adaa313e7e0b2e9bccaf21712671b0b3546cccfab')
        result = control_guard.apply_sources(code_dir, result)
        # Feature Age belongs to the final deployed stage. The partial
        # pre-postcommit builder must retain its earlier exact Runtime hash.
        # RAW Age/operator/UI remain pristine for the old phone updater.
        laboratory = load(code_dir, 'scripts/lab_age_stage_candidate_20261118.py',
                          'c09e31ae86901302b8414ddae794e5df5ccbe59292cc700f22ba709701d5acdf')
        result = laboratory.apply_sources(code_dir, result)
    for name, raw in result.items():
        if name.endswith('.py'):
            compile(raw, name, 'exec')
    return result
