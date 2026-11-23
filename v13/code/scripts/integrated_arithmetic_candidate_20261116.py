"""Compose source-bound arithmetic into the runnable review tree.

Derived from #1987/#1989, with the C5 action, packet contract and C6 fallback
completed. Frozen Runtime/Store and existing SourceHandoff pins stay intact.
"""
import hashlib
from pathlib import Path


SOURCE_PINS = {
    'v13/runtime.py': 'c64ed6170bbc49c3a60d24d2566d10e9d53586c6608534c738a10b8834718c52',
    'v13/broker.py': '3be190e0f2314ab360915996d1bd3e9f6a6ef69e7134c2ef86dccc01b4bc5562',
    'v13/contracts.py': '25466e9f938251db981256e8cbf7313c414aeddb4d7c9b880598fe61d92765b1',
    'v13/focal.py': 'e1f17b7865c35a268feb898551c1fd8d190f63a68819fec3b0c07dd21ceef6cf',
    'v13/arithmetic_reflex.py': '93486e8e5e7e9c9c66178833d3c25218e57172688623fb2a29af8e45b6246927',
}
UPSTREAM_RUNTIME_SHA = 'cf6da240935d60bbef5472af07db7a0b0a495d53cb6f6206f95fc3b47a4317d7'


def _replace(raw, old, new, label):
    old, new = old.encode(), new.encode()
    if raw.count(old) != 1:
        raise ValueError('arithmetic composition anchor mismatch: ' + label)
    return raw.replace(old, new, 1)


def apply_sources(code_dir, sources):
    code_dir = Path(code_dir)
    original = {}
    for name, expected in SOURCE_PINS.items():
        path = code_dir / name
        raw = path.read_bytes()
        if path.is_symlink() or hashlib.sha256(raw).hexdigest() != expected:
            raise ValueError('arithmetic source changed: ' + name)
        original[name] = raw
    result = dict(sources)
    runtime = result['v13/runtime.py']
    if hashlib.sha256(runtime).hexdigest() != UPSTREAM_RUNTIME_SHA:
        raise ValueError('upstream arithmetic Runtime changed; expected=' + UPSTREAM_RUNTIME_SHA + '; actual=' + hashlib.sha256(runtime).hexdigest() + '; review composition')
    for name in ('v13/broker.py', 'v13/contracts.py', 'v13/focal.py'):
        if result.get(name, original[name]) != original[name]:
            raise ValueError('upstream arithmetic source changed: ' + name)

    runtime = _replace(runtime,
        "            mark('policy_check');fixed_policy=match(self.store,text)\n",
        "            mark('policy_check');fixed_policy=match(self.store,text)\n"
        "            from .arithmetic_reflex import exact_arithmetic\n"
        "            arithmetic_answer=None if fixed_policy else exact_arithmetic(text)\n",
        'bounded source computation')
    # Like approved exact output, the narrow arithmetic path needs the current
    # A5 source and executive state, without optional native perception/recall.
    runtime = _replace(runtime,
        "            if fixed_policy:\n                self.store.add_packet('PerceptPacket'",
        "            if fixed_policy or arithmetic_answer is not None:\n                self.store.add_packet('PerceptPacket'",
        'minimal source percept')
    runtime = _replace(runtime, "            if fixed_policy:memories=[]\n",
        "            if fixed_policy or arithmetic_answer is not None:memories=[]\n", 'memory admission')
    runtime = _replace(runtime,
        "            if not fixed_policy:\n                try:memories=episodes.recall_turn",
        "            if not fixed_policy and arithmetic_answer is None:\n                try:memories=episodes.recall_turn",
        'episodic recall')
    runtime = _replace(runtime,
        "            if not fixed_policy:\n                try:  # WP-N7",
        "            if not fixed_policy and arithmetic_answer is None:\n                try:  # WP-N7",
        'warm recall')
    runtime = _replace(runtime,
        "            elif exact:direct=True;route='simple';meta['route']={'source':'EXPLICIT_EXACT_COPY'}\n",
        "            elif arithmetic_answer is not None:\n"
        "                direct=True;route='simple';meta['route']={'source':'EXACT_ARITHMETIC_REFLEX'}\n"
        "                meta['arithmetic_reflex']={'source_ref':e['source_ref'],'model_generated':False,'bounded':True}\n"
        "                meta.update(output_authority='LOCAL_EXACT_ARITHMETIC',skipped_native_stages=['A3_NATIVE_ALIGNMENT','SEMANTIC_RECALL','C2_CONTROL','B_OBSERVERS','C3_DECODE','NATIVE_WORLD_PREDICTION'])\n"
        "            elif exact:direct=True;route='simple';meta['route']={'source':'EXPLICIT_EXACT_COPY'}\n",
        'arithmetic route')
    runtime = _replace(runtime,
        "select(e,route=route,direct=direct,resource_state=state",
        "select(e,route=route,direct=direct,direct_action='LOCAL_EXACT_ARITHMETIC' if arithmetic_answer is not None else 'SOURCE_COPY',resource_state=state",
        'typed C5 action')
    runtime = _replace(runtime,
        "output=safe_text(fixed_policy['answer'] if fixed_policy else exact.group(1))",
        "output=safe_text(fixed_policy['answer'] if fixed_policy else arithmetic_answer if arithmetic_answer is not None else exact.group(1))",
        'deterministic output')
    runtime = _replace(runtime, "meta['direct_source_copy']=True\n",
        "meta['direct_source_copy']=arithmetic_answer is None\n", 'copy classification')
    runtime = _replace(runtime, "'role':'SOURCE_COPY' if direct else (runner.role if runner else None)",
        "'role':predicted_role if direct else (runner.role if runner else None)", 'action outcome')
    runtime = _replace(runtime,
        "c5ctl.check_output(self.store,e,'EXACT_RENDER' if direct else 'TEXT_REPORT',output)",
        "c5ctl.check_output(self.store,e,'EXACT_RENDER' if direct and not meta.get('arithmetic_reflex') else 'TEXT_REPORT',output)",
        'broker failure C6 fallback')
    result['v13/runtime.py'] = runtime

    broker = _replace(original['v13/broker.py'],
        "RANK={'APPROVED_FIXED_RULE':0,'EXPLICIT_EXACT_COPY':1,'MODEL_ANSWER':2,'SOURCE_SYSTEM_REPORT':3}",
        "RANK={'APPROVED_FIXED_RULE':0,'EXPLICIT_EXACT_COPY':1,'LOCAL_EXACT_ARITHMETIC':2,'MODEL_ANSWER':3,'SOURCE_SYSTEM_REPORT':4}",
        'broker authority order')
    broker = _replace(broker,
        "  MODEL_ANSWER          body answer",
        "  LOCAL_EXACT_ARITHMETIC exact bounded computation from the current user source (not a source copy)\n"
        "  MODEL_ANSWER          body answer", 'broker authority documentation')
    broker = _replace(broker,
        "    if authority in ('APPROVED_FIXED_RULE','EXPLICIT_EXACT_COPY'):return 'EXACT_RENDER'\n",
        "    if authority in ('APPROVED_FIXED_RULE','EXPLICIT_EXACT_COPY'):return 'EXACT_RENDER'\n"
        "    if authority=='LOCAL_EXACT_ARITHMETIC':return 'TEXT_REPORT'\n", 'computed egress')
    broker = _replace(broker,
        "        if exact_requested or (direct and not cands):cands.append('EXPLICIT_EXACT_COPY')\n",
        "        if meta.get('output_authority')=='LOCAL_EXACT_ARITHMETIC':cands.append('LOCAL_EXACT_ARITHMETIC')\n"
        "        elif exact_requested or (direct and not cands):cands.append('EXPLICIT_EXACT_COPY')\n", 'computed authority')
    result['v13/broker.py'] = broker
    result['v13/contracts.py'] = _replace(original['v13/contracts.py'],
        'obj["authority"] not in {"APPROVED_FIXED_RULE","EXPLICIT_EXACT_COPY","MODEL_ANSWER","SOURCE_SYSTEM_REPORT","NONE"}',
        'obj["authority"] not in {"APPROVED_FIXED_RULE","EXPLICIT_EXACT_COPY","LOCAL_EXACT_ARITHMETIC","MODEL_ANSWER","SOURCE_SYSTEM_REPORT","NONE"}',
        'broker packet contract')

    focal = _replace(original['v13/focal.py'],
        'def candidates(self,route,direct,coalition,view,age,tool=None):',
        "def candidates(self,route,direct,coalition,view,age,tool=None,direct_action='SOURCE_COPY'):", 'C5 candidate signature')
    focal = _replace(focal,
        "        if direct:add('SOURCE_COPY',1.,0.,'local_text_only',1.,'EXACT_RENDER')\n",
        "        if direct:add(direct_action,1.,0.,'local_text_only',1.,'TEXT_REPORT' if direct_action=='LOCAL_EXACT_ARITHMETIC' else 'EXACT_RENDER')\n",
        'C5 arithmetic candidate')
    focal = _replace(focal,
        'def select(self,e,*,route,direct,resource_state,coalition=(),view=None,age=None,predicted=False,effort=None,gain_action=None,tool=None,clarify=None):\n',
        "def select(self,e,*,route,direct,resource_state,coalition=(),view=None,age=None,predicted=False,effort=None,gain_action=None,tool=None,clarify=None,direct_action='SOURCE_COPY'):\n"
        "        if direct_action not in {'SOURCE_COPY','LOCAL_EXACT_ARITHMETIC'} or (not direct and direct_action!='SOURCE_COPY'):\n"
        "            raise ValueError('Invalid deterministic C5 action')\n", 'C5 select signature')
    focal = _replace(focal, 'self.candidates(route,direct,coalition,view,age,tool)',
        'self.candidates(route,direct,coalition,view,age,tool,direct_action)', 'C5 candidate consumer')
    focal = _replace(focal, "elif direct and c['action_id']!='SOURCE_COPY':",
        "elif direct and c['action_id']!=direct_action:", 'C5 permission suppression')
    result['v13/focal.py'] = focal
    result['v13/arithmetic_reflex.py'] = original['v13/arithmetic_reflex.py']
    for name in ('v13/runtime.py', 'v13/broker.py', 'v13/contracts.py', 'v13/focal.py', 'v13/arithmetic_reflex.py'):
        compile(result[name], name, 'exec')
    return result
