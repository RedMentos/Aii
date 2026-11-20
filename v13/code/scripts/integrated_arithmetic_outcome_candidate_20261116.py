"""Complete deterministic World receipts and source-only diagnostic authority.

Apply after the arithmetic layer in the disposable review tree. Model World
training roles/checkpoints and all permission gates retain their existing scope.
"""
import hashlib
from pathlib import Path


SOURCE_PINS = {
    'v13/world.py': 'bb221176167cb1f83285127cba2b2e059ebf9b0cec79b9405b3b5f23cef0343e',
    'v13/broker.py': '3be190e0f2314ab360915996d1bd3e9f6a6ef69e7134c2ef86dccc01b4bc5562',
    'v13/world_semantic_evidence_candidate.py': '354306bb763fda116728bd13e8502d81ed8e6a790c4387d98e0920960a87b8a5',
    'v13/local_error_route_shadow_candidate.py': '87bb77ed43b739fb890308fa565d0ca4a84278992a2312e219122c358f2c5187',
}
UPSTREAM_PINS = {
    'v13/world.py': SOURCE_PINS['v13/world.py'],
    'v13/broker.py': 'd035f8bcdcc7acade340a2db893c32a93a892598f2be6e280ccdae3f6fe6899d',
    'v13/world_semantic_evidence_candidate.py': '0711ed851c5126c3b1c414725b99b509ff53a6e821cf5a021cbc443e93ea3b5e',
    'v13/local_error_route_shadow_candidate.py': '3106cb3eb0808c16a7d91c1199eff5eb6b310cab9f1f67c06097026e7b621893',
}
REVIEWED_WORLD_SHA = 'bcb96249eb1e7cb914ea82949d106118f4738c2605e02b2c360d4b4f2d276e27'


def _replace(raw, old, new, label):
    old, new = old.encode(), new.encode()
    if raw.count(old) != 1:
        raise ValueError('arithmetic outcome anchor mismatch: ' + label)
    return raw.replace(old, new, 1)


def apply_sources(code_dir, sources):
    code_dir = Path(code_dir)
    original = {}
    for name, expected in SOURCE_PINS.items():
        path = code_dir / name
        raw = path.read_bytes()
        if path.is_symlink() or hashlib.sha256(raw).hexdigest() != expected:
            raise ValueError('arithmetic outcome frozen source changed: ' + name)
        original[name] = raw
    result = dict(sources)
    for name, expected in UPSTREAM_PINS.items():
        raw = result.get(name, original[name])
        if hashlib.sha256(raw).hexdigest() != expected:
            raise ValueError('arithmetic outcome upstream changed: ' + name)
        result[name] = raw

    world = _replace(result['v13/world.py'],
        "        r=self.r\n        data={'role':role,'model_revision':r.models.revision(role) if role!='SOURCE_COPY' else None,\n",
        "        r=self.r\n"
        "        if role not in {'SOURCE_COPY','LOCAL_EXACT_ARITHMETIC','C3_LANGUAGE','B1_DETAIL','B2_GIST'}:\n"
        "            raise ValueError('Unknown World action role')\n"
        "        data={'role':role,'model_revision':None if role in {'SOURCE_COPY','LOCAL_EXACT_ARITHMETIC'} else r.models.revision(role),\n",
        'deterministic World profile')
    world = _replace(world,
        "        if role not in ('SOURCE_COPY','C3_LANGUAGE','B1_DETAIL','B2_GIST') or forecast.get('profile',{}).get('role')!=role:raise ValueError('World measured action role mismatch')\n"
        "        if role!='SOURCE_COPY' and forecast['profile'].get('model_revision')!=self.r.models.revision(role):raise Unavailable('World action model changed')\n",
        "        if role not in ('SOURCE_COPY','LOCAL_EXACT_ARITHMETIC','C3_LANGUAGE','B1_DETAIL','B2_GIST') or forecast.get('profile',{}).get('role')!=role:raise ValueError('World measured action role mismatch')\n"
        "        if role=='LOCAL_EXACT_ARITHMETIC':\n"
        "            from .arithmetic_reflex import exact_arithmetic\n"
        "            if (forecast['profile'].get('model_revision') is not None or actual.get('model_generated') is not False\n"
        "                    or exact_arithmetic(self.s.read_source(env['source_ref']))!=own['text']):\n"
        "                raise ValueError('World arithmetic outcome/source mismatch')\n"
        "        elif role!='SOURCE_COPY' and forecast['profile'].get('model_revision')!=self.r.models.revision(role):raise Unavailable('World action model changed')\n",
        'source-bound deterministic transition')
    result['v13/world.py'] = world
    new_world_sha = hashlib.sha256(world).hexdigest()
    if new_world_sha != REVIEWED_WORLD_SHA:
        raise ValueError('arithmetic outcome World output changed; review semantic binding')
    semantic_name = 'v13/world_semantic_evidence_candidate.py'
    result[semantic_name] = _replace(result[semantic_name],
        SOURCE_PINS['v13/world.py'], new_world_sha, 'semantic World source pin')
    result['v13/local_error_route_shadow_candidate.py'] = _replace(
        result['v13/local_error_route_shadow_candidate.py'],
        UPSTREAM_PINS[semantic_name], hashlib.sha256(result[semantic_name]).hexdigest(),
        'local error semantic source pin')

    # A diagnostic was produced instead of the requested answer. Stale fixed,
    # exact-copy or arithmetic route flags cannot claim authority for it.
    result['v13/broker.py'] = _replace(result['v13/broker.py'],
        "        if meta.get('output_authority')=='SOURCE_SYSTEM_REPORT':cands.append('SOURCE_SYSTEM_REPORT')\n",
        "        if meta.get('output_authority')=='SOURCE_SYSTEM_REPORT':cands=['SOURCE_SYSTEM_REPORT']\n",
        'diagnostic owns its actual output')
    for name in UPSTREAM_PINS:
        compile(result[name], name, 'exec')
    return result
