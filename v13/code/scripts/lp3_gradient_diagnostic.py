#!/usr/bin/env python3
"""Preregistered no-update real-LFM350M LP3 gradient diagnostic only."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import time

from scripts.lp3_heldout_utility import (
    SEED, fixture, _tokenizer_prompt, _answer_ids,
)
from scripts.lp3_real_master_smoke import (
    MODEL_ID, REVISION, MASTER_SHA256, verify_master,
)

SMOKE = (
    ('What is the name of my cat?', 'Brombeer'),
    ('What is the name of my dog?', 'Tromso'),
)


def _sum_grad(parameters):
    return sum(float(p.grad.detach().abs().sum()) for p in parameters
               if p.grad is not None)


def _measure(candidate, tok, torch, question, answer):
    prompt = _tokenizer_prompt(tok, question, torch)
    target = _answer_ids(tok, answer, torch)
    with torch.no_grad():
        own = candidate.next_token_logits(prompt, 'own')
        zero = candidate.next_token_logits(prompt, 'zero')
        next_delta = float((own - zero).abs().max())
    result = {'question': question, 'answer': answer,
              'prompt_tokens': int(prompt.shape[1]),
              'answer_tokens': int(target.shape[1]),
              'next_own_zero_delta': next_delta}
    for label, ids in [('full', target), ('first', target[:, :1])]:
        candidate.zero_grad(set_to_none=True)
        loss = candidate.answer_loss(prompt, ids, 'own')
        loss.backward()
        pred = _sum_grad(candidate.predictor.parameters())
        proj = _sum_grad(candidate.prefix_projector.parameters())
        result[label + '_ce'] = float(loss.detach())
        result[label + '_predictor_grad_abs_sum'] = pred
        result[label + '_projector_grad_abs_sum'] = proj
        result[label + '_grad_finite'] = all(
            math.isfinite(x) for x in (float(loss.detach()), pred, proj))
    return result


def run(master):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from v13.lp3_state_prefix import StateConditionedPrefix

    started = time.monotonic()
    torch.set_num_threads(4)
    torch.manual_seed(SEED)
    tok = AutoTokenizer.from_pretrained(str(master), local_files_only=True)
    base = AutoModelForCausalLM.from_pretrained(
        str(master), dtype=torch.float32, local_files_only=True)
    base.eval()
    candidate = StateConditionedPrefix(base, prefix_tokens=2)
    candidate.train()
    sample = next(base.parameters()).detach().flatten()[:2048]
    before = hashlib.sha256(sample.cpu().numpy().tobytes()).hexdigest()
    rows = fixture()
    measured = [_measure(candidate, tok, torch, row['train'], row['answer'])
                for row in rows]
    smoke = [_measure(candidate, tok, torch, q, a) for q, a in SMOKE]
    prompts = [_tokenizer_prompt(tok, q, torch) for q, _ in SMOKE]
    if prompts[0].shape != prompts[1].shape:
        raise ValueError('Original smoke prompt shapes unexpectedly differ')
    prompt_batch = torch.cat(prompts, dim=0)
    first_targets = [_answer_ids(tok, a, torch)[:, :1] for _, a in SMOKE]
    target_batch = torch.cat(first_targets, dim=0)
    candidate.zero_grad(set_to_none=True)
    batch_loss = candidate.answer_loss(prompt_batch, target_batch, 'own')
    batch_loss.backward()
    batch = {
        'prompt_tokens': int(prompt_batch.shape[1]),
        'batch_size': 2,
        'first_answer_token_only': True,
        'ce': float(batch_loss.detach()),
        'predictor_grad_abs_sum': _sum_grad(candidate.predictor.parameters()),
        'projector_grad_abs_sum': _sum_grad(candidate.prefix_projector.parameters()),
    }
    if any(p.grad is not None or p.requires_grad for p in base.parameters()):
        raise ValueError('Frozen base gradient/trainability violation')
    after = hashlib.sha256(sample.cpu().numpy().tobytes()).hexdigest()
    if before != after:
        raise ValueError('Frozen base parameter changed without optimizer')
    return {
        'schema': 'lp3-gradient-diagnostic-v1',
        'status': 'LP3_GRADIENT_DIAGNOSTIC_COMPLETE',
        'evidence_class': 'LINUX_NATIVE_DIAGNOSTIC_NO_UPDATES',
        'model_id': MODEL_ID, 'revision': REVISION,
        'master_sha256': MASTER_SHA256, 'seed': SEED,
        'original_failed_run': 40527420680,
        'optimizer_updates': 0, 'prefix_tokens': 2,
        'six_train_prompt_gradients': measured,
        'two_compatibility_single_prompt_gradients': smoke,
        'compatibility_two_row_batch': batch,
        'frozen_base_sample_sha256': before,
        'frozen_base_gradients': False,
        'elapsed_s': round(time.monotonic() - started, 3),
        'utility_proven': False, 'jepa_weight': 0,
        'age_authority': 0, 'redmi_measured': False,
        'whole_system_complete': False,
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
        raise ValueError('Refusing to replace diagnostic receipt')
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
