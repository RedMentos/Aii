"""Connect a scoped, bounded World-JEPA job to the existing G13/Sleep worker."""
import hashlib
import importlib.util
from pathlib import Path

BASE_SHA = 'cc581a85f131417af184f38b86f732ce4bafc4e49a51bd55c89afad78f21ff4a'
IDLE_SHA = '71dabc5e1d015029e910cd7f96e9317a89d03e39e5ee5f5574b059174b96c1e7'
SOURCE_PINS = {'v13/authority.py': '01e1550943f22b117b5bc471fac88ed729b61c6dadf24a1c4d4ad99ec14dbfdb', 'v13/sleep.py': '8c964b77ba436236430e4812e8304b062b4f4059caf2c52035860edb4bed1eee', 'v13/scheduler.py': 'e44512b92b66cb63902645f73128d4063f3afc51367052e7e81491035bda17fb', 'v13/operator.py': '67f2118efce0495ea144b11e8853cbf949d56e53e141fe7f801b31c56406f9a3', 'v13/agi/trainers.py': '67a4ff83cf536ddd2171b0262d1b03b73a72c5adac120456c269e06f95b2dc98', 'v13/agi/weights.py': '6e17a419638d357499a8140d64e6d0d6d1a48fcac42d5033664cfd986257da6e', 'v13/agi/__init__.py': '75333b385dbc2d581e8fc028b433b0a93847dc80b64f83d9aedf104cc45c8661'}


def replace(raw, old, new, label):
    if raw.count(old) != 1:
        raise ValueError('unexpected idle integration source: ' + label)
    return raw.replace(old, new, 1)


def build_sources(code_dir):
    code_dir = Path(code_dir)
    path = code_dir / 'scripts/integrated_c3_consent_candidate_20261111.py'
    idle = (code_dir / 'v13/world_jepa_idle_runtime_candidate.py').read_bytes()
    if hashlib.sha256(path.read_bytes()).hexdigest() != BASE_SHA or hashlib.sha256(idle).hexdigest() != IDLE_SHA:
        raise ValueError('idle composition source changed')
    for name, expected in SOURCE_PINS.items():
        if hashlib.sha256((code_dir / name).read_bytes()).hexdigest() != expected:
            raise ValueError('idle frozen dependency changed: ' + name)
    spec = importlib.util.spec_from_file_location('verified_c3_consent_composition', path)
    parent = importlib.util.module_from_spec(spec);spec.loader.exec_module(parent)
    result = parent.build_sources(code_dir)
    policy = result['v13/online_world_policy.py']
    old_policy_sha = hashlib.sha256(policy).hexdigest().encode()
    start = policy.index(b'    from .inputs import paused\n', policy.index(b'def blocked('))
    end = policy.index(b'\n\ndef status(', start)
    tail = policy[start:end]
    policy = policy[:start] + b"    return safety_blocked(runtime)\n\n\ndef safety_blocked(runtime):\n    if runtime.cfg.get('learning_mode') not in {'SHADOW_UPDATE','APPROVED_COMMIT'}:\n        return 'RECORD_ONLY'\n" + tail + policy[end:]
    new_policy_sha = hashlib.sha256(policy).hexdigest().encode()
    for name, data in list(result.items()):
        if old_policy_sha in data:
            result[name] = data.replace(old_policy_sha, new_policy_sha)
    result['v13/online_world_policy.py'] = policy

    guard = result['v13/world_jepa_runtime_guard_candidate.py']
    guard = replace(guard, b'from . import world_model\n', b'from . import world_model\nfrom . import world_jepa_idle_runtime_candidate as idle_scope\n', 'guard scope import')
    guard = replace(guard, b'PINS = {\n', b"PINS = {\n    'world_jepa_idle_runtime_candidate.py': '" + IDLE_SHA.encode() + b"',\n", 'idle helper pin')
    old = b"    if authority != policy.HUMAN:\n        return {'status': 'SKIPPED_EXPLICIT_HUMAN_REQUIRED', 'trained': False}\n    reason = policy.blocked(runtime, authority)\n"
    new = b"    if authority == idle_scope.AUTHORITY:\n        reason = idle_scope.scope_blocked(runtime,'update')\n    elif authority != policy.HUMAN:\n        return {'status': 'SKIPPED_EXPLICIT_HUMAN_REQUIRED', 'trained': False}\n    else:reason = policy.blocked(runtime, authority)\n"
    guard = replace(guard, old, new, 'update scoped authority')
    guard = replace(guard, b'    runtime.require_idle()\n',
                    b"    if authority==idle_scope.AUTHORITY:idle_scope.validate_update(runtime,steps,limit)\n    else:runtime.require_idle()\n", 'actual background owner')
    guard = replace(guard, b'        reason = policy.blocked(runtime, authority)\n',
                    b"        reason = idle_scope.scope_blocked(runtime,'update') if authority==idle_scope.AUTHORITY else policy.blocked(runtime,authority)\n", 'locked update scope recheck')
    guard = replace(guard, b'                result = experiment.update(candidate, rows, steps=steps)\n',
                    b"                if authority==idle_scope.AUTHORITY:idle_scope.claim_update(runtime,steps,limit)\n                result = experiment.update(candidate, rows, steps=steps)\n", 'single-use reserved numeric step')
    result['v13/world_jepa_runtime_guard_candidate.py'] = guard

    lineage = result['v13/world_jepa_lineage_checkpoint_candidate.py']
    lineage = replace(lineage, b'from . import world_model\n',
                      b'from . import world_model\nfrom . import world_jepa_idle_runtime_candidate as idle_scope\n', 'lineage scope import')
    start = lineage.index(b'def _authorize(runtime, authority):\n')
    end = lineage.index(b'\n\ndef _open_home(', start)
    authorization = b'''def _authorize(runtime, authority, operation):
    guard._check_sources()
    if type(runtime.store) is not Store:
        raise ValueError('reviewed Store instance required')
    if authority == idle_scope.AUTHORITY:
        idle_scope.require_owner(runtime,operation)
        reason=None
    elif authority != policy.HUMAN:
        raise PermissionError('explicit operator or actual scoped idle owner required')
    else:reason=policy.blocked(runtime,authority)
    if reason:
        raise ValueError('JEPA checkpoint unavailable: ' + reason)
    if authority==idle_scope.AUTHORITY:idle_scope.require_owner(runtime,operation)
    else:runtime.require_idle()
'''
    lineage = lineage[:start] + authorization + lineage[end:]
    start = lineage.index(b'def save(runtime,')
    end = lineage.index(b'def restore(runtime,', start)
    saving, restoring = lineage[start:end], lineage[end:]
    if saving.count(b'_authorize(runtime, authority)') != 2 or restoring.count(b'_authorize(runtime, authority)') != 2:
        raise ValueError('unexpected lineage authorization calls')
    saving = saving.replace(b'_authorize(runtime, authority)', b"_authorize(runtime, authority,'save')")
    restoring = restoring.replace(b'_authorize(runtime, authority)', b"_authorize(runtime, authority,'restore')")
    result['v13/world_jepa_lineage_checkpoint_candidate.py'] = lineage[:start] + saving + restoring

    scheduler = (code_dir / 'v13/scheduler.py').read_bytes()
    scheduler = replace(scheduler, b"ACTIONS|={'learn_medium','learn_slow'}", b"ACTIONS|={'learn_medium','learn_slow','learn_world_jepa_idle'}", 'scheduler accepted action')
    result['v13/scheduler.py'] = scheduler
    sleep = (code_dir / 'v13/sleep.py').read_bytes()
    sleep = replace(sleep, b'        state=self.resource_state()\n',
                    b"        state=self.resource_state()\n        from . import world_jepa_idle_runtime_candidate as idle_world\n        idle_world.maybe_post(self.r)\n", 'idle tick on existing worker')
    sleep = replace(sleep, b"                    if medium_due(self.r.store,self.clock()):self.scheduler.post('IDLE',action='learn_medium',dedup='learn-medium')\n",
                    b"                    from .online_world_policy import safety_blocked\n                    if safety_blocked(self.r) is None and medium_due(self.r.store,self.clock()):self.scheduler.post('IDLE',action='learn_medium',dedup='learn-medium')\n", 'legacy medium no record-only hot loop')
    sleep = replace(sleep, b"        try:out=job(self.r,e['action'],e['origin'])\n",
                    b"        try:\n            if e['action']=='learn_world_jepa_idle':\n                from .world_jepa_idle_runtime_candidate import step\n                out=step(self.r,e)\n            else:out=job(self.r,e['action'],e['origin'])\n", 'actual dispatched idle job')
    result['v13/sleep.py'] = sleep
    authority = (code_dir / 'v13/authority.py').read_bytes()
    anchor = b"    out={'action':action,'review':review(r,origin)['changes']}\n"
    authority = replace(authority, anchor,
        b"    if action not in ('learn_medium','learn_slow'):raise ValueError('Unknown learning action')\n    from .online_world_policy import safety_blocked\n    reason=safety_blocked(r)\n    if reason:return {'action':action,'review':[],'status':'SKIPPED_'+reason}\n" + anchor, 'legacy ridge mode/pause/resources before any mutation')
    result['v13/authority.py'] = authority
    operator = result['v13/operator.py']
    anchor = b"        if cmd in {'route','observers','channel','learning'}:\n"
    operator = replace(operator, anchor, b"        if cmd=='learning' and args and args[0]=='idle':\n            from .world_jepa_idle_runtime_candidate import operator\n            return operator(r,args[1:])\n" + anchor, 'explicit idle console')
    result.update({'v13/operator.py': operator, 'v13/world_jepa_idle_runtime_candidate.py': idle})
    return result
