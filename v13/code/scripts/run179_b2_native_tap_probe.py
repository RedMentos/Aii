"""Read-only pinned Qwen B2 native tap provenance probe (no learning)."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import tempfile
import threading
import time

from v13.config import DEFAULTS
from v13.runners import LlamaRunner, TAP_SPECS

EXPECTED_MODEL_SHA = '57d1997790d1744fba5b40a7317df71ea5e2acee28c47e78f0cce39c0703f8cf'
EXPECTED_ARCHIVE_SHA = '9abf88aea48a55d0f80edb1ee20220b186848cca0b4e919d71518cfd7ca67443'
PROMPTS = ('The blue robot moves left.', 'The blue robot moves left.',
           'The red robot moves right.')


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for part in iter(lambda: f.read(1024 * 1024), b''):
            h.update(part)
    return h.hexdigest()


def probe(model, server, archive_sha=EXPECTED_ARCHIVE_SHA):
    model, server = Path(model).resolve(), Path(server).resolve()
    if sha256(model) != EXPECTED_MODEL_SHA:
        raise ValueError('B2 pinned model sha256 mismatch')
    if archive_sha != EXPECTED_ARCHIVE_SHA:
        raise ValueError('llama b10964 archive sha256 mismatch')
    if not server.is_file():
        raise ValueError('native server missing')
    expected_id, expected_dim = TAP_SPECS['gist']
    if (expected_id, expected_dim) != ('qwen35.result_norm.final.v1', 1024):
        raise ValueError('B2 tap spec unexpectedly changed')
    cfg = dict(DEFAULTS, context_tokens=1024, threads=2,
               native_cache_ram_mb=0, native_ctx_checkpoints=0)
    rows = []
    with tempfile.TemporaryDirectory(prefix='v13-run179-') as d:
        home = Path(d)
        (home / 'logs').mkdir()
        runner = LlamaRunner(home, 'B2_GIST', model, cfg, purpose='tap')
        runner.binary = str(server)
        runner.tap_id, runner.tap_dim = expected_id, expected_dim
        try:
            for prompt in PROMPTS:
                item = runner.tap(prompt, threading.Event(), time.monotonic() + 120,
                                  max_tokens=64)
                tokens, vectors, metrics = item['token_ids'], item['vectors'], item['metrics']
                if not (1 <= len(tokens) <= 64 and len(vectors) == len(tokens)):
                    raise ValueError('B2 native token row count mismatch')
                if not all(len(v) == expected_dim and all(math.isfinite(x) for x in v)
                           and sum(x*x for x in v) > 1e-20 for v in vectors):
                    raise ValueError('B2 native nonfinite/zero/dimension mismatch')
                if (metrics.get('tap_id') != expected_id or
                    metrics.get('embedding_dim') != expected_dim or
                    metrics.get('role') != 'B2_GIST' or
                    metrics.get('CAN_LATENT_TAP') is not True or
                    metrics.get('CAN_TRAIN_BODY') is not False or
                    metrics.get('CAN_LATENT_INJECT') is not False):
                    raise ValueError('B2 native metrics/authority mismatch')
                rows.append({'prompt_sha256':hashlib.sha256(prompt.encode()).hexdigest(),
                             'tokens':tokens, 'vectors':vectors})
        finally:
            runner.unload()
    if rows[0]['tokens'] != rows[1]['tokens']:
        raise ValueError('same prompt native token IDs changed')
    if rows[0]['tokens'] == rows[2]['tokens']:
        raise ValueError('changed prompt token IDs did not change')
    max_repeat_delta = max(abs(a-b) for va,vb in zip(rows[0]['vectors'], rows[1]['vectors'])
                           for a,b in zip(va,vb))
    return {'schema':'V13_RUN179_PINNED_B2_NATIVE_TAP_V1',
            'status':'PASS_NATIVE_READONLY_TAP_ONLY',
            'evidence_class':'LINUX_NATIVE_MODEL_READONLY',
            'model_sha256':EXPECTED_MODEL_SHA,
            'llama_server_binary_sha256':sha256(server),
            'llama_archive_sha256':archive_sha,
            'runner_revision':'b10964',
            'tap_id':expected_id, 'embedding_dim':expected_dim,
            'token_counts':[len(x['tokens']) for x in rows],
            'prompt_sha256':[x['prompt_sha256'] for x in rows],
            'max_repeat_abs_delta':max_repeat_delta,
            'no_body_training':True, 'no_latent_injection':True,
            'cgroup_containment_proven':False, 'redmi_proven':False,
            'step2_promoted':False, 'b3_promoted':False, 'v13_complete':False}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--model', required=True)
    p.add_argument('--server', required=True)
    p.add_argument('--output', required=True)
    p.add_argument('--archive-sha256', default=EXPECTED_ARCHIVE_SHA)
    args = p.parse_args()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        result = probe(args.model, args.server, args.archive_sha256)
    except BaseException as exc:
        result = {'schema':'V13_RUN179_PINNED_B2_NATIVE_TAP_V1',
                  'status':'FAIL_NOT_PROMOTED', 'error_type':type(exc).__name__,
                  'error':str(exc)[:300], 'redmi_proven':False,
                  'step2_promoted':False, 'b3_promoted':False, 'v13_complete':False}
        output.write_text(json.dumps(result, sort_keys=True, indent=2) + '\n')
        raise
    output.write_text(json.dumps(result, sort_keys=True, indent=2) + '\n')
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
