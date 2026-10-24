#!/usr/bin/env python3
"""Read-only, pinned comparison of scoped package files across fetched Git refs.

This checks bytes and ownership declarations, not utility, completion or live agents.
It never fetches, checks out, merges, writes Git objects or changes runtime/status.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import subprocess


SCHEMA = 'v13-branch-content-audit-v1'


def git(repo, *args, input=None, check=True):
    # A read-only command must not refresh/lock the user's index.
    env = dict(os.environ, GIT_OPTIONAL_LOCKS='0', GIT_NO_LAZY_FETCH='1')
    result = subprocess.run(['git', '-C', str(repo), *args], input=input,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
    if check and result.returncode:
        raise ValueError('Git read failed: ' + ' '.join(args) + ': ' +
                         result.stderr.decode('utf-8', 'replace').strip())
    return result


def resolve(repo, ref):
    return git(repo, 'rev-parse', '--verify', ref + '^{commit}').stdout.decode().strip()


def tree(repo, commit):
    return git(repo, 'rev-parse', '--verify', commit + '^{tree}').stdout.decode().strip()


def entry(repo, commit, path):
    rows = git(repo, 'ls-tree', '-z', commit, '--', path).stdout.split(b'\0')
    for row in rows:
        if not row:
            continue
        metadata, name = row.split(b'\t', 1)
        if name.decode() == path:
            mode, kind, oid = metadata.decode().split()
            if kind != 'blob':
                raise ValueError('Scoped path must be a file: ' + path)
            return {'mode': mode, 'blob': oid}
    return None


def worktree_entry(repo, path):
    file = Path(repo) / path
    if file.is_symlink():
        data, mode = os.fsencode(os.readlink(file)), '120000'
    elif file.is_file():
        data = file.read_bytes()
        mode = '100755' if file.stat().st_mode & 0o111 else '100644'
    else:
        return None
    oid = git(repo, 'hash-object', '--stdin', input=data).stdout.decode().strip()
    return {'mode': mode, 'blob': oid, 'sha256': hashlib.sha256(data).hexdigest()}


def validate_plan(plan):
    if plan.get('schema') != SCHEMA or not plan.get('packages'):
        raise ValueError('Expected schema and nonempty packages')
    required = ('ref', 'commit', 'tree')
    for snapshot in [plan['baseline']] + plan['packages']:
        if any(not isinstance(snapshot.get(k), str) or not snapshot[k] for k in required):
            raise ValueError('Each snapshot requires ref, commit and tree pins')
    owners, package_owners = {}, set()
    for package in plan['packages']:
        owner = package['owner']
        if not owner or owner in package_owners:
            raise ValueError('Duplicate or empty package owner: ' + owner)
        package_owners.add(owner)
        if not package.get('paths') or len(set(package['paths'])) != len(package['paths']):
            raise ValueError('Missing or duplicate scoped paths: ' + owner)
        for path in package['paths']:
            parsed = PurePosixPath(path)
            if parsed.is_absolute() or '..' in parsed.parts or str(parsed) != path or path == '.':
                raise ValueError('Unsafe scoped path: ' + path)
            if path in owners:
                raise ValueError('Ownership conflict: ' + path + ': ' + owners[path] + ' / ' + owner)
            owners[path] = owner
    return owners


def audit(repo, plan):
    owners = validate_plan(plan)
    issues, rows, snapshots = [], [], []
    baseline = plan['baseline']
    for snapshot in [baseline] + plan['packages']:
        current = resolve(repo, snapshot['ref'])
        actual_tree = tree(repo, snapshot['commit'])
        snapshots.append({'owner': snapshot.get('owner', 'BASELINE'), 'ref': snapshot['ref'],
                          'commit': snapshot['commit'], 'tree': actual_tree,
                          'resolved_ref': current})
        if current != snapshot['commit']:
            issues.append({'kind': 'REF_MOVED', 'ref': snapshot['ref'],
                           'expected': snapshot['commit'], 'actual': current})
        if actual_tree != snapshot['tree']:
            issues.append({'kind': 'TREE_PIN_MISMATCH', 'ref': snapshot['ref']})
    for package in plan['packages']:
        for path in sorted(package['paths']):
            source = entry(repo, package['commit'], path)
            base = entry(repo, baseline['commit'], path)
            working = worktree_entry(repo, path)
            if source is None:
                issues.append({'kind': 'SOURCE_PATH_MISSING', 'owner': package['owner'], 'path': path})
            def comparison(other):
                if source is None:
                    return 'SOURCE_MISSING'
                if other is None:
                    return 'MISSING'
                return 'MATCH' if all(source[k] == other[k] for k in ('mode', 'blob')) else 'DIFFERENT'
            dirty = bool(git(repo, 'status', '--porcelain=v1', '-z', '--untracked-files=all',
                             '--', path).stdout)
            rows.append({'owner': package['owner'], 'path': path, 'source': source,
                         'baseline': base, 'working': working,
                         'baseline_comparison': comparison(base),
                         'working_comparison': comparison(working), 'scoped_dirty': dirty})
            if dirty:
                issues.append({'kind': 'SCOPED_WORKTREE_DIRTY', 'path': path})
    # Bound to the actual checked-out snapshot, including staged changes via status.
    head = resolve(repo, 'HEAD')
    if head != baseline['commit']:
        issues.append({'kind': 'WORKTREE_HEAD_DIFFERS', 'expected': baseline['commit'], 'actual': head})
    for snapshot in snapshots:
        if resolve(repo, snapshot['ref']) != snapshot['resolved_ref']:
            issues.append({'kind': 'REF_CHANGED_DURING_AUDIT', 'ref': snapshot['ref']})
    counts = {kind: sum(r['working_comparison'] == kind for r in rows)
              for kind in ('MATCH', 'MISSING', 'DIFFERENT', 'SOURCE_MISSING')}
    return {'schema': SCHEMA, 'evidence_level': 'FETCHED_LOCAL_GIT_AND_SCOPED_WORKTREE',
            'network_used': False, 'runtime_changed': False, 'active_thread_state': 'NOT_OBSERVED',
            'scope': 'Declared package paths only; differences do not imply a required merge or completion.',
            'source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'plan_sha256': hashlib.sha256(json.dumps(plan, sort_keys=True, separators=(',', ':')).encode()).hexdigest(),
            'head': head, 'snapshots': snapshots, 'files': rows, 'working_counts': counts,
            'issues': issues, 'status': 'CLEAN_SCOPED_COMPARISON' if not issues else 'AUDIT_ISSUES'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    report = audit(args.repo, json.loads(args.plan.read_text()))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    return 0 if not report['issues'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
