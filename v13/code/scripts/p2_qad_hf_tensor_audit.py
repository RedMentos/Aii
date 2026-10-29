#!/usr/bin/env python3
"""Read-only, fail-closed P2 HF↔GGUF structural audit; no training or weight loading.

STRUCTURE_MATCH_PARITY_UNPROVEN is NOT tensor-value, tokenizer, RoPE, native
logit, LoRA transfer, causal-state, STEP2 or Redmi acceptance.
"""
import argparse
import hashlib
import json
from pathlib import Path

MASTER_SHA = '1c9c77a4471a7f590f85240f74ed1fc26df7fbde88c3006724e2f93ca993ea4e'
GGUF_SHA = '3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d'


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def safetensors_header(path):
    """Read only the header; reject malformed or truncated tensor metadata."""
    with open(path, 'rb') as f:
        prefix = f.read(8)
        if len(prefix) != 8:
            raise ValueError('short safetensors prefix')
        size = int.from_bytes(prefix, 'little')
        if not 2 <= size <= 64 * 1024 * 1024:
            raise ValueError('invalid safetensors header length')
        header = f.read(size)
        if len(header) != size:
            raise ValueError('truncated safetensors header')
    raw = json.loads(header)
    if not isinstance(raw, dict):
        raise ValueError('safetensors header is not a dictionary')
    out = {}
    for name, record in raw.items():
        if name == '__metadata__':
            continue
        if not isinstance(record, dict) or not isinstance(record.get('shape'), list):
            raise ValueError('invalid tensor metadata')
        dims = record['shape']
        if not dims or any(type(x) is not int or x <= 0 for x in dims):
            raise ValueError('invalid tensor dimensions')
        if not isinstance(record.get('dtype'), str):
            raise ValueError('invalid tensor dtype')
        out[name] = {'shape': dims, 'dtype': record['dtype']}
    if not out:
        raise ValueError('no tensors in safetensors header')
    return out


def compare(hf, gguf_tensors, mapper):
    """Compare HF shapes against reversed GGUF on-disk dimensions.

    gguf_tensors: {name: {shape: GGML on-disk dims, type: quant type}}.
    mapper: existing gguf.get_tensor_name_map(...).get_name callable.
    """
    matched, missing, shape_mismatch, unmapped, collision = [], [], [], [], []
    seen = set()
    for name in sorted(hf):
        if not name.endswith('.weight'):
            unmapped.append(name)
            continue
        g = mapper(name[:-7])
        if not g:
            unmapped.append(name)
            continue
        key = g + '.weight'
        if key in seen:
            collision.append({'hf': name, 'gguf': key})
            continue
        seen.add(key)
        rec = gguf_tensors.get(key)
        if rec is None:
            missing.append({'hf': name, 'gguf': key})
            continue
        expected = list(hf[name]['shape'])
        actual = list(reversed(rec['shape']))
        if actual != expected:
            shape_mismatch.append({'hf': name, 'gguf': key,
                                   'hf_shape': expected, 'gguf_decoded_shape': actual})
        else:
            matched.append({'hf': name, 'gguf': key, 'shape': expected,
                            'gguf_type': rec['type']})
    extras = sorted(set(gguf_tensors) - seen)
    clean = not (missing or shape_mismatch or unmapped or collision or extras)
    return {'schema': 'v13.p2.qad_hf_tensor_structural_audit.v1',
            'status': 'STRUCTURE_MATCH_PARITY_UNPROVEN' if clean else 'STRUCTURE_RED',
            'hf_count': len(hf), 'gguf_count': len(gguf_tensors),
            'matched_count': len(matched), 'matched': matched,
            'missing': missing, 'shape_mismatch': shape_mismatch,
            'unmapped_hf': unmapped, 'collisions': collision,
            'unaccounted_gguf': extras,
            'unproven': ['QAD tensor values', 'tokenizer/template parity',
                         'q/k RoPE layout', 'native logits', 'adapter transfer',
                         'LP3 causal-state utility', 'Redmi']}


def audit(master, gguf_path):
    master, gguf_path = Path(master), Path(gguf_path)
    weight = master / 'model.safetensors'
    if sha256(weight) != MASTER_SHA or sha256(gguf_path) != GGUF_SHA:
        raise ValueError('immutable master/GGUF SHA256 mismatch')
    import gguf  # optional, lazy; only after source hashes pass
    config = json.loads((master / 'config.json').read_text(encoding='utf-8'))
    arch = [a for a, n in gguf.MODEL_ARCH_NAMES.items() if n == config.get('model_type')]
    if len(arch) != 1:
        raise ValueError('unknown or ambiguous GGUF architecture')
    mapping = gguf.get_tensor_name_map(arch[0], int(config['num_hidden_layers']))
    reader = gguf.GGUFReader(str(gguf_path))
    tensors = {t.name: {'shape': [int(v) for v in t.shape],
                        'type': t.tensor_type.name} for t in reader.tensors}
    result = compare(safetensors_header(weight), tensors, mapping.get_name)
    result['pins'] = {'master_sha256': MASTER_SHA, 'gguf_sha256': GGUF_SHA,
                      'config_sha256': sha256(master / 'config.json')}
    for name in ('tokenizer.json', 'tokenizer_config.json'):
        p = master / name
        result['pins'][name + '_sha256'] = sha256(p) if p.is_file() else None
    return result


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--master', required=True)
    p.add_argument('--gguf', required=True)
    p.add_argument('--output', required=True)
    args = p.parse_args(argv)
    try:
        result = audit(args.master, args.gguf)
    except (OSError, ValueError, KeyError, ImportError) as exc:
        result = {'schema': 'v13.p2.qad_hf_tensor_structural_audit.v1',
                  'status': 'STRUCTURE_RED',
                  'error': type(exc).__name__ + ': ' + str(exc)}
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, sort_keys=True, indent=2) + '\n', encoding='utf-8')
    return 0 if result['status'] == 'STRUCTURE_MATCH_PARITY_UNPROVEN' else 2


if __name__ == '__main__':
    raise SystemExit(main())
