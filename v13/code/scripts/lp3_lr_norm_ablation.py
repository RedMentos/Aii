#!/usr/bin/env python3
"""Preregistered LP3 2x2 LR/frozen-feature normalization diagnostic.

Four identical-start 24-step native 350M arms. No heldout evaluation, learning
authority, production hook, persisted weights, or claim of JEPA/answer utility.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import time

from scripts import lp3_optimizer_trajectory as trajectory
from scripts.lp3_heldout_utility import (
    SEED, STEPS, LR, fixture, audit_fixture, _tokenizer_prompt, _answer_ids,
)
from scripts.lp3_real_master_smoke import (
    MODEL_ID, REVISION, MASTER_SHA256, verify_master,
)

LOW_LR = 0.0005
NORMALIZATION_EPS = 1e-5
ARMS = (('raw', LR), ('raw', LOW_LR),
        ('layernorm', LR), ('layernorm', LOW_LR))


def normalize_frozen_features(features, torch):
    """No fitted statistics, affine parameters, heldout data, or gradients."""
    if (features.ndim != 2 or not features.shape[0] or not features.shape[1]
            or not bool(torch.isfinite(features).all())):
        raise ValueError('Invalid frozen prompt features for normalization')
    return torch.nn.functional.layer_norm(
        features, (features.shape[-1],), eps=NORMALIZATION_EPS)


def _candidate_class():
    from v13.lp3_state_prefix import StateConditionedPrefix

    class NormalizedFrozenPrompt(StateConditionedPrefix):
        def prompt_features(self, prompt_ids):
            import torch
            raw = super().prompt_features(prompt_ids)
            return normalize_frozen_features(raw, torch)

    return StateConditionedPrefix, NormalizedFrozenPrompt


def _train(candidate, tok, torch, rows, lr):
    if type(lr) is not float or lr not in (LR, LOW_LR):
        raise ValueError('Only preregistered learning rates are allowed')
    optimizer = torch.optim.AdamW(
        candidate.trainable_parameters(), lr=lr, weight_decay=0.0)
    trace = []
    for step in range(STEPS):
        row = rows[step % len(rows)]
        prompt = _tokenizer_prompt(tok, row['train'], torch)
        target = _answer_ids(tok, row['answer'], torch)
        candidate.train()
        optimizer.zero_grad(set_to_none=True)
        loss = candidate.answer_loss(prompt, target, 'own')
        loss_finite = bool(torch.isfinite(loss))
        item = {'step': step, 'key': row['key'],
                'loss_finite': loss_finite,
                'loss': float(loss.detach()) if loss_finite else None}
        if not loss_finite:
            item.update(pred_finite=False, proj_finite=False,
                        pred_abs_sum=None, proj_abs_sum=None,
                        pred_missing_tensors=None, proj_missing_tensors=None,
                        tanh_saturation_fraction=None,
                        update_abs_sum=None, optimizer_moments_finite=False)
            trace.append(item)
            break
        loss.backward()
        pred = trajectory._grad_stat(candidate.predictor, torch)
        proj = trajectory._grad_stat(candidate.prefix_projector, torch)
        item.update(pred_finite=pred['finite'], proj_finite=proj['finite'],
                    pred_abs_sum=pred['abs_sum'], proj_abs_sum=proj['abs_sum'],
                    pred_missing_tensors=pred['missing_tensors'],
                    proj_missing_tensors=proj['missing_tensors'],
                    pred_nonfinite_elements=pred['nonfinite_elements'],
                    proj_nonfinite_elements=proj['nonfinite_elements'])
        if any(p.grad is not None or p.requires_grad
               for p in candidate.base.parameters()):
            raise ValueError('Frozen base gradient/trainability violation')
        with torch.no_grad():
            features = candidate.prompt_features(prompt)
            z = candidate.predictor(features)
            item['tanh_saturation_fraction'] = float(
                (z.abs() >= .999).float().mean())
        if not pred['finite'] or not proj['finite']:
            item.update(update_abs_sum=None, optimizer_moments_finite=False)
            trace.append(item)
            break
        old = [p.detach().clone() for p in candidate.trainable_parameters()]
        optimizer.step()
        delta = sum(float((p.detach()-prior).abs().double().sum())
                    for p, prior in zip(candidate.trainable_parameters(), old))
        item['update_abs_sum'] = delta if math.isfinite(delta) else None
        item['optimizer_moments_finite'] = trajectory._optimizer_finite(
            optimizer, torch)
        trace.append(item)
        if item['update_abs_sum'] is None or not item['optimizer_moments_finite']:
            break
    positive = sum(int(r['pred_abs_sum'] is not None
                       and r['pred_abs_sum'] > 0) for r in trace)
    saturations = [r['tanh_saturation_fraction'] for r in trace
                   if r['tanh_saturation_fraction'] is not None]
    return {
        'trace': trace, 'steps_recorded': len(trace),
        'positive_predictor_gradient_steps': positive,
        'first_issue': trajectory.first_issue(trace),
        'mean_tanh_saturation_fraction': (
            sum(saturations)/len(saturations) if saturations else None),
        'all_24_gradients_positive': (
            len(trace) == STEPS and all(
                r['loss_finite'] and r['pred_finite'] and r['proj_finite']
                and r['pred_abs_sum'] is not None and r['pred_abs_sum'] > 0
                and r['proj_abs_sum'] is not None and r['proj_abs_sum'] > 0
                and r['optimizer_moments_finite'] for r in trace)),
    }


def run(master):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    start = time.monotonic()
    torch.set_num_threads(4)
    torch.manual_seed(SEED)
    rows = fixture()
    audit_fixture(rows)
    tok = AutoTokenizer.from_pretrained(str(master), local_files_only=True)
    base = AutoModelForCausalLM.from_pretrained(
        str(master), dtype=torch.float32, local_files_only=True)
    base.eval()
    raw_class, normalized_class = _candidate_class()
    initial = raw_class(base, prefix_tokens=2)
    pred_init = {k: v.detach().clone()
                 for k, v in initial.predictor.state_dict().items()}
    proj_init = {k: v.detach().clone()
                 for k, v in initial.prefix_projector.state_dict().items()}
    initial_hash = trajectory._param_hash(initial)
    sample = next(base.parameters()).detach().flatten()[:2048]
    base_before = hashlib.sha256(sample.cpu().numpy().tobytes()).hexdigest()
    output = []
    for normalization, lr in ARMS:
        cls = raw_class if normalization == 'raw' else normalized_class
        candidate = cls(base, prefix_tokens=2)
        candidate.predictor.load_state_dict(pred_init)
        candidate.prefix_projector.load_state_dict(proj_init)
        if trajectory._param_hash(candidate) != initial_hash:
            raise ValueError('Arm initialization differs from preregistered start')
        arm = _train(candidate, tok, torch, rows, lr)
        arm.update(normalization=normalization, lr=lr,
                   initial_trainable_sha256=initial_hash,
                   final_trainable_sha256=trajectory._param_hash(candidate))
        output.append(arm)
        del candidate
    base_after = hashlib.sha256(sample.cpu().numpy().tobytes()).hexdigest()
    if base_before != base_after or any(
            p.grad is not None or p.requires_grad for p in base.parameters()):
        raise ValueError('Frozen base integrity violation')
    return {
        'schema': 'lp3-lr-norm-ablation-v1',
        'status': 'LP3_FOUR_ARM_MECHANISM_DIAGNOSTIC_ONLY',
        'evidence_class': 'LINUX_NATIVE_TRAINING_DIAGNOSTIC_NOT_UTILITY',
        'model_id': MODEL_ID, 'revision': REVISION,
        'master_sha256': MASTER_SHA256, 'seed': SEED,
        'steps_per_arm': STEPS, 'lr_values': [LR, LOW_LR],
        'normalization': ['raw', 'frozen_prompt_layernorm_eps1e-5'],
        'train_prompts': len(rows), 'prefix_tokens': 2,
        'initial_trainable_sha256': initial_hash,
        'frozen_base_sample_sha256': base_before,
        'arms': output, 'elapsed_s': round(time.monotonic()-start, 3),
        'heldout_scored': False, 'retention_scored': False,
        'utility_proven': False, 'jepa_weight': 0, 'age_authority': 0,
        'redmi_measured': False, 'whole_system_complete': False,
    }


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--master', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--execute-native', action='store_true')
    args = ap.parse_args(argv)
    if not args.execute_native:
        raise ValueError('Explicit --execute-native required')
    verify_master(args.master)
    if args.out.exists() or args.out.is_symlink():
        raise ValueError('Refusing to replace prior ablation receipt')
    data = json.dumps(run(args.master), sort_keys=True,
                      separators=(',', ':'), allow_nan=False) + '\n'
    with args.out.open('x', encoding='utf-8') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    print(data, end='', flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
