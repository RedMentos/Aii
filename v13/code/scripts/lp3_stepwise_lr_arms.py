#!/usr/bin/env python3
"""Preregistered two-arm LP3 optimizer trace; experimental, no V13 gate."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import time

from scripts.lp3_real_master_smoke import MODEL_ID, REVISION, MASTER_SHA256, verify_master
from scripts.lp3_heldout_utility import (
    SEED, STEPS, fixture, audit_fixture, evaluate, retention_ce,
    summarize, classify, _tokenizer_prompt, _answer_ids,
)

ARMS = (('A_original_lr', 0.005), ('B_low_lr', 0.0005))


def _grad_sum(parameters):
    return sum(float(p.grad.detach().abs().sum())
               for p in parameters if p.grad is not None)


def _param_norm(parameters):
    return math.sqrt(sum(float((p.detach() ** 2).sum()) for p in parameters))


def _finite(x):
    return x if math.isfinite(x) else str(x)


def run_arm(base, tok, torch, rows, name, lr):
    from v13.lp3_state_prefix import StateConditionedPrefix

    # Same predictor/projector initialization, independent optimizer states.
    torch.manual_seed(SEED)
    candidate = StateConditionedPrefix(base, prefix_tokens=2)
    initial_params = [p.detach().clone() for p in candidate.trainable_parameters()]
    before_rows = evaluate(candidate, base, tok, rows, torch)
    before = summarize(before_rows)
    retention_before = retention_ce(candidate, tok, torch)
    optimizer = torch.optim.AdamW(candidate.trainable_parameters(),
                                  lr=lr, weight_decay=0.0)
    trace = []
    first_bad = None
    for step in range(STEPS):
        row = rows[step % len(rows)]
        prompt = _tokenizer_prompt(tok, row['train'], torch)
        answer = _answer_ids(tok, row['answer'], torch)
        candidate.train()
        optimizer.zero_grad(set_to_none=True)
        loss = candidate.answer_loss(prompt, answer, 'own')
        loss.backward()
        pred = _grad_sum(candidate.predictor.parameters())
        proj = _grad_sum(candidate.prefix_projector.parameters())
        ce = float(loss.detach())
        ok = all(math.isfinite(x) and x > 0 for x in (pred, proj)) and math.isfinite(ce)
        if any(p.grad is not None or p.requires_grad for p in base.parameters()):
            raise ValueError('Frozen base gradient/trainability violation')
        trace.append({
            'step': step + 1, 'key': row['key'], 'ce': _finite(ce),
            'predictor_grad_abs_sum': _finite(pred),
            'projector_grad_abs_sum': _finite(proj),
            'predictor_param_norm': _finite(_param_norm(candidate.predictor.parameters())),
            'projector_param_norm': _finite(_param_norm(candidate.prefix_projector.parameters())),
            'gradients_finite_nonzero': ok,
        })
        if not ok:
            first_bad = step + 1
            break
        optimizer.step()
    completed = len(trace) if first_bad is None else first_bad - 1
    changed = any(not torch.equal(old, new.detach()) for old, new in
                  zip(initial_params, candidate.trainable_parameters()))
    result = {
        'name': name, 'lr': lr, 'seed': SEED, 'intended_updates': STEPS,
        'completed_updates': completed,
        'first_bad_step': first_bad,
        'trainable_parameters_changed': changed,
        'before': before, 'retention_before': retention_before,
        'step_trace': trace,
        'heldout_raw_before': before_rows,
    }
    if first_bad is not None:
        result['status'] = 'GRADIENT_COLLAPSE_OR_NONFINITE'
        result['attributable_signal'] = False
        return result
    if completed != STEPS or not changed:
        raise ValueError('Completed arm missing updates or parameter change')
    after_rows = evaluate(candidate, base, tok, rows, torch)
    after = summarize(after_rows)
    retention_after = retention_ce(candidate, tok, torch)
    if (abs(before['base_ce'] - after['base_ce']) > 1e-7
            or before['base_top1'] != after['base_top1']):
        raise ValueError('Frozen no-prefix base baseline drifted')
    status, criteria = classify(before, after, retention_before,
                                retention_after, True)
    result.update({
        'status': status, 'attributable_signal': status == 'LP3_HELDOUT_ATTRIBUTABLE_SIGNAL',
        'after': after, 'retention_after': retention_after,
        'criteria': criteria, 'heldout_raw_after': after_rows,
    })
    return result


def run(master):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    started = time.monotonic()
    torch.set_num_threads(4)
    torch.manual_seed(SEED)
    rows = fixture()
    audit_fixture(rows)
    dataset_sha = hashlib.sha256(json.dumps(
        rows, sort_keys=True, separators=(',', ':')).encode('utf-8')).hexdigest()
    tok = AutoTokenizer.from_pretrained(str(master), local_files_only=True)
    base = AutoModelForCausalLM.from_pretrained(
        str(master), dtype=torch.float32, local_files_only=True)
    base.eval()
    sample = next(base.parameters()).detach().flatten()[:2048]
    frozen_before = hashlib.sha256(sample.cpu().numpy().tobytes()).hexdigest()
    arms = []
    for name, lr in ARMS:
        arms.append(run_arm(base, tok, torch, rows, name, lr))
        if hashlib.sha256(sample.cpu().numpy().tobytes()).hexdigest() != frozen_before:
            raise ValueError('Frozen base parameter sample changed')
    return {
        'schema': 'lp3-stepwise-lr-arms-v1',
        'status': 'LP3_STEPWISE_TWO_ARMS_RECORDED',
        'evidence_class': 'LINUX_NATIVE_EXPERIMENTAL_TWO_ARM',
        'model_id': MODEL_ID, 'revision': REVISION,
        'master_sha256': MASTER_SHA256, 'dataset_sha256': dataset_sha,
        'seed': SEED, 'intended_steps_per_arm': STEPS,
        'arms': arms,
        'frozen_base_sample_sha256': frozen_before,
        'frozen_base_gradients': False,
        'elapsed_s': round(time.monotonic() - started, 3),
        'jepa_weight': 0, 'age_authority': 0,
        'redmi_measured': False, 'whole_system_complete': False,
        'production_utility_proven': False,
        'original_failed_run_unchanged': 40527420680,
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
        raise ValueError('Refusing to replace arm evidence')
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
