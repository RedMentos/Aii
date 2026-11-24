"""Materialize the Body-JEPA step candidate only against exact reviewed bytes."""
import hashlib
from pathlib import Path


SOURCE_SHAS={'974ee7372fdecb2b81619b95647c1881c1eeb4e7170c7890823c9ca2a58cd835',
             '7bb55359c57a7b3baf79001fd0ed45b1faa7a6c78f47e23e26a7657d95b098a0'}
EMA_OLD=b'''            # No live shadow is modified before all candidates are validated.
            for s, candidate in zip(self.shadow, proposed):
                s.copy_(candidate)
        self.updates += 1
'''
EMA_NEW=b'''            # Publish the staged list only after every tensor is valid.
            if type(self.updates) is not int or self.updates < 0:
                raise ValueError('invalid EMA update counter')
            next_updates = self.updates + 1
            self.shadow = proposed
        self.updates = next_updates
'''
STEP_OLD=b'''            checked_gradient_step(torch,params+list(pred.parameters()),opt,cfg.get('grad_clip_norm'))
            ema.update();step+=1
'''
STEP_NEW=b'''            from .body_jepa_atomic_step_candidate import checked_training_step
            checked_training_step(torch,params+list(pred.parameters()),opt,ema,cfg.get('grad_clip_norm'))
            step+=1
'''


def build_sources(source_dir):
    raw=(Path(source_dir)/'body_jepa.py').read_bytes()
    if hashlib.sha256(raw).hexdigest() not in SOURCE_SHAS:raise ValueError('unsupported Body-JEPA source')
    for old,new in ((EMA_OLD,EMA_NEW),(STEP_OLD,STEP_NEW)):
        if raw.count(old)!=1:raise ValueError('ambiguous Body-JEPA candidate anchor')
        raw=raw.replace(old,new,1)
    return {'body_jepa.py':raw}
