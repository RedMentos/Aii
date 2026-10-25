"""Run166 isolated FP32 master/autograd/EMA plumbing micro, NOT JEPA training.

Requires Run163 source-bound verification. Synthetic quadratic target only;
never writes inference GGUF or input master, no learning/Runtime authority.
"""
import hashlib
from pathlib import Path
import numpy as np
import torch
from scripts.body_fp32_export_verify_run163 import verify, digest, GATES

LR = 0.1
MAX_UPDATE_L2 = 0.2
EMA_BETA = 0.9


def micro(model, master, report, expected_sha, candidate):
    model, master, report, candidate = map(Path, (model, master, report, candidate))
    if candidate.is_symlink() or candidate.exists():
        raise FileExistsError('candidate_exists_or_symlink')
    if candidate.resolve(strict=False) in (model.resolve(), master.resolve(), report.resolve()):
        raise ValueError('candidate_overlaps_source')
    original_master_sha = digest(master)
    source_audit = verify(model, master, report, expected_sha)
    names = []
    baseline, updated, ema = {}, {}, {}
    grads, steps = [], []
    with np.load(master, allow_pickle=False) as z:
        names = sorted(z.files)
        if len(names) != source_audit['selected_count']:
            raise ValueError('selection_mismatch')
        for name in names:
            x = z[name]
            if x.dtype != np.dtype('<f4') or x.ndim != 1 or not np.isfinite(x).all():
                raise ValueError('source_vector_invalid')
            baseline[name] = x.copy()
            w = torch.tensor(x.copy(), dtype=torch.float32, requires_grad=True)
            target = w.detach().clone() + 0.01  # SYNTHETIC, not a JEPA target.
            loss = torch.sum((w - target) ** 2)
            (grad,) = torch.autograd.grad(loss, w)
            if not bool(torch.isfinite(grad).all()) or not bool(torch.any(grad != 0)):
                raise ValueError('zero_or_nonfinite_gradient')
            grads.append(grad.detach().numpy().copy())
    total_norm = float(np.sqrt(sum(float(np.sum((LR * g.astype(np.float64)) ** 2)) for g in grads)))
    if not np.isfinite(total_norm) or total_norm <= 0:
        raise ValueError('invalid_step_norm')
    scale = min(1., MAX_UPDATE_L2 / total_norm)
    report_rows = []
    for name, grad in zip(names, grads):
        w0 = baseline[name]
        delta = (-LR * scale * grad).astype('<f4')
        w1 = (w0 + delta).astype('<f4')
        slow = (EMA_BETA * w0.astype(np.float64) + (1 - EMA_BETA) * w1.astype(np.float64)).astype('<f4')
        before = float(np.sum((w0.astype(np.float64) - (w0.astype(np.float64) + .01)) ** 2))
        after = float(np.sum((w1.astype(np.float64) - (w0.astype(np.float64) + .01)) ** 2))
        if not np.isfinite(w1).all() or not np.isfinite(slow).all() or not after < before:
            raise ValueError('micro_update_not_finite_or_improving')
        if not np.all(np.abs(slow.astype(np.float64) - w0) <= np.abs(w1.astype(np.float64) - w0) + 1e-6):
            raise ValueError('ema_outside_segment')
        updated[name], ema[name] = w1, slow
        steps.append(delta.astype(np.float64))
        report_rows.append({'name': name, 'gradient_l2': float(np.linalg.norm(grad)),
                            'applied_update_l2': float(np.linalg.norm(delta)),
                            'synthetic_loss_before': before, 'synthetic_loss_after': after})
    applied_norm = float(np.sqrt(sum(float(np.sum(d*d)) for d in steps)))
    if applied_norm > MAX_UPDATE_L2 + 1e-5:
        raise ValueError('update_budget_exceeded')
    arrays = {}
    for name in names:
        arrays['baseline__' + name] = baseline[name]
        arrays['updated__' + name] = updated[name]
        arrays['ema__' + name] = ema[name]
    with candidate.open('xb') as f:
        np.savez(f, **arrays)
    with np.load(candidate, allow_pickle=False) as z:
        if sorted(z.files) != sorted(arrays):
            raise ValueError('checkpoint_names')
        if any(z[k].tobytes() != v.tobytes() for k,v in arrays.items()):
            raise ValueError('checkpoint_reload_bytes')
        if any(z['baseline__' + name].tobytes() != baseline[name].tobytes() for name in names):
            raise ValueError('rollback_mismatch')
    if digest(model) != expected_sha or digest(master) != original_master_sha:
        raise ValueError('source_modified')
    return {'schema': 'V13_RUN166_FP32_MASTER_MICRO_V1',
            'registered_model_sha256': expected_sha, 'source_master_sha256': original_master_sha,
            'private_candidate_sha256': digest(candidate), 'private_candidate_bytes': candidate.stat().st_size,
            'selected_tensors': len(names), 'synthetic_objective': 'QUADRATIC_W0_PLUS_0P01_NOT_JEPA',
            'learning_rate': LR, 'max_update_l2': MAX_UPDATE_L2,
            'applied_update_l2': applied_norm, 'ema_beta': EMA_BETA,
            'gradients_finite_nonzero': True, 'exclusive_persist_reload': True,
            'rollback_exact_baseline': True, 'inference_gguf_unchanged': True,
            'input_master_unchanged': True, 'per_tensor': report_rows,
            'body_training_authority': 0, 'jepa_weight': 0, 'gates': GATES,
            'gate': 'UNVERIFIED', 'evidence_class': 'ISOLATED_SYNTHETIC_GRADIENT_ON_SOURCE_BOUND_FP32',
            'limitations': ['synthetic quadratic objective is NOT JEPA or semantic learning',
                            'no native body update, inference integration, requantization or retention',
                            'no answer utility or Redmi evidence; private candidate weights never publish']}
