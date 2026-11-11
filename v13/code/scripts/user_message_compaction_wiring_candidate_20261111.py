"""Apply explicit USER-message readers to an already-composed review tree.

Does not stage files, change global row factories or patch the frozen sources.
The owning integration builder must separately wire the existing G13 action.
"""
import hashlib
from pathlib import Path

HELPER_SHA = '3208fabfd73daa7ecdf16bf2ff981fcc7ddadb5e71d7e9f6bcfea05846b1c8e6'
RAW_PINS = {
    'v13/body_jepa.py': 'c050037928bc6e4b89fbeddea54fc358e8c418688bdb32e1e32630bc3b2b707c',
    'v13/guards.py': '8740e0e912619e33b23e1322629d01b9c3cca4f69df559d23a4583f15b6f2523',
    'v13/store.py': 'fe66f92533b20738b5ec384e9d7c0b5ac8b4b4f658c6c1ad23792d813ff29980',
    'v13/history.py': '5e3d7023331c08dbad7dbfdfcf3a6a9ea0eb55a3391bd27cc9338d8a1e40d95b',
    'v13/context_source_recall_candidate.py': '56282c1d95610ce3c3266d63f48b78362d0bf32e2a7291b90a3f55e386aa1f64',
    'v13/agi/weights.py': '6e17a419638d357499a8140d64e6d0d6d1a48fcac42d5033664cfd986257da6e',
    'v13/drift.py': 'c638a7dfa08cfbd2dfd142d37e0c1fdc955069a864aab9d75105057464f541fb',
    'v13/duplex.py': '6fb144766c601ca77acd5757d7812e7af24db2363be70a7aa524efefbf0f361c',
    'v13/memory.py': '391668fff0b4ad3d7c36d5d7a9823055ff74821c10f71b945e87edaa62597484',
}


def _hash(value):
    return hashlib.sha256(value).hexdigest()


def _replace(raw, old, new, name):
    if raw.count(old) != 1:
        raise ValueError('unexpected user-message compaction source: ' + name)
    return raw.replace(old, new, 1)


def apply_sources(code_dir, replacements):
    root = Path(code_dir)
    result = dict(replacements)
    original = dict(replacements)
    def source(name):
        if name in result:
            if type(result[name]) is not bytes:
                raise ValueError('non-byte composed user-reader source')
            return result[name]
        path = root / name
        if path.is_symlink():
            raise ValueError('symlink user-reader input')
        raw = path.read_bytes()
        if _hash(raw) != RAW_PINS[name]:
            raise ValueError('user-message raw fallback changed: ' + name)
        original[name] = raw;result[name] = raw
        return raw
    path = root / 'v13/user_message_compaction_candidate.py'
    if path.is_symlink():
        raise ValueError('symlink message-compaction helper')
    helper = path.read_bytes()
    if _hash(helper) != HELPER_SHA:
        raise ValueError('user-message compaction helper changed')
    original['v13/user_message_compaction_candidate.py'] = helper

    store = source('v13/store.py')
    anchor = b'    def history(self,session,limit=100):return self.rows("SELECT * FROM (SELECT * FROM messages WHERE session_id=? ORDER BY id DESC LIMIT ?) ORDER BY id",(session,limit))\n'
    result['v13/store.py'] = _replace(store, anchor,
        b'    def history(self,session,limit=100):\n        from .user_message_compaction_candidate import hydrate_rows\n        return hydrate_rows(self,self.rows("SELECT * FROM (SELECT * FROM messages WHERE session_id=? ORDER BY id DESC LIMIT ?) ORDER BY id",(session,limit)))\n', 'Store.history')
    helper = _replace(helper, ("STORE_SHA256 = '" + RAW_PINS['v13/store.py'] + "'").encode(),
                      ("STORE_SHA256 = '" + _hash(result['v13/store.py']) + "'").encode(), 'helper Store pin')
    result['v13/user_message_compaction_candidate.py'] = helper

    history = source('v13/history.py')
    result['v13/history.py'] = _replace(history, b'    groups={}\n',
        b'    if after_id is not None:\n        from .user_message_compaction_candidate import hydrate_rows\n        records=hydrate_rows(store,records)\n    groups={}\n', 'native history forward page; tail already hydrated by Store.history')

    context = source('v13/context_source_recall_candidate.py')
    context = _replace(context, b'from .store import Store\n',
        b'from .store import Store\nfrom . import user_message_compaction_candidate as message_compaction\n', 'recall import')
    context = _replace(context, b"        if row['event_id'] in excluded:\n            continue\n",
        b"        if row['event_id'] in excluded:\n            continue\n        try:row['prefix']=message_compaction.search_prefix(store,row['id'],row['prefix'],budget=budget)\n        except message_compaction.CompactionError:continue\n", 'recall search-only prefix')
    result['v13/context_source_recall_candidate.py'] = context

    weights = source('v13/agi/weights.py')
    weights = _replace(weights, b'from ..common import digest,dumps,atomic_write,uid\n',
        b'from ..common import digest,dumps,atomic_write,uid\nfrom .. import user_message_compaction_candidate as message_compaction\n', 'AG6 reader import')
    weights = _replace(weights,
        b'''            q=self.s.one("SELECT text,metadata FROM messages WHERE event_id=? AND session_id=? AND role='user' ORDER BY id LIMIT 1",\n                         (r['event_id'],ev['session_id']))\n''',
        b"            q=message_compaction.user_event(self.s,r['event_id'],ev['session_id'])\n", 'AG6 rated user prompt')
    result['v13/agi/weights.py'] = weights

    for name, old, new in (
        ('v13/drift.py',
         b'''            q=self.s.one("SELECT text FROM messages WHERE event_id=? AND role='user' ORDER BY id LIMIT 1",(r['event_id'],))\n''',
         b"            from .user_message_compaction_candidate import user_event\n            q=user_event(self.s,r['event_id'])\n"),
        ('v13/duplex.py',
         b'''    q=s.one("SELECT text FROM messages WHERE event_id=? AND role='user' ORDER BY id LIMIT 1",(h['from_event'],))\n''',
         b"    from .user_message_compaction_candidate import user_event\n    q=user_event(s,h['from_event'])\n")):
        result[name] = _replace(source(name), old, new, name + ' user projection')

    guards = source('v13/guards.py')
    guards = _replace(guards, b'SELECT u.text AS q,a.text AS a,a.metadata AS m FROM messages',
        b'SELECT u.event_id AS user_event,u.session_id AS user_session,u.text AS q,a.text AS a,a.metadata AS m FROM messages', 'collapse pair owner')
    guards = _replace(guards, b"        if meta.get('model_generated'):out.append((r['q'],r['a']))\n",
        b"        if meta.get('model_generated'):\n            from .user_message_compaction_candidate import user_event\n            query=user_event(store,r['user_event'],r['user_session'])\n            if query is not None:out.append((query['text'],r['a']))\n", 'collapse user text')
    result['v13/guards.py'] = guards

    # Real compacted prompts can be much longer than earlier tiny fixtures.
    # Both local JEPA views must honor the configured training token window.
    body = source('v13/body_jepa.py')
    old = b'''    def _views(self,tok,items):
        ctx=[self._encode(tok,i['prompt'])[0] for i in items]
        tgt=[tok(str(i['target']),add_special_tokens=False)['input_ids'] for i in items]
        return ctx,tgt
'''
    new = b'''    def _views(self,tok,items):
        n=self.cfg['max_tokens']
        ctx=[self._encode(tok,i['prompt'])[0][-n:] for i in items]
        tgt=[tok(str(i['target']),add_special_tokens=False)['input_ids'][-n:] for i in items]
        return ctx,tgt
'''
    result['v13/body_jepa.py'] = _replace(body, old, new, 'bounded Body context and target views')
    result['v13/body_jepa.py'] = _replace(result['v13/body_jepa.py'],
        b"checkpoint_source=digest(dumps({'master_sha256':self.master_sha,",
        b"checkpoint_source=digest(dumps({'view_policy':'TAIL_MAX_TOKENS_V1','master_sha256':self.master_sha,",
        'Body checkpoint view-policy revision')
    result['v13/body_jepa.py'] = _replace(result['v13/body_jepa.py'],
        b"'checkpoint_resume_enabled':checkpoint_dir is not None",
        b"'view_token_policy':'TAIL_MAX_TOKENS_V1','checkpoint_resume_enabled':checkpoint_dir is not None",
        'Body view-policy telemetry')

    # Experience/export already use the Event SourceRef for their USER input;
    # only Assistant/Teacher lanes consume messages.text. Bind this invariant.
    memory = source('v13/memory.py')
    if (memory.count(b"env=json.loads(e['packet']);source_ref=env['source_ref'];input_text=self.s.read_source(source_ref)") != 1
            or memory.count(b"if row['role'] not in {'assistant','teacher'}:continue") != 1):
        raise ValueError('Memory.experience/export no longer source-backed')

    # Retarget explicit source pins transitively (Store -> semantic helper ->
    # error preview, archive readers, World guards, etc.). Each pass only
    # propagates the previous pass's exact byte-hash changes; reject cycles.
    changes = {_hash(original[name]): _hash(raw) for name, raw in result.items()
               if name in original and raw != original[name]}
    for _ in range(4 * len(result) + 4):
        if not changes:
            break
        upcoming = {}
        for name, raw in list(result.items()):
            revised = raw
            for old, new in changes.items():
                revised = revised.replace(old.encode(), new.encode())
            if revised != raw:
                result[name] = revised;upcoming[_hash(raw)] = _hash(revised)
        changes = upcoming
    else:
        raise ValueError('cyclic user-message reader source pins')
    for name, raw in result.items():
        if name.endswith('.py'):
            compile(raw, name, 'exec')
    return result
