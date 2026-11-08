"""Build a hash-bound AG4 correction and optional shadow parity observer.

The returned source bytes are only for isolated copies. Registered runtime
sources and their cohorts are not modified by this builder.
"""
from hashlib import sha256
from pathlib import Path

from .ag4_outcome_crosspath_candidate import build_sources as build_ag4


OPERATOR_SHA256 = '29004759a8d6d017fb10aee32af92ad7a1163651a855ce0dce9a247f7bde49e2'
SHADOW_OLD = b"        c=[{'name':sk['name'],'route':_route_only(sk)} for sk in matches(hub(r).skills,text,LEARNING)][:4]\n"
SHADOW_NEW = b'''        c=[{'name':sk['name'],'route':_route_only(sk)} for sk in matches(hub(r).skills,text,LEARNING)][:4]
        try:
            from .skill_parity_shadow_candidate import annotate_candidates
            c=annotate_candidates(r.store,c)
        except Exception as exc:
            try:r.store.log('skill_parity_shadow_unavailable',e['event_id'],{'stage':'predict','error':type(exc).__name__})
            except Exception:pass
'''
RECORD_OLD = b'''        for c in meta.get('skill_shadow') or []:
            out.setdefault('parity',[]).append([c['name'],lib.record(c['name'],True,parity=float(c['route']==route))])
'''
RECORD_NEW = b'''        if meta.get('skill_shadow'):
            try:
                from .skill_parity_shadow_candidate import observe_final
                out['parity_shadow']=observe_final(r.store,e['event_id'],route)
            except Exception as exc:
                try:r.store.log('skill_parity_shadow_unavailable',e['event_id'],{'stage':'observe','error':type(exc).__name__})
                except Exception:pass
'''
HELP_OLD = b':skilllive [status] (Skills im Turn: automatischer Pfad, Parit\xc3\xa4t, Gewohnheiten)'
HELP_NEW = b':skilllive [status|parity-shadow on|off|status] (Skills und separate Routenbeobachtung)'
OPERATOR_OLD = b'''        if cmd=='skilllive':
            from . import skilllive
            if not args or args==['status']:return dumps(skilllive.report(r))
            raise ValueError(':skilllive [status]')
'''
OPERATOR_NEW = b'''        if cmd=='skilllive':
            from . import skilllive
            if not args or args==['status']:return dumps(skilllive.report(r))
            if args and args[0]=='parity-shadow':
                from . import skill_parity_shadow_candidate as parity_shadow
                if args==['parity-shadow'] or args==['parity-shadow','status']:
                    return dumps({'capture_enabled':parity_shadow.capture_enabled(r.store),
                                  'view':parity_shadow.view(r.store,r.session)})
                if args in (['parity-shadow','on'],['parity-shadow','off']):
                    enabled=parity_shadow.set_capture_enabled(r.store,args[1]=='on','EXPLICIT_HUMAN')
                    return dumps({'capture_enabled':enabled,'mode':'SHADOW','learning_authority':0})
            raise ValueError(':skilllive [status|parity-shadow on|off|status]')
'''


def build_sources(source_dir):
    source_dir = Path(source_dir)
    data = build_ag4(source_dir)
    operator = (source_dir / 'operator.py').read_bytes()
    if sha256(operator).hexdigest() != OPERATOR_SHA256:
        raise ValueError('unsupported source: operator.py')
    for name, old, new in (('skilllive.py', SHADOW_OLD, SHADOW_NEW),
                           ('skilllive.py', RECORD_OLD, RECORD_NEW),
                           ('operator.py', HELP_OLD, HELP_NEW),
                           ('operator.py', OPERATOR_OLD, OPERATOR_NEW)):
        source = operator if name == 'operator.py' and 'operator.py' not in data else data[name]
        if source.count(old) != 1:
            raise ValueError('ambiguous parity integration anchor: ' + name)
        data[name] = source.replace(old, new, 1)
    return data
