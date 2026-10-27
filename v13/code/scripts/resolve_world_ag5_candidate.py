#!/usr/bin/env python3
"""One-off exact-source merge resolution for review-only World+AG5 candidate.

Run only after git merge has left the two registered unmerged paths. No git
commit, push, approval, authority or model action is performed by this script.
"""
import hashlib
import json
from pathlib import Path
import subprocess

EXPECTED = {
    (2, 'v13/code/scripts/handy_pflicht.py'): '76d77f590d396b191c51b00f3a38079bf0dea72c909b3b8e2bf8e62c95d3b6c7',
    (3, 'v13/code/scripts/handy_pflicht.py'): '5f6608fbef758cf4438e5307aee9f95413e334764f83250881263a3e7c0417c9',
    (2, 'v13/code/v13/operator.py'): 'da5d7a5e11489e6f53bc0d72ea2465e01d42d6989dbf0b78650ad3de2e616307',
    (3, 'v13/code/v13/operator.py'): '19697e2aaa99751e2082969205e874b69d583f4caab7972feacfd2547e070d2f',
}


def stage(which, path):
    raw = subprocess.run(['git', 'show', f':{which}:{path}'],
                         check=True, stdout=subprocess.PIPE).stdout
    expected = EXPECTED[(which, path)]
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError('Merge stage SHA256 mismatch: ' + path)
    return raw


def replace_once(text, before, after):
    if text.count(before) != 1:
        raise ValueError('Nonunique or absent AG5 operator anchor: ' + before[:100])
    return text.replace(before, after)


def resolve():
    handy = 'v13/code/scripts/handy_pflicht.py'
    op = 'v13/code/v13/operator.py'
    stage(2, handy)  # preserve and validate World V1, but AG5 V2 is stricter
    ag5_handy = stage(3, handy)
    world = stage(2, op).decode('utf-8')
    ag5 = stage(3, op).decode('utf-8')
    ag5 = replace_once(ag5, 'from .common import dumps,safe_text,file_hash',
                       'from .common import dumps,atomic_write,safe_text,file_hash')
    before = ':self / :world / :native / :knobs / :components / :objectives / :plasticity [component]'
    ag5 = replace_once(ag5, before, before +
        '\n:world shadow <checkpoint.npz> <sha256> <provenance.json> <observation.json> (nur lokales TTY, read-only SHADOW, keine Aktion/Lernfreigabe)')
    before = ':feedback route simple|detail|gist|both [--learn]'
    ag5 = replace_once(ag5, before, before +
        '\n:ersetze route <Route> <Wort>[,<Wort>] [--sofort] [--notiz Text] | :ersetze list | :ersetze undo <Id> (neuere Routen-Korrektur ersetzt ältere)')
    before = "        if cmd=='neuromod':"
    ag5 = replace_once(ag5, before,
        "        if cmd=='ersetze':  # WP-Z6c operator-scoped route correction replacement\n"
        "            from .route_supersede import operator_command\n"
        "            return operator_command(r,args)\n" + before)
    begin = "        if cmd=='world':"
    end = "        if cmd in {'components','objectives'}:"
    if world.count(begin) != 1 or world.count(end) != 1:
        raise ValueError('World source command anchor mismatch')
    world_handler = world[world.index(begin):world.index(end)].rstrip('\n')
    ag5 = replace_once(ag5, "        if cmd=='world':return dumps(r.world.world_state())", world_handler)
    ag5 = replace_once(ag5,
        ':effort [disabled|low|adaptive|high|max] (Reasoning-Effort/Body-Wake; ohne Wert: Status)',
        ':effort [disabled|low|adaptive|high|max|detail|gist] (Reasoning-Effort/Body-Wake; detail/gist = nur ein Körper; ohne Wert: Status)')
    ag5 = replace_once(ag5,
        "if len(args)!=1:raise ValueError(':effort [disabled|low|adaptive|high|max]')",
        "if len(args)!=1:raise ValueError(':effort [disabled|low|adaptive|high|max|detail|gist]')")
    Path(handy).write_bytes(ag5_handy)
    Path(op).write_bytes(ag5.encode('utf-8'))
    print(json.dumps({'schema': 'V13_REVIEW_MERGE_RESOLUTION_V1',
                      'operator_sha256': hashlib.sha256(ag5.encode()).hexdigest(),
                      'handy_sha256': hashlib.sha256(ag5_handy).hexdigest(),
                      'conflicts_resolved': [handy, op],
                      'source_parents_verified': True,
                      'production_merge': False}, sort_keys=True))


if __name__ == '__main__':
    resolve()
