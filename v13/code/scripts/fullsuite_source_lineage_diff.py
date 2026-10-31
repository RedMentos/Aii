"""Read-only exact-lineage diff for frozen V13 candidate views vs live sources.

Diagnostic only: never a whitelist, automatic rebase or source promotion.
"""
import argparse
import difflib
import hashlib
import json
from pathlib import Path


def digest(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def compare(actual, expected):
    """Byte-level comparison with line-level location, never content output."""
    if set(actual) != set(expected):
        raise ValueError('VIEW_FILE_SET_MISMATCH')
    result = {}
    for name in sorted(actual):
        left, right = actual[name], expected[name]
        if not isinstance(left, str) or not isinstance(right, str):
            raise TypeError('SOURCE_NOT_TEXT')
        before, after = left.splitlines(keepends=True), right.splitlines(keepends=True)
        edits = [x for x in difflib.SequenceMatcher(None, after, before, autojunk=False).get_opcodes() if x[0]!='equal']
        result[name] = {'live_sha256':digest(left),'expected_sha256':digest(right),
                        'byte_equal':left.encode('utf-8')==right.encode('utf-8'),
                        'changed_hunks':len(edits),
                        'first_expected_line':edits[0][1]+1 if edits else None,
                        'first_live_line':edits[0][3]+1 if edits else None}
    return result


def snapshots(root):
    """Load only existing exact pinned sources; do not modify any live file."""
    from scripts import integrated_candidates as integrated
    from scripts import source_handoff_candidate as handoff
    expected_native = integrated.integrated_sources(root)
    original = {}
    folder = root/handoff.SNAPSHOT
    manifest = json.loads((folder/'manifest.json').read_text())
    if manifest.get('schema')!='SOURCE_HANDOFF_FROZEN_BASELINE_V1' or set(manifest['files'])!=set(handoff.NAMES):
        raise ValueError('HANDOFF_MANIFEST_INVALID')
    for name, sha in manifest['files'].items():
        raw=(folder/Path(name).name).read_bytes()
        if hashlib.sha256(raw).hexdigest()!=sha:
            raise ValueError('HANDOFF_FROZEN_SOURCE_HASH_RED')
        original[name]=raw.decode('utf-8')
    _, candidate = handoff._transform(original)
    return {'native_integrated_frozen_chain':expected_native,
            'handoff_rebased_baseline':integrated.rebase(original,root),
            'handoff_rebased_candidate':integrated.rebase(candidate,root)}


def report(root):
    root=Path(root).resolve()
    views=snapshots(root)
    result={'schema':'V13_FULLSUITE_EXACT_LINEAGE_DIFF_V1',
            'forensic_only':True,'promotion_authority':False,'root':str(root), 'views':{}}
    for label, expected in views.items():
        actual={name:(root/name).read_text(encoding='utf-8') for name in expected}
        diffs=compare(actual,expected)
        result['views'][label]={'exact':all(v['byte_equal'] for v in diffs.values()),
                                'mismatch_count':sum(not v['byte_equal'] for v in diffs.values()),
                                'files':diffs}
    return result


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root',required=True)
    ap.add_argument('--out',help='Exclusive-create JSON file, never overwrite')
    args=ap.parse_args(argv)
    payload=json.dumps(report(args.root),sort_keys=True,indent=2)+'\n'
    if args.out:
        with Path(args.out).open('x',encoding='utf-8') as f:f.write(payload)
    else:print(payload,end='')


if __name__=='__main__':main()
