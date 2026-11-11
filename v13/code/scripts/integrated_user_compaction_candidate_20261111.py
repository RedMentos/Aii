"""Compose explicit USER-text hydration with the actual bounded idle workers."""
import hashlib
import importlib.util
from pathlib import Path

BASE_SHA = '8d18f9fcde0eac79442dceb16544e747b6baa4e7edc07436ef131b889d288282'
WIRING_SHA = '622ef73418fe0698b549df95564458ecd8a357e03365c2c27cb197690bb27069'


def module(path, name, expected):
    if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise ValueError('user-compaction composition input changed: '+name)
    spec = importlib.util.spec_from_file_location(name, path)
    loaded = importlib.util.module_from_spec(spec);spec.loader.exec_module(loaded)
    return loaded


def replace(data, old, new, label):
    if data.count(old) != 1:
        raise ValueError('unexpected compaction scheduler source: '+label)
    return data.replace(old, new, 1)


def build_sources(code_dir):
    code_dir = Path(code_dir)
    parent = module(code_dir/'scripts/integrated_dataset_idle_candidate_20261111.py', 'verified_dataset_composition', BASE_SHA)
    wiring = module(code_dir/'scripts/user_message_compaction_wiring_candidate_20261111.py', 'verified_user_compaction_wiring', WIRING_SHA)
    result = wiring.apply_sources(code_dir, parent.build_sources(code_dir))
    result['v13/scheduler.py'] = replace(result['v13/scheduler.py'],
        b"'import_dataset_idle'}", b"'import_dataset_idle','compact_user_messages'}", 'accepted action')
    sleep = result['v13/sleep.py']
    sleep = replace(sleep, b'        dataset_import.maybe_post(self.r)\n',
        b'        dataset_import.maybe_post(self.r)\n        from . import user_message_compaction_candidate as compact_users\n        compact_users.maybe_post(self.r)\n', 'existing idle tick')
    sleep = replace(sleep,
        b" or e['action']=='import_dataset_idle':return self._learn(e)\n",
        b" or e['action'] in {'import_dataset_idle','compact_user_messages'}:return self._learn(e)\n", 'actual worker dispatch')
    anchor = b"            elif e['action']=='import_dataset_idle':\n"
    sleep = replace(sleep, anchor,
        b"            elif e['action']=='compact_user_messages':\n                from .user_message_compaction_candidate import step\n                out=step(self.r,e)\n"+anchor, 'bounded compaction job')
    result['v13/sleep.py'] = sleep
    operator = result['v13/operator.py']
    anchor = b"        if cmd=='archive':\n"
    result['v13/operator.py'] = replace(operator, anchor,
        b"        if cmd=='archive' and args and args[0]=='compact':\n            from .user_message_compaction_candidate import operator\n            return operator(r,args[1:])\n"+anchor, 'explicit storage choice')
    return result
