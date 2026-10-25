"""Run163: read-only, external-SHA-bound verification of Run162 FP32 NPZ.

No GGUF/NPZ writes, training, model updates, or permission promotion.
This checker verifies only selected F32 vectors, not every GGUF tensor span.
"""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

import numpy as np
from scripts.body_gguf_dtype_audit_run160 import MAX_PREFIX, parse

GATES = {'STEP2': 'UTILITY_FAIL', 'B3_L1': 'FAIL',
         'Body_JEPA': 'UNAVAILABLE', 'jepa_weight': 0,
         'DS2_H2': 'FAIL', 'V13': 'INCOMPLETE'}
MAX_VECTORS = 8
MAX_VECTOR_BYTES = 16 * 1024 * 1024


def digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def verify(model, master, report, expected_sha):
    """Verify independent external model SHA and Run162 report, no mutations."""
    model, master, report = map(Path, (model, master, report))
    if any(p.is_symlink() or not p.is_file() for p in (model, master, report)):
        raise ValueError('regular_nonsymlink_files_required')
    if not isinstance(expected_sha, str) or len(expected_sha) != 64 or any(
            c not in '0123456789abcdef' for c in expected_sha):
        raise ValueError('external_sha_required')
    if digest(model) != expected_sha:
        raise ValueError('external_model_sha_mismatch')
    r = json.loads(report.read_text(encoding='utf-8'))
    if not isinstance(r, dict) or r.get('schema') != 'V13_RUN162_FP32_SLICE_EXPORT_V1':
        raise ValueError('report_schema')
    if r.get('registered_model_sha256') != expected_sha or r.get('full_model_sha256_verified') is not True:
        raise ValueError('report_model_binding')
    if r.get('master_candidate_sha256') != digest(master) or r.get('master_candidate_bytes') != master.stat().st_size:
        raise ValueError('master_digest_mismatch')
    if r.get('body_training_authority') != 0 or r.get('train_master_authority') != 0 or r.get('gates') != GATES:
        raise ValueError('authority_or_gates')
    selection = r.get('selected_tensors')
    if not isinstance(selection, list) or not 1 <= len(selection) <= MAX_VECTORS:
        raise ValueError('selection_bounds')
    names = [t.get('name') for t in selection if isinstance(t, dict)]
    if len(names) != len(selection) or any(not isinstance(n, str) or not n or len(n) > 64 for n in names) or len(set(names)) != len(names):
        raise ValueError('selection_names')
    with open(model, 'rb') as f:
        meta = parse(f.read(MAX_PREFIX))
    expected = {}
    spans = []
    for entry in selection:
        name = entry['name']
        t = meta['tensors'].get(name)
        if t is None or t['type'] != 'F32' or len(t['dims']) != 1:
            raise ValueError('source_tensor_not_f32_vector')
        size = 4 * t['dims'][0]
        pos = meta['tensor_data_start'] + t['offset']
        if size > MAX_VECTOR_BYTES or pos + size > model.stat().st_size:
            raise ValueError('source_tensor_bounds')
        if (entry.get('shape') != list(t['dims']) or entry.get('dtype') != 'float32' or
                entry.get('bytes') != size or entry.get('offset_in_gguf') != pos):
            raise ValueError('source_manifest_mismatch')
        spans.append((pos, pos + size))
        expected[name] = (pos, size, entry.get('sha256'))
    spans.sort()
    if any(a[1] > b[0] for a, b in zip(spans, spans[1:])):
        raise ValueError('selected_source_spans_overlap')
    with zipfile.ZipFile(master) as archive:
        infos = archive.infolist()
        if sorted(i.filename for i in infos) != sorted(n + '.npy' for n in names):
            raise ValueError('npz_entries_mismatch')
        if any(i.file_size > MAX_VECTOR_BYTES + 4096 or i.file_size < 128 or i.flag_bits & 1 for i in infos):
            raise ValueError('npz_entry_bounds')
        with np.load(master, allow_pickle=False) as z, open(model, 'rb') as source:
            if sorted(z.files) != sorted(names):
                raise ValueError('npz_names')
            for name in names:
                pos, size, claimed = expected[name]
                source.seek(pos)
                raw = source.read(size)
                if len(raw) != size or hashlib.sha256(raw).hexdigest() != claimed:
                    raise ValueError('source_tensor_digest')
                x = z[name]
                if x.dtype != np.dtype('<f4') or x.shape != (size // 4,) or not np.isfinite(x).all():
                    raise ValueError('npz_tensor_type_shape_finite')
                # np.array_equal() incorrectly treats +0.0 and -0.0 as identical.
                if x.tobytes(order='C') != raw:
                    raise ValueError('npz_source_bytes_mismatch')
    if digest(model) != expected_sha or digest(master) != r['master_candidate_sha256']:
        raise ValueError('postread_digest_mismatch')
    return {'schema': 'V13_RUN163_FP32_EXPORT_AUDIT_V1',
            'model_sha256': expected_sha, 'master_sha256': r['master_candidate_sha256'],
            'selected_count': len(names), 'selected_source_spans_nonoverlap': True,
            'selected_bytes_exact': True, 'evidence_class': 'READ_ONLY_SOFTWARE_OR_SOURCE_AUDIT',
            'body_training_authority': 0, 'gate': 'UNVERIFIED', 'gates': GATES,
            'limitations': ['only selected F32 vectors checked; unselected GGUF tensors not fully validated',
                            'not a train master, no gradients/EMA/requantizer or model integration',
                            'no native training, learning utility, retention or Redmi evidence']}


def main():
    p = argparse.ArgumentParser()
    for n in ('model', 'master', 'report'):
        p.add_argument('--' + n, type=Path, required=True)
    p.add_argument('--sha256', required=True)
    a = p.parse_args()
    print(json.dumps(verify(a.model, a.master, a.report, a.sha256), sort_keys=True))


if __name__ == '__main__':
    main()
