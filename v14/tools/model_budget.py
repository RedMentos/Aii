"""Read-only V14 model storage budget audit. Never downloads or swaps weights."""
import argparse
import json
from pathlib import Path


def audit(registry, available_bytes):
    if not isinstance(available_bytes, int) or available_bytes < 0:
        raise ValueError('available_bytes must be a nonnegative integer')
    models = registry['models']
    rows = []
    for role, spec in models.items():
        files = spec.get('files', [])
        if not files:
            continue
        total = 0
        for item in files:
            size = item['size']
            if type(size) is not int or size < 0:
                raise ValueError(f'invalid size for {role}')
            total += size
        rows.append({'role': role, 'model_id': spec['model_id'], 'revision': spec['revision'], 'license_id': spec.get('license_id', 'UNKNOWN'), 'disk_bytes': total})
    rows.sort(key=lambda row: row['role'])
    combined = sum(row['disk_bytes'] for row in rows)
    return {'models': rows, 'combined_disk_bytes': combined, 'available_disk_bytes': available_bytes, 'fits_disk_only': combined <= available_bytes, 'warning': 'Disk-only static estimate. Not RAM/PSS/TTFT/quality/Android compatibility or download approval.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('registry', type=Path)
    parser.add_argument('--available-disk-bytes', required=True, type=int)
    args = parser.parse_args()
    print(json.dumps(audit(json.loads(args.registry.read_text()), args.available_disk_bytes), indent=2))


if __name__ == '__main__':
    main()
