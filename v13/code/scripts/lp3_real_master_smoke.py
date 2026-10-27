#!/usr/bin/env python3
"""Opt-in real HF FP32 LP3 compatibility smoke; never a utility or JEPA proof."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import time

MODEL_ID = 'LiquidAI/LFM2.5-350M'
REVISION = '120bf032c36dd1273de754669da040dba7ad4982'
MASTER_SHA256 = '1c9c77a4471a7f590f85240f74ed1fc26df7fbde88c3006724e2f93ca993ea4e'
PROMPTS = ('What is the name of my cat?', 'What is the name of my dog?')
TARGETS = ('Brombeer', 'Tromso')
SEED = 73


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def verify_master(directory, expected=MASTER_SHA256):
    directory = Path(directory)
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError('Master directory must be a real directory')
    master = directory / 'model.safetensors'
    if master.is_symlink() or not master.is_file():
        raise ValueError('Missing or symlinked official master')
    observed = sha256_file(master)
    if observed != expected:
        raise ValueError('Official master SHA256 mismatch')
    for name in ('config.json', 'tokenizer.json', 'tokenizer_config.json'):
        path = directory / name
        if path.is_symlink() or not path.is_file():
            raise ValueError('Missing or symlinked tokenizer/model metadata: ' + name)
    return observed


def _rss_kib():
    with open('/proc/self/status', encoding='utf-8') as stream:
        for line in stream:
            if line.startswith('VmRSS:'):
                return int(line.split()[1])
    return None


def smoke(master):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from v13.lp3_state_prefix import StateConditionedPrefix

    torch.set_num_threads(4)
    torch.manual_seed(SEED)
    started = time.monotonic()
    tok = AutoTokenizer.from_pretrained(str(master), local_files_only=True)
    base = AutoModelForCausalLM.from_pretrained(
        str(master), dtype=torch.float32, local_files_only=True)
    base.eval()
    candidate = StateConditionedPrefix(base, prefix_tokens=2)
    def encode_prompt(q):
        encoded = tok.apply_chat_template(
            [{'role': 'user', 'content': q}],
            add_generation_prompt=True, tokenize=True,
            return_dict=True, return_tensors='pt')
        if not hasattr(encoded, 'input_ids'):
            raise ValueError('Tokenizer did not return BatchEncoding.input_ids')
        ids = encoded.input_ids
        if (not isinstance(ids, torch.Tensor) or ids.ndim != 2
                or ids.shape[0] != 1 or ids.dtype != torch.long or not ids.shape[1]):
            raise ValueError('Tokenizer input_ids must be a single nonempty LongTensor row')
        return ids[0].tolist()
    prompts = [encode_prompt(q) for q in PROMPTS]
    if len(prompts[0]) != len(prompts[1]):
        raise ValueError('Preregistered prompts tokenize to unequal lengths')
    answers = [tok.encode(a, add_special_tokens=False) for a in TARGETS]
    if not all(ids and all(type(t) is int for t in ids) for ids in answers):
        raise ValueError('Missing first target token')
    prompt_ids = torch.tensor(prompts, dtype=torch.long)
    answer_ids = torch.tensor([[ids[0]] for ids in answers], dtype=torch.long)
    sample = next(base.parameters()).detach().flatten()[:2048]
    frozen_before = hashlib.sha256(sample.cpu().numpy().tobytes()).hexdigest()

    candidate.train()
    own = candidate.answer_logits(prompt_ids, answer_ids, 'own')
    shifted = candidate.answer_logits(prompt_ids, answer_ids, 'shift')
    zero = candidate.answer_logits(prompt_ids, answer_ids, 'zero')
    next_own = candidate.next_token_logits(prompt_ids, 'own')
    next_shift = candidate.next_token_logits(prompt_ids, 'shift')
    if own.shape != shifted.shape or own.shape != zero.shape or own.shape[:2] != (2, 1):
        raise ValueError('Real master answer-logit shape mismatch')
    delta_shift = float((own - shifted).detach().abs().max())
    delta_zero = float((own - zero).detach().abs().max())
    next_delta = float((next_own - next_shift).detach().abs().max())
    loss = candidate.answer_loss(prompt_ids, answer_ids)
    if not bool(torch.isfinite(loss)):
        raise ValueError('Nonfinite answer CE')
    opt = torch.optim.AdamW(candidate.trainable_parameters(), lr=1e-3)
    opt.zero_grad()
    loss.backward()
    pred_grad = sum(float(p.grad.detach().abs().sum()) for p in candidate.predictor.parameters()
                    if p.grad is not None)
    proj_grad = sum(float(p.grad.detach().abs().sum()) for p in candidate.prefix_projector.parameters()
                    if p.grad is not None)
    if not all(math.isfinite(x) and x > 0 for x in (delta_shift, delta_zero, next_delta,
                                                     pred_grad, proj_grad)):
        raise ValueError('No finite state-to-answer gradient or control effect')
    if not all(p.grad is None and not p.requires_grad for p in base.parameters()):
        raise ValueError('Frozen base acquired gradient')
    opt.step()
    frozen_after = hashlib.sha256(sample.cpu().numpy().tobytes()).hexdigest()
    if frozen_after != frozen_before:
        raise ValueError('Frozen base tensor changed')
    candidate.eval()
    greedy = candidate.greedy(prompt_ids, max_new_tokens=2)
    if tuple(greedy.shape) != (2, 2) or not bool((greedy >= 0).all()):
        raise ValueError('Real master target-free greedy failed')
    return {
        'schema': 'lp3-real-master-smoke-v1',
        'status': 'LP3_REAL_MASTER_COMPAT_PASS',
        'evidence_class': 'LINUX_NATIVE_COMPATIBILITY',
        'model_id': MODEL_ID,
        'revision': REVISION,
        'master_sha256': MASTER_SHA256,
        'seed': SEED,
        'prompt_tokens': len(prompts[0]),
        'first_answer_token_only': True,
        'answer_ce': float(loss.detach()),
        'delta_shift_max': delta_shift,
        'delta_zero_max': delta_zero,
        'next_shift_delta_max': next_delta,
        'predictor_grad_abs_sum': pred_grad,
        'projector_grad_abs_sum': proj_grad,
        'frozen_base_sample_sha256': frozen_before,
        'frozen_base_gradients': False,
        'elapsed_s': round(time.monotonic() - started, 3),
        'rss_kib_after': _rss_kib(),
        'jepa_weight': 0,
        'age_authority': 0,
        'redmi_measured': False,
        'utility_proven': False,
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
    result = smoke(args.master)
    data = json.dumps(result, sort_keys=True, separators=(',', ':')) + '\n'
    with args.out.open('x', encoding='utf-8') as f:
        f.write(data)
        f.flush()
        import os
        os.fsync(f.fileno())
    print(data, end='', flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
