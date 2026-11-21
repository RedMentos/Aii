"""Compose reviewed World predictor guards on exact #1663 integration sources.

Only returns source bytes for a disposable copy. No frozen runtime is modified.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import subprocess
import tempfile

HEAD = '95aea15a046e73acf82c67ccf934cebda651ef87'
FILES = {
    'v13/runtime.py': 'a533660776f7e2b1697e9793a3abb811eb6d1e7191ec6fe0af523d58efa0ce38',
    'v13/operator.py': '67f2118efce0495ea144b11e8853cbf949d56e53e141fe7f801b31c56406f9a3',
    'v13/agi/__init__.py': '75333b385dbc2d581e8fc028b433b0a93847dc80b64f83d9aedf104cc45c8661',
    'v13/online_world.py': 'ebd6044651ccd031c947a2e8d0d188232c2bab2da79b19ea6c513c433d59e8c8',
    'v13/continuous_predictor.py': '65ac1d863610ba82547dc715f74a0812ed31dd39f216398defb1bdb085392d8a',
    'tests/test_online_world_20261108.py': '7a76845424f5ade953286a6684803a79778f543379a84393eecd90163de3ced6',
    'v13/world_model.py': 'cb58f26778501c02b986b08d4e356591776d998fa7e5bc14f81bb5b33a29322b',
    'v13/store.py': 'fe66f92533b20738b5ec384e9d7c0b5ac8b4b4f658c6c1ad23792d813ff29980',
    'v13/age.py': '77a6f67a6c78fd6f08af1265d4a6818ef8b720f1fd5f3f4b3e9acf7939414dd8',
    'v13/inputs.py': '235cce055cdc5eb1c889593dd279d9c837a718f0630b8427223a3883c5079539',
    'v13/world.py': 'bb221176167cb1f83285127cba2b2e059ebf9b0cec79b9405b3b5f23cef0343e',
    'v13/common.py': '0bc5a2a8eb5cc246d72410cdc1e1090dc838114999ca132a4ddac0104d03262a',
    'specs/models.json': '81fe561e19b92614555453a1b99a39d8d77fe35dd7c7e06034e6dc7ff2e0bc58',
}
ASSETS = {
    'changes.patch': '75d3d269b1f97bb8d63bdd1ce5caa1a8465dd52958a43f23e69656316fbc8f3c',
    'online_world_policy.py.txt': 'd75e5ec91ac40bd6898d2cf01e2261795455090b9c98a948fa56b20098031e53',
    'test_online_world_safety.py.txt': '680697834f64f874362a7cea1044e6397c2c0ca9fe180394b1e7a15cbcab17d8',
    'staged_observe_1648.py.txt': '071dbbca5d531537c59c159729f07fabbce470749a212df73e735312ab690a81',
    'test_checkpoint_guards_1648.py.txt': '3f122d133741995289331ae3a8238555da2e551bfe275129fef503405df7f2c7',
    'test_observe_atomic_1648.py.txt': '1b476d4af877e6e7a65dc0318b4bfde2440a625b2178159cbeeaa38614551f12',
    'test_known_revocation_window.py.txt': 'e3c3fa0bcfa90afd8f6e8d23addd7439ccba614b89a521754f959ed40fd6de7f',
}
EXPECTED_1631 = {
    'v13/continuous_predictor.py': '6f1407c4bbc16d8f298fba2fb384f6022e88a1d8093cc5822a40069b34ee062a',
    'v13/online_world.py': 'f4d415a0f600b1ea5313964801e06525e51bb882d09a99f04a67f678ed4126ff',
    'tests/test_online_world_20261108.py': 'fc2c47bcf183f29a7f18cd8f5dcb1946b109ff273865242a4a5683af9c3289c7',
}
ASSET_DIR = Path(__file__).resolve().parents[1] / 'candidates/online_world_20261109'

RUNTIME_OLD = b'''    def online_world_update(self,limit=2048):
        """Explicit bounded online learning from committed T8 transitions.

        The predictor is local and never modifies pretrained GGUF weights.
        No model is initialized until the operator invokes this entrypoint.
        """
        from .online_world import OnlineWorld
        if not hasattr(self,'_online_world'):
            self._online_world=OnlineWorld(self)
        return self._online_world.update(limit=limit)
'''
RUNTIME_NEW = b'''    def online_world_update(self,limit=2048,authority='SYSTEM'):
        """Bounded local SHADOW learning, gated by explicit user and Age settings."""
        from . import online_world_policy as policy
        reason=policy.blocked(self,authority)
        if reason:return {'status':'SKIPPED_'+reason,'learned':0}
        if authority==policy.HUMAN:self.require_idle()
        from .online_world import OnlineWorld
        with self.lock:
            if not hasattr(self,'_online_world'):self._online_world=OnlineWorld(self)
            world=self._online_world
        check=lambda:policy.blocked(self,authority) is None
        return world.update(limit=limit,should_continue=check,authority=authority)
'''
RUNTIME_LOG_OLD = b'''                        except Exception as exc:
                            self.store.log('online_world_learning_error',payload['event_id'],
                                           {'error':type(exc).__name__})
'''
RUNTIME_LOG_NEW = b'''                        except Exception as exc:
                            try:self.store.log('online_world_learning_error',payload['event_id'],
                                               {'error':type(exc).__name__})
                            except Exception:pass
'''
AGI_OLD = b'''    if args and args[0]=='onlineworld':
        if len(args)>2:raise ValueError('Usage: :growth onlineworld [LIMIT]')
        limit=int(args[1]) if len(args)==2 else 2048
        return dumps(r.online_world_update(limit=limit))
'''
AGI_NEW = b'''    if args and args[0]=='onlineworld':
        from .. import online_world_policy as policy
        if len(args)==1 or args==['onlineworld','status']:return dumps(policy.status(r))
        if args in (['onlineworld','on'],['onlineworld','off']):
            policy.set_enabled(r.store,args[1]=='on',policy.HUMAN)
            return dumps(policy.status(r))
        if len(args)==2 and args[1].isdigit():
            return dumps(r.online_world_update(limit=int(args[1]),authority=policy.HUMAN))
        if len(args) in (2,3) and args[1]=='run':
            return dumps(r.online_world_update(limit=int(args[2]) if len(args)==3 else 64,authority=policy.HUMAN))
        raise ValueError('Usage: :growth onlineworld [status|on|off|run [LIMIT]|LIMIT]')
'''
DIRECT_OLD = b'''    def update(self,limit=2048,should_continue=None):
        if should_continue is not None and not callable(should_continue):raise ValueError('Invalid continuation check')
        with self.lock:return self._update(limit,should_continue)
'''
DIRECT_NEW = b'''    def _blocked(self,authority):
        from . import online_world_policy as policy
        return policy.blocked(self.runtime,authority)

    def update(self,limit=2048,should_continue=None,authority='SYSTEM'):
        if should_continue is not None and not callable(should_continue):raise ValueError('Invalid continuation check')
        reason=self._blocked(authority)
        if reason:return {'status':'SKIPPED_'+reason,'learned':0}
        if authority=='EXPLICIT_HUMAN':self.runtime.require_idle()
        def allowed():
            return self._blocked(authority) is None and (should_continue is None or should_continue())
        with self.lock:
            reason=self._blocked(authority)
            if reason:return {'status':'SKIPPED_'+reason,'learned':0}
            return self._update(limit,allowed)
'''


def _checked(raw, expected, name):
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError('integrated online-world hash mismatch: ' + name)
    return raw


def _replace(raw, old, new, name):
    if raw.count(old) != 1:
        raise ValueError('integrated online-world anchor mismatch: ' + name)
    return raw.replace(old, new, 1)


def build_sources(code_dir):
    code_dir = Path(code_dir)
    raw = {name: _checked((code_dir / name).read_bytes(), expected, name)
           for name, expected in FILES.items()}
    assets = {name: _checked((ASSET_DIR / name).read_bytes(), expected, name)
              for name, expected in ASSETS.items()}
    added = ('v13/online_world_policy.py', 'tests/test_online_world_safety_20261109.py',
             'tests/test_checkpoint_guards_1648.py', 'tests/test_observe_atomic_1648.py',
             'tests/test_known_revocation_window.py')
    if any((code_dir / name).exists() for name in added):
        raise ValueError('integrated online-world target already exists')
    # Apply only #1631 sections whose entire source still matches #1663.
    sections = assets['changes.patch'].split(b'diff --git ')
    wanted = set(EXPECTED_1631)
    selected = []
    for section in sections:
        if not section:
            continue
        header = section.splitlines()[0]
        for name in wanted:
            if header == ('a/v13/code/' + name + ' b/v13/code/' + name).encode():
                selected.append(b'diff --git ' + section)
    if len(selected) != len(wanted):
        raise ValueError('missing reviewed online-world patch sections')
    with tempfile.TemporaryDirectory(prefix='v13-world-integration-') as home:
        root = Path(home)
        for name in wanted:
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw[name])
        patch_path = root / 'reviewed.patch'
        patch_path.write_bytes(b''.join(selected))
        result = subprocess.run(['patch', '--batch', '--fuzz=0', '--forward', '-p3', '-i', str(patch_path)],
                                cwd=root, capture_output=True, text=True, check=False)
        if result.returncode:
            raise ValueError('reviewed online-world patch failed: ' + result.stdout + result.stderr)
        for name, expected in EXPECTED_1631.items():
            raw[name] = _checked((root / name).read_bytes(), expected, name + ' #1631 output')
    predictor = raw['v13/continuous_predictor.py']
    start = predictor.index(b'    def _observe(self,x,action,y,rehearsals=2):\n')
    end = predictor.index(b'    def learn_stream(', start)
    raw['v13/continuous_predictor.py'] = predictor[:start] + assets['staged_observe_1648.py.txt'] + b'\n' + predictor[end:]
    raw['v13/online_world.py'] = _replace(raw['v13/online_world.py'], DIRECT_OLD, DIRECT_NEW, 'direct update gate')
    raw['v13/runtime.py'] = _replace(raw['v13/runtime.py'], RUNTIME_OLD, RUNTIME_NEW, 'runtime online update')
    raw['v13/runtime.py'] = _replace(raw['v13/runtime.py'], RUNTIME_LOG_OLD, RUNTIME_LOG_NEW, 'runtime error logging')
    raw['v13/agi/__init__.py'] = _replace(raw['v13/agi/__init__.py'], AGI_OLD, AGI_NEW, 'operator online update')
    marker = b':neuromod [status|path <Name>|sleep|clear-veto <Name>]'
    extra = b':growth onlineworld [status|on|off|run [LIMIT]] (lokales Weltmodell; nur im freigegebenen Lernmodus)\n'
    raw['v13/operator.py'] = _replace(raw['v13/operator.py'], marker, extra + marker, 'help')
    # Fabricated-row fixtures intentionally bypass source/policy checks only in the tests.
    test = raw['tests/test_online_world_20261108.py']
    anchor = b"    monkeypatch.setattr(OnlineWorld,'_source_current',lambda self,row:True)\n"
    raw['tests/test_online_world_20261108.py'] = _replace(
        test, anchor, anchor + b"    monkeypatch.setattr(OnlineWorld,'_blocked',lambda self,authority:None)\n", 'legacy fixture')
    safety = assets['test_online_world_safety.py.txt']
    safety = _replace(safety, anchor, anchor + b"    monkeypatch.setattr(OnlineWorld,'_blocked',lambda self,authority:None)\n", 'synthetic fixture')
    safety = _replace(safety, b'def test_source_revoked_during_batch_is_rechecked_before_update(tmp_path):',
                      b'def test_source_revoked_during_batch_is_rechecked_before_update(tmp_path,synthetic_sources):', 'mock fixture')
    raw['tests/test_online_world_safety_20261109.py'] = safety
    raw['tests/test_checkpoint_guards_1648.py'] = assets['test_checkpoint_guards_1648.py.txt']
    raw['tests/test_observe_atomic_1648.py'] = assets['test_observe_atomic_1648.py.txt']
    raw['tests/test_known_revocation_window.py'] = assets['test_known_revocation_window.py.txt']
    raw['v13/online_world_policy.py'] = assets['online_world_policy.py.txt']
    keep = ('v13/runtime.py', 'v13/operator.py', 'v13/agi/__init__.py', 'v13/online_world.py',
            'v13/continuous_predictor.py', 'v13/online_world_policy.py',
            'tests/test_online_world_20261108.py', 'tests/test_online_world_safety_20261109.py',
            'tests/test_checkpoint_guards_1648.py', 'tests/test_observe_atomic_1648.py',
            'tests/test_known_revocation_window.py')
    return {name: raw[name] for name in keep}
