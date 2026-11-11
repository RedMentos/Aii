"""Offline, separately authorized dataset RECORD intake in the shared stage."""
import hashlib
import importlib.util
from pathlib import Path

BASE_SHA = '38c6879b74bcd3158e6e95b48f08b98015662010f55423c54a5db09d879a49f9'
IMPORT_SHA = 'a460cd843a9f1fd05d6039f2743df44d13289684e938aff1d3c94b0cf08c1228'
SOURCE_PINS = {'v13/runtime.py': 'a533660776f7e2b1697e9793a3abb811eb6d1e7191ec6fe0af523d58efa0ce38', 'v13/dataset_probe_candidate.py': '7a2c5615cf9742f87ae67a6f599d3a8c084866c7a899a95e9e15f42eee939c16', 'v13/source_read_budget_candidate.py': 'a9fdddeb9ff67b5bb733e86bc845508d8d883afed2a035b42fc39ebc0a11526a', 'specs/bootstrap_dataset_catalog_20261109.json': '53c4d35d0b7b9348282b8e5e5877156969e1bcf6f37aa8bd8ee25aa751f1df2b'}


def replace(data, old, new, label):
    if data.count(old) != 1:
        raise ValueError('unexpected dataset integration source: '+label)
    return data.replace(old, new, 1)


def build_sources(code_dir):
    code_dir = Path(code_dir)
    path = code_dir/'scripts/integrated_idle_world_candidate_20261111.py'
    helper = (code_dir/'v13/dataset_idle_import_candidate.py').read_bytes()
    if hashlib.sha256(path.read_bytes()).hexdigest() != BASE_SHA or hashlib.sha256(helper).hexdigest() != IMPORT_SHA:
        raise ValueError('dataset composition source changed')
    for name, expected in SOURCE_PINS.items():
        if hashlib.sha256((code_dir/name).read_bytes()).hexdigest() != expected:
            raise ValueError('dataset frozen dependency changed: '+name)
    spec = importlib.util.spec_from_file_location('verified_idle_composition', path)
    parent = importlib.util.module_from_spec(spec);spec.loader.exec_module(parent)
    result = parent.build_sources(code_dir)

    # Bind the existing transient World scope to the actual coordinator too.
    # A dispatched event alone does not identify the thread that owns it.
    idle = result['v13/world_jepa_idle_runtime_candidate.py']
    old_sha = hashlib.sha256(idle).hexdigest().encode()
    idle = replace(idle,
        b"    if type(event) is not dict or runtime.current != 'sleep' or runtime in OWNERS:\n",
        b"    if (type(event) is not dict or runtime.current != 'sleep' or runtime in OWNERS\n            or threading.current_thread() is not runtime.worker):\n",
        'World scope belongs to actual worker')
    new_sha = hashlib.sha256(idle).hexdigest().encode()
    for name, payload in list(result.items()):
        if old_sha in payload:result[name] = payload.replace(old_sha, new_sha)
    result['v13/world_jepa_idle_runtime_candidate.py'] = idle

    scheduler = result['v13/scheduler.py']
    scheduler = replace(scheduler, b"'learn_world_jepa_idle'}", b"'learn_world_jepa_idle','import_dataset_idle'}", 'scheduler record action')
    result['v13/scheduler.py'] = scheduler
    sleep = result['v13/sleep.py']
    sleep = replace(sleep, b'        idle_world.maybe_post(self.r)\n',
        b'        idle_world.maybe_post(self.r)\n        from . import dataset_idle_import_candidate as dataset_import\n        dataset_import.maybe_post(self.r)\n', 'existing idle tick')
    sleep = replace(sleep, b"        if str(e['action']).startswith('learn_'):return self._learn(e)\n",
        b"        if str(e['action']).startswith('learn_') or e['action']=='import_dataset_idle':return self._learn(e)\n", 'record job dispatch')
    sleep = replace(sleep, b"            else:out=job(self.r,e['action'],e['origin'])\n",
        b"            elif e['action']=='import_dataset_idle':\n                from .dataset_idle_import_candidate import step\n                out=step(self.r,e)\n            else:out=job(self.r,e['action'],e['origin'])\n", 'record consumer')
    result['v13/sleep.py'] = sleep
    operator = result['v13/operator.py']
    anchor = b"        if cmd=='learning' and args and args[0]=='idle':\n"
    operator = replace(operator, anchor,
        b"        if cmd=='dataset':\n            from .dataset_idle_import_candidate import operator\n            return operator(r,args)\n"+anchor, 'explicit dataset choice')
    result.update({'v13/operator.py':operator, 'v13/dataset_idle_import_candidate.py':helper})
    return result
