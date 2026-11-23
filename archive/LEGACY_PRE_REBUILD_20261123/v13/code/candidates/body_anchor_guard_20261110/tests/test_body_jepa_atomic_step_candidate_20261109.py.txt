"""Real small Torch counterexamples; no model download or native body proof."""
import copy
from unittest.mock import patch

import pytest
torch=pytest.importorskip('torch')

from v13.body_jepa import EmaAdapter,checked_gradient_step
from v13.body_jepa_atomic_step_candidate import checked_training_step


def setup():
    p=torch.nn.Parameter(torch.tensor([1.,2.]))
    q=torch.nn.Parameter(torch.tensor([3.,4.]))
    opt=torch.optim.AdamW([p,q],lr=.1)
    ema=EmaAdapter([p,q],.5)
    return [p,q],opt,ema


def gradients(params):
    for p in params:p.grad=torch.ones_like(p)


def test_original_finite_gradient_can_still_corrupt_parameter_from_optimizer_state():
    params,opt,_=setup();gradients(params);checked_gradient_step(torch,params,opt)
    opt.state[params[1]]['exp_avg'].fill_(float('nan'))
    gradients(params);checked_gradient_step(torch,params,opt)
    assert torch.isfinite(params[1].grad).all() and not torch.isfinite(params[1]).all()


def test_bad_optimizer_state_is_rejected_before_any_parameter_changes():
    params,opt,ema=setup();gradients(params);checked_training_step(torch,params,opt,ema)
    opt.state[params[1]]['exp_avg'].fill_(float('nan'));gradients(params)
    before=[p.clone() for p in params];updates=ema.updates
    with pytest.raises(ValueError,match='optimizer state'):
        checked_training_step(torch,params,opt,ema)
    assert all(torch.equal(p,b) for p,b in zip(params,before)) and ema.updates==updates


def test_finite_step_updates_both_optimizer_and_ema():
    params,opt,ema=setup();gradients(params);before=[p.clone() for p in params]
    checked_training_step(torch,params,opt,ema)
    assert all(not torch.equal(p,b) for p,b in zip(params,before))
    assert ema.updates==1 and all(torch.isfinite(s).all() for s in ema.shadow)


def test_nonfinite_after_finite_gradient_rolls_back_optimizer_and_gradients():
    p=torch.nn.Parameter(torch.tensor([1.]))
    opt=torch.optim.SGD([p],lr=1e38);ema=EmaAdapter([p],.5)
    p.grad=torch.tensor([1e10]);before=p.clone();before_grad=p.grad.clone()
    with pytest.raises(ValueError,match='optimizer output'):
        checked_training_step(torch,[p],opt,ema)
    assert torch.equal(p,before) and torch.equal(p.grad,before_grad)
    assert ema.updates==0 and torch.equal(ema.shadow[0],before) and not opt.state


def test_failed_optimizer_restores_model_state_ema_and_clipped_gradients():
    params,opt,ema=setup();gradients(params);checked_training_step(torch,params,opt,ema)
    for p in params:p.grad=torch.full_like(p,20.)
    before=[p.clone() for p in params];before_grad=[p.grad.clone() for p in params]
    before_opt=copy.deepcopy(opt.state_dict());before_shadow=[s.clone() for s in ema.shadow];count=ema.updates
    def broken_step():
        with torch.no_grad():params[0].add_(99.)
        opt.state[params[0]]['exp_avg'].fill_(55.)
        raise RuntimeError('injected optimizer failure')
    with patch.object(opt,'step',side_effect=broken_step):
        with pytest.raises(RuntimeError,match='injected optimizer failure'):
            checked_training_step(torch,params,opt,ema,max_norm=1.)
    assert all(torch.equal(p,b) for p,b in zip(params,before))
    assert all(torch.equal(p.grad,b) for p,b in zip(params,before_grad))
    assert all(torch.equal(s,b) for s,b in zip(ema.shadow,before_shadow)) and ema.updates==count
    after=opt.state_dict()
    assert after['param_groups']==before_opt['param_groups']
    for key in before_opt['state']:
        for field,value in before_opt['state'][key].items():
            assert torch.equal(after['state'][key][field],value)


def test_ema_failure_rolls_back_successful_optimizer_step():
    params,opt,ema=setup();gradients(params);before=[p.clone() for p in params]
    with patch.object(ema,'update',side_effect=RuntimeError('injected EMA failure')):
        with pytest.raises(RuntimeError,match='injected EMA failure'):
            checked_training_step(torch,params,opt,ema)
    assert all(torch.equal(p,b) for p,b in zip(params,before))
    assert not opt.state and ema.updates==0


def test_nonfinite_ema_output_also_rolls_back_the_optimizer():
    params,opt,ema=setup();gradients(params);before=[p.clone() for p in params]
    def bad_ema():
        ema.shadow[0].fill_(float('nan'));ema.updates+=1
    with patch.object(ema,'update',side_effect=bad_ema):
        with pytest.raises(ValueError,match='invalid EMA output'):
            checked_training_step(torch,params,opt,ema)
    assert all(torch.equal(p,b) for p,b in zip(params,before))
    assert not opt.state and ema.updates==0 and all(torch.isfinite(s).all() for s in ema.shadow)


def test_unrecoverable_rollback_poison_marks_optimizer_unusable():
    params,opt,ema=setup();gradients(params)
    with patch.object(ema,'update',side_effect=RuntimeError('EMA failure')):
        with patch.object(opt,'load_state_dict',side_effect=RuntimeError('restore failure')):
            with pytest.raises(RuntimeError,match='recovery failed'):
                checked_training_step(torch,params,opt,ema)
    with pytest.raises(RuntimeError,match='requires discard'):
        checked_training_step(torch,params,opt,ema)


def test_unrelated_optimizer_parameter_fails_before_training():
    params,opt,ema=setup();gradients(params)
    with pytest.raises(ValueError,match='do not match'):
        checked_training_step(torch,params[:1],opt,ema)
