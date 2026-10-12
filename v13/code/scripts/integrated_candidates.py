"""Reviewed candidates that are integrated into the live runtime (2026-10-12).

After the SourceHandoff cohort closed, the merged approval-reader + native
firing candidate was written into the live sources byte-exactly. Candidate
regressions stay runnable: a candidate loader accepts live sources only when
they are the exact frozen baseline, its own complete candidate, or this exact
integrated composition. Anything else still fails shut.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIRING_SNAPSHOT = 'docs/proofs/continuation-20261011/native-firing-runtime-baseline'
NAMES = ('v13/runners.py', 'v13/memory_server.py', 'v13/runtime.py', 'v13/store.py')
INTEGRATED = ('approval_reader_runtime_candidate', 'native_firing_runtime_candidate')


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


def integrated_sources(root=ROOT):
    """Frozen baseline -> approval reader -> native firing, as reviewed."""
    from scripts import approval_reader_runtime_candidate as reader
    from scripts import native_firing_runtime_candidate as firing
    original = _baseline(root)
    interim = dict(original)
    interim.update(reader.transform({k: original[k] for k in reader.NAMES}))
    return firing.transform(interim)


def overlay(original, root=ROOT):
    """Baseline files with the integrated files replaced, if live equals that."""
    expected = integrated_sources(root)
    view = {name: expected.get(name, text) for name, text in original.items()}
    actual = {name: (root/name).read_text() for name in original}
    return view if actual == view else None


def rebase(texts, root=ROOT):
    """Apply the same integrated transforms to another candidate's view.

    Files of `texts` outside the integrated set are returned unchanged; the
    remaining integrated files come from the digest-bound baseline.
    """
    from scripts import approval_reader_runtime_candidate as reader
    from scripts import native_firing_runtime_candidate as firing
    full = _baseline(root)
    full.update({k: v for k, v in texts.items() if k in NAMES})
    full.update(reader.transform({k: full[k] for k in reader.NAMES}))
    out = firing.transform(full)
    return {k: (out[k] if k in NAMES else v) for k, v in texts.items()}
