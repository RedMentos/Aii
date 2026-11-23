#!/usr/bin/env python3
"""Pinned QAD GGUF embedded Jinja template exact-byte audit, no model inference."""
import argparse
import hashlib
import json
import os
from pathlib import Path

GGUF_SHA = '3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d'
TEMPLATE_SHA = 'ba551d58630afa3190b1be3602e28301f3d2e9bbac978dfc49d6d825171648b6'


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def compare(template_bytes, embedded):
    if not isinstance(embedded, str):
        raise ValueError('GGUF chat template missing or not UTF-8 text')
    encoded = embedded.encode('utf-8')
    return {'schema': 'v13.p2.qad_gguf_chat_template_metadata.v1',
            'status': 'TEMPLATE_BYTES_EQUAL_TOKEN_IDS_UNPROVEN'
                      if encoded == template_bytes else 'TEMPLATE_BYTES_RED',
            'source_sha256': hashlib.sha256(template_bytes).hexdigest(),
            'embedded_sha256': hashlib.sha256(encoded).hexdigest(),
            'source_bytes': len(template_bytes), 'embedded_bytes': len(encoded),
            'token_id_logit_and_utility_parity_proven': False}


def audit(template, gguf_path):
    template, gguf_path = Path(template), Path(gguf_path)
    if template.is_symlink() or gguf_path.is_symlink():
        raise ValueError('symlinked source')
    if template.stat().st_size != 5487 or sha(template) != TEMPLATE_SHA:
        raise ValueError('QAD source template SHA/size mismatch')
    if gguf_path.stat().st_size != 219312832 or sha(gguf_path) != GGUF_SHA:
        raise ValueError('deployed GGUF SHA/size mismatch')
    import gguf
    reader = gguf.GGUFReader(str(gguf_path))
    field = reader.fields.get('tokenizer.chat_template')
    if field is None:
        raise ValueError('GGUF tokenizer.chat_template absent')
    result = compare(template.read_bytes(), field.contents())
    result['gguf_sha256'] = GGUF_SHA
    return result


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--template', required=True)
    p.add_argument('--gguf', required=True)
    p.add_argument('--output', required=True)
    args = p.parse_args(argv)
    try:
        result = audit(args.template, args.gguf)
    except (OSError, ValueError, ImportError, TypeError) as exc:
        result = {'schema': 'v13.p2.qad_gguf_chat_template_metadata.v1',
                  'status': 'TEMPLATE_BYTES_RED',
                  'error': type(exc).__name__ + ': ' + str(exc)}
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open('x', encoding='utf-8') as f:
        f.write(json.dumps(result, sort_keys=True, indent=2) + '\n')
        f.flush()
        os.fsync(f.fileno())
    return 0 if result['status'] == 'TEMPLATE_BYTES_EQUAL_TOKEN_IDS_UNPROVEN' else 2


if __name__ == '__main__':
    raise SystemExit(main())
