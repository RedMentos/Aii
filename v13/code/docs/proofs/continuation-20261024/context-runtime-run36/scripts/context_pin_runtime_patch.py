"""V13 WP-N7 isolated, source-bound candidate builder for ContextOS fail-closed pinning.

Does not edit production: writes two full candidate copies to a NEW output dir
only when exact frozen original Git blob identities match. No Age or mode change.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path

CONTEXT_BLOB = '028376012e328624fb527a927bb0e2a1071a86a0'
RUNTIME_BLOB = 'a691d27bd0772a4fa1f03d57ec90663237bf6825'


def git_blob(raw):
    return hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()


def once(source, before, after, label):
    if source.count(before) != 1:
        raise ValueError(f'{label}: expected exactly one source anchor, got {source.count(before)}')
    return source.replace(before, after, 1)


def patch_context(source):
    source = once(source,
        "VOLATILE_HEAD='Context for the next message (reference material, not a question):'\n",
        "VOLATILE_HEAD='Context for the next message (reference material, not a question):'\n"
        "\nclass ContextBudgetExceeded(ValueError):\n"
        "    \"\"\"ACTIVE ContextOS cannot fit immutable sources without violating pins.\"\"\"\n"
        "\n", 'exception')
    source = once(source,
        "if s[2]!='RAW' or s[4]:return False",
        "if s[2]!='RAW' or s[3] or s[4]:return False", 'compression-pin')
    source = once(source,
        """        # budget pressure: compress, then point, unpinned first; the newest turn is never dropped by policy
        for group in (unpinned,[s for s in state[:-1] if s[3]]):
            for s in group:
                if size()<=budget:break
                if try_compress(s):decisions.append('compress_budget')
            for s in group:
                if size()<=budget:break
                if not s[4]:s[2]='POINTER';decisions.append('pointer_budget')
""",
        """        # Budget pressure may change ONLY unpinned, non-restored turns.
        for s in unpinned:
            if size()<=budget:break
            if try_compress(s):decisions.append('compress_budget')
        for s in unpinned:
            if size()<=budget:break
            if not s[4] and s[2]!='POINTER':s[2]='POINTER';decisions.append('pointer_budget')
        if size()>budget:decisions.append('no_plan_pinned_budget')
""", 'budget-loop')
    source = once(source,
        "        applied=st['mode']=='ACTIVE'\n        fp_legacy,fp_planned=fingerprint(legacy),fingerprint(planned)",
        """        # Compare ACTUAL planned message chars, including volatile headers/layout.
        # SHADOW can log a counterfactual overflow; ACTIVE must not execute it.
        planned_chars=sum(len(m['content']) for m in planned)
        if planned_chars>budget:
            decisions.append('no_plan_budget_overflow')
            if st['mode']=='ACTIVE':
                raise ContextBudgetExceeded('ContextOS ACTIVE immutable context exceeds budget')
        applied=st['mode']=='ACTIVE'
        fp_legacy,fp_planned=fingerprint(legacy),fingerprint(planned)""", 'active-overflow')
    ast.parse(source)
    return source


def patch_runtime(source):
    source = once(source,
        "                except Exception as exc:self.store.log('context_os_unavailable',eid,{'stage':'plan','error':type(exc).__name__})",
        """                except Exception as exc:
                    self.store.log('context_os_unavailable',eid,{'stage':'plan','error':type(exc).__name__})
                    # Never silently fall back to unplanned legacy messages
                    # when the user explicitly enabled ContextOS ACTIVE.
                    # If state cannot be read, fail closed as well.
                    if ctxos.controller(self)._load()[0].get('mode') != 'SHADOW':
                        raise""", 'runtime-active-fallback')
    ast.parse(source)
    return source


def build(context_path, runtime_path, output):
    src_paths=(Path(context_path),Path(runtime_path));expected=(CONTEXT_BLOB,RUNTIME_BLOB)
    for path in src_paths:
        if not path.is_file() or path.is_symlink():raise ValueError('regular source file required')
    raw=[p.read_bytes() for p in src_paths]
    for b,want in zip(raw,expected):
        if git_blob(b)!=want:raise ValueError('frozen source Git blob mismatch')
    if output.exists() or output.is_symlink():raise FileExistsError('output must be a new directory')
    patched=[patch_context(raw[0].decode('utf-8')),patch_runtime(raw[1].decode('utf-8'))]
    output.mkdir(parents=True,exist_ok=False)
    for name,content in zip(('context_os.py','runtime.py'),patched):
        (output/name).write_text(content,encoding='utf-8')
    manifest={'schema':'V13_CONTEXT_PIN_CANDIDATE_V1','production_integrated':False,
              'source_git_blobs':dict(zip(('context_os.py','runtime.py'),expected)),
              'candidate_sha256':{name:hashlib.sha256(content.encode()).hexdigest()
                                  for name,content in zip(('context_os.py','runtime.py'),patched)},
              'authority':'OFF_REVIEW_ONLY','canonical_gate_pass':False}
    (output/'MANIFEST.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    return manifest


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--context',required=True);ap.add_argument('--runtime',required=True)
    ap.add_argument('--output',required=True)
    args=ap.parse_args()
    print(json.dumps(build(args.context,args.runtime,Path(args.output)),indent=2))
