"""Run169 private native B1 baseline-vs-F32-patch receiver probe; NOT JEPA.

Only temporary GGUF copy is changed; always restore it, never active model.
All native jobs serial. Synthetic quadratic weights have no utility authority.
"""
import hashlib
import json
import os
from pathlib import Path
import threading
import time
import numpy as np
from scripts.body_fp32_export_verify_run163 import digest, GATES
from scripts.body_fp32_gguf_reversible_run168 import patch_rollback

PROMPTS = ['Say hello in one short sentence.',
           'What is 2 plus 2? Answer with one number.',
           'Repeat exactly: blue river.']
PROMPTS_SHA = 'f744b15218f8448879ae4339cf158e463e114b2026e6967fa9e3e7197f3ac64f'
SYSTEM = 'You are a concise assistant. Respond to the user directly.'


def prompt_hash():
    return hashlib.sha256(json.dumps(PROMPTS, sort_keys=True,
                   separators=(',', ':')).encode()).hexdigest()


def _rewrite_spans(out, master, source_report, micro, prefix):
    r = json.loads(Path(source_report).read_text())
    with np.load(master, allow_pickle=False) as base, np.load(micro, allow_pickle=False) as z, Path(out).open('r+b') as f:
        for row in r['selected_tensors']:
            name = row['name']
            raw = base[name].tobytes() if prefix == 'baseline' else z['updated__' + name].tobytes()
            if len(raw) != row['bytes']:
                raise ValueError('span_length_mismatch')
            f.seek(row['offset_in_gguf']); f.write(raw)
        f.flush(); os.fsync(f.fileno())


def run_pair(model, patched, home, cfg, runner_cls):
    """Sequential native model loads; injected runner_cls only for synthetic tests."""
    rows = []
    for role_name, path in (('baseline', model), ('private_patched', patched)):
        runner = None
        try:
            runner = runner_cls(home, 'B1_DETAIL', path, cfg)
            for i, q in enumerate(PROMPTS):
                cancel = threading.Event()
                response = ''.join(runner.generate(
                    [{'role': 'system', 'content': SYSTEM}, {'role': 'user', 'content': q}],
                    cancel, time.monotonic() + 70, max_tokens=32, seed=16900 + i))
                if not response or len(response) > 4096:
                    raise ValueError('native_response_empty_or_oversize')
                rows.append({'model': role_name, 'prompt_index': i,
                             'response_sha256': hashlib.sha256(response.encode()).hexdigest(),
                             'response_chars': len(response)})
        finally:
            if runner is not None:
                runner.unload()
    if len(rows) != 2 * len(PROMPTS):
        raise ValueError('native_incomplete')
    return rows


def probe(model, master, source_report, micro, micro_report, expected_sha,
          patched, home, cfg, runner_cls):
    model, master, source_report, micro, micro_report, patched = map(
        Path, (model, master, source_report, micro, micro_report, patched))
    if prompt_hash() != PROMPTS_SHA:
        raise ValueError('prompt_prereg_hash_mismatch')
    proof = patch_rollback(model, master, source_report, micro, micro_report,
                           expected_sha, patched)
    try:
        _rewrite_spans(patched, master, source_report, micro, 'updated')
        if digest(patched) != proof['private_patched_sha256_before_rollback']:
            raise ValueError('private_patch_sha_mismatch')
        rows = run_pair(model, patched, home, cfg, runner_cls)
    finally:
        # Only this private copy is restored. Original registered GGUF never writable.
        if patched.is_file():
            _rewrite_spans(patched, master, source_report, micro, 'baseline')
            if digest(patched) != expected_sha:
                raise ValueError('private_rollback_failed')
    if digest(model) != expected_sha:
        raise ValueError('registered_model_changed')
    pairs = [{'prompt_index': i, 'same_output_hash': rows[i]['response_sha256'] ==
              rows[i + len(PROMPTS)]['response_sha256']}
             for i in range(len(PROMPTS))]
    return {'schema': 'V13_RUN169_NATIVE_PRIVATE_B1_RECEIVER_V1',
            'model_sha256': expected_sha,
            'private_patch_sha256': proof['private_patched_sha256_before_rollback'],
            'private_restored_sha256': expected_sha,
            'prompt_set_sha256': PROMPTS_SHA, 'rows': rows, 'pairs': pairs,
            'native_model_loads_sequential': True, 'native_runner_unloaded': True,
            'body_training_authority': 0, 'jepa_weight': 0, 'gates': GATES,
            'evidence_class': 'NATIVE_RECEIVER_ONLY_NO_JEPA_OR_UTILITY',
            'limitations': ['synthetic quadratic weight delta, not predictive JEPA',
                            'output differences are not improvements',
                            'no real training, retention, activation or Redmi proof']}
