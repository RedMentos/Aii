"""Compose phone recovery into the existing pinned integrated review tree.

Frozen source files are only read. The ordinary stager writes the complete
review copy, with its source manifest, before any explicit local activation.
"""
import hashlib
import importlib.util
from pathlib import Path

BUILDERS = {
    'scripts/integrated_world_training_resume_candidate_20261111.py': '5ababdcb3faecae4fb3847ae3281b691e302b63f678c3e7e45675220f0e7ae82',
    'scripts/termux_probe_recovery_candidate_20261112.py': '27aec15dc1f003fd2c90d3d5a08d5a4a9af223ab57c188720ea9cd18aebc1b2b',
    'scripts/termux_chat_recovery_candidate_20261112.py': 'befbaca164fd5453d4c93017eca1b556f2d771b1b7cf54879c6764e4716587c7',
    'scripts/termux_idle_recovery_candidate_20261112.py': '2cc656b102b9950fdb9cb81970708692573189995218bff8a18f95ff01fa97d7',
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
                              'b568613863fef6a687a3237d089b91d8b612ce4163ccb5795df9e21af51c1489')
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

    def recall_pin(raw, name):
        needle = b"    '" + name.encode('ascii') + b"': '"
        if raw.count(needle) != 1:
            raise ValueError('Integrated source recall pin ambiguous: ' + name)
        start = raw.index(needle) + len(needle)
        value = raw[start:start + 64]
        if (len(value) != 64 or raw[start + 64:start + 65] != b"'"
                or any(char not in b"0123456789abcdef" for char in value)):
            raise ValueError('Integrated source recall pin malformed: ' + name)
        return value.decode('ascii')

    if recall_pin(recall, 'store.py') != hashlib.sha256(result['v13/store.py']).hexdigest():
        raise ValueError('Integrated source recall Store binding changed')
    if recall_pin(recall, 'archive_stream_range_candidate.py') != hashlib.sha256(
            result['v13/archive_stream_range_candidate.py']).hexdigest():
        raise ValueError('Integrated source recall stream binding changed')
    old_pin = b'a35966dbe77a603470d73285eac9c8087163d8cf675a1b8516e3b9f38b267232'
    if recall_pin(recall, 'context_os.py').encode('ascii') != old_pin:
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
                             'e062fbf1f0ffc2db0ecdf86aadae123fd15dc7f8de151c819bb040b60ac4adc7')
        result = control_guard.apply_sources(code_dir, result)
        # Feature Age belongs to the final deployed stage. The partial
        # pre-postcommit builder must retain its earlier exact Runtime hash.
        # RAW Age/operator/UI remain pristine for the old phone updater.
        laboratory = load(code_dir, 'scripts/lab_age_stage_candidate_20261118.py',
                          'c09e31ae86901302b8414ddae794e5df5ccbe59292cc700f22ba709701d5acdf')
        result = laboratory.apply_sources(code_dir, result)
    # Integrate the reviewed C4 source-span rule into the ordinary pinned stage.
    # The overlay is exact-blob-pinned and changes only the FocalLoop redundancy calculation.
    focal_overlay_path = code_dir / 'scripts/integrated_focal_scale_diversity_candidate_20261121.py'
    if focal_overlay_path.is_symlink() or not focal_overlay_path.is_file():
        raise ValueError('C4 source-span overlay missing or unsafe')
    focal_overlay_raw = focal_overlay_path.read_bytes()
    focal_overlay_blob = hashlib.sha1(
        b'blob ' + str(len(focal_overlay_raw)).encode('ascii') + b'\0' + focal_overlay_raw
    ).hexdigest()
    if focal_overlay_blob != '9987525960ba0955dd2fd57d421e32f4b76b892c':
        raise ValueError('C4 source-span overlay source changed')
    focal_overlay_ns = {
        '__name__': 'v14_checked_focal_scale_overlay',
        '__file__': str(focal_overlay_path),
    }
    exec(compile(focal_overlay_raw, str(focal_overlay_path), 'exec'), focal_overlay_ns)
    focal_source = result.get('v13/focal.py', (code_dir / 'v13/focal.py').read_bytes())
    if type(focal_source) is not bytes:
        raise ValueError('C4 FocalLoop source is not immutable bytes')
    result['v13/focal.py'] = focal_overlay_ns['apply_staged_focal'](code_dir, focal_source)

    for name, raw in result.items():
        if name.endswith('.py'):
            compile(raw, name, 'exec')
    return result
