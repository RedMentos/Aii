"""WP-N12 gate dependency graph (IH-H28) with the §100 / IH-H33 definition of done.

Each gate lists evidence per criterion (code, real_data, persistence, test, telemetry, ablation,
limitations) in specs/gate-graph.json. Evidence is checked, not trusted: files must exist, real data must
come from a real run (bench-results/ or docs/proofs/, never tests/), telemetry kinds must be logged by code.
A gate is GREEN only with all required criteria, passing result verdicts and all dependencies GREEN.
"""
import json
import re
from .common import APP

REAL_DATA_PREFIXES=('../bench-results/','bench-results/','docs/proofs/','docs/canon/')

def spec():return json.loads((APP/'specs/gate-graph.json').read_text())

def _code_logs():
    text=''.join(p.read_text(encoding='utf-8') for p in sorted((APP/'v13').rglob('*.py')))
    return set(re.findall(r"\.log\(\s*['\"]([a-z_]+)['\"]",text))

def check(gate,logged=None):
    logged=_code_logs() if logged is None else logged;out={}
    for crit in spec()['criteria']:
        ev=gate.get(crit)
        if ev is None:out[crit]={'required':False,'present':True,'missing':[]};continue
        if crit=='telemetry':missing=[k for k in ev if k not in logged]
        else:
            missing=[p for p in ev if not (APP/p).exists()]
            if crit=='real_data':missing+=[p for p in ev if not p.startswith(REAL_DATA_PREFIXES)]
        out[crit]={'required':True,'present':bool(ev) and not missing,'missing':missing if ev else ['NO_EVIDENCE']}
    return out

def verdicts(gate):
    """Result-file checks: [{file, path a.b.c, op, value}] -> list of failures (empty = passing)."""
    fails=[]
    for v in gate.get('verdict') or []:
        try:
            cur=json.loads((APP/v['file']).read_text())
            for part in v['path'].split('.'):cur=cur[part]
            expected=v['value'];op=v['op']
            if op=='==':
                # Python's 1 == True must never satisfy a Boolean proof gate.
                if isinstance(expected,bool) or isinstance(cur,bool):
                    ok=type(cur) is type(expected) and cur==expected
                else:ok=cur==expected
            elif op in ('>=','<='):
                if isinstance(cur,bool) or isinstance(expected,bool):ok=False
                else:ok=cur>=expected if op=='>=' else cur<=expected
            else:raise ValueError('Unbekannter Gate-Vergleich')
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
