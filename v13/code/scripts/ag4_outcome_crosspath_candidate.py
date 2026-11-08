"""Materialize the reviewed AG4 patch beside the feedback/replay candidates.

All source and patch hashes are verified first. Original files are read only;
the returned bytes are for an isolated copy, never the registered cohort.
"""
from hashlib import sha256
from pathlib import Path
import subprocess
import tempfile


BASE = {
    'agi/live.py': '5cb746a5c9f558f8c5599a471eac29573bf73ca523f65766b6d0cf5f875eb821',
    'agi/skills.py': '8a7d047264427a46d07fcbb6b1b2b19d5edd388d15cfc42a6f301d5150e69bc9',
    'skilllive.py': '3b86eea05a73628e49d561e8cb69c90f3ac0bffed643b61a76dd8303146e5086',
    'inputs.py': 'e9ecad21980e07c91807f7f9fe7f4472c5ec0e2a07c5cadc666962d8e61e2942',
}
TARGET = {
    'agi/live.py': '8dd9a4fbfa5bb5e696f4910f46f67971e37bad4ed91e67511b5be138fa38af45',
    'agi/skills.py': '415d10e6e5be94a172ffb3e4fecae279a875c8865ba0be34ff8eefcfd8fbfcc7',
    'skilllive.py': 'f8365557e5cc9afea80d5088b18848054a01ad8f7a62c73fab50eb6fbc93f5f7',
}
PATCH_SHA256 = 'eee6f3e8dc9e0a463a5eb333f66af9bd0c19f529f1aa1b822d39f590a8c3b892'
PATCH = Path(__file__).with_name('ag4_human_outcome_review_20261108.patch')
OLD = b'        try:import_module(module_name,__package__).on_rating(store,event_id,score)\n'
NEW = b'''        try:
            callback=import_module(module_name,__package__).on_rating
            if module_name=='.agi.live':callback(store,event_id,score,origin=origin)
            else:callback(store,event_id,score)
'''


def build_sources(source_dir, patch_file=PATCH):
    source_dir, patch_file = Path(source_dir), Path(patch_file)
    data = {}
    for name, expected in BASE.items():
        data[name] = (source_dir / name).read_bytes()
        if sha256(data[name]).hexdigest() != expected:
            raise ValueError('unsupported source: ' + name)
    patch = patch_file.read_bytes()
    if sha256(patch).hexdigest() != PATCH_SHA256:
        raise ValueError('unsupported AG4 review patch')
    if data['inputs.py'].count(OLD) != 1:
        raise ValueError('ambiguous feedback fanout anchor')
    with tempfile.TemporaryDirectory() as home:
        root = Path(home)
        for name in TARGET:
            out = root / name
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(data[name])
        local_patch = root / 'review.patch'
        local_patch.write_bytes(patch)
        try:
            subprocess.run(['git', 'apply', '--check', '--unidiff-zero', '-p4', str(local_patch)], cwd=root,
                           capture_output=True, check=True)
            subprocess.run(['git', 'apply', '--unidiff-zero', '-p4', str(local_patch)], cwd=root,
                           capture_output=True, check=True)
        except subprocess.CalledProcessError as exc:
            raise ValueError('AG4 patch does not apply to pinned sources') from exc
        for name, expected in TARGET.items():
            data[name] = (root / name).read_bytes()
            if sha256(data[name]).hexdigest() != expected:
                raise ValueError('AG4 reviewed output mismatch: ' + name)
    data['inputs.py'] = data['inputs.py'].replace(OLD, NEW, 1)
    return data
