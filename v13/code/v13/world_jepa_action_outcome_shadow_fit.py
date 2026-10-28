"""Explicitly approved synthetic-only World-JEPA SHADOW fit + action ablation.

No Runtime/Store access, no files, no production authority. This module does
not certify causality or independently verify any real training provenance.
"""
from __future__ import annotations

import hashlib
import json
import re

import numpy as np

from v13 import world_jepa as wj
from v13 import world_jepa_action_outcome_adapter as adapter
from v13 import world_jepa_holdout_diagnostic as audit

SCHEMA = 'v13.world_jepa.action_outcome_shadow_fit.v1'
HEX64 = re.compile(r'[0-9a-f]{64}\Z')


def _arrays(triple, n):
    if type(triple) not in (tuple, list) or len(triple) != 3:
        raise ValueError('RUN51_INVALID_TRANSITION_TRIPLE')
    x, a, x2 = (np.asarray(v, dtype=np.float64) for v in triple)
    if (x.shape != (n, 7) or a.shape != (n, 4) or x2.shape != x.shape
            or not all(np.isfinite(v).all() for v in (x, a, x2))
            or not np.array_equal(x[:, 4:], np.zeros((n, 3)))
            or not np.array_equal(x2[:, :4], x[:, :4])
            or not np.all((a == 0) | (a == 1))
            or not np.all(a.sum(axis=1) == 1)):
        raise ValueError('RUN51_INVALID_ACTION_OUTCOME_EMBEDDING')
    return x.copy(), a.copy(), x2.copy()


def run(bundle, *, approved_shadow_fit=False, source_kind=None,
        seed=0, steps=20, ensemble=2):
    """Return two fitted *synthetic-only* in-memory SHADOW models and metrics."""
    if approved_shadow_fit is not True or source_kind != 'SYNTHETIC_TEST_ONLY':
        raise PermissionError('RUN51_EXPLICIT_SYNTHETIC_SHADOW_APPROVAL_REQUIRED')
    if (type(seed) is not int or not 0 <= seed <= 2**63 - 1
            or type(steps) is not int or not 1 <= steps <= 1000
            or type(ensemble) is not int or not 2 <= ensemble <= 4):
        raise ValueError('RUN51_INVALID_BOUNDED_FIT_CONFIG')
    if type(bundle) is not dict or type(bundle.get('manifest')) is not dict:
        raise ValueError('RUN51_ADAPTER_MANIFEST_REQUIRED')
    m = bundle['manifest']
    if (m.get('schema') != adapter.SCHEMA
            or m.get('training_executed') is not False
            or m.get('source_verified') is not False
            or m.get('within_supplied_records_id_disjoint') is not True
            or type(m.get('n_train')) is not int or not 8 <= m['n_train'] <= adapter.MAX_ROWS
            or type(m.get('n_holdout')) is not int or not 8 <= m['n_holdout'] <= adapter.MAX_ROWS
            or type(m.get('train_rows_sha256')) is not str
            or not HEX64.fullmatch(m['train_rows_sha256'])
            or type(m.get('holdout_rows_sha256')) is not str
            or not HEX64.fullmatch(m['holdout_rows_sha256'])):
        raise ValueError('RUN51_INVALID_ADAPTER_PROVENANCE')
    # Caller-declared 'synthetic' is not proof. Only the preregistered
    # deterministic Run50 FakeReadOnlyView(128) fixture is authorized here.
    if (m.get('n_total') != 128 or m['n_train'] != 89 or m['n_holdout'] != 39
            or m.get('all_rows_sha256') !=
            '2cf785f5d0f991f411bca4a6c4fd6f729f4986ecde3c22c3ee5445f8a1909b2e'
            or m['train_rows_sha256'] !=
            '391ddead524a2ab65d7265fbe65d7a53722c1f5af9346e736498972b3d2b7064'
            or m['holdout_rows_sha256'] !=
            '1f212c95c3ada20db225603880daca7397c6e5c1eb16f6ba19724ff882253d37'):
        raise PermissionError('RUN51_UNREGISTERED_SYNTHETIC_SOURCE')
    train = _arrays(bundle.get('train'), m['n_train'])
    holdout = _arrays(bundle.get('holdout'), m['n_holdout'])
    def array_digest(triple):
        return hashlib.sha256(b''.join(
            np.ascontiguousarray(v, dtype='<f8').tobytes() for v in triple
        )).hexdigest()
    if (array_digest(train) !=
            'cebc931259fa7d22405066b4481f10bac944b8de6eab9c3d0f0359c40fc474cf'
            or array_digest(holdout) !=
            '11a59b45890f4634d2cbb2526fc3dcd25d345d73dc4c5c84fb64de433fa97680'):
        raise PermissionError('RUN51_UNREGISTERED_SYNTHETIC_ARRAYS')
    x, a, x2 = train
    if len(set(np.argmax(a, axis=1))) < 2:
        raise ValueError('RUN51_TRAIN_ACTION_DIVERSITY_REQUIRED')
    rng = np.random.default_rng(seed)
    perm = rng.permutation(len(a))
    shuffled = a[perm].copy()
    if np.array_equal(shuffled, a):
        perm = np.roll(np.arange(len(a)), 1)
        shuffled = a[perm].copy()
    if np.array_equal(shuffled, a):
        raise ValueError('RUN51_ACTION_ABLATION_UNCHANGED')
    observed = wj.WorldJEPA(seed=seed, ensemble=ensemble).fit(
        x, a, x2, steps=steps, log_every=max(1, steps))
    control = wj.WorldJEPA(seed=seed, ensemble=ensemble).fit(
        x, shuffled, x2, steps=steps, log_every=max(1, steps))
    control_hash = hashlib.sha256(
        bytes.fromhex(m['train_rows_sha256'])
        + np.ascontiguousarray(shuffled, dtype='<f8').tobytes()
    ).hexdigest()
    original = audit.evaluate(observed, *holdout,
                              train_source_sha256=m['train_rows_sha256'],
                              holdout_source_sha256=m['holdout_rows_sha256'])
    shuffled_report = audit.evaluate(control, *holdout,
                                     train_source_sha256=control_hash,
                                     holdout_source_sha256=m['holdout_rows_sha256'])
    if (original['status'] != 'SHADOW_OBSERVATION_ONLY'
            or shuffled_report['status'] != 'SHADOW_OBSERVATION_ONLY'):
        raise ValueError('RUN51_HOLDOUT_EVIDENCE_UNAVAILABLE')
    report = {'schema': SCHEMA, 'status': 'SYNTHETIC_SHADOW_ABLATION_ONLY',
              'source_kind': source_kind, 'adapter_rows_sha256': m.get('all_rows_sha256'),
              'train_rows_sha256': m['train_rows_sha256'],
              'holdout_rows_sha256': m['holdout_rows_sha256'],
              'control_train_source_sha256': control_hash,
              'action_permutation_sha256': hashlib.sha256(
                  np.ascontiguousarray(perm.astype('<i8')).tobytes()).hexdigest(),
              'seed': seed, 'steps': steps, 'ensemble': ensemble,
              'observed_action': original, 'shuffled_action': shuffled_report,
              'source_disjointness_verified': False,
              'real_world_causality_proven': False,
              'native_executed': False, 'phone_measured': False,
              'age_authority': 0, 'learning_gate_pass': False,
              'jepa_weight': 0, 'whole_system_complete': False}
    return {'report': report, 'observed_model': observed, 'shuffled_model': control}
