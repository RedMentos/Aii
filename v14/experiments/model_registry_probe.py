"""Read-only V14 model slot comparison; never downloads, imports or switches models."""
import argparse
import json
from pathlib import Path

ROLES = ('language', 'body', 'gist', 'needle')

def audit(manifest, installed=None):
    models = manifest['models']
    out = []
    for role in ROLES:
        spec = models[role]
        files = spec['files']
        total = sum(f['size'] for f in files)
        warnings = []
        if not spec.get('revision') or not spec.get('license_id') or not spec.get('license_url'):
            warnings.append('MISSING_PROVENANCE')
        if any(not f.get('sha256') or len(f['sha256']) != 64 for f in files):
            warnings.append('MISSING_CHECKSUM')
        if role == 'needle' and 'android-arm64' not in spec.get('platforms', {}):
            warnings.append('ANDROID_ARM64_ARTIFACT_MISSING')
        slot = (installed or {}).get(role)
        if slot is None:
            status = 'NOT_INSTALLED_OR_UNVERIFIED'
        elif slot.get('exact_revision') != spec['revision']:
            status = 'REVISION_MISMATCH'
        elif not slot.get('download_complete'):
            status = 'INCOMPLETE'
        else:
            status = 'MANIFEST_MATCH_NOT_RUNTIME_PROOF'
        out.append({'role': role, 'model_id': spec['model_id'],
                    'revision': spec['revision'], 'license': spec.get('license_id'),
                    'quant': spec['quant_format'], 'download_bytes': total,
                    'slot_status': status, 'warnings': warnings,
                    'native_ttft_ms': None, 'native_rss_bytes': None,
                    'redmi_verified': False})
    return out

def main():
    p = argparse.ArgumentParser()
    p.add_argument('registry', type=Path)
    p.add_argument('--installed', type=Path)
    a = p.parse_args()
    manifest = json.loads(a.registry.read_text())
    installed = json.loads(a.installed.read_text()) if a.installed else None
    print(json.dumps(audit(manifest, installed), indent=2))

if __name__ == '__main__':
    main()
