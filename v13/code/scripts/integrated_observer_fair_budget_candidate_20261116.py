"""Keep both pre-answer bodies eligible under measured C3 recovery in the isolated stage.

Frozen sources stay unchanged. Sequential B1/B2 receive fair native slices inside
the existing 45% pre-answer window; the remaining turn budget is reserved for C3.
A body moves post-commit only when its own slice has expired. This is scheduling
correctness, not a Redmi latency or native-model proof.
"""
import hashlib
from pathlib import Path

PINS = {
    'v13/runtime.py': '08c1ef961b0c7316da8c1c8265feb71a7a4acf009018788e7accb81eecb2337d',
    'v13/observer_schedule.py': '879a76528d2d35c519ecf585a583046cecb84609fc35c09901a2e85045e88ca6',
    'v13/native_turn_budget.py': 'c8e2b4df580e7ea8dfe61d5e41b4682e5f6e98f79199b9b2106f2c7055cf18ba',
    'v13/cognition.py': '8cc8df2e517b16b98ba7d13d94ee0c6a9b52b901b23806c5a748abad2ecab2b0',
    'v13/store.py': 'c413e135c765876263835140541a253a6494ebe57714ee43e18ace0c31548521',
}


def replace(raw, old, new, label):
    old_count = raw.count(old)
    new_count = raw.count(new)
    if old_count == 1 and new_count == 0:
        return raw.replace(old, new, 1)
    if old_count == 0 and new_count == 1:
        return raw
    if old_count == 1 and new_count == 1 and old in new:
        # The current source already contains the exact replacement block;
        # the old bytes are a suffix/subsequence of that same block, not a
        # second competing patch. Preserve strict ambiguity rejection otherwise.
        return raw
    raise ValueError('observer fairness anchor changed: ' + label)


def apply_sources(code_dir, sources):
    originals = {}
    for name, expected in PINS.items():
        path = Path(code_dir) / name
        raw = path.read_bytes()
        if path.is_symlink() or hashlib.sha256(raw).hexdigest() != expected:
            raise ValueError('observer fairness source changed: ' + name)
        originals[name] = raw
    result = dict(sources)
    runtime = result.get('v13/runtime.py', originals['v13/runtime.py'])
    runtime = replace(runtime,
        b'                def ask(role,focus=None,use_peer=True):\n',
        b'                def ask(role,focus=None,use_peer=True,role_end=None):\n', 'ask')
    runtime = replace(runtime,
        b'                    p=self.cognition.offer(role,e,version,min(observer_end,time.monotonic()+observer_seconds),',
        b'                    native_end=min(observer_end,time.monotonic()+observer_seconds)\n'
        b'                    if role_end is not None:native_end=min(native_end,role_end)\n'
        b'                    p=self.cognition.offer(role,e,version,native_end,', 'native deadline')
    runtime = replace(runtime,
        b"                offers+=obsched.run(sched,lambda role,use_peer:ask(role,use_peer=use_peer),observer_end,lambda role,exc:self.store.log('offer_rejected',eid,{'role':role,'error':str(exc)[:300]}),cancelled=(Cancelled,))\n",
        b"                offers+=obsched.run(sched,lambda role,use_peer,role_end=None:ask(role,use_peer=use_peer,role_end=role_end),observer_end,lambda role,exc:self.store.log('offer_rejected',eid,{'role':role,'error':str(exc)[:300]}),cancelled=(Cancelled,),budgeted=not sched['parallel'])\n", 'scheduler call')
    schedule = result.get('v13/observer_schedule.py', originals['v13/observer_schedule.py'])
    schedule = replace(schedule,
        b'def run(p,ask,end,on_error,clock=time.monotonic,cancelled=()):\n',
        b'def run(p,ask,end,on_error,clock=time.monotonic,cancelled=(),budgeted=False):\n', 'scheduler signature')
    schedule = replace(schedule,
        b'        for role in roles:\n            if clock()+1>=end:break\n            try:offers.append(ask(role,True))\n',
        b'        for index,role in enumerate(roles):\n'
        b'            now=clock()\n'
        b'            if now>=end or (not budgeted and now+1>=end):break\n'
        b'            try:\n'
        b'                if budgeted:\n'
        b'                    role_end=min(end,now+max(0.,end-now)/(len(roles)-index))\n'
        b'                    offers.append(ask(role,True,role_end))\n'
        b'                else:\n'
        b'                    offers.append(ask(role,True))\n', 'sequential slice')
    budget = result.get('v13/native_turn_budget.py', originals['v13/native_turn_budget.py'])
    # Preserve the pinned measured C3 recovery reserve. The 45% ordinary
    # observer window is not a substitute for the 26 s short-turn recovery
    # reserve; observer_deadline only caps each body's own fair slice.
    required_budget_blocks = (
        b'NATIVE_FIRST_RESERVE_FRACTION = .87\n',
        b'DEFAULT_PREANSWER_FRACTION = .45\n',
        b'MIN_ROLE_SLICE_S = 1.0\n',
        b'def plan(start, deadline, now, *, recent=(), background_enabled=True, direct=False, observer_deadline=None):\n',
        b'    if observer_deadline is not None and (\n            type(observer_deadline) not in (int, float) or not math.isfinite(observer_deadline)):\n        raise ValueError("invalid observer deadline")\n',
        b'    if recover:\n        reserve = min(total*NATIVE_FIRST_RESERVE_FRACTION,\n                      max(26.0,total*.80))\n        allotted = min(ordinary_end,deadline-reserve)\n        reason="RECENT_C3_ZERO_TOKEN_PREFILL_TIMEOUTS"\n    else:\n        reserve=deadline-ordinary_end\n        allotted=ordinary_end\n        reason="NORMAL_COGNITIVE_PREANSWER"\n    if observer_deadline is not None:\n        allotted=min(allotted,observer_deadline)\n',
        b'        "minimum_role_slice_s": MIN_ROLE_SLICE_S,\n',
    )
    if any(budget.count(block) != 1 for block in required_budget_blocks):
        raise ValueError('pinned native C3 recovery reserve or observer cap changed')
    cognition = result.get('v13/cognition.py', originals['v13/cognition.py'])
    # This exact source already carries the reviewed fair-slice consumer from Core.
    # Recognize its complete behavior rather than requiring a historical text layout.
    fair_slice_markers = (
        b"observer_deadline=deadline",
        b"minimum_role_slice_s",
        b"native_body_budgeted_for_c3",
        b"preanswer_seconds_available",
        b"native_body_deferred_for_c3",
    )
    if not all(marker in cognition for marker in fair_slice_markers):
        cognition = replace(cognition,
            b"""        # On repeated measured zero-token C3 prefill deadlines, pre-answer
            # B passes must not consume the remaining foreground native time.
            # The existing postcommit body observer is unaffected (its caller
            # omits valid_until). Both B1 and B2 retain real source/provenance.
            if preanswer_observer and self.r.cfg.get('observer_mode') == 'background':
                try:
                    from .native_turn_budget import plan,recent_proof
                    budget=plan(valid_until-self.r.cfg['deadline_seconds'],
                                valid_until,time.monotonic(),
                                recent=recent_proof(self.s),
                                background_enabled=True)
                except (OSError,ValueError,RuntimeError,KeyError,TypeError):
                    budget=None
                if budget and budget['recovery']:
                    self.s.log('native_body_deferred_for_c3',e['event_id'],
                               {'role':role,'status':'POSTCOMMIT_ELIGIBLE',
                                'recent_failures':budget['recent_real_prefill_failures']})
                    raise Limits('Redmi C3 braucht native Antwortzeit; B-Observer nach erfolgreicher Antwort')
    """,
            b"""        # A measured C3 recovery keeps the C3 reserve but does not blanket-skip
            # both hemispheres. The staged scheduler supplies each sequential role's
            # fair slice as this offer's deadline; only an expired/tiny slice defers.
            if preanswer_observer and self.r.cfg.get('observer_mode') == 'background':
                try:
                    from .native_turn_budget import plan,recent_proof
                    budget=plan(valid_until-self.r.cfg['deadline_seconds'],
                                valid_until,time.monotonic(),
                                recent=recent_proof(self.s),
                                background_enabled=True,
                                observer_deadline=deadline)
                except (OSError,ValueError,RuntimeError,KeyError,TypeError):
                    budget=None
                if budget and budget['recovery']:
                    available=budget['preanswer_seconds_available']
                    if available < budget['minimum_role_slice_s']:
                        self.s.log('native_body_deferred_for_c3',e['event_id'],
                                   {'role':role,'status':'POSTCOMMIT_ELIGIBLE',
                                    'preanswer_seconds_available':round(available,3),
                                    'c3_reserved_seconds':budget['c3_reserved_seconds'],
                                    'recent_real_prefill_failures':budget['recent_real_prefill_failures']})
                        raise Limits('No fair B1/B2 slice remains inside the C3-reserved turn window')
                    self.s.log('native_body_budgeted_for_c3',e['event_id'],
                               {'role':role,'status':'PREANSWER_BUDGETED',
                                'preanswer_seconds_available':round(available,3),
                                'c3_reserved_seconds':budget['c3_reserved_seconds'],
                                'recent_real_prefill_failures':budget['recent_real_prefill_failures']})
    """,
            'Cognition consumes fair recovery slice')
    store = result.get('v13/store.py', originals['v13/store.py'])
    store = replace(store,
        b"TELEMETRY_FIELDS.update('observer_schedule schedule pre post parallel sampled rss_mb'.split())  # \xc2\xa722.2.4 observer scheduling, \xc2\xa773 RSS budget\n",
        b"TELEMETRY_FIELDS.update('observer_schedule schedule pre post parallel sampled rss_mb'.split())  # \xc2\xa722.2.4 observer scheduling, \xc2\xa773 RSS budget\nTELEMETRY_FIELDS.update('preanswer_seconds_available c3_reserved_seconds recent_real_prefill_failures'.split())\nTELEMETRY_ENUMS.update('PREANSWER_BUDGETED POSTCOMMIT_ELIGIBLE'.split())\n",
        'budget telemetry allowlist')
    for name, raw in (('v13/runtime.py', runtime), ('v13/observer_schedule.py', schedule),
                      ('v13/native_turn_budget.py', budget), ('v13/cognition.py', cognition),
                      ('v13/store.py', store)):
        compile(raw, name, 'exec')
        result[name] = raw
    return result
