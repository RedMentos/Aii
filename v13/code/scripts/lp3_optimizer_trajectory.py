#!/usr/bin/env python3
"""LP3 frozen-350M optimizer/evaluation-state trajectory diagnosis, no utility claim.

Separate preregistered cohort; original failed LP3 heldout pilot is untouched.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import time

from scripts.lp3_heldout_utility import (
    SEED, STEPS, LR, fixture, audit_fixture, _tokenizer_prompt, _answer_ids,
    evaluate, retention_ce,
)
from scripts.lp3_real_master_smoke import MODEL_ID, REVISION, MASTER_SHA256, verify_master


def first_issue(trace):
    """Software-verifiable first missing/nonfinite gradient, never a utility verdict."""
    for row in trace:
        if not row['loss_finite'] or not row['pred_finite'] or not row['proj_finite']:
            return {'step': row['step'], 'kind': 'NONFINITE'}
        if row['pred_abs_sum'] == 0 or row['proj_abs_sum'] == 0:
            return {'step': row['step'], 'kind': 'ZERO_GRADIENT'}
        if row.get('optimizer_moments_finite') is False:
            return {'step': row['step'], 'kind': 'OPTIMIZER_NONFINITE'}
        if 'update_abs_sum' in row and row['update_abs_sum'] is None:
            return {'step': row['step'], 'kind': 'UPDATE_NONFINITE'}
    return None


def _grad_stat(module, torch):
    params = list(module.parameters())
    grads = [p.grad for p in params]
    present = sum(g is not None for g in grads)
    missing = len(params) - present
    # A missing tensor must not hide NaN/Inf in a different present tensor.
    # Stop the optimizer on any nonfinite gradient, even for a partial graph.
    nonfinite = sum(int((~torch.isfinite(g)).sum()) for g in grads if g is not None)
    if nonfinite:
        return {'abs_sum': None, 'finite': False, 'missing_tensors': missing,
                'nonfinite_elements': nonfinite}
    if missing:
        return {'abs_sum': 0., 'finite': True, 'missing_tensors': missing,
                'nonfinite_elements': 0}
    # Accumulate in float64: finite FP32 elements can overflow an FP32 sum.
    total = sum(float(g.detach().abs().double().sum()) for g in grads)
    return {'abs_sum': total if math.isfinite(total) else None,
            'finite': math.isfinite(total), 'missing_tensors': 0,
            'nonfinite_elements': 0}


def _param_hash(candidate):
    h = hashlib.sha256()
    for module in (candidate.predictor, candidate.prefix_projector):
        for key, tensor in sorted(module.state_dict().items()):
            h.update(key.encode())
            h.update(tensor.detach().cpu().contiguous().numpy().tobytes())
    return h.hexdigest()


def _optimizer_finite(opt, torch):
    for state in opt.state.values():
        for name in ('exp_avg', 'exp_avg_sq'):
            t = state.get(name)
            if t is not None and not bool(torch.isfinite(t).all()):
                return False
    return True


def _train_arm(candidate, tok, torch, rows, pre_eval):
    candidate.train()
    pre_eval_count = 0
    if pre_eval:
        # Reproduce original pilot's evaluation-state transition, without using
        # heldout scores to choose any update or publish a utility verdict.
        pre = evaluate(candidate, candidate.base, tok, rows, torch)
        pre_eval_count = len(pre)
        retention_ce(candidate, tok, torch)
    opt = torch.optim.AdamW(candidate.trainable_parameters(), lr=LR, weight_decay=0.0)
    trace = []
    for step in range(STEPS):
        row = rows[step % len(rows)]
        prompt = _tokenizer_prompt(tok, row['train'], torch)
        target = _answer_ids(tok, row['answer'], torch)
        candidate.train()
        opt.zero_grad(set_to_none=True)
        loss = candidate.answer_loss(prompt, target, 'own')
        loss_finite = bool(torch.isfinite(loss))
        entry = {'step': step, 'key': row['key'], 'loss_finite': loss_finite,
                 'loss': float(loss.detach()) if loss_finite else None}
        if not loss_finite:
            entry.update(pred_finite=False, proj_finite=False,
                         pred_abs_sum=None, proj_abs_sum=None,
                         pred_missing_tensors=None, proj_missing_tensors=None,
                         pred_nonfinite_elements=None, proj_nonfinite_elements=None,
                         tanh_saturation_fraction=None, update_abs_sum=None,
                         optimizer_moments_finite=False)
            trace.append(entry)
            break
        loss.backward()
        pred = _grad_stat(candidate.predictor, torch)
        proj = _grad_stat(candidate.prefix_projector, torch)
        entry.update(pred_finite=pred['finite'], proj_finite=proj['finite'],
                     pred_abs_sum=pred['abs_sum'], proj_abs_sum=proj['abs_sum'],
                     pred_missing_tensors=pred['missing_tensors'],
                     proj_missing_tensors=proj['missing_tensors'],
                     pred_nonfinite_elements=pred['nonfinite_elements'],
                     proj_nonfinite_elements=proj['nonfinite_elements'])
        if any(p.grad is not None or p.requires_grad for p in candidate.base.parameters()):
            raise ValueError('Frozen base gradient/trainability violation')
        with torch.no_grad():
            features = candidate.prompt_features(prompt)
            z = candidate.predictor(features)
            entry['tanh_saturation_fraction'] = float((z.abs() >= .999).float().mean())
        if not pred['finite'] or not proj['finite']:
            entry.update(update_abs_sum=None, optimizer_moments_finite=False)
            trace.append(entry)
            break
        before = [p.detach().clone() for p in candidate.trainable_parameters()]
        opt.step()
        delta = sum(float((p.detach()-old).abs().double().sum())
                    for p, old in zip(candidate.trainable_parameters(), before))
        entry['update_abs_sum'] = delta if math.isfinite(delta) else None
        entry['optimizer_moments_finite'] = _optimizer_finite(opt, torch)
        trace.append(entry)
        if not entry['optimizer_moments_finite'] or entry['update_abs_sum'] is None:
            break
    return {'pre_eval': bool(pre_eval), 'pre_eval_rows': pre_eval_count,
            'trace': trace, 'first_issue': first_issue(trace),
            'steps_recorded': len(trace), 'all_24_gradients_positive': (
                len(trace) == STEPS and all(
                    x['loss_finite'] and x['pred_finite'] and x['proj_finite']
                    and x['pred_abs_sum'] is not None and x['pred_abs_sum'] > 0
                    and x['proj_abs_sum'] is not None and x['proj_abs_sum'] > 0
                    and x['optimizer_moments_finite'] for x in trace))}


def run(master):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from v13.lp3_state_prefix import StateConditionedPrefix

    started = time.monotonic()
    torch.set_num_threads(4)
    torch.manual_seed(SEED)
    rows = fixture()
    audit_fixture(rows)
    tok = AutoTokenizer.from_pretrained(str(master), local_files_only=True)
    base = AutoModelForCausalLM.from_pretrained(
        str(master), dtype=torch.float32, local_files_only=True)
    base.eval()
    candidate = StateConditionedPrefix(base, prefix_tokens=2)
    initial_pred = {k: v.detach().clone() for k, v in candidate.predictor.state_dict().items()}
    initial_proj = {k: v.detach().clone() for k, v in candidate.prefix_projector.state_dict().items()}
    initial_hash = _param_hash(candidate)
    sample = next(base.parameters()).detach().flatten()[:2048]
    frozen_before = hashlib.sha256(sample.cpu().numpy().tobytes()).hexdigest()
    arms = []
    for pre_eval in (True, False):
        candidate.predictor.load_state_dict(initial_pred)
        candidate.prefix_projector.load_state_dict(initial_proj)
        candidate.zero_grad(set_to_none=True)
        if _param_hash(candidate) != initial_hash:
            raise ValueError('Diagnostic arms did not start from identical trainable weights')
        arm = _train_arm(candidate, tok, torch, rows, pre_eval)
        arm['initial_trainable_sha256'] = initial_hash
        arm['final_trainable_sha256'] = _param_hash(candidate)
        arms.append(arm)
    frozen_after = hashlib.sha256(sample.cpu().numpy().tobytes()).hexdigest()
    if frozen_before != frozen_after:
        raise ValueError('Frozen base changed during diagnostic')
    if any(p.grad is not None or p.requires_grad for p in base.parameters()):
        raise ValueError('Frozen base gradients at completion')
    return {
        'schema': 'lp3-optimizer-trajectory-v1',
        'status': 'LP3_OPTIMIZER_DIAGNOSTIC_RECORDED',
        'evidence_class': 'LINUX_NATIVE_DIAGNOSTIC_NOT_UTILITY',
        'model_id': MODEL_ID, 'revision': REVISION,
        'master_sha256': MASTER_SHA256,
        'original_failed_run': 40527420680,
        'seed': SEED, 'steps_per_arm': STEPS, 'lr': LR, 'prefix_tokens': 2,
        'train_prompts': 6, 'arms': arms,
        'frozen_base_sample_sha256': frozen_before,
        'frozen_base_gradients': False,
        'elapsed_s': round(time.monotonic()-started, 3),
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
        raise ValueError('Refusing to replace trajectory receipt')
    data = json.dumps(run(args.master), sort_keys=True,
                      separators=(',', ':'), allow_nan=False) + '\n'
    with args.out.open('x', encoding='utf-8') as stream:
        stream.write(data)
        stream.flush(); os.fsync(stream.fileno())
    print(data, end='', flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
