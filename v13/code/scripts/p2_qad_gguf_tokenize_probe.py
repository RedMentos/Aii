#!/usr/bin/env python3
"""Eight pinned synthetic QAD source vs deployed GGUF tokenizer-ID probes, no inference."""
import argparse
import hashlib
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen

QAD_TOKENIZER_SHA = 'df1d8d5ec5d091b460562ffd545e4a5e91d17d4a0db7ebe733be34ed374377bd'
PROMPTS = ('Hello.', '2 + 2 = ?', '<|tool_call_start|>python<|tool_call_end|>',
           '<think>reasoning</think>', 'Mathias uses python.', '{"tool":"python"}',
           'Äpfel, Öl und Straße.', 'Line one\nLine two')


def parse_ids(data):
    if not isinstance(data, dict) or not isinstance(data.get('tokens'), list):
        raise ValueError('invalid GGUF /tokenize JSON response')
    tokens = data['tokens']
    if any(type(v) is not int or v < 0 for v in tokens):
        raise ValueError('noninteger or negative GGUF token ID')
    return tokens


def compare(source, gguf_ids):
    if len(source) != len(PROMPTS) or len(gguf_ids) != len(PROMPTS):
        raise ValueError('preregistered eight-probe count mismatch')
    rows = []
    for prompt, a, b in zip(PROMPTS, source, gguf_ids):
        if any(type(v) is not int or v < 0 for v in a + b):
            raise ValueError('invalid token IDs')
        rows.append({'prompt': prompt, 'qad_source_ids': a, 'gguf_runtime_ids': b,
                     'ids_equal': a == b})
    equal = sum(r['ids_equal'] for r in rows)
    return {'schema': 'v13.p2.qad_gguf_native_tokenizer_ids.v1',
            'status': 'EIGHT_TOKEN_IDS_EQUAL_NATIVE_NO_LOGIT_PARITY'
                      if equal == 8 else 'TOKEN_ID_MISMATCH_RED',
            'probes': rows, 'equal_count': equal, 'probe_count': len(rows),
            'model_forward_calls': 0, 'training': False,
            'full_tokenizer_chat_logit_utility_parity_proven': False}


def audit(tokenizer_json, endpoint):
    path = Path(tokenizer_json)
    if path.is_symlink() or not path.is_file():
        raise ValueError('missing or symlinked QAD tokenizer')
    h = hashlib.sha256(path.read_bytes()).hexdigest()
    if h != QAD_TOKENIZER_SHA:
        raise ValueError('QAD source tokenizer SHA mismatch')
    if endpoint != 'http://127.0.0.1:8080/tokenize':
        raise ValueError('only pinned local loopback endpoint allowed')
    from tokenizers import Tokenizer
    tok = Tokenizer.from_file(str(path))
    source = [tok.encode(s, add_special_tokens=False).ids for s in PROMPTS]
    native = []
    for prompt in PROMPTS:
        req = Request(endpoint, data=json.dumps({'content': prompt,
            'add_special': False, 'parse_special': True, 'with_pieces': False},
            ensure_ascii=False).encode('utf-8'),
            headers={'Content-Type': 'application/json'}, method='POST')
        with urlopen(req, timeout=15) as resp:
            native.append(parse_ids(json.loads(resp.read(2 * 1024 * 1024))))
    result = compare(source, native)
    result['qad_tokenizer_sha256'] = h
    return result


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--tokenizer-json', required=True)
    p.add_argument('--endpoint', default='http://127.0.0.1:8080/tokenize')
    p.add_argument('--output', required=True)
    args = p.parse_args(argv)
    try:
        result = audit(args.tokenizer_json, args.endpoint)
    except (OSError, ValueError, ImportError, TypeError, TimeoutError) as exc:
        result = {'schema': 'v13.p2.qad_gguf_native_tokenizer_ids.v1',
                  'status': 'TOKEN_ID_MISMATCH_RED',
                  'error': type(exc).__name__ + ': ' + str(exc)}
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open('x', encoding='utf-8') as f:
        f.write(json.dumps(result, sort_keys=True, indent=2, ensure_ascii=False) + '\n')
        f.flush()
        os.fsync(f.fileno())
    return 0 if result['status'] == 'EIGHT_TOKEN_IDS_EQUAL_NATIVE_NO_LOGIT_PARITY' else 2


if __name__ == '__main__':
    raise SystemExit(main())
