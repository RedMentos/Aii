"""Compose #1629 and #1631 in a source-checked disposable copy only."""
import hashlib
import importlib.util
from pathlib import Path

from .ag4_fact_precedence_integration_candidate import build_sources as build_ag4
from v13.world_semantic_evidence_candidate import verify_sources


ONLINE_BUILDER_SHA='3bd21ea08b14b33b1069577cc078a7120c5d0066fbe3fd03652451d315b542c7'
BASE_SHA={
    'v13/runtime.py':'8a403bffd1c2b14d9caa798cf17ea3c299cea5796115bad40cbaf9a2054072ed',
    'v13/agi/__init__.py':'686183d3458989bd7b91e8da005ca5cb0163d8f1dbad56f355ec47e71a679f82',
}
ONLINE_HELP=b':growth onlineworld [status|on|off|run [LIMIT]] (lokales Weltmodell; Lernen nur im freigegebenen Lernmodus)\n'
HELP_ANCHOR=b':neuromod [status|path <Name>|sleep|clear-veto <Name>]'


def build_sources(base_code,online_code):
    """Return exact overlay bytes. Both source checkouts are read-only."""
    base_code=Path(base_code);online_code=Path(online_code)
    verify_sources(base_code/'v13')
    for name,expected in BASE_SHA.items():
        if hashlib.sha256((base_code/name).read_bytes()).hexdigest()!=expected:
            raise ValueError('unsupported composition source: '+name)
    builder=online_code/'scripts/online_world_integration_candidate.py'
    if hashlib.sha256(builder.read_bytes()).hexdigest()!=ONLINE_BUILDER_SHA:
        raise ValueError('unsupported online candidate builder')
    spec=importlib.util.spec_from_file_location('_v13_online_review_builder',builder)
    if spec is None or spec.loader is None:raise ValueError('online builder unavailable')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    online=module.build_sources(online_code)
    # AG4 and online candidates both amend the operator help. Preserve AG4's
    # independently built command handlers and insert only the online help.
    ag4={'v13/'+name:data for name,data in build_ag4(base_code/'v13').items()}
    operator=ag4['v13/operator.py']
    if (operator.count(HELP_ANCHOR)!=1 or ONLINE_HELP in operator
            or online['v13/operator.py'].count(ONLINE_HELP)!=1):
        raise ValueError('ambiguous operator composition')
    ag4['v13/operator.py']=operator.replace(HELP_ANCHOR,ONLINE_HELP+HELP_ANCHOR,1)
    for name,data in online.items():
        if name!='v13/operator.py':
            if name in ag4:raise ValueError('overlapping candidate output: '+name)
            ag4[name]=data
    return ag4
