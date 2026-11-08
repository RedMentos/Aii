"""Experimental repeated JEPA updates on committed V13 digital transitions.

Uses the existing strict ID/content-disjoint action-outcome adapter. Updates
model parameters regardless of holdout score; reports forgetting rather than
turning ordinary local learning into a global approval gate. No runtime or
active-model promotion authority is created here.
"""
from .world_jepa_action_outcome_adapter import build


def update(model,committed_records,steps=50):
    if type(steps) is not int or not 1<=steps<=2000:
        raise ValueError('Invalid JEPA update budget')
    split=build(committed_records)
    train=split['train'];holdout=split['holdout']
    previous=None
    if hasattr(model,'enc'):
        previous=model.prediction_loss(*holdout)
        model.partial_fit(*train,steps=steps,log_every=max(1,steps//4))
        mode='CONTINUED_WEIGHTS'
    else:
        model.fit(*train,steps=steps,log_every=max(1,steps//4))
        mode='INITIAL_WEIGHTS'
    current=model.prediction_loss(*holdout)
    return {'mode':mode,'holdout_loss_before':previous,'holdout_loss_after':current,
            'holdout_delta':None if previous is None else current-previous,
            'train_rows':len(split['train_action_ids']),
            'holdout_rows':len(split['holdout_action_ids']),
            'source_verified':False,'active_model_promoted':False}
