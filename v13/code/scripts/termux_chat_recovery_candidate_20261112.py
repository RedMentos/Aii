"""Hash-bound plain-chat recovery candidate; frozen runtime files stay untouched.

The composition entry point preserves unrelated edits already made by the
integrated review builder. It only replaces unique, checked source anchors.
"""
import ast
import hashlib
from pathlib import Path


SOURCE_PINS = {
    "v13/ui.py": "ad1c495b1a09989ca307ae7b34f045abe60b390996787ee604e20273c975d4e8",
    "v13/operator.py": "67f2118efce0495ea144b11e8853cbf949d56e53e141fe7f801b31c56406f9a3",
}


def _replace(raw, old, new, label):
    if raw.count(old) != 1:
        raise ValueError("chat recovery anchor changed: " + label)
    return raw.replace(old, new, 1)


def apply_sources(sources):
    """Transform validated base/composed source bytes without discarding edits."""
    if any(name not in sources or not isinstance(sources[name], bytes)
           for name in SOURCE_PINS):
        raise ValueError("chat recovery requires UI and operator source bytes")
    ui = _replace(
        sources["v13/ui.py"],
        b"    op=Operator(r);done=threading.Event();seen={};held=[]\n",
        b"    op=Operator(r);done=threading.Event();held=[]\n"
        b"    # Existing answers belong to persisted history, not this process's output.\n"
        b"    seen={m['id']:len(m['text']) for m in r.store.history(r.session,8) if m['role']!='user'}\n",
        "plain initial history",
    )
    ui = _replace(
        ui,
        b"        print('V13 lokal \xc2\xb7 :help \xc2\xb7 Strg+C bricht ab \xc2\xb7 :shutdown beendet',flush=True)\n",
        b"        print('V13 lokal \xc2\xb7 :help \xc2\xb7 Strg+C bricht ab \xc2\xb7 :shutdown beendet',flush=True)\n"
        b"        if seen:print('Bisheriger Verlauf gespeichert; neue Ausgabe folgt.',flush=True)\n",
        "plain history notice",
    )
    operator = _replace(
        sources["v13/operator.py"],
        b"        if cmd=='status':return dumps(",
        b"        if cmd=='learning' and not args:\n"
        b"            return dumps({'learning_mode':r.cfg['learning_mode'],'read_only':True})\n"
        b"        if cmd=='status':return dumps(",
        "read-only learning status",
    )
    operator = _replace(
        operator,
        b":budget [Name Wert] / :learning record|shadow|commit / :learn ",
        b":budget [Name Wert] / :learning [record|shadow|commit] / :learn ",
        "learning help",
    )
    result = {"v13/ui.py": ui, "v13/operator.py": operator}
    for name, raw in result.items():
        ast.parse(raw, filename=name)
    return result


def build_sources(code_dir):
    """Validate exact frozen sources and return replacement bytes only."""
    code_dir = Path(code_dir)
    if (code_dir / "v13").is_symlink():
        raise ValueError("chat recovery source directory cannot be a symlink")
    originals = {}
    for name, pin in SOURCE_PINS.items():
        path = code_dir / name
        if path.is_symlink() or not path.is_file():
            raise ValueError("chat recovery source is unsafe: " + name)
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != pin:
            raise ValueError("chat recovery source hash mismatch: " + name)
        originals[name] = raw
    return apply_sources(originals)
