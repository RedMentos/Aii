"""Loads the frozen WP-UR8 (LLM second reader) code from code_snapshot/ so the evidence stays reproducible after the runtime
moved on (the parallel WP-UR8 with the learned second opinion, PR #416, became the runtime v8). Hashes: freeze_v8.json."""
import hashlib,json,types
from pathlib import Path
HERE=Path(__file__).resolve().parent;SNAP=HERE/'code_snapshot'


def check():
    for f,h in json.loads((HERE/'freeze_v8.json').read_text())['files'].items():
        if hashlib.sha256((SNAP/Path(f).name).read_bytes()).hexdigest()!=h:raise SystemExit('changed after freeze: '+f)


def _mod(path,name,src):
    m=types.ModuleType(name);m.__file__=str(path);exec(compile(src,str(path),'exec'),m.__dict__);return m


def load():
    check()
    U=_mod(SNAP/'userrules.py','userrules_v8llm',(SNAP/'userrules.py').read_text().replace('from .agi.base import StateBox','StateBox=None'))
    S=_mod(SNAP/'userrules_second.py','userrules_second_v8llm',(SNAP/'userrules_second.py').read_text().replace('from . import userrules as U','U=None'))
    S.U=U
    return U,S
