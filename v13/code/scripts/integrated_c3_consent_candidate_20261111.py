"""Close C3 direct/SDFT consent admission in the single staged Runtime."""
import hashlib
import importlib.util
from pathlib import Path

BASE_SHA = '41e08c932535bb450c0f031a2fdea5511f588d1d2be8abdcccd9c65044d6eef0'
CONSENT_SHA = 'ac4d5f592442165ce8e94535e232e445341c0f6a9b7af320cd0ff54e715588e6'


def build_sources(code_dir):
    code_dir = Path(code_dir)
    path = code_dir / 'scripts/integrated_body_role_candidate_20261111.py'
    helper = (code_dir / 'v13/c3_consent_admission_candidate.py').read_bytes()
    if hashlib.sha256(path.read_bytes()).hexdigest() != BASE_SHA or hashlib.sha256(helper).hexdigest() != CONSENT_SHA:
        raise ValueError('C3 consent composition source changed')
    spec = importlib.util.spec_from_file_location('verified_body_composition', path)
    parent = importlib.util.module_from_spec(spec);spec.loader.exec_module(parent)
    result = parent.build_sources(code_dir)
    data = result['v13/agi/weights.py']
    def change(old, new):
        nonlocal data
        if data.count(old) != 1:
            raise ValueError('unexpected C3 consent source')
        data = data.replace(old, new, 1)
    change(b'from .. import body_jepa_runtime_candidate as body_route\n',
           b'from .. import body_jepa_runtime_candidate as body_route\nfrom .. import c3_consent_admission_candidate as c3_consent\n')
    start = data.index(b'    def candidates(self,')
    end = data.index(b'    def rated_candidates(self,', start)
    data = data[:start] + b'    def candidates(self,require_replay_pass=True,cap=True):\n        if self.role in body_route.ROLES:return body_route.candidates(self,require_replay_pass)\n        return c3_consent.candidates(self,require_replay_pass,cap)\n' + data[end:]
    start = data.index(b'    def sdft_candidates(self):\n')
    end = data.index(b'    def stage(self,', start)
    data = data[:start] + b'    def sdft_candidates(self):\n        return c3_consent.sdft_candidates(self)\n' + data[end:]
    change(b'        self.s.read_source(ref)\n        if self.role in body_route.ROLES',
           b"        self.s.read_source(ref)\n        if self.role=='C3_LANGUAGE':c3_consent.check(self,item)\n        if self.role in body_route.ROLES")
    change(b"            out=self.trainer.fit(todo,b['base_generation'],cancel,deadline) or {}\n",
           b"            checked_cancel=c3_consent.training_cancel(self,b['items'],cancel) if self.role=='C3_LANGUAGE' else cancel\n            if checked_cancel is not None and (checked_cancel() if callable(checked_cancel) else checked_cancel.is_set()):\n                from ..common import Cancelled\n                raise Cancelled('Training cancelled before model load')\n            out=self.trainer.fit(todo,b['base_generation'],checked_cancel,deadline) or {}\n            if self.role=='C3_LANGUAGE' and checked_cancel():\n                from ..common import Cancelled\n                raise Cancelled('Training cancelled before publication')\n")
    result.update({'v13/agi/weights.py': data, 'v13/c3_consent_admission_candidate.py': helper})
    return result
