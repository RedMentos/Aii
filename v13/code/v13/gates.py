"""WP-N12 gate dependency graph (IH-H28) with the §100 / IH-H33 definition of done.

Each gate lists evidence per criterion (code, real_data, persistence, test, telemetry, ablation,
limitations) in specs/gate-graph.json. Evidence is checked, not trusted: files must exist, real data must
come from a real run (bench-results/ or docs/proofs/, never tests/), telemetry kinds must be logged by code.
A gate is GREEN only with all required criteria, passing result verdicts and all dependencies GREEN.
"""
import json
import math
import re
from pathlib import PurePosixPath
from .common import APP

REAL_DATA_PREFIXES=('../bench-results/','docs/proofs/','docs/canon/')

def spec():return json.loads((APP/'specs/gate-graph.json').read_text())

def _code_logs():
    text=''.join(p.read_text(encoding='utf-8') for p in sorted((APP/'v13').rglob('*.py')))
    return set(re.findall(r"\.log\(\s*['\"]([a-z_]+)['\"]",text))

def _real_data_file(name):
    """A real-data *path* must name a regular file inside a registered evidence root.

    This is path integrity, not a native-run or provenance attestation.  Keep the
    historically registered ../bench-results paths while rejecting traversal,
    directory placeholders and symlink aliases into source/tests.
    """
    if not isinstance(name, str) or not name or "\x00" in name:
        return False
    path = PurePosixPath(name)
    parts = path.parts
    if path.is_absolute() or len(parts) < 3:
        return False
    if parts[:2] == ('..', 'bench-results'):
        root = APP.parent / 'bench-results'
    elif parts[:2] in (('docs', 'proofs'), ('docs', 'canon')):
        root = APP / parts[0] / parts[1]
    else:
        return False
    if any(part in ('.', '..') for part in parts[2:]):
        return False
    try:
        if root.is_symlink() or (parts[0] == 'docs' and (APP / 'docs').is_symlink()) or not root.is_dir():
            return False
        candidate = root
        for part in parts[2:]:
            candidate = candidate / part
            if candidate.is_symlink():
                return False
        return candidate.is_file() and candidate.resolve(strict=True).is_relative_to(root.resolve(strict=True))
    except (OSError, RuntimeError, ValueError):
        return False


def check(gate,logged=None):
    logged=_code_logs() if logged is None else logged;out={}
    for crit in spec()['criteria']:
        ev=gate.get(crit)
        if ev is None:out[crit]={'required':False,'present':True,'missing':[]};continue
        if crit=='telemetry':missing=[k for k in ev if k not in logged]
        elif crit=='real_data':missing=[p for p in ev if not _real_data_file(p)]
        else:missing=[p for p in ev if not (APP/p).exists()]
        out[crit]={'required':True,'present':bool(ev) and not missing,'missing':missing if ev else ['NO_EVIDENCE']}
    return out

def _verdict_compare(actual, op, expected):
    """Fail closed on JSON type coercion, bool-as-number, and nonfinite values."""
    for value in (actual, expected):
        if type(value) is float and not math.isfinite(value):
            return False
    if op == '==':
        return type(actual) is type(expected) and actual == expected
    if op in ('>=', '<='):
        if type(actual) not in (int, float) or type(expected) not in (int, float):
            return False
        return actual >= expected if op == '>=' else actual <= expected
    return False


def verdicts(gate):
    """Result-file checks: [{file, path a.b.c, op, value}] -> list of failures (empty = passing)."""
    fails=[]
    for v in gate.get('verdict') or []:
        try:
            cur=json.loads((APP/v['file']).read_text())
            for part in v['path'].split('.'):cur=cur[part]
            ok=_verdict_compare(cur,v['op'],v['value'])
        except Exception as exc:ok=False;cur=type(exc).__name__
        if not ok:fails.append({'file':v['file'],'path':v['path'],'expected':f"{v['op']} {v['value']}",'actual':cur})
    return fails

def evaluate():
    gates=spec()['gates'];logged=_code_logs();own={g:check(v,logged) for g,v in gates.items()};status={}
    def resolve(g,stack=()):
        if g in status:return status[g]
        if g in stack:raise ValueError('Zyklus im Gate-Graph: '+' -> '.join(stack+(g,)))
        deps=[resolve(d,stack+(g,)) for d in gates[g]['deps']]
        complete=all(c['present'] for c in own[g].values());failing=verdicts(gates[g])
        if complete and failing:s='EVIDENCE_NOT_PASSING'
        elif complete and all(d=='GREEN' for d in deps):s='GREEN'
        elif complete:s='BLOCKED_BY_DEP'
        elif own[g]['code']['present'] and own[g]['test']['present']:s='PARTIAL'
        else:s='OPEN'
        status[g]=s;return s
    for g in gates:resolve(g)
    return {g:{'title':gates[g]['title'],'status':status[g],'deps':gates[g]['deps'],
               'missing':{c:v['missing'] for c,v in own[g].items() if v['required'] and not v['present']},'verdict_failures':verdicts(gates[g])} for g in gates}

def summary():
    ev=evaluate();count={}
    for v in ev.values():count[v['status']]=count.get(v['status'],0)+1
    return {'counts':count,'gates':{g:v['status'] for g,v in ev.items()},'definition':'GREEN = code+real data+persistence+test+telemetry+ablation+limitations and all deps GREEN'}

def operator_command(r,args):
    if not args or args==['summary']:return summary()
    if args==['all']:return evaluate()
    if len(args)==1:
        ev=evaluate()
        if args[0] not in ev:raise ValueError('Gate unbekannt')
        return ev[args[0]]
    raise ValueError(':gates [summary|all|<Gate>]')
