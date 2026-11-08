"""Build an isolated, source-bound Runtime integration for the shadow slice.

The original files and frozen SourceHandoff sources are never written here.
The caller may materialize the returned bytes in a separate review copy only.
"""
from hashlib import sha256
from pathlib import Path


BASE_SHA256 = {
    'memory.py': '391668fff0b4ad3d7c36d5d7a9823055ff74821c10f71b945e87edaa62597484',
    'episodes.py': '0e3bdee29ef2e5572c6a60d5a2fe9c6252f1dc04df908609580999a2987126c1',
    'runtime.py': '8a403bffd1c2b14d9caa798cf17ea3c299cea5796115bad40cbaf9a2054072ed',
    'sleep.py': '8c964b77ba436236430e4812e8304b062b4f4059caf2c52035860edb4bed1eee',
    'store.py': 'fe66f92533b20738b5ec384e9d7c0b5ac8b4b4f658c6c1ad23792d813ff29980',
}

_MEMORY_OLD = b"        self.s.log('feedback',event_id,{'memory_id':mid,'kind':kind,'permission':permission});return mid\n"
_MEMORY_NEW = b'''        try:
            from .correction_association_shadow_candidate import record_correction
            record_correction(self.s,self.cfg,event_id,mid,e['session_id'])
        except Exception as exc:self.s.log('correction_association_unavailable',event_id,{'error':type(exc).__name__})
        self.s.log('feedback',event_id,{'memory_id':mid,'kind':kind,'permission':permission});return mid
'''

_RECALL_OLD = b'''    if added:meta['associative_memory_ids']=added
    return merged
'''
_RECALL_NEW = b'''    if added:meta['associative_memory_ids']=added
    try:
        from .correction_association_shadow_candidate import candidates
        shadow=candidates(runtime.store,runtime.cfg,runtime.session,merged)
        if shadow:meta['correction_association_shadow']=shadow
    except Exception as exc:runtime.store.log('correction_association_unavailable',None,{'error':type(exc).__name__})
    return merged
'''

_OPERATOR_OLD = b"    raise ValueError(':episodes [status|list|cut|graph <id>|relation <a> <b>|forgetting|spread [off|shadow|on]|route [off|shadow|active]]')\n"
_OPERATOR_NEW = b'''    if args[0]=='correction-association':
        from .correction_association_shadow_candidate import set_mode,rollback
        if len(args)==2:return {'correction_association':set_mode(r.store,args[1])}
        if len(args)==3 and args[1]=='rollback':return rollback(r.store,args[2])
    raise ValueError(':episodes [status|list|cut|graph <id>|relation <a> <b>|forgetting|spread [off|shadow|on]|route [off|shadow|active]|correction-association off|shadow|rollback <id>]')
'''


def build_sources(source_dir):
    source_dir = Path(source_dir)
    data = {}
    for name, expected in BASE_SHA256.items():
        content = (source_dir / name).read_bytes()
        if sha256(content).hexdigest() != expected:
            raise ValueError('unsupported source: ' + name)
        data[name] = content
    for name, old, new in (('memory.py', _MEMORY_OLD, _MEMORY_NEW),
                           ('episodes.py', _RECALL_OLD, _RECALL_NEW),
                           ('episodes.py', _OPERATOR_OLD, _OPERATOR_NEW)):
        if data[name].count(old) != 1:
            raise ValueError('ambiguous integration anchor: ' + name)
        data[name] = data[name].replace(old, new, 1)
    return {name: data[name] for name in ('memory.py', 'episodes.py')}
