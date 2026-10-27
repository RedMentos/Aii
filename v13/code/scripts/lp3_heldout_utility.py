#!/usr/bin/env python3
"""Preregistered LP3 frozen-350M heldout pilot; never a V13/JEPA/Redmi gate."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import time

from scripts.lp3_real_master_smoke import MODEL_ID, REVISION, MASTER_SHA256, verify_master

SEED = 109
STEPS = 24
LR = 0.005
FACTS = (
    ('cobalt', 'marigold'),
    ('amber', 'harbor'),
    ('quartz', 'cinnamon'),
    ('jade', 'lighthouse'),
    ('indigo', 'orchard'),
    ('silver', 'tundra'),
)
TRAIN_TEMPLATE = 'What is the registry marker for {key}?'
HELDOUT_TEMPLATES = (
    'Which marker belongs to {key} in the registry?',
    'Tell me the registry marker assigned to {key}.',
)
RETENTION = (
    ('What is two plus two?', ' 4'),
    ('What color is grass?', ' green'),
    ('What planet do humans live on?', ' Earth'),
)


def fixture():
    """No answer appears in the prompt, including wrong-source prompt."""
    result = []
    for index, (key, answer) in enumerate(FACTS):
        next_key = FACTS[(index + 1) % len(FACTS)][0]
        result.append({
            'key': key,
            'answer': ' ' + answer,
            'train': TRAIN_TEMPLATE.format(key=key),
            'heldout': [t.format(key=key) for t in HELDOUT_TEMPLATES],
            'wrong_sources': [t.format(key=next_key) for t in HELDOUT_TEMPLATES],
        })
    return result


def audit_fixture(rows):
    if not isinstance(rows, list) or len(rows) != 6:
        raise ValueError('Exactly six fixed fact rows required')
    expected = fixture()
    if rows != expected:
        raise ValueError('Pilot fixture differs from preregistered key/answer/source mapping')
    seen = set()
    for row in rows:
        answer = row['answer'].strip().casefold()
        prompts = [row['train'], *row['heldout']]
        for prompt in [*prompts, *row['wrong_sources']]:
            norm = ' '.join(prompt.casefold().split())
            if answer in norm:
                raise ValueError('Target answer leaked into source or target prompt')
        for prompt in prompts:
            norm = ' '.join(prompt.casefold().split())
            if norm in seen:
                raise ValueError('Training/heldout prompt duplication')
            seen.add(norm)
        for target, source in zip(row['heldout'], row['wrong_sources']):
            if target == source or row['key'].casefold() in source.casefold():
                raise ValueError('Wrong-source identity or same-key source')
    return True


def mean(values):
    if not values or not all(math.isfinite(v) for v in values):
        raise ValueError('Empty/nonfinite metrics')
    return sum(values) / len(values)


def summarize(rows):
    return {
        arm + '_ce': mean([row[arm + '_ce'] for row in rows])
        for arm in ('own', 'wrong', 'zero', 'base')
    } | {
        arm + '_top1': sum(int(row[arm + '_top1']) for row in rows)
        for arm in ('own', 'wrong', 'zero', 'base')
    }


def classify(before, after, retention_before, retention_after, integrity):
    """Fixed pilot acceptance, not a production promotion gate."""
    own_gain = before['own_ce'] - after['own_ce']
    wrong_gain = before['wrong_ce'] - after['wrong_ce']
    retention_delta = retention_after - retention_before
    criteria = {
        'heldout_own_ce_gain_at_least_0_05': own_gain >= 0.05,
        'own_better_than_wrong_at_least_0_03': after['wrong_ce'] - after['own_ce'] >= 0.03,
        'own_better_than_zero_at_least_0_03': after['zero_ce'] - after['own_ce'] >= 0.03,
        'own_gain_over_wrong_gain_at_least_0_03': own_gain - wrong_gain >= 0.03,
        'own_top1_exceeds_wrong_by_one': after['own_top1'] >= after['wrong_top1'] + 1,
        'own_top1_exceeds_zero_by_one': after['own_top1'] >= after['zero_top1'] + 1,
        'retention_ce_degradation_under_0_20': retention_delta < 0.20,
        'integrity': integrity is True,
    }
    return ('LP3_HELDOUT_ATTRIBUTABLE_SIGNAL' if all(criteria.values())
            else 'LP3_HELDOUT_NO_ATTRIBUTABLE_SIGNAL'), criteria


def _tokenizer_prompt(tok, question, torch):
    encoded = tok.apply_chat_template(
        [{'role': 'user', 'content': question}],
        add_generation_prompt=True, tokenize=True,
        return_dict=True, return_tensors='pt')
    ids = getattr(encoded, 'input_ids', None)
    if (not isinstance(ids, torch.Tensor) or ids.ndim != 2
            or ids.shape[0] != 1 or ids.dtype != torch.long or not ids.shape[1]):
        raise ValueError('Invalid pinned chat-template BatchEncoding')
    return ids


def _answer_ids(tok, answer, torch):
    ids = tok.encode(answer, add_special_tokens=False)
    if not ids or not all(type(x) is int for x in ids):
        raise ValueError('Invalid nonempty target tokenization')
    return torch.tensor([ids], dtype=torch.long)


def _logit_metrics(logits, answer_ids, torch):
    from torch.nn import functional as F
    ce = float(F.cross_entropy(
        logits.reshape(-1, logits.shape[-1]), answer_ids.reshape(-1)))
    first = int(logits[0, 0, :].argmax() == answer_ids[0, 0])
    if not math.isfinite(ce):
        raise ValueError('Nonfinite CE')
    return ce, first


def _base_logits(base, prompt_ids, answer_ids, torch):
    seq = torch.cat((prompt_ids, answer_ids), dim=1)
    logits = base(input_ids=seq, use_cache=False).logits
    start = prompt_ids.shape[1] - 1
    return logits[:, start:start + answer_ids.shape[1], :]


def evaluate(candidate, base, tok, rows, torch):
    output = []
    candidate.eval()
    with torch.no_grad():
        for row in rows:
            answer = _answer_ids(tok, row['answer'], torch)
            for question, source in zip(row['heldout'], row['wrong_sources']):
                prompt = _tokenizer_prompt(tok, question, torch)
                wrong = _tokenizer_prompt(tok, source, torch)
                if torch.equal(prompt, wrong):
                    raise ValueError('Wrong-source prompt equals target tokens')
                logits = {
                    'own': candidate.answer_logits(prompt, answer, 'own'),
                    'wrong': candidate.answer_logits_from_source(prompt, wrong, answer),
                    'zero': candidate.answer_logits(prompt, answer, 'zero'),
                    'base': _base_logits(base, prompt, answer, torch),
                }
                item = {'key': row['key'], 'question': question,
                        'wrong_source': source, 'answer': row['answer'],
                        'target_tokens': int(answer.shape[1])}
                for arm, value in logits.items():
                    item[arm + '_ce'], item[arm + '_top1'] = _logit_metrics(
                        value, answer, torch)
                output.append(item)
    if len(output) != 12:
        raise ValueError('Heldout scoring must contain twelve examples')
    return output


def retention_ce(candidate, tok, torch):
    from torch.nn import functional as F
    candidate.eval()
    values = []
    with torch.no_grad():
        for question, answer in RETENTION:
            prompt = _tokenizer_prompt(tok, question, torch)
            target = _answer_ids(tok, answer, torch)
            logits = candidate.answer_logits(prompt, target, 'own')
            values.append(float(F.cross_entropy(
                logits.reshape(-1, logits.shape[-1]), target.reshape(-1))))
    return mean(values)


def run(master):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from v13.lp3_state_prefix import StateConditionedPrefix

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
    candidate = StateConditionedPrefix(base, prefix_tokens=2)
    sample = next(base.parameters()).detach().flatten()[:2048]
    frozen_before = hashlib.sha256(sample.cpu().numpy().tobytes()).hexdigest()
    trainable_before = [p.detach().clone() for p in candidate.trainable_parameters()]
    before_rows = evaluate(candidate, base, tok, rows, torch)
    before = summarize(before_rows)
    retention_before = retention_ce(candidate, tok, torch)
    opt = torch.optim.AdamW(candidate.trainable_parameters(),
                            lr=LR, weight_decay=0.0)
    loss_trace = []
    for step in range(STEPS):
        row = rows[step % len(rows)]
        prompt = _tokenizer_prompt(tok, row['train'], torch)
        target = _answer_ids(tok, row['answer'], torch)
        candidate.train()
        opt.zero_grad(set_to_none=True)
        loss = candidate.answer_loss(prompt, target, 'own')
        if not bool(torch.isfinite(loss)):
            raise ValueError('Nonfinite train loss')
        loss.backward()
        pred_grad = sum(float(p.grad.detach().abs().sum())
                        for p in candidate.predictor.parameters() if p.grad is not None)
        proj_grad = sum(float(p.grad.detach().abs().sum())
                        for p in candidate.prefix_projector.parameters() if p.grad is not None)
        if not all(math.isfinite(x) and x > 0 for x in (pred_grad, proj_grad)):
            raise ValueError('Missing predictor/projector gradient')
        if any(p.grad is not None or p.requires_grad for p in base.parameters()):
            raise ValueError('Frozen decoder gradient or trainability violation')
        opt.step()
        loss_trace.append(float(loss.detach()))
    after_rows = evaluate(candidate, base, tok, rows, torch)
    after = summarize(after_rows)
    if (abs(before['base_ce'] - after['base_ce']) > 1e-7
            or before['base_top1'] != after['base_top1']):
        raise ValueError('No-prefix frozen-base baseline drifted')
    if not any(not torch.equal(old, new.detach()) for old, new in
               zip(trainable_before, candidate.trainable_parameters())):
        raise ValueError('Optimizer did not update trainable LP3 parameters')
    retention_after = retention_ce(candidate, tok, torch)
    frozen_after = hashlib.sha256(sample.cpu().numpy().tobytes()).hexdigest()
    if frozen_before != frozen_after:
        raise ValueError('Frozen decoder parameter sample changed')
    status, criteria = classify(
        before, after, retention_before, retention_after, True)
    return {
        'schema': 'lp3-heldout-utility-pilot-v1',
        'status': status,
        'evidence_class': 'LINUX_NATIVE_EXPERIMENTAL_HELDOUT',
        'model_id': MODEL_ID, 'revision': REVISION,
        'master_sha256': MASTER_SHA256,
        'dataset_sha256': dataset_sha,
        'seed': SEED, 'steps': STEPS, 'lr': LR, 'prefix_tokens': 2,
        'train_prompts': 6, 'heldout_prompts': 12,
        'source_prompt_policy': 'cyclic-next-key-same-heldout-template',
        'before': before, 'after': after,
        'retention_before': retention_before,
        'retention_after': retention_after,
        'loss_trace': loss_trace,
        'criteria': criteria,
        'heldout_raw_before': before_rows,
        'heldout_raw_after': after_rows,
        'frozen_base_sample_sha256': frozen_before,
        'frozen_base_gradients': False,
        'elapsed_s': round(time.monotonic() - started, 3),
        'jepa_weight': 0, 'age_authority': 0,
        'redmi_measured': False, 'whole_system_complete': False,
        'production_utility_proven': False,
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
        raise ValueError('Refusing to replace raw pilot result')
    result = run(args.master)
    data = json.dumps(result, sort_keys=True, separators=(',', ':')) + '\n'
    with args.out.open('x', encoding='utf-8') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    print(data, end='', flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
