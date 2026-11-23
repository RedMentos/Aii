"""Isolated candidate (not live): B2 offer without body_state + quote cap of one rule sentence.

Patch: docs/proofs/continuation-20261013/b2-offer-candidate/cognition.patch against live v13/cognition.py.
It adds two cfg switches, both off by default so the patched file behaves exactly like live unless enabled:
  b2_offer_body_state=False   B2 offers leave out the WP-T5 body_state view (hijacked 41/50 B2 offers in STEP2)
  offer_quote_min_chars=N     quotes may hold N chars; the room comes from the summary (same worst-case budget)
Basis: docs/proofs/continuation-20261012/step2-body-state-ablation/BEFUND.md.

Live integration belongs to the owner of the live chain (scripts/integrated_candidates.py covers runners/
memory_server/runtime/store, source_handoff_candidate binds cognition.py exactly); hand over this patch, do not
write live from here. `install()` loads the patched source as `v13.cognition` in this process only.
"""
import hashlib
import subprocess
import sys
import tempfile
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATCH = ROOT/'docs/proofs/continuation-20261013/b2-offer-candidate/cognition.patch'
ENABLE = {'b2_offer_body_state': False, 'offer_quote_min_chars': 90}


def candidate_source(root=ROOT):
    live = (root/'v13/cognition.py').read_text()
    if 'def offer_schema(tokens,quote_min_chars=0):' in live:
        # Integrated 2026-10-13 by thread G (scripts/integrated_candidates.b2_offer, switches off by default):
        # live already is the candidate, so the archived patch no longer applies and is not needed.
        return live, live
    with tempfile.TemporaryDirectory() as d:
        src = Path(d)/'cognition.py'; src.write_text(live); out = Path(d)/'out.py'
        r = subprocess.run(['patch', '-s', '-o', str(out), str(src), str(PATCH)], capture_output=True, text=True)
        if r.returncode: raise ValueError('Candidate patch does not apply to live cognition.py: '+r.stdout+r.stderr)
        return live, out.read_text()


def install(root=ROOT):
    """Register the patched cognition module before v13.runtime imports it. Returns a binding record."""
    if 'v13.cognition' in sys.modules: raise RuntimeError('v13.cognition already imported; install() must run first')
    import v13
    live, text = candidate_source(root)
    module = types.ModuleType('v13.cognition'); module.__package__ = 'v13'; module.__file__ = str(root/'v13/cognition.py')
    sys.modules['v13.cognition'] = module
    exec(compile(text, str(root/'v13/cognition.py'), 'exec'), module.__dict__)
    v13.cognition = module
    sha = lambda s: hashlib.sha256(s.encode()).hexdigest()
    return {'live_cognition_sha256': sha(live), 'candidate_cognition_sha256': sha(text),
            'patch_sha256': hashlib.sha256(PATCH.read_bytes()).hexdigest(), 'enable': ENABLE}
