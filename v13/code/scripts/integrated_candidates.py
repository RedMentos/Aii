"""Reviewed changes integrated into the live runtime, as one ordered chain.

After the SourceHandoff cohort closed (2026-10-12), the merged approval-reader
+ native firing candidate was written into the live sources byte-exactly.
Later reviewed runtime changes to the same files are appended to `_later`.
Candidate regressions stay runnable: a candidate loader accepts live sources
only when they are the exact frozen baseline, its own complete candidate, or
this exact integrated chain. Anything else still fails shut.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIRING_SNAPSHOT = 'docs/proofs/continuation-20261011/native-firing-runtime-baseline'
NAMES = ('v13/runners.py', 'v13/memory_server.py', 'v13/runtime.py', 'v13/store.py')
INTEGRATED = ('approval_reader_runtime_candidate', 'native_firing_runtime_candidate', 'native_cache_bounds', 'schema_order', 'resource_modes')

NATIVE_CACHE_ARGS = '''def native_cache_args(cfg):
    # b10964 defaults (--cache-ram 8192 MiB host prompt cache, 32 context
    # checkpoints per slot) assume a desktop. Qwen3.5 checkpoints are ~19 MiB
    # each (docs/NATIVE_CACHE.md), so a 6 GB phone needs explicit bounds.
    from .config import DEFAULTS
    ram=cfg.get('native_cache_ram_mb',DEFAULTS['native_cache_ram_mb'])
    checkpoints=cfg.get('native_ctx_checkpoints',DEFAULTS['native_ctx_checkpoints'])
    return ['--cache-ram',str(ram),'--ctx-checkpoints',str(checkpoints)]
'''


def _replace(text, old, new):
    if text.count(old) != 1:
        raise ValueError('Integrated anchor changed: '+old[:80])
    return text.replace(old, new, 1)


def native_cache_bounds(sources):
    """2026-10-12 thread G: bound host prompt cache and context checkpoints."""
    out = dict(sources)
    t = out['v13/runners.py']
    t = _replace(t, 'def rotate_log(path,cap=3*1024*1024):', NATIVE_CACHE_ARGS+'def rotate_log(path,cap=3*1024*1024):')
    t = _replace(t, '"-ngl","0","--no-warmup","--no-webui","--log-disable"]\n',
                 '"-ngl","0","--no-warmup","--no-webui","--log-disable"]\n        cmd += native_cache_args(self.cfg)\n')
    out['v13/runners.py'] = t
    return out


WIRE_JSON = '''def wire_json(v):
    """Request body for llama-server. Unlike common.dumps it keeps key order: the server builds the JSON-schema
    grammar in property order, so sorting would make the model decide e.g. `action` before `options` or
    `needs_reentry` before `summary` (WP-W1). Hashes/logs keep using the sorted common.dumps."""
    return json.dumps(v,ensure_ascii=False,separators=(",",":"),allow_nan=False)
'''


def schema_order(sources):
    """2026-10-12 thread H (WP-W1): llama-server request bodies keep schema key order."""
    out = dict(sources)
    t = out['v13/runners.py']
    t = _replace(t, 'from .resources import process_memory\n', 'from .resources import process_memory\n'+WIRE_JSON)
    t = _replace(t, 'conn.request(method,path,dumps(payload)', 'conn.request(method,path,wire_json(payload)')
    t = _replace(t, "conn.request('POST','/completion',dumps(payload|", "conn.request('POST','/completion',wire_json(payload|")
    t = _replace(t, 'conn.request("POST","/completion",dumps(payload)', 'conn.request("POST","/completion",wire_json(payload)')
    out['v13/runners.py'] = t
    return out


def resource_modes(sources):
    """2026-10-12 thread N (§97.2): GREEN/YELLOW/ORANGE/RED resource modes in the turn, replay and telemetry."""
    out = dict(sources)
    t = out['v13/runtime.py']
    t = _replace(t, 'from .resources import snapshot,ResourceGuard,prune_runner_logs\n',
                 'from .resources import snapshot,ResourceGuard,prune_runner_logs\nfrom . import resource_modes as rmodes\n')
    t = _replace(t, '(self.cfg);self.notify=notify or',
                 '(self.cfg);self.guard.load_profile(self.store);self.notify=notify or')
    t = _replace(t, '            check(self.cancel_event,deadline);resource=self.resources();state=self.guard.update(resource)\n',
                 "            check(self.cancel_event,deadline);resource=self.resources();state=self.guard.update(resource)\n            rmode=self.guard.mode;rpol=rmodes.policy(rmode);meta['resource_mode']={'mode':rmode,'reasons':list(self.guard.reasons),'profile':self.guard.profile.get('status')}  # §97.2\n")
    t = _replace(t, "ressure=0. if state=='NORMAL' else 1.,provide",
                 "ressure=rpol['focal_pressure'],provide")
    t = _replace(t, 'lf.cfg,resource,state);version=exec_',
                 'lf.cfg,resource,rmode);version=exec_')
    t = _replace(t, 'deadline=deadline,top_k=top_k)\n',
                 "deadline=deadline,top_k=rmodes.scaled(self.cfg['memory_top_k'] if top_k is None else top_k,rmode,'context_scale'))  # §97.2 YELLOW+: less context\n")
    t = _replace(t, 'agectl.controller(self),state)\n',
                 'agectl.controller(self),rmode)\n')
    t = _replace(t, 'rce_state=state,observer_window_',
                 'rce_state=state,resource_mode=rmode,observer_window_')
    t = _replace(t, "ect and state=='NORMAL' and sel",
                 "ect and rpol['learned_wake'] and sel")
    t = _replace(t, "h'} and state=='NORMAL' and not",
                 "h'} and rpol['max_observer_bodies'] and not")
    t = _replace(t, "effort.roles(wake_route);peers={};observer_seconds=max(1.,self.cfg['observer_seconds']*effort_plan['observer_scale'])",
                 "rmodes.cap_roles(effort.roles(wake_route),rmode);peers={};observer_seconds=max(1.,self.cfg['observer_seconds']*effort_plan['observer_scale'])  # §97.2 ORANGE: one body")
    t = _replace(t, "ressure=0. if state=='NORMAL' else 1.,world_e",
                 "ressure=rpol['focal_pressure'],world_e")
    t = _replace(t, "t() and self.guard.state=='NORMAL':\n",
                 "t() and rmodes.policy(self.guard.mode)['background_observers']:\n")
    t = _replace(t, "            background_roles={'none':[],'detail':['B1_DETAIL'],'gist':['B2_GIST'],'both':['B1_DETAIL','B2_GIST']}[wake_decision['action']] if wake_decision and wake_decision['learned'] else ['B1_DETAIL','B2_GIST']\n",
                 "            background_roles={'none':[],'detail':['B1_DETAIL'],'gist':['B2_GIST'],'both':['B1_DETAIL','B2_GIST']}[wake_decision['action']] if wake_decision and wake_decision['learned'] else ['B1_DETAIL','B2_GIST']\n            background_roles=rmodes.cap_roles(background_roles,self.guard.mode,'background_observers')  # §97.2 YELLOW: one post-commit body\n")
    t = _replace(t, "f.resources())!='NORMAL':break\n",
                 "f.resources())!='NORMAL' or not rmodes.policy(self.guard.mode)['background_observers']:break\n")
    t = _replace(t, "        if not isinstance(count,int) or not 1<=count<=16:raise ValueError('Replay-Anzahl 1..16')\n",
                 "        if not isinstance(count,int) or not 1<=count<=16:raise ValueError('Replay-Anzahl 1..16')\n        self.guard.update(self.resources());count=rmodes.scaled(count,self.guard.mode,'replay_scale')  # §97.2: YELLOW halves, ORANGE/RED none\n        if not count:raise Limits('Replay pausiert wegen RAM-/Temperaturlimit (Modus '+self.guard.mode+')')\n")
    t = _replace(t, "effective_config':dict(self.cfg)}\n",
                 "effective_config':dict(self.cfg),'resource_mode':self.guard.mode}\n")
    out['v13/runtime.py'] = t
    t = out['v13/store.py']
    t = _replace(t, "TELEMETRY_ENUMS.update('OBSERVED_NATIVE_WRITES REQUEST_WRITES_ONLY REQUEST_NOT_FINAL REQUEST_NOT_COMPLETED REQUEST_BINDING_CHANGED AUDIT_LOG_CHANGED AUDIT_LOG_UNREADABLE AUDIT_WINDOW_LIMIT NO_REQUEST_WINDOW MULTIPLE_NATIVE_STEPS NO_PROMPT_MARKER NO_EVALUATED_ROWS MULTIPLE_REQUESTS NO_REQUEST_OBSERVATION AUDIT_BINDING_OR_AUTHORITY_INVALID INVALID_REQUEST_ROW_MAP'.split())\n",
                 "TELEMETRY_ENUMS.update('OBSERVED_NATIVE_WRITES REQUEST_WRITES_ONLY REQUEST_NOT_FINAL REQUEST_NOT_COMPLETED REQUEST_BINDING_CHANGED AUDIT_LOG_CHANGED AUDIT_LOG_UNREADABLE AUDIT_WINDOW_LIMIT NO_REQUEST_WINDOW MULTIPLE_NATIVE_STEPS NO_PROMPT_MARKER NO_EVALUATED_ROWS MULTIPLE_REQUESTS NO_REQUEST_OBSERVATION AUDIT_BINDING_OR_AUTHORITY_INVALID INVALID_REQUEST_ROW_MAP'.split())\nTELEMETRY_FIELDS.update('resource_mode orange_mb yellow_mb'.split())  # §97.2 resource modes\nTELEMETRY_ENUMS.update('GREEN YELLOW ORANGE RED UNCALIBRATED DEVICE_MEASURED HOST_MEASURED_NOT_REDMI MEM_BELOW_RED MEM_BELOW_ORANGE MEM_BELOW_YELLOW TEMP_AT_RED TEMP_AT_ORANGE TEMP_AT_YELLOW'.split())\n")
    out['v13/store.py'] = t
    return out


def _later(sources):
    return resource_modes(schema_order(native_cache_bounds(sources)))


def _baseline(root):
    folder = root/FIRING_SNAPSHOT
    manifest = json.loads((folder/'manifest.json').read_text())
    if manifest.get('schema') != 'NATIVE_FIRING_RUNTIME_BASELINE_V1' or set(manifest['files']) != set(NAMES):
        raise ValueError('Integrated baseline manifest changed')
    original = {}
    for name, expected in manifest['files'].items():
        data = (folder/Path(name).name).read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise ValueError('Integrated baseline digest changed: '+name)
        original[name] = data.decode()
    return original


def _chain(full):
    from scripts import approval_reader_runtime_candidate as reader
    from scripts import native_firing_runtime_candidate as firing
    full = dict(full)
    full.update(reader.transform({k: full[k] for k in reader.NAMES}))
    return _later(firing.transform(full))


def integrated_sources(root=ROOT):
    """Frozen baseline -> approval reader -> native firing -> later changes."""
    return _chain(_baseline(root))


def overlay(original, root=ROOT):
    """Baseline files with the integrated files replaced, if live equals that."""
    expected = integrated_sources(root)
    view = {name: expected.get(name, text) for name, text in original.items()}
    actual = {name: (root/name).read_text() for name in original}
    return view if actual == view else None


def rebase(texts, root=ROOT):
    """Apply the same integrated chain to another candidate's view.

    Files of `texts` outside the integrated set are returned unchanged; the
    remaining integrated files come from the digest-bound baseline.
    """
    full = _baseline(root)
    full.update({k: v for k, v in texts.items() if k in NAMES})
    out = _chain(full)
    return {k: (out[k] if k in NAMES else v) for k, v in texts.items()}


def write_live(root=ROOT):
    """Write the integrated chain to the live files (used once per change)."""
    for name, text in integrated_sources(root).items():
        (root/name).write_text(text)
