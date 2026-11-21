"""Refine the already-composed exact-arithmetic path in a disposable V14 stage.

This does not add a second arithmetic engine. It adds date disambiguation,
German/English intent prefixes, a result receipt and a no-model world profile
to the existing pinned Runtime/C5/Broker arithmetic candidate.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

SOURCE_PINS = {
    "v13/arithmetic_reflex.py": "b721b769157b3df3936752419c5b93bed78bc347",
    "v13/runtime.py": "30360f40eb784be5ea975ee85e94a57f0b154164",
    "v13/world.py": "03c87501862eb773f80b3704f1e2b8f81b5cfc75",
}


def git_blob_sha1(raw: bytes) -> str:
    header = b"blob " + str(len(raw)).encode("ascii") + bytes([0])
    return hashlib.sha1(header + raw).hexdigest()


def _replace(raw: bytes, old: bytes, new: bytes, label: str) -> bytes:
    if raw.count(old) != 1:
        raise ValueError("arithmetic stage anchor changed: " + label)
    return raw.replace(old, new, 1)


def apply_staged_arithmetic(code_dir: Path, staged_root: Path) -> dict[str, bytes]:
    code_dir = Path(code_dir).resolve(strict=True)
    staged_root = Path(staged_root).resolve(strict=True)
    for relative, expected in SOURCE_PINS.items():
        source = code_dir / relative
        if source.is_symlink() or not source.is_file():
            raise ValueError("arithmetic source missing or unsafe: " + relative)
        if git_blob_sha1(source.read_bytes()) != expected:
            raise ValueError("arithmetic source changed; review a new overlay: " + relative)

    arithmetic_path = staged_root / "v13/arithmetic_reflex.py"
    runtime_path = staged_root / "v13/runtime.py"
    world_path = staged_root / "v13/world.py"
    for path in (arithmetic_path, runtime_path, world_path):
        if path.is_symlink() or not path.is_file():
            raise ValueError("staged arithmetic consumer missing or unsafe: " + str(path))

    arithmetic = arithmetic_path.read_bytes()
    runtime = runtime_path.read_bytes()
    world = world_path.read_bytes()

    # Require the upstream pinned candidate to have already composed the typed
    # LOCAL_EXACT_ARITHMETIC action; this overlay is not a replacement engine.
    if (b"LOCAL_EXACT_ARITHMETIC" not in runtime
            or b"arithmetic_answer=None if fixed_policy else exact_arithmetic(text)" not in runtime):
        raise ValueError("upstream exact-arithmetic Runtime candidate is not present")
    if b"LOCAL_EXACT_ARITHMETIC" not in runtime_path.read_bytes():
        raise ValueError("staged Runtime lost the typed arithmetic action")

    arithmetic = _replace(
        arithmetic,
        b'r"\\s*(?:(?:what\\s+is|what\'s|was\\s+ist|berechne|calculate)\\s+)?"',
        b'r"\\s*(?:(?:what\\s+is|what\'s|was\\s+ist|wie\\s+viel\\s+ist|wieviel\\s+ist|berechne|calculate|compute)\\s+)?"',
        "English/German arithmetic intent prefixes",
    )
    expression_anchor = (
        b'_EXPRESSION = re.compile(r"([+-]?\\d{1,8})\\s*([+\\-*/])\\s*([+-]?\\d{1,8})")\n'
    )
    date_shapes = (
        b'_DATE_SHAPE = re.compile(\n'
        b'    r"\\s*(?:\\d{4}\\s*[-/]\\s*\\d{1,2}|\\d{1,2}\\s*[-/]\\s*\\d{1,2})\\s*[?=]?\\s*",\n'
        b'    re.IGNORECASE,\n'
        b')\n'
        b'_EXPLICIT_MATH_CUE = re.compile(r"\\s*(?:calculate|compute|berechne)\\s+", re.IGNORECASE)\n'
    )
    if b"_DATE_SHAPE = re.compile(" in arithmetic:
        raise ValueError("date-shape guard already present")
    arithmetic = _replace(arithmetic, expression_anchor, expression_anchor + date_shapes,
                          "date-shape guard insertion")
    function_anchor = (
        b"    match = _PATTERN.fullmatch(text)\n"
        b"    if not match:\n"
        b"        return None\n"
        b"    expr = _EXPRESSION.fullmatch(match.group(1))\n"
    )
    guarded_function = (
        b"    match = _PATTERN.fullmatch(text)\n"
        b"    if not match:\n"
        b"        return None\n"
        b"    expression = match.group(1)\n"
        b"    if _DATE_SHAPE.fullmatch(expression) and not _EXPLICIT_MATH_CUE.match(text):\n"
        b"        return None\n"
        b"    expr = _EXPRESSION.fullmatch(expression)\n"
    )
    arithmetic = _replace(arithmetic, function_anchor, guarded_function, "date-shape guard consumer")

    runtime = _replace(
        runtime,
        b"meta['arithmetic_reflex']={'source_ref':e['source_ref'],'model_generated':False,'bounded':True}",
        b"meta['arithmetic_reflex']={'source_ref':e['source_ref'],'result':arithmetic_answer,'model_generated':False,'bounded':True}",
        "source-bound arithmetic result receipt",
    )
    world = _replace(
        world,
        b"data={'role':role,'model_revision':r.models.revision(role) if role!='SOURCE_COPY' else None,",
        b"data={'role':role,'model_revision':r.models.revision(role) if role not in {'SOURCE_COPY','LOCAL_EXACT_ARITHMETIC'} else None,",
        "non-model arithmetic world profile",
    )

    for name, raw in (("v13/arithmetic_reflex.py", arithmetic),
                      ("v13/runtime.py", runtime),
                      ("v13/world.py", world)):
        compile(raw, name, "exec")
    return {
        "v13/arithmetic_reflex.py": arithmetic,
        "v13/runtime.py": runtime,
        "v13/world.py": world,
    }
