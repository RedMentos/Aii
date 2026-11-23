#!/usr/bin/env python3
"""WP-S6 rest: native (no Python/torch) selective finetune of the LFM2 C3 master with the patched ggml backward.

Before 2026-10-12 `native-select-finetune` aborted on LFM2 ("unsupported ggml op for backward pass: SSM_CONV").
`scripts/patches/ggml-lfm2-backward-b10964.patch` adds SSM_CONV + CONCAT backward (finite-difference checked with
`test-backend-ops grad`), a contiguous TRANSPOSE gradient, a larger training graph budget and masked labels. This
bench measures what the native path learns on the same 8 invented facts as scripts/lora_bench.py and what it
forgets, on the deployed llama.cpp inference path. Build: scripts/build_native_lfm2_finetune.sh.

Training stream: each fact is the exact inference prompt (`render`, generation prompt, thinking off) followed by
the answer and `<|im_end|>`, i.e. the history form of the template. (Dev runs before this fix used the template's
prefill form, which adds `<think></think>` and drops `<|im_end|>`; kept as negative evidence.)
Loss modes: `all` = every token of the stream (native-select-finetune), `answer` = answer tokens + `<|im_end|>` only
(native-answer-finetune, spans marked with \x01/\x02). Optional anchor replay: the base model's own greedy answers to
lora_bench.ANCHORS (disjoint from probes and near-misses) are mixed into the stream as extra answer turns (hard
labels). KL anchor: the same anchor turns marked \x03/\x04; native-answer-finetune trains them towards the base
model's own top-k next-token distribution (soft labels, weight V13_KL_WEIGHT) instead of the greedy tokens.

Per variant: train (fixed tensor set, AdamW) -> quantise to Q4_0 with the trained tensors kept in F32 (base gets the
identical recipe) -> greedy eval through llama-server b10964: fact recall, paraphrases, near-miss leak, general
probes (retention vs base). Nothing is installed or activated.

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
from lora_bench import ANCHORS, FACTS, PARAPHRASES, NEAR_MISS, PROBES  # noqa: E402  (same items as the torch LoRA bench)
from native_cache_bench import Server, sha256  # noqa: E402

FFN_LATE = ['blk.12.ffn_down', 'blk.13.ffn_down', 'blk.14.ffn_down', 'blk.15.ffn_down']
FFN_MID = ['blk.6.ffn_down', 'blk.7.ffn_down', 'blk.8.ffn_down', 'blk.9.ffn_down']
VARIANTS = {
    # name: (tensor keys, learning rate, epochs, loss mode, anchor: None | 'replay' | 'kl', KL weight)
    # lr 1e-4 on ffn_late (dev run, broken stream) collapsed the model into repeated <|im_start|>; hence <= 3e-5
    'ffn_late_all': (FFN_LATE, 1e-5, 4, 'all', None, 0),
    'ffn_late_answer': (FFN_LATE, 1e-5, 4, 'answer', None, 0),
    'ffn_late_answer_anchor': (FFN_LATE, 1e-5, 4, 'answer', 'replay', 0),
    'ffn_late_answer_anchor_lr3e-5': (FFN_LATE, 3e-5, 4, 'answer', 'replay', 0),
    'ffn_mid_answer_anchor': (FFN_MID, 1e-5, 4, 'answer', 'replay', 0),
    'conv_kernels_answer_anchor': (['shortconv.conv'], 1e-3, 4, 'answer', 'replay', 0),
    # WP-S6 rest 2: KL anchor with soft base labels
    'ffn_late_answer_kl1': (FFN_LATE, 1e-5, 4, 'answer', 'kl', 1.0),
    'ffn_late_answer_kl3': (FFN_LATE, 1e-5, 4, 'answer', 'kl', 3.0),
    'ffn_late_answer_kl3_lr3e-5': (FFN_LATE, 3e-5, 4, 'answer', 'kl', 3.0),
    'ffn_mid_answer_kl1': (FFN_MID, 1e-5, 4, 'answer', 'kl', 1.0),
}
TOOLS = {'all': 'native-select-finetune', 'answer': 'native-answer-finetune'}


def hit(text, keys):
    t = (text or '').lower()
    return any(k in t for k in keys)


def first_sentence(text):
    return re.split(r'[.!?\n]', (text or '').strip(), maxsplit=1)[0]


def turn(server, q, a):
    """(prompt, answer) exactly as at inference: generation prompt, then answer + end-of-turn of the history form."""
    gen = server.render([{'role': 'user', 'content': q}])
    full = server.post('/apply-template', {'messages': [{'role': 'user', 'content': q}, {'role': 'assistant', 'content': a},
                                                         {'role': 'user', 'content': 'V13CUT'}], 'add_generation_prompt': False,
                                           'chat_template_kwargs': {'enable_thinking': False}})['prompt']
    if not full.startswith(gen):
        raise RuntimeError('history form does not extend the generation prompt: %r vs %r' % (gen, full))
    rest = full[len(gen):]; end = rest.index('<|im_end|>') + len('<|im_end|>')
    return gen.replace('<|startoftext|>', ''), rest[:end], rest[end:rest.index('<|im_start|>', end)]  # tool adds BOS once


def anchor_turns(server):
    out = []
    for q in ANCHORS:
        d = server.post('/completion', {'prompt': server.render([{'role': 'user', 'content': q}]), 'n_predict': 96,
                                        'temperature': 0, 'cache_prompt': False})
        if d.get('stop_type') == 'eos' and d['content'].strip():  # only complete answers; a cut answer would teach early stops
            out.append((q, d['content']))
    return out


def train_text(server, reps, seed, mode, anchors, anchor_mode='replay'):
    rnd = random.Random(seed); chunks = []; per_rep = max(1, -(-len(anchors) * 3 // (2 * reps))) if anchors else 0
    for r in range(reps):
        items = [(q, a, False) for q, a, _ in FACTS] + [anchors[(r * per_rep + i) % len(anchors)] + (True,) for i in range(per_rep)]
        rnd.shuffle(items)
        for q, a, is_anchor in items:
            prompt, answer, sep = turn(server, q, a)
            if is_anchor and anchor_mode == 'kl':  # whole turn -> soft base labels
                chunks.append('\x03' + prompt + answer + '\x04' + sep)
            else:
                chunks.append(prompt + ('\x01' + answer + '\x02' if mode == 'answer' else answer) + sep)
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
        # 'ok'/'leak' = keyword anywhere (lora_bench rule, loose: also counts hedges that merely mention the word);
        # 'strict' = keyword in the first sentence, i.e. the answer leads with it
        row = lambda q, keys, k='ok': (lambda ans: {'q': q, 'a': ans, k: hit(ans, keys), 'strict': hit(first_sentence(ans), keys)})(ask(q))
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
                        'near_miss_leak': round(n(near, 'leak') / len(near), 3), 'probes_ok': n(probes, 'ok'), 'probes_n': len(probes),
                        'facts_strict': n(facts, 'strict'), 'para_strict': n(para, 'strict'),
                        'near_miss_leak_strict': round(n(near, 'strict') / len(near), 3)}}


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
    lib = lambda f: sha256(tool / f) if (tool / f).exists() else None
    rep = {'created': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'evidence_level': 'LINUX_NATIVE_CLOUD (not Redmi)',
           'master_sha256': sha256(master), 'tool_sha256': {m: lib(t) for m, t in TOOLS.items()},
           'libggml_base_sha256': lib('libggml-base.so'), 'libllama_sha256': lib('libllama.so'),
           'patch_sha256': sha256(Path(__file__).resolve().parent / 'patches' / 'ggml-lfm2-backward-b10964.patch'),
           'server_sha256': sha256(server), 'script_sha256': sha256(Path(__file__)), 'seed': a.seed, 'reps': a.reps,
           'stream': 'inference prompt + answer + <|im_end|> (history form)', 'variants': {}}
    s = Server(server, master, ['--cache-ram', '0'], out / 'template.log')
    try:
        anchors = anchor_turns(s)
        texts = {(m, anc): train_text(s, a.reps, a.seed, m, anchors if anc else [], anc or 'replay')
                 for m, anc in {VARIANTS[v][3:5] for v in a.variants}}
    finally:
        s.stop()
    rep['anchors_used'] = len(anchors)
    stream_name = lambda m, anc: f'train-{m}{"" if not anc else "-anchor" if anc == "replay" else "-kl"}.txt'
    for (m, anc), text in texts.items():
        (out / stream_name(m, anc)).write_text(text)
    base_cache = {}
    for name in a.variants:
        keys, lr, epochs, mode, anc, kl_w = VARIANTS[name]; d = out / name; d.mkdir(exist_ok=True)
        trained = d / 'trained-f32.gguf'; train_file = out / stream_name(mode, anc)
        env = dict(os.environ, V13_TRAIN_TENSORS=','.join(keys), LD_LIBRARY_PATH=str(tool), V13_KL_WEIGHT=str(kl_w), V13_KL_K='32')
        cmd = [str(tool / TOOLS[mode]), '-m', str(master), '-f', str(train_file), '-o', str(trained),
               '-c', '256', '-b', '256', '-ub', '256', '--epochs', str(epochs), '-lr', str(lr), '-t', str(a.threads), '-s', str(a.seed)]
        t0 = time.monotonic(); r = subprocess.run(cmd, env=env, capture_output=True, text=True, errors="replace"); wall = time.monotonic() - t0
        (d / 'train.log').write_text(r.stdout + r.stderr)
        res = {'keys': keys, 'lr': lr, 'epochs': epochs, 'loss_mode': mode, 'anchor': anc, 'kl_weight': kl_w, 'train_file': train_file.name,
               'train_file_sha256': sha256(train_file), 'returncode': r.returncode, 'wall_s': round(wall, 1),
               'epoch_loss': [json.loads(x) for x in re.findall(r'V13_EPOCH (\{.*\})', r.stderr)]}
        mres = re.search(r'V13_RESULT (\{.*\})', r.stdout)
        res['result'] = json.loads(mres.group(1)) if mres else None
        if r.returncode or not mres:
            res['status'] = 'TRAIN_FAILED'; rep['variants'][name] = res
            (out / 'report.json').write_text(json.dumps(rep, indent=1)); continue
        bq, tq = d / 'base-q4.gguf', d / 'trained-q4.gguf'
        if tuple(keys) not in base_cache:  # same F32 set -> same base file -> same base answers
            quantize(tool, master, bq, keys); base_cache[tuple(keys)] = evaluate(server, bq, d / 'eval-base.log')
        quantize(tool, trained, tq, keys)
        res['base'] = base_cache[tuple(keys)]; res['trained'] = evaluate(server, tq, d / 'eval-trained.log')
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
