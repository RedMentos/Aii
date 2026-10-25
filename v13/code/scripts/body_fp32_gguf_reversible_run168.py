"""Run168 private reversible F32 GGUF patch, NOT inference or JEPA training.

Copies registered model, modifies only selected proven F32 vector spans in
private copy, verifies unchanged gaps, then restores original SHA. No active
model writes, no quantized tensor writes, no deployment or learning authority.
"""
import json
import os
from pathlib import Path
import shutil
import numpy as np
from scripts.body_fp32_export_verify_run163 import verify, digest, GATES

MAX_BYTES = 16 * 1024 * 1024


def equal_region(a, b, start, end):
    a.seek(start); b.seek(start)
    while start < end:
        n = min(1 << 20, end - start)
        if a.read(n) != b.read(n):
            return False
        start += n
    return True


def patch_rollback(model, master, source_report, micro_candidate, micro_report,
                   expected_sha, out):
    model, master, source_report, micro_candidate, micro_report, out = map(
        Path, (model, master, source_report, micro_candidate, micro_report, out))
    if out.exists() or out.is_symlink():
        raise FileExistsError('output_exists')
    if any(p.is_symlink() or not p.is_file() for p in (model, master, source_report,
                                                      micro_candidate, micro_report)):
        raise ValueError('regular_input_required')
    if out.resolve(strict=False) in {p.resolve() for p in (model, master, source_report,
                                                          micro_candidate, micro_report)}:
        raise ValueError('output_overlaps_input')
    a = verify(model, master, source_report, expected_sha)
    r = json.loads(source_report.read_text())
    m = json.loads(micro_report.read_text())
    if (m.get('schema') != 'V13_RUN166_FP32_MASTER_MICRO_V1' or
            m.get('registered_model_sha256') != expected_sha or
            m.get('source_master_sha256') != digest(master) or
            m.get('private_candidate_sha256') != digest(micro_candidate) or
            m.get('body_training_authority') != 0 or m.get('jepa_weight') != 0 or
            m.get('gates') != GATES or
            m.get('synthetic_objective') != 'QUADRATIC_W0_PLUS_0P01_NOT_JEPA'):
        raise ValueError('micro_binding_or_authority')
    rows = r['selected_tensors']
    if len(rows) != a['selected_count'] or len(rows) != m.get('selected_tensors'):
        raise ValueError('selection_count')
    patches = []
    all_delta_sq = 0.
    with np.load(master, allow_pickle=False) as baseline, np.load(micro_candidate, allow_pickle=False) as z:
        names = sorted(x['name'] for x in rows)
        if sorted(z.files) != sorted(prefix + name for name in names
                                    for prefix in ('baseline__', 'updated__', 'ema__')):
            raise ValueError('micro_npz_names')
        for row in rows:
            name = row['name']; pos = row['offset_in_gguf']; size = row['bytes']
            if size > MAX_BYTES or pos < 0 or pos + size > model.stat().st_size:
                raise ValueError('span_bounds')
            original = baseline[name]
            before, after = z['baseline__' + name], z['updated__' + name]
            if (before.dtype != np.dtype('<f4') or after.dtype != np.dtype('<f4') or
                    before.shape != original.shape or after.shape != original.shape or
                    not np.isfinite(after).all() or before.tobytes() != original.tobytes()):
                raise ValueError('micro_baseline_or_updated')
            all_delta_sq += float(np.sum((after.astype(np.float64)-before.astype(np.float64))**2))
            patches.append((pos, pos + size, original.tobytes(), after.tobytes()))
    patches.sort()
    if any(x[1] > y[0] for x,y in zip(patches, patches[1:])):
        raise ValueError('overlapping_spans')
    update_l2 = float(np.sqrt(all_delta_sq))
    if not 0 < update_l2 <= .2 + 1e-5 or abs(update_l2 - m['applied_update_l2']) > 1e-4:
        raise ValueError('micro_update_bound')
    # A fresh private copy; never open the source for writing.
    with model.open('rb') as source, out.open('xb') as dest:
        shutil.copyfileobj(source, dest, length=1 << 20)
        dest.flush(); os.fsync(dest.fileno())
    if digest(out) != expected_sha:
        raise ValueError('copy_not_exact')
    with out.open('r+b') as f:
        for start, _, _, new in patches:
            f.seek(start); f.write(new)
        f.flush(); os.fsync(f.fileno())
    patched_sha = digest(out)
    if patched_sha == expected_sha:
        raise ValueError('no_bytes_changed')
    with model.open('rb') as original, out.open('rb') as changed:
        last = 0
        for start, end, _, new in patches:
            if not equal_region(original, changed, last, start):
                raise ValueError('unselected_region_changed')
            changed.seek(start)
            if changed.read(end-start) != new:
                raise ValueError('selected_patch_mismatch')
            last = end
        if not equal_region(original, changed, last, model.stat().st_size):
            raise ValueError('unselected_tail_changed')
    with out.open('r+b') as f:
        for start, _, old, _ in patches:
            f.seek(start); f.write(old)
        f.flush(); os.fsync(f.fileno())
    if digest(out) != expected_sha or digest(model) != expected_sha:
        raise ValueError('rollback_or_source_changed')
    return {'schema': 'V13_RUN168_REVERSIBLE_FP32_GGUF_V1',
            'registered_model_sha256': expected_sha,
            'private_patched_sha256_before_rollback': patched_sha,
            'private_restored_sha256': expected_sha,
            'selected_spans': len(patches), 'updated_l2': update_l2,
            'unselected_bytes_identical': True, 'source_model_unchanged': True,
            'private_rollback_exact': True, 'quantized_tensors_touched': 0,
            'body_training_authority': 0, 'jepa_weight': 0, 'gates': GATES,
            'gate': 'UNVERIFIED',
            'evidence_class': 'PRIVATE_BINARY_REVERSIBLE_FP32_ONLY_NO_INFERENCE',
            'limitations': ['synthetic Run166 objective, not JEPA or learning utility',
                            'no native model inference/receiver or persistent active swap',
                            'no Redmi, retention, requantizer or Body-JEPA acceptance']}
