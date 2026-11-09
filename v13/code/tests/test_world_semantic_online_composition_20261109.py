"""Cross-branch composition, exercised only in a temporary source tree."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

import pytest

from scripts.world_semantic_online_composition_candidate import build_sources


CODE=Path(__file__).resolve().parents[1]
PROBE='''
import time
from types import SimpleNamespace
from unittest.mock import Mock
from v13 import inputs,online_world_policy,world_semantic_evidence_candidate as semantic
from v13.runtime import Runtime

def test_same_committed_action_has_technical_and_explicit_feedback_evidence(tmp_path):
    r=Runtime(tmp_path)
    try:
        r.sleep.cycle.set_policy('enabled','off')
        r.cfg['learning_mode']='SHADOW_UPDATE'
        online_world_policy.set_enabled(r.store,True,'EXPLICIT_HUMAN')
        r._route=Mock(return_value=('simple',{'source':'TEST_ROUTE_SEAM'}))
        r.pool.get=Mock(return_value=SimpleNamespace(role='C3_LANGUAGE',last_metrics={},
                        generate=lambda *a,**k:iter(['2 + 2 = 5'])))
        r.learner.output_delta=Mock(return_value=None)
        event=r.submit('Check 2 + 2')
        end=time.monotonic()+10
        while not r.idle() and time.monotonic()<end:time.sleep(.005)
        assert r.idle() and r.last_answer()['status']=='FINAL'
        assert r._online_world.model.seen==1
        inputs.record_rating(r.store,event,8,'EXPLICIT_NOTE')
        r.memory.feedback(event,'fact','2 + 2 = 4',permission='learn',key='result')
        observed=semantic.snapshot(r.store,r.session,event)
        assert observed['t8_action_id'] in r._online_world.processed
        assert observed['fact_correction']['learning_permission']=='learn'
        assert observed['quality_rating']['score']==8
        assert observed['training_authority']==0
        # The semantic signal has not yet trained the numeric predictor.
        assert r.online_world_update(limit=64,authority='EXPLICIT_HUMAN')['learned']==0
        assert semantic.still_current(r.store,r.session,event,observed['fingerprint_sha256'])
    finally:r.close()
'''


def test_two_source_bound_candidates_and_feedback_share_a_real_action():
    online_path=os.environ.get('V13_ONLINE_CANDIDATE_CODE')
    if not online_path:pytest.skip('set V13_ONLINE_CANDIDATE_CODE to the #1631 checkout code directory')
    online=Path(online_path);overlay=build_sources(CODE,online)
    with tempfile.TemporaryDirectory(prefix='v13-world-feedback-composed-') as home:
        target=Path(home)
        shutil.copytree(CODE/'v13',target/'v13',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
        shutil.copytree(CODE/'specs',target/'specs')
        (target/'tests').mkdir()
        shutil.copy2(online/'tests/test_continuous_predictor_20261108.py',target/'tests')
        shutil.copy2(CODE/'tests/test_world_semantic_evidence_candidate_20261109.py',target/'tests')
        for name,data in overlay.items():
            dest=target/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
        (target/'tests/test_composed_runtime_probe.py').write_text(PROBE)
        env=dict(os.environ,PYTHONPATH=str(target))
        command=[sys.executable,'-m','pytest','-q','tests/test_online_world_20261108.py',
                 'tests/test_continuous_predictor_20261108.py','tests/test_online_world_safety_20261109.py',
                 'tests/test_world_semantic_evidence_candidate_20261109.py','tests/test_composed_runtime_probe.py']
        run=subprocess.run(command,cwd=target,env=env,capture_output=True,text=True,timeout=120)
        assert run.returncode==0,run.stdout+'\n'+run.stderr
        assert '41 passed' in run.stdout,run.stdout
