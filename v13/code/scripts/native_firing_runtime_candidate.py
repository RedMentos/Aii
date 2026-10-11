"""Isolated WP-T9 diagnostic candidate. Never grants Exact omission or learning.

The four live runtime modules remain unchanged until the frozen native cohort
finishes. Source snapshots are hash-bound and the resulting patch is reviewable.
"""
import argparse
import difflib
import hashlib
import json
from pathlib import Path
import types

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = 'docs/proofs/continuation-20261011/native-firing-runtime-baseline'
NAMES = ('v13/runners.py', 'v13/memory_server.py', 'v13/runtime.py', 'v13/store.py')


RUNNER_METHODS = '''    def _audit_begin_window(self,multiple_steps=False):
        self._audit_window=None
        if not self._audit_enabled:return
        reason='MULTIPLE_NATIVE_STEPS' if multiple_steps else 'NO_MATCHING_LOADED_BINDING'
        self._audit_unavailable=reason
        binding=self.memory_delivery_binding
        if multiple_steps or not binding:return
        try:
            self.log_handle.flush();stat=os.fstat(self.log_handle.fileno())
            self._audit_window={'path':self.home/'logs'/(self.role+'.log'),
                'offset':stat.st_size,'identity':(stat.st_dev,stat.st_ino),
                'pid':self.proc.pid,'binding':binding}
            self._audit_unavailable=None
        except (OSError,ValueError,AttributeError):self._audit_unavailable='AUDIT_LOG_UNREADABLE'
    def _audit_finish_window(self,status):
        if not self._audit_enabled:return None
        base={'status':'UNAVAILABLE','exact_retained':True,'quality_proven':False,
              'activation_authorized':False,'semantic_truth_authority':False}
        window=self._audit_window
        if status!='FINAL':return dict(base,reason='REQUEST_NOT_FINAL',request_status=status)
        if not window:return dict(base,reason=self._audit_unavailable or 'NO_REQUEST_WINDOW')
        if not self._audit_completed:return dict(base,reason='REQUEST_NOT_COMPLETED')
        if (self.proc is None or self.proc.poll() is not None or self.proc.pid!=window['pid']
                or self.memory_delivery_binding!=window['binding']):
            return dict(base,reason='REQUEST_BINDING_CHANGED')
        try:
            stat=window['path'].stat()
            if (stat.st_dev,stat.st_ino)!=window['identity'] or stat.st_size<window['offset']:
                return dict(base,reason='AUDIT_LOG_CHANGED')
            from .sparse_audit import read_firing_window
            observed=read_firing_window(window['path'],window['offset'])
        except OSError:return dict(base,reason='AUDIT_LOG_UNREADABLE')
        if self.memory_delivery_binding!=window['binding']:
            return dict(base,reason='REQUEST_BINDING_CHANGED')
        return dict(observed,request_status=status,loaded_binding=window['binding'],
                    semantic_truth_authority=False)
'''

DELIVERY_METHOD = '''def observed_shadow_delivery(store,home,role,model_path,loaded_binding,memories,audit):
    """Map actual writes only to currently approved ordinary facts, still SHADOW.

    The ordinary inventory/source checks remain required. A write measures an
    execution event, never semantic truth, useful recall or permission to omit.
    """
    from .sparse_memory import native_items_path
    result=shadow_delivery(store,home,role,model_path,loaded_binding,memories)
    result.update(observed_memory_ids=[],observed_provenance=[],quality_proven=False,
                  activation_authorized=False,semantic_truth_authority=False)
    def reject(reason):
        result['firing_reason']=reason
        return result
    if result['reason']!='INVENTORY_ONLY':return reject('NO_MATCHING_LOADED_BINDING')
    if not isinstance(audit,dict) or audit.get('status')!='OBSERVED_NATIVE_WRITES':
        return reject(audit.get('reason','NO_REQUEST_OBSERVATION') if isinstance(audit,dict) else 'NO_REQUEST_OBSERVATION')
    if (audit.get('request_status')!='FINAL' or audit.get('loaded_binding')!=loaded_binding
            or audit.get('exact_retained') is not True or audit.get('quality_proven') is not False
            or audit.get('activation_authorized') is not False or audit.get('semantic_truth_authority') is not False):
        return reject('AUDIT_BINDING_OR_AUTHORITY_INVALID')
    import struct
    try:
        metadata=json.loads(native_items_path(loaded_binding['path']).read_text())
        raw=Path(loaded_binding['path']).read_bytes()
        layer=struct.unpack_from('<i',raw,8)[0]
        n=len(metadata['rows']);counts=audit['slot_applied_counts'];blocked=audit['slot_guard_blocked_counts']
        if (type(audit.get('request')) is not int or audit['request']<1
                or type(audit.get('layer')) is not int or audit['layer']!=layer
                or type(audit.get('evaluated_rows')) is not int or audit['evaluated_rows']<1
                or type(audit.get('batches')) is not int or audit['batches']<1
                or not isinstance(counts,list) or not isinstance(blocked,list)
                or len(counts)!=n or len(blocked)!=n
                or any(type(v) is not int or not 0<=v<=audit['evaluated_rows'] for v in counts+blocked)
                or any(a+b>audit['evaluated_rows'] for a,b in zip(counts,blocked))
                or audit.get('fired_rows')!=[r for r,v in enumerate(counts) if v]):
            raise ValueError('Native request/slot dimensions')
    except (OSError,ValueError,KeyError,TypeError,struct.error):return reject('INVALID_REQUEST_ROW_MAP')
    fired=set(audit['fired_rows'])
    for mid,ref in zip(result['candidates'],result['provenance']):
        if any(r in fired and mapped==mid for r,mapped in enumerate(metadata['rows'])):
            result['observed_memory_ids'].append(mid);result['observed_provenance'].append(dict(ref))
    # Recheck after reading/mapping; concurrent forget/reapproval or changed
    # source bytes cannot turn the earlier valid inventory into stale evidence.
    final=shadow_delivery(store,home,role,model_path,loaded_binding,memories)
    if (final['reason']!='INVENTORY_ONLY' or final['candidates']!=result['candidates']
            or final['provenance']!=result['provenance']):
        result['observed_memory_ids']=[];result['observed_provenance']=[]
        return reject('REQUEST_BINDING_CHANGED')
    result.update(firing='OBSERVED_NATIVE_WRITES',firing_reason='REQUEST_WRITES_ONLY',
                  native_request=audit['request'],evaluated_rows=audit['evaluated_rows'],
                  slot_applied_counts=list(counts),slot_guard_blocked_counts=list(blocked))
    return result

'''


def replace(text, old, new):
    if text.count(old) != 1:
        raise ValueError('Candidate anchor changed: '+old[:80])
    return text.replace(old, new, 1)


def transform(original):
    changed = dict(original)
    name = 'v13/runners.py'
    t = changed[name]
    t = replace(t, '        self.binary=os.environ.get("V13_LLAMA_SERVER",str(home/"bin/llama-server"))\n',
        '        self.binary=os.environ.get("V13_LLAMA_SERVER",str(home/"bin/llama-server"))\n'
        '        self._audit_enabled=False;self._audit_window=None;self._audit_unavailable=None;self._audit_lock=threading.Lock()\n')
    t = replace(t, '        return tuple(stamp(p) for p in paths)',
        "        return (('native_memory_audit',self.cfg.get('native_memory_audit',False) is True),)+tuple(stamp(p) for p in paths)")
    t = replace(t, '    def embed(self,texts,cancel,deadline):', RUNNER_METHODS+'    def embed(self,texts,cancel,deadline):')
    t = replace(t, '        self._loaded_binary=cmd[0];launch_stamp=self._lifecycle_stamp()',
        "        env.pop('V13_MEMORY_AUDIT',None)\n"
        "        self._audit_enabled=self.purpose=='generate' and bool(self.memory) and self.cfg.get('native_memory_audit',False) is True\n"
        "        if self._audit_enabled:env['V13_MEMORY_AUDIT']='1'\n"
        '        self._loaded_binary=cmd[0];launch_stamp=self._lifecycle_stamp()')
    t = replace(t, '        # Measure cold load, prefill and streaming, including failed/cancelled calls.',
        "        audit_requested=self.cfg.get('native_memory_audit',False) is True\n"
        "        audit_locked=False\n"
        "        if audit_requested:\n"
        "            audit_locked=self._audit_lock.acquire(blocking=False)\n"
        "            if not audit_locked:raise Unavailable('Concurrent native audit request')\n"
        "        self._audit_window=None;self._audit_unavailable=None;self._audit_completed=False\n"
        '        # Measure cold load, prefill and streaming, including failed/cancelled calls.')
    t = replace(t, "            if status!='FINAL':self.last_metrics['interruption_unload']=self.unload()",
        "            if audit_locked:\n"
        "                try:\n"
        "                    observed=self._audit_finish_window(status)\n"
        "                    if observed is not None:self.last_metrics['native_memory_firing']=observed\n"
        "                finally:self._audit_lock.release()\n"
        "            if status!='FINAL':self.last_metrics['interruption_unload']=self.unload()")
    t = replace(t, '        first_step=None;first_tokens=0',
        '        self._audit_begin_window(multiple_steps=bool(first_token_bias))\n        first_step=None;first_tokens=0')
    t = replace(t, '                if data.get("stop"):break',
        '                if data.get("stop"):\n'
        '                    if self._audit_enabled:self._audit_completed=True\n'
        '                    break')
    changed[name] = t
    name = 'v13/memory_server.py'
    changed[name] = replace(changed[name], 'def main():', DELIVERY_METHOD+'def main():')
    name = 'v13/runtime.py'
    changed[name] = replace(changed[name],
        '                        delivery=shadow_delivery(self.store,self.home,runner.role,runner.model,loaded,memories)',
        "                        audit=runner.last_metrics.get('native_memory_firing')\n"
        "                        if audit is not None:\n"
        "                            from .memory_server import observed_shadow_delivery\n"
        "                            delivery=observed_shadow_delivery(self.store,self.home,runner.role,runner.model,loaded,memories,audit)\n"
        "                        else:delivery=shadow_delivery(self.store,self.home,runner.role,runner.model,loaded,memories)")
    name = 'v13/store.py'
    changed[name] = replace(changed[name], 'def telemetry_metrics(value):',
        "TELEMETRY_FIELDS.update('native_memory_firing request_status loaded_binding quality_proven activation_authorized layer evaluated_rows batches slot_applied_counts slot_guard_blocked_counts fired_rows observed_memory_ids observed_provenance firing_reason native_request'.split())\n"
        "TELEMETRY_ENUMS.update('OBSERVED_NATIVE_WRITES REQUEST_WRITES_ONLY REQUEST_NOT_FINAL REQUEST_NOT_COMPLETED REQUEST_BINDING_CHANGED AUDIT_LOG_CHANGED AUDIT_LOG_UNREADABLE AUDIT_WINDOW_LIMIT NO_REQUEST_WINDOW MULTIPLE_NATIVE_STEPS NO_PROMPT_MARKER NO_EVALUATED_ROWS MULTIPLE_REQUESTS NO_REQUEST_OBSERVATION AUDIT_BINDING_OR_AUTHORITY_INVALID INVALID_REQUEST_ROW_MAP'.split())\n\n"
        'def telemetry_metrics(value):')
    return changed


def sources(root=ROOT):
    folder = root/SNAPSHOT
    manifest = json.loads((folder/'manifest.json').read_text())
    if manifest.get('schema')!='NATIVE_FIRING_RUNTIME_BASELINE_V1' or set(manifest['files'])!=set(NAMES):
        raise ValueError('Candidate baseline manifest changed')
    original = {}
    for name, expected in manifest['files'].items():
        data = (folder/Path(name).name).read_bytes()
        if hashlib.sha256(data).hexdigest()!=expected:
            raise ValueError('Candidate baseline digest changed: '+name)
        original[name] = data.decode()
    changed = transform(original)
    actual = {name:(root/name).read_text() for name in NAMES}
    if actual!=original and actual!=changed:
        raise ValueError('Live sources differ from complete baseline/candidate')
    return original, changed


def load_candidate(name, root=ROOT):
    _, changed = sources(root)
    module = types.ModuleType('v13._native_firing_candidate_'+name)
    module.__package__ = 'v13'
    module.__file__ = str(root/('v13/'+name+'.py'))
    exec(compile(changed['v13/'+name+'.py'],module.__file__,'exec'),module.__dict__)
    return module


def patch_text(root=ROOT):
    original, changed = sources(root)
    return ''.join(''.join(difflib.unified_diff(original[name].splitlines(True),changed[name].splitlines(True),
        fromfile='a/'+name,tofile='b/'+name)) for name in NAMES)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();args.out.write_text(patch_text());print(args.out)
