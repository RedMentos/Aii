"""Give sequential observers fair native slices in the isolated runtime stage.

Frozen sources stay unchanged. The caller pins and composes the upstream tree.
This is scheduling correctness, not a Redmi latency or native model proof.
"""
import hashlib
from pathlib import Path

PINS = {
    'v13/runtime.py': 'a533660776f7e2b1697e9793a3abb811eb6d1e7191ec6fe0af523d58efa0ce38',
    'v13/observer_schedule.py': '343a4544b873e13f3549556ee52849a46dc2b55242536535b56f959022272943',
    'v13/native_turn_budget.py': '172bf70b05e21fd3c117273473446d0f77a11f625cc2665df1f4991708a1505c',
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
        b'            if now+1>=end:break\n'
        b'            try:\n'
        b'                role_end=min(end,now+max(0.,end-now)/(len(roles)-index))\n'
        b'                offers.append(ask(role,True,role_end) if budgeted else ask(role,True))\n', 'sequential slice')
    budget = result.get('v13/native_turn_budget.py', originals['v13/native_turn_budget.py'])
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
    for name, raw in (('v13/runtime.py', runtime), ('v13/observer_schedule.py', schedule),
                      ('v13/native_turn_budget.py', budget)):
        compile(raw, name, 'exec')
        result[name] = raw
    return result
