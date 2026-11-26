"""Keep both pre-answer bodies eligible under measured C3 recovery in the isolated stage.

Frozen sources stay unchanged. Sequential B1/B2 receive fair native slices inside
the existing 45% pre-answer window; the remaining turn budget is reserved for C3.
A body moves post-commit only when its own slice has expired. This is scheduling
correctness, not a Redmi latency or native-model proof.
"""
import hashlib
from pathlib import Path

PINS = {
    'v13/runtime.py': 'a533660776f7e2b1697e9793a3abb811eb6d1e7191ec6fe0af523d58efa0ce38',
    'v13/observer_schedule.py': '343a4544b873e13f3549556ee52849a46dc2b55242536535b56f959022272943',
    'v13/native_turn_budget.py': '527d7ca89667f1700b89ac643573f272f5ba1890133e64fdce658d2e7910bbf0',
    'v13/cognition.py': '208a713119212caa85a1cb1aa7955e919820cab39471d5ba576cf8fcaf2a3c90',
    'v13/store.py': '40a387e24f8c4d9533bde484c1c82c1dd700517fa652469b4eea7b8b21a471bb',
}


def replace(raw, old, new, label):
    if raw.count(old) != 1:
        raise ValueError('observer fairness anchor changed: ' + label)
    return raw.replace(old, new, 1)


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
        b'                role_end=min(end,now+max(0.,end-now)/(len(roles)-index))\n'
        b'                offers.append(ask(role,True,role_end) if budgeted else ask(role,True))\n', 'sequential slice')
    budget = result.get('v13/native_turn_budget.py', originals['v13/native_turn_budget.py'])
    # Preserve a source-pinned adaptive module that already contains the fair
    # B1/B2 slices and measured C3/C4 reserves; only legacy modules need rewriting.
    advanced_budget = isinstance(budget, bytes) and all(marker in budget for marker in (
        b"observer_deadline=None",
        b"MIN_ROLE_SLICE_S = 2.0",
        b"register_store_telemetry()",
        b"recent_focal_durations",
        b"focal_reserve_source",
        b"RECENT_FOCAL_MAX",
    ))
    if not advanced_budget:
        budget = replace(budget,
            b'NATIVE_FIRST_RESERVE_FRACTION = .87\nDEFAULT_PREANSWER_FRACTION = .45\n',
            b'DEFAULT_PREANSWER_FRACTION = .45\nMIN_ROLE_SLICE_S = 1.0\n',
            'fair recovery slice')
        budget = replace(budget,
            b'def plan(start, deadline, now, *, recent=(), background_enabled=True, direct=False):\n',
            b'def plan(start, deadline, now, *, recent=(), background_enabled=True, direct=False, observer_deadline=None):\n',
            'observer deadline argument')
        budget = replace(budget,
            b'    for number in (start,deadline,now):\n        if type(number) not in (int, float) or not math.isfinite(number):\n            raise ValueError("invalid monotonic budget")\n    if deadline < start or now < start-1:\n',
            b'    for number in (start,deadline,now):\n        if type(number) not in (int, float) or not math.isfinite(number):\n            raise ValueError("invalid monotonic budget")\n    if observer_deadline is not None and (type(observer_deadline) not in (int,float) or not math.isfinite(observer_deadline)):\n        raise ValueError("invalid observer deadline")\n    if deadline < start or now < start-1:\n',
            'observer deadline validation')
        budget = replace(budget,
            b'            and native.get("generated_tokens") == 0\n',
            b'            and type(native.get("generated_tokens")) is int\n            and native.get("generated_tokens") == 0\n',
            'strict zero-token evidence')
        budget = replace(budget, b'        if status == "FINAL":\n', b'''        data = row.get("metadata")
            if isinstance(data, str):
                try:
                    data = json.loads(data)
                except (ValueError, TypeError):
                    data = None
            native = data.get("runner") if isinstance(data, dict) else None
            if (status == "FINAL" and isinstance(native, dict)
                    and native.get("role") == "C3_LANGUAGE"
                    and type(native.get("generated_tokens")) is int
                    and native["generated_tokens"] > 0):
    ''', 'native success evidence')
        budget = replace(budget,
            b'    if recover:\n        reserve = min(total*NATIVE_FIRST_RESERVE_FRACTION,\n                      max(26.0,total*.80))\n        allotted = min(ordinary_end,deadline-reserve)\n        reason="RECENT_C3_ZERO_TOKEN_PREFILL_TIMEOUTS"\n    else:\n        reserve=deadline-ordinary_end\n        allotted=ordinary_end\n        reason="NORMAL_COGNITIVE_PREANSWER"\n',
            b'    observer_end = ordinary_end if observer_deadline is None else min(ordinary_end, observer_deadline)\n    reserve = deadline-ordinary_end\n    if recover:\n        allotted=observer_end\n        reason="RECENT_C3_ZERO_TOKEN_PREFILL_TIMEOUTS"\n    else:\n        allotted=observer_end\n        reason="NORMAL_COGNITIVE_PREANSWER"\n',
            'retain fair preanswer window')
        budget = replace(budget,
            b'        "c3_reserved_seconds": round(reserve,3),\n',
            b'        "c3_reserved_seconds": round(reserve,3),\n        "minimum_role_slice_s": MIN_ROLE_SLICE_S,\n',
            'minimum fair role slice')
    cognition = result.get('v13/cognition.py', originals['v13/cognition.py'])
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
                metrics = {
                    'role': role,
                    'preanswer_seconds_available': round(available,3),
                    'focal_reserved_seconds': budget['focal_reserved_seconds'],
                    'focal_reserve_estimate_seconds': budget['focal_reserve_estimate_seconds'],
                    'focal_reserve_source': budget['focal_reserve_source'],
                    'focal_reserve_capped': budget['focal_reserve_capped'],
                    'recent_focal_samples': budget['recent_focal_samples'],
                    'c3_reserved_seconds': budget['c3_reserved_seconds'],
                    'c3_reserve_estimate_seconds': budget['c3_reserve_estimate_seconds'],
                    'c3_reserve_source': budget['c3_reserve_source'],
                    'c3_reserve_capped': budget['c3_reserve_capped'],
                    'minimum_role_slice_s': budget['minimum_role_slice_s'],
                    'recent_real_prefill_failures': budget['recent_real_prefill_failures'],
                }
                if available < budget['minimum_role_slice_s']:
                    metrics['status'] = 'POSTCOMMIT_ELIGIBLE'
                    self.s.log('native_body_deferred_for_c3',e['event_id'],metrics)
                    raise Limits('No fair B1/B2 slice remains inside the C3-reserved turn window')
                metrics['status'] = 'PREANSWER_BUDGETED'
                self.s.log('native_body_budgeted_for_c3',e['event_id'],metrics)
""",
        'Cognition consumes fair recovery slice')
    store = result.get('v13/store.py', originals['v13/store.py'])
    store = replace(store,
        b"TELEMETRY_FIELDS.update('observer_schedule schedule pre post parallel sampled rss_mb'.split())  # \xc2\xa722.2.4 observer scheduling, \xc2\xa773 RSS budget\n",
        b"TELEMETRY_FIELDS.update('observer_schedule schedule pre post parallel sampled rss_mb'.split())  # \xc2\xa722.2.4 observer scheduling, \xc2\xa773 RSS budget\nTELEMETRY_FIELDS.update('preanswer_seconds_available focal_reserved_seconds focal_reserve_estimate_seconds focal_reserve_source focal_reserve_capped recent_focal_samples c3_reserved_seconds c3_reserve_estimate_seconds c3_reserve_source c3_reserve_capped recent_real_prefill_failures minimum_role_slice_s'.split())\nTELEMETRY_ENUMS.update('PREANSWER_BUDGETED POSTCOMMIT_ELIGIBLE RECENT_FOCAL_MAX RECENT_SUCCESS_MAX FALLBACK_DEFAULT native_turn_budget_plan native_turn_budget_unavailable native_body_budgeted_for_c3 native_body_deferred_for_c3'.split())\n",
        'budget telemetry allowlist')
    for name, raw in (('v13/runtime.py', runtime), ('v13/observer_schedule.py', schedule),
                      ('v13/native_turn_budget.py', budget), ('v13/cognition.py', cognition),
                      ('v13/store.py', store)):
        compile(raw, name, 'exec')
        result[name] = raw
    return result
