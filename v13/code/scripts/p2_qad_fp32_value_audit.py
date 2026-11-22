#!/usr/bin/env python3
"""Pinned QAD FP32 ↔ deployed QAD GGUF descriptive value audit; NO inference/training."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path

from p2_qad_hf_tensor_audit import compare, sha256, safetensors_header

REVISION = '657e078c94084481950a2d555a941481f715536b'
QAD_MASTER_SHA = '1d90518482c4ec204bebb4820bbaee4f8a38c5a6df72256f86bcd21fe52ad079'
QAD_GGUF_SHA = '3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d'
META_SHA = {
    'config.json': '884c7b2b936f296dd448bfca18a14fd9bc903be7d3bff1303ac62bbb43f641d6',
    'tokenizer.json': 'df1d8d5ec5d091b460562ffd545e4a5e91d17d4a0db7ebe733be34ed374377bd',
    'tokenizer_config.json': 'b99856c5bdc9f88cc30a7ffff78bfc7768427e0b1216d0c196b27e5d55043455',
    'chat_template.jinja': 'ba551d58630afa3190b1be3602e28301f3d2e9bbac978dfc49d6d825171648b6',
}


def source_offsets(path):
    """Validate FP32 safetensors header and offsets without reading all weights."""
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError('missing or symlinked FP32 source')
    size = path.stat().st_size
    with path.open('rb') as f:
        raw = f.read(8)
        if len(raw) != 8:
            raise ValueError('short safetensors header')
        length = int.from_bytes(raw, 'little')
        if not 2 <= length <= 64 * 1024 * 1024 or 8 + length > size:
            raise ValueError('invalid safetensors header size')
        header = json.loads(f.read(length))
    if not isinstance(header, dict):
        raise ValueError('invalid safetensors header')
    out = {}
    for name, rec in header.items():
        if name == '__metadata__':
            continue
        if rec.get('dtype') != 'F32':
            raise ValueError('non-F32 QAD tensor: ' + name)
        dims = rec['shape']
        offsets = rec['data_offsets']
        if (not dims or any(type(d) is not int or d <= 0 for d in dims)
                or len(offsets) != 2 or any(type(v) is not int for v in offsets)):
            raise ValueError('invalid tensor metadata: ' + name)
        count = math.prod(dims)
        start, end = offsets
        if start < 0 or end - start != count * 4 or 8 + length + end > size:
            raise ValueError('invalid tensor data range: ' + name)
        out[name] = {'shape': dims, 'dtype': 'F32', 'offset': 8 + length + start}
    if not out:
        raise ValueError('empty QAD safetensors')
    return out


def value_stats(a, b, block=1_000_000):
    """Numerically stable, bounded-chunk descriptive stats; no parity threshold."""
    import numpy as np
    a = np.asarray(a, dtype=np.float32).reshape(-1)
    b = np.asarray(b, dtype=np.float32).reshape(-1)
    if a.size != b.size or not a.size:
        raise ValueError('tensor element count mismatch')
    dot = aa = bb = sqerr = 0.0
    max_abs = 0.0
    for start in range(0, a.size, block):
        x = a[start:start + block].astype(np.float64)
        y = b[start:start + block].astype(np.float64)
        if not np.isfinite(x).all() or not np.isfinite(y).all():
            raise ValueError('nonfinite tensor values')
        delta = x - y
        dot += float(np.dot(x, y))
        aa += float(np.dot(x, x))
        bb += float(np.dot(y, y))
        sqerr += float(np.dot(delta, delta))
        max_abs = max(max_abs, float(np.max(np.abs(delta))))
    denom = math.sqrt(aa * bb)
    cosine = dot / denom if denom else (1.0 if aa == bb == 0 else 0.0)
    rmse = math.sqrt(sqerr / a.size)
    reference_rms = math.sqrt(bb / a.size)
    return {'elements': int(a.size), 'cosine': round(cosine, 9),
            'normalized_rmse': round(rmse / max(reference_rms, 1e-12), 9),
            'max_abs': round(max_abs, 8)}


def audit(master, gguf_path):
    import numpy as np
    master, gguf_path = Path(master), Path(gguf_path)
    if master.is_symlink() or not master.is_dir() or gguf_path.is_symlink():
        raise ValueError('symlinked or missing source')
    weight = master / 'model.safetensors'
    if weight.stat().st_size != 1417952352 or sha256(weight) != QAD_MASTER_SHA:
        raise ValueError('QAD FP32 source size/SHA mismatch')
    if gguf_path.stat().st_size != 219312832 or sha256(gguf_path) != QAD_GGUF_SHA:
        raise ValueError('deployed QAD GGUF size/SHA mismatch')
    for name, expected in META_SHA.items():
        p = master / name
        if p.is_symlink() or sha256(p) != expected:
            raise ValueError('QAD metadata source SHA mismatch: ' + name)
    import gguf
    from gguf.quants import dequantize
    config = json.loads((master / 'config.json').read_text())
    arch = [a for a, n in gguf.MODEL_ARCH_NAMES.items() if n == config['model_type']]
    if len(arch) != 1 or config.get('dtype') != 'float32':
        raise ValueError('QAD source architecture/dtype mismatch')
    mapper = gguf.get_tensor_name_map(arch[0], int(config['num_hidden_layers'])).get_name
    reader = gguf.GGUFReader(str(gguf_path))
    tensors = {t.name: t for t in reader.tensors}
    hf = source_offsets(weight)
    structure = compare(hf, {n: {'shape': list(map(int, t.shape)),
                                 'type': t.tensor_type.name} for n, t in tensors.items()}, mapper)
    if structure['status'] != 'STRUCTURE_MATCH_PARITY_UNPROVEN':
        raise ValueError('QAD structural mapping RED')
    rows = []
    for name in sorted(hf):
        key = mapper(name[:-7]) + '.weight'
        t = tensors[key]
        meta = hf[name]
        original = np.memmap(weight, mode='r', dtype='<f4', offset=meta['offset'],
                             shape=tuple(meta['shape']))
        quantized = dequantize(t.data, t.tensor_type)
        stats = value_stats(quantized, original)
        rows.append({'hf': name, 'gguf': key, 'quant_type': t.tensor_type.name,
                     'rope_layout_review': '.q_proj.' in name or '.k_proj.' in name,
                     **stats})
        del original, quantized
    return {'schema': 'v13.p2.qad_fp32_gguf_value_diagnostic.v1',
            'status': 'VALUES_MEASURED_PARITY_UNPROVEN', 'source_revision': REVISION,
            'source_sha256': QAD_MASTER_SHA, 'gguf_sha256': QAD_GGUF_SHA,
            'source_metadata_sha256': META_SHA, 'structure': {
                'hf_count': structure['hf_count'], 'gguf_count': structure['gguf_count'],
                'matched_count': structure['matched_count'],
                'approved_shape_transforms': structure['approved_shape_transforms']},
            'tensors': rows, 'tensor_count': len(rows),
            'no_inference': True, 'no_training': True,
            'weight_logit_adapter_and_utility_parity_proven': False}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--master', required=True)
    p.add_argument('--gguf', required=True)
    p.add_argument('--output', required=True)
    args = p.parse_args(argv)
    try:
        result = audit(args.master, args.gguf)
    except (OSError, ValueError, KeyError, ImportError, TypeError) as exc:
        result = {'schema': 'v13.p2.qad_fp32_gguf_value_diagnostic.v1',
                  'status': 'VALUE_AUDIT_RED', 'error': type(exc).__name__ + ': ' + str(exc)}
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open('x', encoding='utf-8') as f:
        f.write(json.dumps(result, sort_keys=True, indent=2) + '\n')
        f.flush()
        os.fsync(f.fileno())
    return 0 if result['status'] == 'VALUES_MEASURED_PARITY_UNPROVEN' else 2


if __name__ == '__main__':
    raise SystemExit(main())
