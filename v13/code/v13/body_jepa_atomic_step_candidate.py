"""Review-only fail-closed Body-JEPA step, including EMA update.

Snapshots selected parameters, their gradients and optimizer state in memory;
this is not crash-durable checkpointing or a measured mobile-memory design.
"""
import copy
import math
import numbers


def _finite(torch,value):
    if torch.is_tensor(value):
        if value.is_sparse:return False
        return bool(torch.isfinite(value).all())
    if isinstance(value,dict):return all(_finite(torch,item) for item in value.values())
    if isinstance(value,(list,tuple)):return all(_finite(torch,item) for item in value)
    if isinstance(value,numbers.Real) and not isinstance(value,bool):return math.isfinite(value)
    return value is None or isinstance(value,(str,bool))


def checked_training_step(torch,params,opt,ema,max_norm=None):
    """Run one optimizer+EMA step or restore the prior in-memory state."""
    from .body_jepa import checked_gradient_step
    if getattr(opt,'_v13_body_step_unusable',False):
        raise RuntimeError('optimizer requires discard after failed recovery')
    params=list(params)
    if not params or len({id(p) for p in params})!=len(params):
        raise ValueError('unique training parameters required')
    groups=[p for group in opt.param_groups for p in group['params']]
    if len(groups)!=len(params) or {id(p) for p in groups}!={id(p) for p in params}:
        raise ValueError('optimizer parameters do not match training step')
    if any(id(p) not in {id(q) for q in params} for p in opt.state):
        raise ValueError('optimizer state references an unrelated parameter')
    if (max_norm is not None and (type(max_norm) not in (int,float)
            or not math.isfinite(max_norm) or max_norm<=0)):
        raise ValueError('grad_clip_norm must be finite and positive')
    grads=[p.grad for p in params if p.requires_grad and p.grad is not None]
    if not grads:raise ValueError('body JEPA step has no trainable gradients')
    if not all(_finite(torch,p.detach()) for p in params) or not all(_finite(torch,g) for g in grads):
        raise ValueError('nonfinite body parameter or gradient')
    if not _finite(torch,opt.state) or not _finite(torch,opt.param_groups):
        raise ValueError('nonfinite or unsupported optimizer state')
    ema._validate()
    if (len({id(p) for p in ema.params})!=len(ema.params)
            or any(id(p) not in {id(q) for q in params} for p in ema.params)
            or type(ema.updates) is not int or ema.updates<0
            or not all(_finite(torch,s) for s in ema.shadow)):
        raise ValueError('invalid EMA state')
    # Allocate all rollback data before allowing any optimizer mutation.
    before=[p.detach().clone() for p in params]
    before_grad=[None if p.grad is None else p.grad.detach().clone() for p in params]
    before_opt=copy.deepcopy(opt.state_dict())
    before_shadow=[s.detach().clone() for s in ema.shadow];before_updates=ema.updates
    try:
        checked_gradient_step(torch,params,opt,max_norm)
        if (not all(_finite(torch,p.detach()) for p in params)
                or not _finite(torch,opt.state) or not _finite(torch,opt.param_groups)):
            raise ValueError('nonfinite optimizer output')
        ema.update()
        ema._validate()
        if (ema.updates!=before_updates+1 or not all(_finite(torch,s) for s in ema.shadow)
                or not all(_finite(torch,p.detach()) for p in params) or not _finite(torch,opt.state)):
            raise ValueError('invalid EMA output')
    except BaseException as exc:
        try:
            with torch.no_grad():
                for p,old in zip(params,before):p.copy_(old)
                for p,old in zip(params,before_grad):
                    if old is None:p.grad=None
                    elif p.grad is None:p.grad=old.clone()
                    else:p.grad.copy_(old)
            opt.load_state_dict(before_opt)
            ema.shadow=before_shadow;ema.updates=before_updates
        except BaseException as recovery:
            opt._v13_body_step_unusable=True
            raise RuntimeError('body step recovery failed; discard optimizer and model') from recovery
        raise
