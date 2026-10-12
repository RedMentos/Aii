#!/usr/bin/env python3
"""WP-S6 rest: native (no Python/torch) selective finetune of the LFM2 C3 master with the patched ggml backward.

Before 2026-10-12 `native-select-finetune` aborted on LFM2 ("unsupported ggml op for backward pass: SSM_CONV").
`scripts/patches/ggml-lfm2-backward-b10964.patch` adds SSM_CONV + CONCAT backward (finite-difference checked with
`test-backend-ops grad`) and a contiguous TRANSPOSE gradient. This bench measures what the native path learns on
the same 8 invented facts as scripts/lora_bench.py and what it forgets, on the deployed llama.cpp inference path.

Per variant: train (fixed tensor set, AdamW, all-token loss of the stock ggml-opt dataset) -> quantise to Q4_0 with
the trained tensors kept in F32 (base gets the identical recipe) -> greedy eval through llama-server b10964:
fact recall, paraphrases, near-miss leak, general probes (retention vs base). Nothing is installed or activated.

  python3 scripts/native_lfm2_finetune_bench.py --tool BUILD/bin --server RELEASE/llama-server \
      --master master350-f32.gguf --out bench-results/native-lfm2-finetune-20261012
"""
import argparse
import hashlib
import json
import os
import random
import re
import subprocess
import sys
import time
import urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lora_bench import FACTS, PARAPHRASES, NEAR_MISS, PROBES  # noqa: E402  (same items as the torch LoRA bench)
from native_cache_bench import Server, sha256  # noqa: E402

VARIANTS = {
    # name: (tensor keys, learning rate, epochs)
    # lr 1e-4 on ffn_late (dev run 2026-10-12) collapsed the model into repeated <|im_start|>; hence 1e-5
    'ffn_late': (['blk.12.ffn_down', 'blk.13.ffn_down', 'blk.14.ffn_down', 'blk.15.ffn_down'], 1e-5, 4),
    'ffn_late_lr3e-6': (['blk.12.ffn_down', 'blk.13.ffn_down', 'blk.14.ffn_down', 'blk.15.ffn_down'], 3e-6, 4),
    'ffn_mid': (['blk.6.ffn_down', 'blk.7.ffn_down', 'blk.8.ffn_down', 'blk.9.ffn_down'], 1e-5, 4),
    'conv_kernels': (['shortconv.conv'], 1e-4, 4),
}


def hit(text, keys):
    t = (text or '').lower()
    return any(k in t for k in keys)


def train_text(server, reps, seed):
    rnd = random.Random(seed); chunks = []
    for _ in range(reps):
        order = list(FACTS); rnd.shuffle(order)
        for q, a, _ in order:
            p = server.post('/apply-template', {'messages': [{'role': 'user', 'content': q}, {'role': 'assistant', 'content': a}],
                                                'add_generation_prompt': False})['prompt']
            chunks.append(p.replace('<|startoftext|>', ''))  # the tool adds BOS once for the whole stream
    return ''.join(chunks)


INVALID = '<INVALID_OUTPUT>'


def evaluate(binary, model, log):
    s = Server(binary, model, ['--cache-ram', '0'], log)
    try:
        def ask(q):
            try:
                return s.post('/completion', {'prompt': s.render([{'role': 'user', 'content': q}]), 'n_predict': 32,
                                              'temperature': 0, 'cache_prompt': False})['content']
            except urllib.error.HTTPError:  # a collapsed model can emit tokens the server refuses to return
                return INVALID
        row = lambda q, keys, k='ok': (lambda ans: {'q': q, 'a': ans, k: hit(ans, keys)})(ask(q))
        facts = [row(q, keys) for q, _, keys in FACTS]
        para = [row(q, keys) for q, keys in PARAPHRASES]
        near = [row(q, keys, 'leak') for q, keys in NEAR_MISS]
        probes = [row(p['prompt'], p['expect']) for p in PROBES]
    finally:
        s.stop()
    n = lambda rows, k: sum(r[k] for r in rows)
    invalid = sum(r['a'] == INVALID for rows in (facts, para, near, probes) for r in rows)
    return {'invalid_outputs': invalid, 'facts': facts, 'paraphrases': para, 'near_miss': near, 'probes': probes,
            'summary': {'facts_ok': n(facts, 'ok'), 'facts_n': len(facts), 'para_ok': n(para, 'ok'), 'para_n': len(para),
                        'near_miss_leak': round(n(near, 'leak') / len(near), 3), 'probes_ok': n(probes, 'ok'), 'probes_n': len(probes)}}


def quantize(tool, src, dst, keys):
    # trained tensors stay F32 (same recipe for base and trained model, so only training differs)
    cmd = [str(tool / 'llama-quantize')]
    for k in keys:
        cmd += ['--tensor-type', re.escape(k) + '=f32']
    cmd += [str(src), str(dst), 'Q4_0', '4']
    r = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
    if r.returncode:
        raise RuntimeError(r.stderr[-2000:])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tool', required=True, help='build/bin with native-select-finetune + llama-quantize (patched)')
    ap.add_argument('--server', required=True, help='release llama-server b10964 for evaluation')
    ap.add_argument('--master', required=True); ap.add_argument('--out', required=True)
    ap.add_argument('--variants', nargs='+', default=list(VARIANTS)); ap.add_argument('--reps', type=int, default=12)
    ap.add_argument('--seed', type=int, default=13); ap.add_argument('--threads', type=int, default=4)
    a = ap.parse_args(); out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    tool, server, master = Path(a.tool).resolve(), Path(a.server).resolve(), Path(a.master).resolve()
    rep = {'created': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'evidence_level': 'LINUX_NATIVE_CLOUD (not Redmi)',
           'master_sha256': sha256(master), 'tool_sha256': sha256(tool / 'native-select-finetune'),
           'libggml_base_sha256': sha256(tool / 'libggml-base.so') if (tool / 'libggml-base.so').exists() else None,
           'libllama_sha256': sha256(tool / 'libllama.so') if (tool / 'libllama.so').exists() else None,
           'patch_sha256': sha256(Path(__file__).resolve().parent / 'patches' / 'ggml-lfm2-backward-b10964.patch'),
           'server_sha256': sha256(server), 'script_sha256': sha256(Path(__file__)), 'seed': a.seed, 'reps': a.reps,
           'loss': 'all tokens of the stream (stock ggml-opt dataset), no answer-only mask, no KL anchor', 'variants': {}}
    s = Server(server, master, ['--cache-ram', '0'], out / 'template.log')
    text = train_text(s, a.reps, a.seed); s.stop()
    (out / 'train.txt').write_text(text)
    for name in a.variants:
        keys, lr, epochs = VARIANTS[name]; d = out / name; d.mkdir(exist_ok=True)
        trained = d / 'trained-f32.gguf'
        env = dict(os.environ, V13_TRAIN_TENSORS=','.join(keys), LD_LIBRARY_PATH=str(tool))
        cmd = [str(tool / 'native-select-finetune'), '-m', str(master), '-f', str(out / 'train.txt'), '-o', str(trained),
               '-c', '256', '-b', '256', '-ub', '256', '--epochs', str(epochs), '-lr', str(lr), '-t', str(a.threads), '-s', str(a.seed)]
        t0 = time.monotonic(); r = subprocess.run(cmd, env=env, capture_output=True, text=True, errors="replace"); wall = time.monotonic() - t0
        (d / 'train.log').write_text(r.stdout + r.stderr)
        res = {'keys': keys, 'lr': lr, 'epochs': epochs, 'returncode': r.returncode, 'wall_s': round(wall, 1),
               'epoch_loss': [json.loads(m) for m in re.findall(r'V13_EPOCH (\{.*\})', r.stderr)]}
        m = re.search(r'V13_RESULT (\{.*\})', r.stdout)
        res['result'] = json.loads(m.group(1)) if m else None
        if r.returncode or not m:
            res['status'] = 'TRAIN_FAILED'; rep['variants'][name] = res
            (out / 'report.json').write_text(json.dumps(rep, indent=1)); continue
        bq, tq = d / 'base-q4.gguf', d / 'trained-q4.gguf'
        quantize(tool, master, bq, keys); quantize(tool, trained, tq, keys)
        res['base'] = evaluate(server, bq, d / 'eval-base.log'); res['trained'] = evaluate(server, tq, d / 'eval-trained.log')
        b, t = res['base'], res['trained']
        lost = [x['q'] for x, y in zip(b['probes'], t['probes']) if x['ok'] and not y['ok']]
        res['retention'] = {'probes_base_ok': b['summary']['probes_ok'], 'probes_trained_ok': t['summary']['probes_ok'],
                            'forgotten': lost, 'forgotten_frac_of_base_ok': round(len(lost) / max(1, b['summary']['probes_ok']), 3)}
        res['status'] = 'MEASURED'
        for f in (trained, bq, tq):
            f.unlink(missing_ok=True)  # large binaries are not evidence; hashes of inputs + logs are kept
        rep['variants'][name] = res
        (out / 'report.json').write_text(json.dumps(rep, indent=1)); print(name, json.dumps(t['summary']), res['retention'], flush=True)
    (out / 'report.json').write_text(json.dumps(rep, indent=1))


if __name__ == '__main__':
    main()
