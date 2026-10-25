"""Read-only, fail-closed distinction between frozen Run177 and current V13 sources.

No runtime authority, model access, native execution, auto-repair or rehashing.
Any reviewed future change to these files needs an explicit new source manifest.
"""
import hashlib
import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
MANIFEST=ROOT/'specs/current_source_lineage_run357.json'
NAMES=('v13/runners.py','v13/memory_server.py','v13/runtime.py','v13/store.py')
SHA=re.compile(r'[a-f0-9]{64}\Z')
RUNNER_MARKERS=(
    "self.role in ('C3_LANGUAGE','B2_GIST') else 2048",
    "'qwen35.result_norm.final.v1' if self.role=='B2_GIST'",
    "'lfm2.result_norm.final.v1'",
    'Pinned role-specific final token-state readout',
)
RUNTIME_MARKER='lead=toolctl.ToolStep(self).lead(tool_result)'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def verify(root=ROOT,manifest_path=MANIFEST):
    """Require BOTH original integrated transformation and current live digests."""
    root=Path(root)
    manifest_path=Path(manifest_path)
    if manifest_path.is_symlink():
        raise ValueError('Current lineage manifest symlink')
    d=json.loads(manifest_path.read_text())
    if d.get('schema')!='v13-current-chain-lineage-v1':
        raise ValueError('Current lineage schema changed')
    for field in ('historical_sha256','current_sha256'):
        hashes=d.get(field)
        if not isinstance(hashes,dict) or set(hashes)!=set(NAMES) or not all(
                isinstance(v,str) and SHA.fullmatch(v) for v in hashes.values()):
            raise ValueError('Current lineage manifest incomplete: '+field)
    from scripts.integrated_candidates import integrated_sources
    historical=integrated_sources(root)
    if set(historical)!=set(NAMES):
        raise ValueError('Historical chain file scope changed')
    current={}
    for name in NAMES:
        p=root/name
        if p.is_symlink() or not p.is_file():
            raise ValueError('Current lineage source missing or symlinked: '+name)
        current[name]=p.read_bytes()
        if sha(historical[name].encode('utf-8'))!=d['historical_sha256'][name]:
            raise ValueError('Historical integrated chain digest changed: '+name)
        if sha(current[name])!=d['current_sha256'][name]:
            raise ValueError('Current reviewed source digest changed: '+name)
    for marker in RUNNER_MARKERS:
        if marker not in historical['v13/runners.py'] or marker.encode() not in current['v13/runners.py']:
            raise ValueError('Run177 B2/C3 native tap marker missing')
    if RUNTIME_MARKER not in historical['v13/runtime.py'] or RUNTIME_MARKER.encode() not in current['v13/runtime.py']:
        raise ValueError('Fixed eligibility first-answer chain marker missing')
    return {'historical_chain_exact':True,'current_reviewed_sources_exact':True,
            'scope':list(NAMES),'claim_limit':'SOURCE_ONLY_NOT_NATIVE_OR_REDMi'}


if __name__=='__main__':
    print(json.dumps(verify(),sort_keys=True))
