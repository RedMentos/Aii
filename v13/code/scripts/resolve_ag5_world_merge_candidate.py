#!/usr/bin/env python3
"""Disposable, exact-SHA AG5/World merge-conflict resolver for CI review only.

Run ONLY after git merge --no-commit has reported exactly the two preregistered
conflicts. Does not create a commit, push, change Age/approval or touch main.
"""
import hashlib
from pathlib import Path
import subprocess

OP = 'v13/code/v13/operator.py'
HANDY = 'v13/code/scripts/handy_pflicht.py'
WORLD_OPERATOR_BLOB = '52886e7a20772bb5732e44dc12f9d6f8e5ab3d18'
AG5_OPERATOR_BLOB = '4065a5f34768477d55719ef450b8ee1fdd2b7f49'
WORLD_HANDY_BLOB = '06d5b0b59c68532d2d9a2c665eb96bd7b4993ab6'
AG5_HANDY_BLOB = '140fbe4e6f8d7a0ab8c0f63434c05e6985eeeff5'


def git(*args):
    return subprocess.check_output(['git', *args], text=True).strip()


def stage(path, stage_number, expected):
    ref = ':%d:%s' % (stage_number, path)
    actual = git('rev-parse', ref)
    if actual != expected:
        raise ValueError('Unexpected merge stage %s SHA: %s' % (ref, actual))
    return subprocess.check_output(['git', 'show', ref]).decode('utf-8')


def between(text, first, last):
    if text.count(first) != 1 or text.count(last) != 1:
        raise ValueError('Unexpected operator source markers')
    start = text.index(first)
    end = text.index(last, start + len(first))
    return text[start:end]


def resolve():
    conflicts = git('diff', '--name-only', '--diff-filter=U').splitlines()
    if conflicts != sorted((HANDY, OP)):
        raise ValueError('Unexpected conflicts; refuse to resolve: %r' % conflicts)
    world = stage(OP, 2, WORLD_OPERATOR_BLOB)
    ag5 = stage(OP, 3, AG5_OPERATOR_BLOB)
    stage(HANDY, 2, WORLD_HANDY_BLOB)
    ag5_handy = stage(HANDY, 3, AG5_HANDY_BLOB)

    # Retain AG5 operator as authoritative baseline and graft only three
    # explicit World operator capabilities from the exact conflict stage.
    world_handler = between(world, "        if cmd=='world':\n",
                            "        if cmd in {'components','objectives'}:")
    supersede_handler = between(world, "        if cmd=='ersetze':",
                                "        if cmd=='neuromod':")
    world_help = next(x for x in world.splitlines() if x.startswith(':world shadow '))
    supersede_help = next(x for x in world.splitlines() if x.startswith(':ersetze route '))
    effort_help = next(x for x in world.splitlines() if x.startswith(':effort ['))
    if ag5.count("        if cmd=='world':return dumps(r.world.world_state())") != 1:
        raise ValueError('AG5 world handler unexpectedly changed')
    ag5 = ag5.replace("        if cmd=='world':return dumps(r.world.world_state())",
                      world_handler.rstrip('\n'), 1)
    if ag5.count("        if cmd=='neuromod':") != 1:
        raise ValueError('AG5 insertion point changed')
    ag5 = ag5.replace("        if cmd=='neuromod':",
                      supersede_handler + "        if cmd=='neuromod':", 1)
    help_anchor = ':self / :world / :native / :knobs / :components / :objectives / :plasticity [component]'
    if ag5.count(help_anchor) != 1:
        raise ValueError('AG5 help anchor changed')
    ag5 = ag5.replace(help_anchor, help_anchor + '\n' + world_help, 1)
    feedback_anchor = ':feedback route simple|detail|gist|both [--learn]'
    if ag5.count(feedback_anchor) != 1:
        raise ValueError('AG5 route help anchor changed')
    ag5 = ag5.replace(feedback_anchor, feedback_anchor + '\n' + supersede_help, 1)
    old_effort_help = next(x for x in ag5.splitlines() if x.startswith(':effort ['))
    ag5 = ag5.replace(old_effort_help, effort_help, 1)
    old_error = "raise ValueError(':effort [disabled|low|adaptive|high|max]')"
    new_error = "raise ValueError(':effort [disabled|low|adaptive|high|max|detail|gist]')"
    if ag5.count(old_error) != 1:
        raise ValueError('AG5 effort handler changed')
    ag5 = ag5.replace(old_error, new_error, 1)

    # Explicit guard assertions: never move the World read before the existing
    # local-TTY guard; preserve AG5 idle locks and chat/language features.
    for required in (
        "if origin!='OPERATOR_TTY':raise ValueError",
        "if cmd=='ersetze':",
        "prohibitions.blocked(s, 'world_shadow_probe', 'READ_LOCAL', True)",
        "prohibitions.announce_all(s)",
        "MAX_PROVENANCE_BYTES, MAX_REQUEST_BYTES",
        "if cmd=='befehle':",
        "if cmd=='language':",
        "with r.lock:",
        "r.require_idle()",
        "SELECT * FROM sessions WHERE created<?",
        "from .chat_export import export_chat",
        "if cmd=='effort':",
    ):
        if required not in ag5:
            raise ValueError('Missing AG5/World safety or capability: ' + required)
    if ag5.index("if origin!='OPERATOR_TTY'") > ag5.index("if cmd=='world':"):
        raise ValueError('World handler before TTY guard')
    if ag5.index("prohibitions.blocked(s, 'world_shadow_probe'") > ag5.index(
            "provenance = _json_file(args[3]"):
        raise ValueError('World read before prohibitions')
    if ag5.count("        if cmd=='world':") != 1:
        raise ValueError('Duplicate world handler')
    if ag5.count("        if cmd=='ersetze':") != 1:
        raise ValueError('Duplicate route supersession handler')

    Path(OP).write_text(ag5)
    Path(HANDY).write_text(ag5_handy)
    subprocess.check_call(['git', 'add', OP, HANDY])
    unresolved = git('ls-files', '-u')
    if unresolved:
        raise ValueError('Unresolved paths remain')
    subprocess.check_call(['git', 'diff', '--cached', '--check'])
    # Preserve AG5 V2 byte-exact, no World V1 regression.
    actual_handy = git('hash-object', HANDY)
    if actual_handy != AG5_HANDY_BLOB:
        raise ValueError('AG5 V2 handy helper changed')
    return {
        'operator_blob_sha': git('hash-object', OP),
        'handy_blob_sha': actual_handy,
        'candidate_tree_sha': git('write-tree'),
        'operator_sha256': hashlib.sha256(Path(OP).read_bytes()).hexdigest(),
        'handy_sha256': hashlib.sha256(Path(HANDY).read_bytes()).hexdigest(),
    }


if __name__ == '__main__':
    import json
    print(json.dumps(resolve(), sort_keys=True))
