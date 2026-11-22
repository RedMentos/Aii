"""Source-bound RECORD_ONLY candidate for the staged control heads.

The frozen runtime remains unchanged. This is a narrow guard for the listed
controllers, not a complete inventory of all adaptive state in V13.
"""
import hashlib
from pathlib import Path


PINS = {
    'v13/runtime.py': {
        # Exact current source SHA for the fair-budget runtime input. The
        # recovery composer validates its pinned overlay chain separately.
        '08c1ef961b0c7316da8c1c8265feb71a7a4acf009018788e7accb81eecb2337d',
        'c23a5a133deaff66f6be560509580b83394064bbff5a72d35d47c14461536978',
        'd3fac6289d2898806d0126a462b8224b1f945fdf0bd87b7cc5715206974334c2',
    },
    'v13/fastforward.py': {'0cc1b4b3002e0e4c400d7889a746fb42055a708ff1a12be81a59ab10d39bad05'},
    'v13/jefbridge.py': {'875000521db3d7a8efe0186d202dbea99fa7ca47c6b4b2c27f83b7231cb2c5ff'},
    'v13/actionlearn.py': {'eff43a5f6590130b478d5c288debaa548b01ac1133d4b46ba500ec63beee546e'},
    'v13/attention.py': {'0d3c0d00492d809c818874cf83ddd723867e77cfc5c50236dac18eddc8422739'},
    'v13/deliberation.py': {'5c0ed4f22cc7c9966867ade83bae0481e1f049cbbde74b684241aad742edc45c'},
    'v13/callosum.py': {'de55ba637b9e0c0fe6ea12f74385b0f9f782735cc2f52098f5b227a52902d5fc'},
    'v13/workspace_learn.py': {'b6e3d2149fe7b7cc461c0edadd1a95b65b99b0d14e39da29206f7343fea74524'},
}

GATE_SOURCE = b'''"""Runtime-bound control-head update permission; unknown mode fails closed."""

def bind(store, provider):
    if not callable(provider):
        raise TypeError('learning mode provider must be callable')
    store._v13_learning_config = provider

def current_mode(store):
    try:
        provider = getattr(store, '_v13_learning_config', None)
        cfg = provider() if callable(provider) else None
        return cfg.get('learning_mode') if isinstance(cfg, dict) else None
    except Exception:
        return None

def updates_allowed(store):
    return current_mode(store) in ('SHADOW_UPDATE', 'APPROVED_COMMIT')

def blocked_status(store):
    return 'SKIPPED_RECORD_ONLY' if current_mode(store) == 'RECORD_ONLY' else 'SKIPPED_INVALID_LEARNING_MODE'
'''


def _replace(raw, before, after, label):
    if raw.count(before) != 1:
        raise ValueError('controller guard anchor changed: ' + label)
    return raw.replace(before, after, 1)


def apply_sources(code_dir, sources):
    code_dir = Path(code_dir)
    result = dict(sources)
    checked = {}
    for name, allowed in PINS.items():
        path = code_dir / name
        if path.is_symlink() or not path.is_file():
            raise ValueError('controller guard source missing or unsafe: ' + name)
        source_raw = path.read_bytes()
        # Runtime is already transformed by the pinned upstream recovery,
        # arithmetic and observer composers when this guard is applied. Pin
        # the immutable on-disk source here; the caller's exact builder pins
        # authenticate the composed bytes, and the anchors below validate
        # that the guard can still be applied to that composition.
        raw = result.get(name)
        if name == 'v13/runtime.py':
            if hashlib.sha256(source_raw).hexdigest() not in allowed:
                raise ValueError('controller guard source changed: ' + name)
            if raw is None:
                raw = source_raw
        else:
            if raw is None:
                raw = source_raw
            if hashlib.sha256(raw).hexdigest() not in allowed:
                raise ValueError('controller guard source changed: ' + name)
        checked[name] = raw

    runtime = checked['v13/runtime.py']
    runtime = _replace(runtime, b'from .store import Store\n',
        b'from .store import Store\nfrom .record_only_gate import bind as bind_learning_gate\n', 'runtime import')
    runtime = _replace(runtime,
        b'        self.store.ensure_generation_snapshot(self.cfg,self.revisions())\n',
        b'        bind_learning_gate(self.store,lambda:self.cfg)\n'
        b'        self.store.ensure_generation_snapshot(self.cfg,self.revisions())\n', 'runtime binding')
    runtime = _replace(runtime,
        b"reflexctl.controller(self).timeout_check(eid,deadline-time.monotonic(),meta['fast_forward']['duration_s'])",
        b"reflexctl.controller(self).timeout_check(eid,deadline-time.monotonic(),meta['fast_forward']['duration_s'] if ffc.report()['mode']=='ACTIVE' and self.cfg.get('learning_mode') in ('RECORD_ONLY','SHADOW_UPDATE','APPROVED_COMMIT') else None)",
        'shadow forecast authority')
    checked['v13/runtime.py'] = runtime

    for name in tuple(checked):
        if name == 'v13/runtime.py':
            continue
        checked[name] = _replace(checked[name], b'from .common import dumps\n',
            b'from .common import dumps\nfrom .record_only_gate import updates_allowed,blocked_status\n', name + ' import')

    name = 'v13/fastforward.py'
    raw = checked[name]
    raw = _replace(raw,
        b'        y={\'log_duration\':math.log(max(.01,duration_s)),',
        b"        if not updates_allowed(self.s):\n            return {'predicted':self.predict(x),'surprise':0.,'errors':{},'status':blocked_status(self.s)}\n"
        b'        y={\'log_duration\':math.log(max(.01,duration_s)),', 'fastforward learn')
    raw = _replace(raw, b'        st,_=self._load();buf=st.get(\'replay\',[])\n',
        b"        if not updates_allowed(self.s):return {'status':blocked_status(self.s),'samples':0}\n"
        b'        st,_=self._load();buf=st.get(\'replay\',[])\n', 'fastforward consolidate')
    raw = _replace(raw,
        b'        def fn(st):\n            p=st[\'procs\'].setdefault(key,',
        b"        if not updates_allowed(self.s):return 'RECORD_ONLY'\n"
        b'        def fn(st):\n            p=st[\'procs\'].setdefault(key,', 'fastforward procedure')
    checked[name] = raw

    name = 'v13/jefbridge.py'
    raw = checked[name]
    raw = _replace(raw,
        b"            st['turns']=(st['turns']+",
        b"            previous=[turn for turn in st['turns'] if turn['event_id']!=eid]\n"
        b"            st['turns']=(previous+", 'jef most recent observation')
    raw = _replace(raw, b'        learned,preds=self._mutate(fn)\n', b'''        if updates_allowed(self.s):
            learned,preds=self._mutate(fn)
        else:
            st,_=self._load()
            preds={r['id']:self.predict(r['x'],st) for r in rows}
            inc=[r for r in rows if preds[r['id']]>=.5 and not r['reentry']]
            hi_unc=any(r['x'][4] or r['x'][5] for r in rows)
            if not inc:learned='QUERY_'+('A' if any(r['role']=='B1_DETAIL' for r in rows) else 'B') if hi_unc and rows else 'IGNORE'
            else:
                rs={r['role'] for r in inc};learned={'B1_DETAIL':'INCORPORATE_A','B2_GIST':'INCORPORATE_B'}.get(next(iter(rs)) if len(rs)==1 else '','INCORPORATE_AB')
            # Keep the bounded observation record for later explicit learning;
            # no weights, online means, or learned controller state change.
            def record_only(st):
                previous=[turn for turn in st['turns'] if turn['event_id']!=eid]
                st['turns']=(previous+[{'event_id':eid,'rows':[{k:r[k] for k in ('id','role','x','selected')} for r in rows],'queries':queries or {},'trigger':trig}])[-TURNS_KEEP:]
                kept={t['event_id'] for t in st['turns']}
                st['outcome_receipts']=[x for x in st.get('outcome_receipts',[]) if x['event_id'] in kept]
            self._mutate(record_only)
''', 'jef turn')
    raw = _replace(raw, b"        if rows:self._touch('offer',eid);self._signal('offer',eid,'internal_crosscheck',task_success=clip(useful/len(rows)))\n        if any(r['reentry'] for r in rows):self._touch('query',eid)\n        if queries:self._touch('bridge',eid)\n",
        b"        if updates_allowed(self.s):\n            if rows:self._touch('offer',eid);self._signal('offer',eid,'internal_crosscheck',task_success=clip(useful/len(rows)))\n            if any(r['reentry'] for r in rows):self._touch('query',eid)\n            if queries:self._touch('bridge',eid)\n", 'jef modulation')
    raw = _replace(raw, b"        u=clip(utility);sc=step(self.n,PATHS['offer'])\n",
        b"        if not updates_allowed(self.s):return {'updated_offers':0,'status':blocked_status(self.s)}\n"
        b"        u=clip(utility);sc=step(self.n,PATHS['offer'])\n", 'jef feedback')
    checked[name] = raw

    name = 'v13/actionlearn.py'
    raw = checked[name]
    raw = _replace(raw, b"        sc=step(self.n,'c5_action_selection')  # WP-U6 \xc2\xa712.7\n",
        b"        if not updates_allowed(self.s):return {'n':0,'mods':{},'status':blocked_status(self.s)}\n"
        b"        sc=step(self.n,'c5_action_selection')  # WP-U6 \xc2\xa712.7\n", 'c5 learn')
    checked[name] = raw

    name = 'v13/attention.py'
    raw = checked[name]
    raw = _replace(raw, b"        key=req['reason']+'|'+req['target'];sc=step(self.n,PATH)  # WP-U6 \xc2\xa712.7\n",
        b"        key=req['reason']+'|'+req['target']\n"
        b"        if not updates_allowed(self.s):return {'key':key,'n':0,'mean':0.,'status':blocked_status(self.s)}\n"
        b"        sc=step(self.n,PATH)  # WP-U6 \xc2\xa712.7\n", 'attention outcome')
    checked[name] = raw

    name = 'v13/deliberation.py'
    raw = checked[name]
    raw = _replace(raw, b'        k=tkey(trigger);sc=step(self.n,PATH)  # WP-U6 \xc2\xa712.7\n',
        b'        if not updates_allowed(self.s):return None\n'
        b'        k=tkey(trigger);sc=step(self.n,PATH)  # WP-U6 \xc2\xa712.7\n', 'deliberation record')
    raw = _replace(raw, b'        u=max(0.,min(1.,float(utility)));sc=step(self.n,PATH)\n',
        b"        if not updates_allowed(self.s):return {'updated_modes':0,'status':blocked_status(self.s)}\n"
        b'        u=max(0.,min(1.,float(utility)));sc=step(self.n,PATH)\n', 'deliberation feedback')
    checked[name] = raw

    name = 'v13/callosum.py'
    raw = checked[name]
    raw = _replace(raw, b"        st,_=self._load();msgs=st['pending'].get(event_id) or []\n",
        b"        if not updates_allowed(self.s):return {'scored':0,'status':blocked_status(self.s)}\n"
        b"        st,_=self._load();msgs=st['pending'].get(event_id) or []\n", 'callosum outcome')
    raw = _replace(raw, b'        u=max(0.,min(1.,float(utility)));sc=step(self.n,PATH)\n',
        b"        if not updates_allowed(self.s):return {'updated':0,'status':blocked_status(self.s)}\n"
        b'        u=max(0.,min(1.,float(utility)));sc=step(self.n,PATH)\n', 'callosum feedback')
    checked[name] = raw

    name = 'v13/workspace_learn.py'
    raw = checked[name]
    before = b'''    for x in active+rest:
        q=_kind(st,x['source_kind']);on=x['state_type']=='ACTIVE'
        if x.get('turns_retained',0)>=1:
            q['n_retained']+=1;q['used']+=int(on);q['v_refresh']=round(q['v_refresh']+RATE*((1. if on else 0.)-q['v_refresh']),6)
        elif on:
            hit=x['payload_ref'] in dropped
            q['n_fresh']+=1;q['restored']+=int(hit);q['r_restore']=round(q['r_restore']+RATE*((1. if hit else 0.)-q['r_restore']),6)
'''
    after = b'    if updates_allowed(store):\n' + b''.join(b'    '+line for line in before.splitlines(keepends=True))
    checked[name] = _replace(raw, before, after, 'workspace adaptive values')

    # Rebind the exact composed semantic modules to the guarded ActionLearn
    # output. Their verification still rejects other input changes.
    semantic_name = 'v13/world_semantic_evidence_candidate.py'
    local_name = 'v13/local_error_route_shadow_candidate.py'
    semantic_pin = '609c9d187e11551663aea238bf07af962f8458582139bd9707c89b6f347dd8f3'
    local_pin = '36de730d7eab40681740c1165ea0510c2412ea1180bc7f6dd7120a6cf894c471'
    action_pin = '86f79e8f3c26928f0a16399070f1b8d729760697a3b9e02ea9f6315ab6fcf87a'
    for name, expected in ((semantic_name, semantic_pin), (local_name, local_pin)):
        actual = hashlib.sha256(result[name]).hexdigest()
        if actual != expected:
            raise ValueError('semantic dependency changed: ' + name + ' expected=' + expected + ' actual=' + actual)
    if hashlib.sha256(checked['v13/actionlearn.py']).hexdigest() != action_pin:
        raise ValueError('guarded ActionLearn output changed')
    old_action_pin, = PINS['v13/actionlearn.py']
    semantic = _replace(result[semantic_name], old_action_pin.encode('ascii'),
                        action_pin.encode('ascii'), 'semantic ActionLearn dependency')
    result[semantic_name] = semantic
    result[local_name] = _replace(result[local_name], semantic_pin.encode('ascii'),
        hashlib.sha256(semantic).hexdigest().encode('ascii'), 'local error semantic dependency')

    # Keep the existing learning/procedural suite meaningful in the staged
    # tree: those positive learning tests opt in to SHADOW_UPDATE explicitly.
    # The source test itself stays frozen and an additional test proves that
    # the same real turn does not update FastForward in RECORD_ONLY.
    test_path = code_dir / 'tests/test_fastforward_reflex.py'
    if test_path.is_symlink() or not test_path.is_file():
        raise ValueError('FastForward test source missing or unsafe')
    test_raw = test_path.read_bytes()
    if hashlib.sha256(test_raw).hexdigest() != 'ea53e2481dc73a13deda565a3538bdd9efcb6ead0d7a5db95b2ebc1b16854797':
        raise ValueError('FastForward test source changed')
    test_raw = _replace(test_raw,
        b'self.tmp=tempfile.TemporaryDirectory();self.r=Runtime(Path(self.tmp.name));self.r.sleep.cycle.set_policy(\'enabled\',\'off\')',
        b'self.tmp=tempfile.TemporaryDirectory();self.r=Runtime(Path(self.tmp.name));self.r.cfg[\'learning_mode\']=\'SHADOW_UPDATE\';self.r.sleep.cycle.set_policy(\'enabled\',\'off\')',
        'FastForward positive test mode')
    test_raw = _replace(test_raw,
        b'    def test_turn_feeds_fast_forward_and_procedures(self):\n',
        b"    def test_record_only_turn_does_not_train_fast_forward(self):\n"
        b"        self.r.cfg['learning_mode']='RECORD_ONLY'\n"
        b"        for _ in range(4):self.assertEqual(self.run_turn()['status'],'FINAL')\n"
        b"        rep=F.controller(self.r).report();self.assertEqual(rep['trained_on'],0);self.assertEqual(rep['procedures'],{})\n"
        b"    def test_turn_feeds_fast_forward_and_procedures(self):\n", 'FastForward record-only turn test')
    compile(test_raw, 'tests/test_fastforward_reflex.py', 'exec')
    result['tests/test_fastforward_reflex.py'] = test_raw

    for name, raw in checked.items():
        compile(raw, name, 'exec')
        result[name] = raw
    compile(GATE_SOURCE, 'v13/record_only_gate.py', 'exec')
    result['v13/record_only_gate.py'] = GATE_SOURCE
    return result
