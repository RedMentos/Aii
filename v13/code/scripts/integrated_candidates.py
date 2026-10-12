"""Reviewed changes integrated into the live runtime, as one ordered chain.

After the SourceHandoff cohort closed (2026-10-12), the merged approval-reader
+ native firing candidate was written into the live sources byte-exactly.
Later reviewed runtime changes to the same files are appended to `_later`.
Candidate regressions stay runnable: a candidate loader accepts live sources
only when they are the exact frozen baseline, its own complete candidate, or
this exact integrated chain. Anything else still fails shut.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIRING_SNAPSHOT = 'docs/proofs/continuation-20261011/native-firing-runtime-baseline'
NAMES = ('v13/runners.py', 'v13/memory_server.py', 'v13/runtime.py', 'v13/store.py')
INTEGRATED = ('approval_reader_runtime_candidate', 'native_firing_runtime_candidate', 'native_cache_bounds')

NATIVE_CACHE_ARGS = '''def native_cache_args(cfg):
    # b10964 defaults (--cache-ram 8192 MiB host prompt cache, 32 context
    # checkpoints per slot) assume a desktop. Qwen3.5 checkpoints are ~19 MiB
    # each (docs/NATIVE_CACHE.md), so a 6 GB phone needs explicit bounds.
    from .config import DEFAULTS
    ram=cfg.get('native_cache_ram_mb',DEFAULTS['native_cache_ram_mb'])
    checkpoints=cfg.get('native_ctx_checkpoints',DEFAULTS['native_ctx_checkpoints'])
    return ['--cache-ram',str(ram),'--ctx-checkpoints',str(checkpoints)]
'''


def _replace(text, old, new):
    if text.count(old) != 1:
        raise ValueError('Integrated anchor changed: '+old[:80])
    return text.replace(old, new, 1)


def native_cache_bounds(sources):
    """2026-10-12 thread G: bound host prompt cache and context checkpoints."""
    out = dict(sources)
    t = out['v13/runners.py']
    t = _replace(t, 'def rotate_log(path,cap=3*1024*1024):', NATIVE_CACHE_ARGS+'def rotate_log(path,cap=3*1024*1024):')
    t = _replace(t, '"-ngl","0","--no-warmup","--no-webui","--log-disable"]\n',
                 '"-ngl","0","--no-warmup","--no-webui","--log-disable"]\n        cmd += native_cache_args(self.cfg)\n')
    out['v13/runners.py'] = t
    return out


def _later(sources):
    return native_cache_bounds(sources)


def _baseline(root):
    folder = root/FIRING_SNAPSHOT
    manifest = json.loads((folder/'manifest.json').read_text())
    if manifest.get('schema') != 'NATIVE_FIRING_RUNTIME_BASELINE_V1' or set(manifest['files']) != set(NAMES):
        raise ValueError('Integrated baseline manifest changed')
    original = {}
    for name, expected in manifest['files'].items():
        data = (folder/Path(name).name).read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise ValueError('Integrated baseline digest changed: '+name)
        original[name] = data.decode()
    return original


def _chain(full):
    from scripts import approval_reader_runtime_candidate as reader
    from scripts import native_firing_runtime_candidate as firing
    full = dict(full)
    full.update(reader.transform({k: full[k] for k in reader.NAMES}))
    return _later(firing.transform(full))


def integrated_sources(root=ROOT):
    """Frozen baseline -> approval reader -> native firing -> later changes."""
    return _chain(_baseline(root))


def overlay(original, root=ROOT):
    """Baseline files with the integrated files replaced, if live equals that."""
    expected = integrated_sources(root)
    view = {name: expected.get(name, text) for name, text in original.items()}
    actual = {name: (root/name).read_text() for name in original}
    return view if actual == view else None


def rebase(texts, root=ROOT):
    """Apply the same integrated chain to another candidate's view.

    Files of `texts` outside the integrated set are returned unchanged; the
    remaining integrated files come from the digest-bound baseline.
    """
    full = _baseline(root)
    full.update({k: v for k, v in texts.items() if k in NAMES})
    out = _chain(full)
    return {k: (out[k] if k in NAMES else v) for k, v in texts.items()}


def write_live(root=ROOT):
    """Write the integrated chain to the live files (used once per change)."""
    for name, text in integrated_sources(root).items():
        (root/name).write_text(text)
