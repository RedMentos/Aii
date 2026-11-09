"""Materialize the full candidate and exercise real synthetic Torch fit."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from unittest.mock import patch

import pytest

from scripts.body_jepa_atomic_step_integration_candidate import build_sources


CODE=Path(__file__).resolve().parents[1]
PROBE='''
from unittest.mock import patch
import pytest
import torch
from v13.body_jepa import EmaAdapter

def test_staged_ema_never_partially_copies_into_old_shadow():
    params=[torch.nn.Parameter(torch.tensor([1.])),torch.nn.Parameter(torch.tensor([2.]))]
    ema=EmaAdapter(params,.5)
    with torch.no_grad():
        for p in params:p.add_(4.)
    calls=[]
    def forbidden(*args,**kwargs):
        calls.append(1)
        raise RuntimeError('copy should not be used for shadow publication')
    with patch.object(torch.Tensor,'copy_',forbidden):ema.update()
    assert not calls and [float(s.item()) for s in ema.shadow]==[3.,4.]
    assert ema.updates==1

def test_staging_exception_leaves_old_shadow_and_counter():
    params=[torch.nn.Parameter(torch.tensor([1.])),torch.nn.Parameter(torch.tensor([2.]))]
    ema=EmaAdapter(params,.5);before=[s.clone() for s in ema.shadow]
    original=torch.Tensor.__add__;calls=[]
    def fail_second(self,other):
        calls.append(1)
        if len(calls)==2:raise RuntimeError('injected staging failure')
        return original(self,other)
    with patch.object(torch.Tensor,'__add__',fail_second):
        with pytest.raises(RuntimeError,match='injected staging failure'):ema.update()
    assert all(torch.equal(s,b) for s,b in zip(ema.shadow,before)) and ema.updates==0

def test_real_tiny_fit_path_rolls_back_when_ema_fails(tmp_path):
    from test_body_jepa_checkpoint_fit import TinyTrainer
    from v13 import body_jepa_atomic_step_candidate as candidate
    cfg={'rank':2,'targets':('c_attn',),'locality_swaps':0,'anchor_weight':0.,
         'jepa_weight':.3,'jepa_target':'ema','max_steps':1,'min_steps':1,
         'target_loss':-1.,'threads':1,'seed':9}
    items=[{'memory_id':'one','prompt':'What is the item?','target':'Blue'},
           {'memory_id':'two','prompt':'Where is the item?','target':'North'}]
    trainer=TinyTrainer('/tmp/synthetic-master',tmp_path,master_sha256='a'*64,cfg=cfg)
    original=candidate.checked_training_step;seen=[]
    def fail_ema(torch_module,params,opt,ema,max_norm=None):
        params=list(params);before=[p.detach().clone() for p in params]
        before_grad=[None if p.grad is None else p.grad.detach().clone() for p in params]
        with patch.object(ema,'update',side_effect=RuntimeError('injected fit EMA failure')):
            with pytest.raises(RuntimeError,match='injected fit EMA failure'):
                original(torch_module,params,opt,ema,max_norm)
        assert all(torch.equal(p,b) for p,b in zip(params,before))
        assert all((p.grad is None and b is None) or torch.equal(p.grad,b)
                   for p,b in zip(params,before_grad))
        assert not opt.state and ema.updates==0
        seen.append(True)
        raise RuntimeError('fit stopped after verified rollback')
    with patch.object(candidate,'checked_training_step',side_effect=fail_ema):
        with pytest.raises(RuntimeError,match='fit stopped after verified rollback'):
            trainer.fit(items,'synthetic-generation')
    assert seen==[True]
'''


def test_builder_rejects_changed_body_source(tmp_path):
    source=CODE/'v13/body_jepa.py';(tmp_path/'body_jepa.py').write_bytes(source.read_bytes()+b'\n# changed\n')
    with pytest.raises(ValueError,match='unsupported'):build_sources(tmp_path)


def test_original_ema_later_copy_failure_partially_changes_shadow():
    torch=pytest.importorskip('torch')
    from v13.body_jepa import EmaAdapter
    params=[torch.nn.Parameter(torch.tensor([1.])),torch.nn.Parameter(torch.tensor([2.]))]
    ema=EmaAdapter(params,.5)
    with torch.no_grad():
        for p in params:p.add_(4.)
    before=[s.clone() for s in ema.shadow];original=torch.Tensor.copy_;calls=[]
    def fail_second_once(self,other,*args,**kwargs):
        calls.append(1)
        if len(calls)==2:raise RuntimeError('injected later copy failure')
        return original(self,other,*args,**kwargs)
    with patch.object(torch.Tensor,'copy_',fail_second_once):
        with pytest.raises(RuntimeError,match='injected later copy failure'):ema.update()
    assert not torch.equal(ema.shadow[0],before[0])
    assert torch.equal(ema.shadow[1],before[1]) and ema.updates==0


def test_candidate_fit_resume_and_optimizer_atomicity_in_copy():
    overlay=build_sources(CODE/'v13')
    with tempfile.TemporaryDirectory(prefix='v13-body-atomic-step-') as home:
        target=Path(home)
        shutil.copytree(CODE/'v13',target/'v13',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
        shutil.copytree(CODE/'specs',target/'specs')
        (target/'tests').mkdir()
        names=('test_body_jepa_atomic_step_candidate_20261109.py','test_body_jepa_gradient_integrity_20261109.py',
               'test_body_jepa_ema_update_integrity_20261109.py','test_body_jepa_ema_atomic_20261109.py',
               'test_body_jepa_checkpoint_fit.py')
        for name in names:shutil.copy2(CODE/'tests'/name,target/'tests'/name)
        for name,data in overlay.items():(target/'v13'/name).write_bytes(data)
        (target/'tests/test_staged_ema_probe.py').write_text(PROBE)
        env=dict(os.environ,PYTHONPATH=str(target)+os.pathsep+str(target/'tests'),
                 HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
        run=subprocess.run([sys.executable,'-m','pytest','-q',*[str(Path('tests')/n) for n in names],
                            'tests/test_staged_ema_probe.py'],cwd=target,env=env,capture_output=True,text=True,timeout=120)
        assert run.returncode==0,run.stdout+'\n'+run.stderr
        assert 'passed' in run.stdout,run.stdout
