"""Real CPU Torch tests for atomic C3 LoRA resume (no master model download)."""
from copy import deepcopy
import pytest
import torch

from v13.common import Unavailable
from v13.lora_trainer import (
    _restore_lora_training_state, _valid_lora_optimizer,
)


class SmallModel(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.lora_A=torch.nn.Linear(3,2,bias=False)
        self.base=torch.nn.Linear(3,2,bias=False)
        self.base.requires_grad_(False)


def setup_model(seed=31):
    torch.manual_seed(seed)
    m=SmallModel()
    opt=torch.optim.AdamW(m.lora_A.parameters(),lr=1e-3)
    return m,opt


def trained_checkpoint():
    m,opt=setup_model(31)
    x=torch.tensor([[1.,2.,3.]])
    m.lora_A(x).sum().backward()
    opt.step()
    g=torch.Generator().manual_seed(13)
    torch.randperm(4,generator=g)
    torch.randperm(2,generator=g)
    return {
        'lora':{k:v.detach().clone() for k,v in m.state_dict().items() if 'lora_' in k},
        'opt':deepcopy(opt.state_dict()),
        'step':1,
        'shuffle_rng_state':g.get_state(),
    }


def frozen_state(m,opt):
    return ({k:v.detach().clone() for k,v in m.state_dict().items()},
            deepcopy(opt.state_dict()))


def unchanged(m,opt,before):
    weights,state=before
    assert all(torch.equal(m.state_dict()[k],v) for k,v in weights.items())
    assert state['param_groups']==opt.state_dict()['param_groups']
    assert set(state['state'])==set(opt.state_dict()['state'])


def test_resumes_actual_adapter_adamw_moments_and_rng_without_touching_base():
    st=trained_checkpoint()
    m,opt=setup_model(47)
    base=m.base.weight.detach().clone()
    rng=_restore_lora_training_state(torch,m,opt,st,13,4,2,1.0)
    assert torch.equal(m.lora_A.weight,st['lora']['lora_A.weight'])
    assert torch.equal(m.base.weight,base)
    assert torch.equal(rng.get_state(),st['shuffle_rng_state'])
    loaded=opt.state_dict()
    assert loaded['state']
    for k,part in st['opt']['state'].items():
        for name,t in part.items():
            assert torch.equal(loaded['state'][k][name],t)
    # The state can take the next real gradient step after recovery.
    opt.zero_grad()
    m.lora_A(torch.tensor([[1.,2.,3.]])).square().sum().backward()
    opt.step()
    assert torch.isfinite(m.lora_A.weight).all()


@pytest.mark.parametrize('failure', ['foreign_group','nonfinite_moment','wrong_moment_shape',
                                     'missing_moment','unrecognized_state','bad_rng'])
def test_bad_checkpoints_leave_model_and_optimizer_unchanged(failure):
    st=trained_checkpoint()
    m,opt=setup_model(47)
    before=frozen_state(m,opt)
    s=st['opt']['state']
    pid=next(iter(s))
    if failure=='foreign_group':
        st['opt']['param_groups'][0]['lr']=7.0
    elif failure=='nonfinite_moment':
        s[pid]['exp_avg'].fill_(float('nan'))
    elif failure=='wrong_moment_shape':
        s[pid]['exp_avg']=torch.zeros(1)
    elif failure=='missing_moment':
        del s[pid]['exp_avg_sq']
    elif failure=='unrecognized_state':
        s[pid]['payload']=torch.zeros(2,3)
    else:
        st['shuffle_rng_state']='not a Torch RNG state'
    with pytest.raises(Unavailable):
        _restore_lora_training_state(torch,m,opt,st,13,4,2,1.0)
    unchanged(m,opt,before)


def test_optimizer_load_exception_is_rolled_back_after_partial_mutation():
    st=trained_checkpoint()
    m,opt=setup_model(47)
    before=frozen_state(m,opt)
    real_load=opt.load_state_dict
    called=0
    def inject(data):
        nonlocal called
        called+=1
        real_load(data)
        if called==1:
            raise RuntimeError('simulated partial optimizer load failure')
    opt.load_state_dict=inject
    with pytest.raises(Unavailable,match='old state restored'):
        _restore_lora_training_state(torch,m,opt,st,13,4,2,1.0)
    assert called==2
    unchanged(m,opt,before)


def test_optimizer_moment_ids_must_refer_to_real_parameters():
    st=trained_checkpoint()
    m,opt=setup_model()
    st['opt']['state'][999]=st['opt']['state'].pop(0)
    assert not _valid_lora_optimizer(torch,st['opt'],opt)
