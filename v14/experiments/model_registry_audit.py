"""Read-only V14 model registry audit. Never downloads or swaps models."""
import argparse
import json
from pathlib import Path

REQUIRED = ('model_id', 'revision', 'license_id', 'license_url', 'main_file', 'files')

def audit(registry):
    issues = []
    models = registry.get('models', {})
    for role, model in models.items():
        for field in REQUIRED:
            if not model.get(field):
                issues.append({'role': role, 'code': 'MISSING_' + field.upper()})
        files = model.get('files', [])
        if not isinstance(files, list):
            issues.append({'role': role, 'code': 'INVALID_FILES'})
            continue
        for i, item in enumerate(files):
            if not isinstance(item, dict):
                issues.append({'role': role, 'code': 'INVALID_FILE_ENTRY', 'index': i})
                continue
            sha = item.get('sha256', '')
            if len(sha) != 64 or any(c not in '0123456789abcdef' for c in sha):
                issues.append({'role': role, 'code': 'INVALID_SHA256', 'index': i})
            if not isinstance(item.get('size'), int) or item['size'] <= 0:
                issues.append({'role': role, 'code': 'INVALID_SIZE', 'index': i})
            if not str(item.get('url', '')).startswith('https://'):
                issues.append({'role': role, 'code': 'INVALID_URL', 'index': i})
        if files and model.get('main_file') not in [x.get('local_name') for x in files if isinstance(x, dict)]:
            issues.append({'role': role, 'code': 'MAIN_FILE_NOT_LISTED'})
    return {'status': 'PASS' if not issues else 'FAIL', 'models_checked': len(models), 'issues': issues,
            'proof': 'METADATA_ONLY_NO_NATIVE_OR_LICENSE_VERIFICATION'}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('registry', type=Path)
    args = parser.parse_args()
    result = audit(json.loads(args.registry.read_text(encoding='utf-8')))
    print(json.dumps(result, indent=2))
    raise SystemExit(bool(result['issues']))

if __name__ == '__main__':
    main()
