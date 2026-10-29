#!/usr/bin/env python3
"""Eight pinned QAD FP32 vs QAD GGUF first-token descriptive native probes, no training."""
import argparse
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen

from p2_qad_hf_tensor_audit import sha256
from p2_qad_gguf_tokenize_probe import PROMPTS

PINS = {
    'model.safetensors': '1d90518482c4ec204bebb4820bbaee4f8a38c5a6df72256f86bcd21fe52ad079',
    'config.json': '884c7b2b936f296dd448bfca18a14fd9bc903be7d3bff1303ac62bbb43f641d6',
    'tokenizer.json': 'df1d8d5ec5d091b460562ffd545e4a5e91d17d4a0db7ebe733be34ed374377bd',
    'tokenizer_config.json': 'b99856c5bdc9f88cc30a7ffff78bfc7768427e0b1216d0c196b27e5d55043455',
    'chat_template.jinja': 'ba551d58630afa3190b1be3602e28301f3d2e9bbac978dfc49d6d825171648b6',
}
GGUF_SHA = '3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d'


def parse_native_first_token(data):
    probs = data.get('completion_probabilities') if isinstance(data, dict) else None
    if not isinstance(probs, list) or len(probs) != 1:
        raise ValueError('missing or invalid one-token native probabilities')
    first = probs[0]
    if not isinstance(first, dict) or type(first.get('id')) is not int:
        raise ValueError('missing native generated token ID')
    top = first.get('top_logprobs')
    if not isinstance(top, list) or not top:
        raise ValueError('missing native top logprobs')
    ids = [t.get('id') for t in top if isinstance(t, dict)]
    if not ids or any(type(x) is not int for x in ids):
        raise ValueError('invalid native top logprob token IDs')
    return first['id'], ids[:5]


def summarize(rows):
    if len(rows) != len(PROMPTS):
        raise ValueError('eight preregistered first-token rows required')
    for row, prompt in zip(rows, PROMPTS):
        if row['prompt'] != prompt or not row['input_ids']:
            raise ValueError('prompt or input ID mismatch')
        if any(type(x) is not int or x < 0 for x in row['input_ids']):
            raise ValueError('invalid prompt token IDs')
        if type(row['hf_first']) is not int or type(row['gguf_first']) is not int:
            raise ValueError('invalid first-token IDs')
    return {'schema': 'v13.p2.qad_fp32_gguf_first_token_native.v1',
            'status': 'FIRST_TOKEN_MEASURED_NO_PARITY_PROMOTION',
            'rows': rows, 'probe_count': len(rows),
            'top1_equal_count': sum(r['hf_first'] == r['gguf_first'] for r in rows),
            'top5_overlap_total': sum(r['top5_overlap'] for r in rows),
            'model_forward_calls': len(rows), 'training': False,
            'full_logit_greedy_cache_adapter_or_utility_parity_proven': False}


def audit(master, gguf_path, endpoint):
    master, gguf_path = Path(master), Path(gguf_path)
    if master.is_symlink() or not master.is_dir() or gguf_path.is_symlink():
        raise ValueError('symlinked or missing source')
    for name, expected in PINS.items():
        p = master / name
        if p.is_symlink() or sha256(p) != expected:
            raise ValueError('QAD FP32 source SHA mismatch: ' + name)
    if sha256(gguf_path) != GGUF_SHA:
        raise ValueError('deployed QAD GGUF SHA mismatch')
    if endpoint != 'http://127.0.0.1:8080/completion':
        raise ValueError('only pinned loopback completion endpoint allowed')
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    torch.set_num_threads(2)
    tokenizer = AutoTokenizer.from_pretrained(str(master), local_files_only=True)
    model = AutoModelForCausalLM.from_pretrained(str(master), dtype=torch.float32,
                                                local_files_only=True)
    model.eval()
    rows = []
    with torch.no_grad():
        for prompt in PROMPTS:
            ids = tokenizer.encode(prompt, add_special_tokens=False)
            if not ids:
                raise ValueError('empty QAD prompt tokenization')
            logits = model(input_ids=torch.tensor([ids], dtype=torch.long),
                           use_cache=False).logits[0, -1].float()
            hf_top5 = [int(x) for x in torch.topk(logits, 5).indices.tolist()]
            payload = {'prompt': ids, 'n_predict': 1, 'temperature': 0,
                       'n_probs': 5, 'stream': False, 'cache_prompt': False,
                       'repeat_penalty': 1.0, 'top_k': 0, 'top_p': 1.0,
                       'min_p': 0.0, 'ignore_eos': True}
            req = Request(endpoint, data=json.dumps(payload).encode(),
                          headers={'Content-Type': 'application/json'}, method='POST')
            with urlopen(req, timeout=120) as resp:
                native_first, native_top5 = parse_native_first_token(
                    json.loads(resp.read(4 * 1024 * 1024)))
            rows.append({'prompt': prompt, 'input_ids': ids,
                         'hf_first': hf_top5[0], 'gguf_first': native_first,
                         'hf_top5': hf_top5, 'gguf_top5': native_top5,
                         'top5_overlap': len(set(hf_top5) & set(native_top5))})
    result = summarize(rows)
    result['source_pins'] = PINS
    result['gguf_sha256'] = GGUF_SHA
    return result


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--master', required=True)
    p.add_argument('--gguf', required=True)
    p.add_argument('--endpoint', default='http://127.0.0.1:8080/completion')
    p.add_argument('--output', required=True)
    args = p.parse_args(argv)
    try:
        result = audit(args.master, args.gguf, args.endpoint)
    except (OSError, ValueError, RuntimeError, KeyError, ImportError, TypeError) as exc:
        result = {'schema': 'v13.p2.qad_fp32_gguf_first_token_native.v1',
                  'status': 'FIRST_TOKEN_AUDIT_RED',
                  'error': type(exc).__name__ + ': ' + str(exc)}
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open('x', encoding='utf-8') as f:
        f.write(json.dumps(result, sort_keys=True, indent=2, ensure_ascii=False) + '\n')
        f.flush()
        os.fsync(f.fileno())
    return 0 if result['status'] == 'FIRST_TOKEN_MEASURED_NO_PARITY_PROMOTION' else 2


if __name__ == '__main__':
    raise SystemExit(main())
