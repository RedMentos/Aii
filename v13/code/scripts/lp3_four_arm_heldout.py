#!/usr/bin/env python3
"""Preregistered LP3 four-arm answer/retention readout; research only.

Same six synthetic facts and 24-step optimizer cohort as original LP3, plus
disjoint heldout phrasings. No training on heldout, no weight persistence.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import time

from scripts import lp3_lr_norm_ablation as ablation
from scripts import lp3_optimizer_trajectory as trajectory
from scripts.lp3_heldout_utility import (
    SEED, STEPS, LR, fixture, audit_fixture, evaluate, summarize, classify,
    retention_ce,
)
from scripts.lp3_real_master_smoke import (
    MODEL_ID, REVISION, MASTER_SHA256, verify_master,
)

FRESH_TEMPLATES = (
    'For the registry key {key}, what marker is recorded?',
    'Read the registry: {key} maps to which marker?',
)


def _digest(value):
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(',', ':'),
        ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def fresh_rows(rows):
    audit_fixture(rows)
    result = []
    originals = {p.casefold() for row in rows
                 for p in [row['train'], *row['heldout']]}
    for index, row in enumerate(rows):
        next_key = rows[(index+1) % len(rows)]['key']
        new = dict(row)
        new['heldout'] = [t.format(key=row['key']) for t in FRESH_TEMPLATES]
        new['wrong_sources'] = [t.format(key=next_key) for t in FRESH_TEMPLATES]
        answer = row['answer'].strip().casefold()
        for question in [*new['heldout'], *new['wrong_sources']]:
            if answer in question.casefold() or question.casefold() in originals:
                raise ValueError('New heldout question overlaps training/answer/old cohort')
        if any(a == b for a, b in zip(new['heldout'], new['wrong_sources'])):
            raise ValueError('New wrong-source question matches target')
        result.append(new)
    if len({p for row in result for p in row['heldout']}) != 12:
        raise ValueError('Fresh heldout family must have twelve distinct prompts')
    return result


def _gain(before, after):
    return {
        'own_ce_gain': float(before['own_ce']-after['own_ce']),
        'own_vs_wrong_ce_after': float(after['wrong_ce']-after['own_ce']),
        'own_vs_zero_ce_after': float(after['zero_ce']-after['own_ce']),
        'own_gain_over_wrong_gain': float(
            (before['own_ce']-after['own_ce'])
            -(before['wrong_ce']-after['wrong_ce'])),
        'own_top1_after': int(after['own_top1']),
        'wrong_top1_after': int(after['wrong_top1']),
        'zero_top1_after': int(after['zero_top1']),
    }


def _score_family(candidate, base, tok, rows, torch):
    return summarize(evaluate(candidate, base, tok, rows, torch))


def run(master):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    start = time.monotonic()
    torch.set_num_threads(4)
    torch.manual_seed(SEED)
    rows = fixture()
    audit_fixture(rows)
    new_rows = fresh_rows(rows)
    tok = AutoTokenizer.from_pretrained(str(master), local_files_only=True)
    base = AutoModelForCausalLM.from_pretrained(
        str(master), dtype=torch.float32, local_files_only=True)
    base.eval()
    raw_class, normalized_class = ablation._candidate_class()
    initial = raw_class(base, prefix_tokens=2)
    pred_init = {k: v.detach().clone()
                 for k, v in initial.predictor.state_dict().items()}
    proj_init = {k: v.detach().clone()
                 for k, v in initial.prefix_projector.state_dict().items()}
    initial_hash = trajectory._param_hash(initial)
    sample = next(base.parameters()).detach().flatten()[:2048]
    base_hash = hashlib.sha256(sample.cpu().numpy().tobytes()).hexdigest()
    arms = []
    for normalization, lr in ablation.ARMS:
        cls = raw_class if normalization == 'raw' else normalized_class
        candidate = cls(base, prefix_tokens=2)
        candidate.predictor.load_state_dict(pred_init)
        candidate.prefix_projector.load_state_dict(proj_init)
        if trajectory._param_hash(candidate) != initial_hash:
            raise ValueError('Arm did not start from fixed weights')
        before = {
            'original': _score_family(candidate, base, tok, rows, torch),
            'new_phrasings': _score_family(candidate, base, tok, new_rows, torch),
        }
        retention_before = retention_ce(candidate, tok, torch)
        diagnostic = ablation._train(candidate, tok, torch, rows, lr)
        after = {
            'original': _score_family(candidate, base, tok, rows, torch),
            'new_phrasings': _score_family(candidate, base, tok, new_rows, torch),
        }
        retention_after = retention_ce(candidate, tok, torch)
        retention_delta = float(retention_after-retention_before)
        statuses, criteria = {}, {}
        for name in ('original', 'new_phrasings'):
            statuses[name], criteria[name] = classify(
                before[name], after[name],
                retention_before, retention_after, True)
        # This is explicitly exploratory: the same six facts were trained on.
        both = all(statuses[name]=='LP3_HELDOUT_ATTRIBUTABLE_SIGNAL'
                   for name in statuses)
        arms.append({
            'normalization': normalization, 'lr': lr,
            'initial_trainable_sha256': initial_hash,
            'final_trainable_sha256': trajectory._param_hash(candidate),
            'train_positive_predictor_steps':
                diagnostic['positive_predictor_gradient_steps'],
            'train_first_issue': diagnostic['first_issue'],
            'train_mean_tanh_saturation':
                diagnostic['mean_tanh_saturation_fraction'],
            'train_steps_recorded': diagnostic['steps_recorded'],
            'before': before, 'after': after,
            'gain': {name: _gain(before[name], after[name])
                     for name in before},
            'retention_before': retention_before,
            'retention_after': retention_after,
            'retention_delta': retention_delta,
            'exploratory_status_by_family': statuses,
            'exploratory_criteria_by_family': criteria,
            'both_families_meet_pilot_criteria': both,
            'utility_proven': False,
        })
        del candidate
    if (hashlib.sha256(sample.cpu().numpy().tobytes()).hexdigest()!=base_hash
            or any(p.grad is not None or p.requires_grad
                   for p in base.parameters())):
        raise ValueError('Frozen base changed or received gradients')
    return {
        'schema': 'lp3-four-arm-heldout-v1',
        'status': 'LP3_HELDOUT_DIAGNOSTIC_ONLY',
        'evidence_class': 'LINUX_NATIVE_SIX_FACT_REUSED_COHORT',
        'model_id': MODEL_ID, 'revision': REVISION,
        'master_sha256': MASTER_SHA256, 'seed': SEED,
        'train_rows': len(rows), 'steps_per_arm': STEPS,
        'lr_values': [LR, ablation.LOW_LR],
        'original_fixture_sha256': _digest(rows),
        'new_phrasing_fixture_sha256': _digest(new_rows),
        'heldout_prompts_per_family': 12,
        'heldout_families': ['original', 'new_phrasings'],
        'new_facts': 0,
        'initial_trainable_sha256': initial_hash,
        'frozen_base_sample_sha256': base_hash,
        'arms': arms, 'elapsed_s': round(time.monotonic()-start, 3),
        'heldout_scored': True, 'retention_scored': True,
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
        raise ValueError('Refusing to replace heldout receipt')
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
