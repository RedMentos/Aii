"""Wire role-owned Body training into the current single staged Runtime."""
import hashlib
import importlib.util
from pathlib import Path
import re

BASE_SHA = '82e2fd27712d17a489ce5fd2f75d749f3f0e08dcc9d7fcc8852bbe6f738e8e18'
BODY_SHA = '804aafadfc043d86f1f8e9b2a2262a18674fbf2c3e3b70a80d672aa259e3a0bf'


def replace(raw, old, new, label):
    if raw.count(old) != 1:
        raise ValueError('unexpected Body integration source: ' + label)
    return raw.replace(old, new, 1)


def build_sources(code_dir):
    code_dir = Path(code_dir)
    path = code_dir / 'scripts/integrated_world_training_resume_candidate_20261111.py'
    body = (code_dir / 'v13/body_jepa_runtime_candidate.py').read_bytes()
    if hashlib.sha256(path.read_bytes()).hexdigest() != BASE_SHA or hashlib.sha256(body).hexdigest() != BODY_SHA:
        raise ValueError('Body role composition source changed')
    spec = importlib.util.spec_from_file_location('verified_training_composition', path)
    parent = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(parent)
    result = parent.build_sources(code_dir)
    trainers = result.get('v13/agi/trainers.py', (code_dir / 'v13/agi/trainers.py').read_bytes())
    trainers = replace(trainers, b'import json\n', b'import json\nfrom .. import body_jepa_runtime_candidate as body_route\n', 'trainer import')
    trainers = replace(trainers, b'    from .weights import NullTrainer\n',
                       b'    from .weights import NullTrainer\n    if kind is None:\n        selected=body_route.build(runtime)\n        if selected is not None:return selected\n', 'selected Body build')
    old = b"    t,info=build(runtime,kind);growth.weights.trainer=t;growth.trainer_info=info;return info\n"
    new = b'''    t,info=build(runtime,kind)
    role=getattr(t,'role','C3_LANGUAGE').split('#')[0]
    if getattr(growth.weights,'role','C3_LANGUAGE')!=role:
        from .weights import WeightConsolidation
        growth.weights=WeightConsolidation(runtime.store,runtime.cfg,growth.eval,growth.age,t,runtime.home,role=role)
    else:growth.weights.trainer=t
    growth.trainer_info=info
    return info
'''
    trainers = replace(trainers, old, new, 'role-owned install')
    trainers = replace(trainers, b'    from ..lora_trainer import DEFAULTS\n',
                       b"    if body_route.box(runtime).load()[0]['selected'] is not None:\n        body_route.set_cfg(runtime,overrides)\n        return install(growth,runtime)\n    from ..lora_trainer import DEFAULTS\n", 'Body cfg')
    trainers = replace(trainers, b"    if kind not in KINDS:raise ValueError('Trainer: '+'|'.join(KINDS))\n",
                       b"    if kind not in KINDS:raise ValueError('Trainer: '+'|'.join(KINDS))\n    body_route.clear(runtime)\n", 'C3 selection clears Body only')
    weights = result.get('v13/agi/weights.py', (code_dir / 'v13/agi/weights.py').read_bytes())
    weights = replace(weights, b'from .base import StateBox,age_allows\n',
                      b'from .base import StateBox,age_allows\nfrom .. import body_jepa_runtime_candidate as body_route\n', 'weight import')
    weights = replace(weights, b'trainer=None,home=None,clock=time.time):\n',
                      b'trainer=None,home=None,clock=time.time,role=None):\n', 'weight role signature')
    anchor = b"        self.box=StateBox(store,KEY,REVISION,lambda:{'batches':{},'consolidated':[],'order':[]})\n"
    weights = replace(weights, anchor, b"        self.role=role or getattr(self.trainer,'role','C3_LANGUAGE').split('#')[0]\n        if self.role not in ('C3_LANGUAGE',*body_route.ROLES):raise ValueError('Unknown weight organ role')\n        self.state_key=KEY if self.role=='C3_LANGUAGE' else KEY+':'+self.role\n" + anchor.replace(b'store,KEY,', b'store,self.state_key,'), 'weight scope')
    # Every transaction and approval recovery must address the same organ box.
    start = weights.index(b'    # -- staging')
    head, tail = weights[:start], weights[start:]
    tail, count = re.subn(rb'\bKEY\b', b'self.state_key', tail)
    if count != 7:
        raise ValueError('unexpected WeightConsolidation transactional key uses')
    weights = head + tail
    weights = replace(weights, b'    def candidates(self,require_replay_pass=True,cap=True):\n',
                      b'    def candidates(self,require_replay_pass=True,cap=True):\n        if self.role in body_route.ROLES:return body_route.candidates(self,require_replay_pass)\n', 'Body admitted candidates')
    weights = replace(weights, b"        items=self.candidates(require_replay_pass,cap=False);admission=None\n",
                      b"        if self.role in body_route.ROLES:include_rated=include_sdft=False\n        items=self.candidates(require_replay_pass,cap=False);admission=None\n", 'Body explicit targets only')
    anchor = b"        h=digest(dumps([[i['memory_id'],i['target']] for i in items]))\n"
    weights = replace(weights, anchor, anchor + b"        if self.role in body_route.ROLES:h=digest(dumps({'role':self.role,'items':items,'trainer':body_route.binding(self.trainer)}))\n", 'role-bound dataset identity')
    weights = replace(weights, b"               'items':items,'trainer':None,'gate':None,'request_id':None,",
                      b"               'target_role':self.role,'trainer_binding':body_route.binding(self.trainer),\n               'items':items,'trainer':None,'gate':None,'request_id':None,", 'staged role binding')
    weights = replace(weights, b"        if b['status']!='STAGED':raise ValueError('Nur STAGED-Batches werden trainiert')\n",
                      b"        if b['status']!='STAGED':raise ValueError('Nur STAGED-Batches werden trainiert')\n        if self.cfg.get('learning_mode')=='RECORD_ONLY':raise ValueError('Weight training disabled in RECORD_ONLY')\n        if b.get('target_role','C3_LANGUAGE')!=self.role or getattr(self.trainer,'role','C3_LANGUAGE').split('#')[0]!=self.role:raise ValueError('Staged target organ changed')\n        if self.role in body_route.ROLES and b.get('trainer_binding')!=body_route.binding(self.trainer):raise ValueError('Staged Body trainer binding changed; restage')\n", 'train role recheck')
    anchor = b"        self.s.read_source(ref)\n        if item.get('kind')=='rated_answer':"
    weights = replace(weights, anchor, b"        self.s.read_source(ref)\n        if self.role in body_route.ROLES and body_route.admitted(self.s,self.cfg,[item])!=[item]:raise ValueError('Body source or explicit learn permission changed')\n        if item.get('kind')=='rated_answer':", 'approval and fit consent recheck')
    weights = replace(weights, b"        if b['status']!='TRAINED':raise ValueError('Gate nur nach TRAINED')\n",
                      b"        if b['status']!='TRAINED':raise ValueError('Gate nur nach TRAINED')\n        body_route.guard_batch(self,b)\n", 'gate target role')
    weights = replace(weights, "            if not b or b['status']!='PENDING_USER':raise ValueError('Freigabe nur für PENDING_USER')\n".encode(),
                      "            if not b or b['status']!='PENDING_USER':raise ValueError('Freigabe nur für PENDING_USER')\n            body_route.guard_batch(self,b)\n".encode(), 'approval target role')
    weights = replace(weights, b"                if self._approval_input_hash(b)!=b['approval_attempt']['input_hash']:\n",
                      b"                body_route.guard_batch(self,b)\n                if self._approval_input_hash(b)!=b['approval_attempt']['input_hash']:\n", 'final approval target role')
    weights = replace(weights, b"('trainer','items','request_id','drift','gate','base_generation')",
                      b"('trainer','items','request_id','drift','gate','base_generation','target_role','trainer_binding')", 'approval target snapshot')
    agi = result['v13/agi/__init__.py']
    anchor = b"        g=runtime.growth=Growth(runtime.store,runtime.cfg,runtime.home,controller(runtime),getattr(sl,'scheduler',None))\n"
    agi = replace(agi, anchor, anchor + b"        from .. import body_jepa_runtime_candidate as body_route\n        if body_route.box(runtime).load()[0]['selected'] is not None:\n            from .trainers import install\n            install(g,runtime)\n", 'Body choice after restart')
    old = b'''    if a=='growth_consolidate':
        st=g.weights.stage('USER' if event['origin']=='USER' else 'SYSTEM',include_sdft=True)  # corrections marked `learn` (WP-S5 SDFT)
        if st.get('batch_id') and st['status']=='STAGED':
            from .trainers import install
            st['trainer']=install(g,r)['active']  # real trainer when master/torch/runner exist, else honest NO_TRAINER
            st['trained']=g.weights.train_and_gate(st['batch_id'],r.cancel_event)['status']
        return st
'''
    new = b'''    if a=='growth_consolidate':
        from .trainers import install
        from .. import body_jepa_runtime_candidate as body_route
        from contextlib import nullcontext
        info=install(g,r)
        context=body_route.training_job(r,event) if g.weights.role in body_route.ROLES else nullcontext()
        with context:
            st=g.weights.stage('USER' if event['origin']=='USER' else 'SYSTEM',include_sdft=True)
            if st.get('batch_id') and st['status']=='STAGED':
                st['trainer']=info['active']
                st['trained']=g.weights.train_and_gate(st['batch_id'],r.cancel_event)['status']
            return st
'''
    agi = replace(agi, old, new, 'actual scheduled owner and stage before correct trainer')
    anchor = b"        if len(args)==1:return dumps(trainers.install(g,r))\n"
    agi = replace(agi, anchor, anchor + b"        if args[1]=='body-jepa':\n            from .. import body_jepa_runtime_candidate as body_route\n            if len(args) not in (3,4):raise ValueError(':growth trainer body-jepa B1_DETAIL|B2_GIST [master]')\n            body_route.choose(r,args[2],args[3] if len(args)==4 else None,authority='EXPLICIT_HUMAN')\n            return dumps(trainers.install(g,r))\n", 'Body operator choice')
    agi = replace(agi, b"""if v[:1] in '[{"' else float(v)""",
                  b"""if v[:1] in '[{"' or v in ('true','false','null') else float(v)""", 'typed operator booleans')
    result.update({'v13/agi/trainers.py': trainers, 'v13/agi/weights.py': weights,
                   'v13/agi/__init__.py': agi, 'v13/body_jepa_runtime_candidate.py': body})
    return result
