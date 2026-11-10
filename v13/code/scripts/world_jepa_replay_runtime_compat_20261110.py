"""Test detached replay with exact #1661 Runtime in an unmodified temporary copy.

The Runtime feed is a synthetic mock, not provenance evidence. No checkout or
production files are modified and the replay proposal is never published.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile

COMMIT = '9c38cc3d54d3345c5a4375f651467d00b7db683c'
CODE = Path(__file__).resolve().parents[1]
PINS = {
    'runtime.py': 'a533660776f7e2b1697e9793a3abb811eb6d1e7191ec6fe0af523d58efa0ce38',
    'world_jepa.py': '14ee7982ab3866a13b2cca83086123281cf112a3c133b91c06df9df3669715fd',
    'world_jepa_shadow_checkpoint.py': 'f88ad5eea241aacd55e5c3d0f53eb0b132a164a2d49cc0185726f1a0a8a076ae',
    'world_jepa_online_experiment.py': 'c05b38d5722fe26c91797448d9e67d3901f2a9efcb98302f90de235c9ac3948b',
    'world_jepa_action_outcome_adapter.py': '202488c7d06707cd92c2d5e46f611f685dbbb08f3ab795d98c7476c66aaeafcd',
    'world_model.py': 'cb58f26778501c02b986b08d4e356591776d998fa7e5bc14f81bb5b33a29322b',
}
LOCAL_PINS = {
    'world_jepa_replay.py': '57e075c2a0345948b7b8d68422b3b67ea9d357e1b8e18724f9254225e9ed8a52',
    'world_jepa_replay_shadow_candidate.py': 'ca3a4b18821047dd12ae0520cc77f42ebeb6c96d15c409537d2b77fa5d155bfb',
}

PROBE = r'''\
import hashlib
import json
from pathlib import Path
import sys
from unittest.mock import patch
import numpy as np
from v13.runtime import Runtime
from v13.world_jepa_replay_shadow_candidate import preview_replay

rows=[{'action_id':f'synthetic-{i:03d}',
       's':[i/90.,(i%7)/7.,float(np.sin(i/11.)),float(np.cos(i/11.))],
       'a':('simple','detail','gist','both')[i%4],
       'y':[i/180.,float(i%3==0),i/200.]} for i in range(96)]
def transitions(n, offset):
    x=np.arange(n*7,dtype=np.float64).reshape(n,7)/100+offset
    a=np.eye(4,dtype=np.float64)[np.arange(n)%4]
    y=x+np.column_stack((a[:,:3]*.1,np.zeros((n,4))))
    return x,a,y
r=Runtime(Path(sys.argv[1]));r.sleep.cycle.set_policy('enabled','off')
try:
    with patch('v13.world_model.transitions', return_value=rows) as feed:
        initial=r.world_jepa_update(steps=2,limit=128)
    active=r._world_jepa_online
    before=active.enc['W1'].copy(); source=r._world_jepa_source_sha
    staged,report=preview_replay(active,transitions(12,0.),transitions(12,10.),
        transitions(8,20.),transitions(8,30.),steps=2,replay_fraction=.25,seed=3)
    assert feed.call_count==1 and r._world_jepa_online is active
    assert np.array_equal(active.enc['W1'],before) and r._world_jepa_source_sha==source
    assert staged is not active and staged._fit_steps==active._fit_steps+2
    assert not np.array_equal(staged.enc['W1'],before)
    assert report['new_train_rows']==12 and report['replay_train_rows']==6
    # Review-only adversarial in-memory counterexample to #1661's unvalidated
    # deepcopy; this object is injected by the test, not supplied by Store.
    original_value=float(active.enc['W1'][0,0]); callback=[]
    class InvalidHistory:
        def __deepcopy__(self,memo):
            callback.append(True)
            active.enc['W1'][0,0]=original_value+1.
            raise ValueError('synthetic deepcopy failure')
    active.history.append(InvalidHistory())
    try:
        r.world_jepa_update(steps=1,limit=128)
    except ValueError as exc:
        assert str(exc)=='synthetic deepcopy failure'
    else:
        raise AssertionError('injected deepcopy unexpectedly succeeded')
    deepcopy_mutated=bool(callback and active.enc['W1'][0,0]==original_value+1.)
    assert deepcopy_mutated and r._world_jepa_online is active
    print(json.dumps({'schema':'v13-jepa-replay-runtime-compat-v1',
        'integration_commit':'9c38cc3d54d3345c5a4375f651467d00b7db683c',
        'scope':'DISPOSABLE_SYNTHETIC_FIXTURE_ONLY','feed':'MOCK_TRANSITIONS_NOT_REAL_STORE',
        'actual_runtime_method_invoked':True,'initial_fit_steps':active._fit_steps,
        'proposal_fit_steps':staged._fit_steps,'proposal_weight_changed':True,
        'runtime_model_unchanged_by_preview':True,'source_digest_unchanged_by_preview':True,
        'injected_invalid_history_deepcopy_mutated_runtime_on_failure':deepcopy_mutated,
        'runtime_receipt_status':initial['status'],'preview':report},sort_keys=True,allow_nan=False))
finally:
    r.close()
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--integration-checkout', required=True, type=Path)
    args = parser.parse_args()
    # Archive the exact Git object, ignoring mutable working-tree contents.
    archive = subprocess.run(['git', '-C', str(args.integration_checkout), 'archive', COMMIT,
                              'v13/code/v13', 'v13/code/specs'],
                             check=True, stdout=subprocess.PIPE).stdout
    with tempfile.TemporaryDirectory(prefix='v13-replay-runtime-compat-') as name:
        root = Path(name)
        with tarfile.open(fileobj=io.BytesIO(archive), mode='r:') as tar:
            tar.extractall(root, filter='data')
        code = root / 'v13/code'
        package = code / 'v13'
        for filename, expected in PINS.items():
            if hashlib.sha256((package / filename).read_bytes()).hexdigest() != expected:
                raise ValueError('integration source changed: ' + filename)
        for filename, expected in LOCAL_PINS.items():
            raw = (CODE / 'v13' / filename).read_bytes()
            if hashlib.sha256(raw).hexdigest() != expected or (package / filename).exists():
                raise ValueError('candidate changed or integration already has a conflicting file: ' + filename)
            (package / filename).write_bytes(raw)
        probe = root / 'probe.py'
        probe.write_text(PROBE)
        env = dict(os.environ, PYTHONPATH=str(code))
        result = subprocess.run([sys.executable, str(probe), str(root / 'runtime-home')],
                                cwd=root, env=env, capture_output=True, text=True, timeout=45)
        if result.returncode:
            raise RuntimeError('synthetic composition failed: ' + result.stderr[-3000:])
        data = json.loads(result.stdout)
        print(json.dumps(data, sort_keys=True, allow_nan=False))


if __name__ == '__main__':
    main()
