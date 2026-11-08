"""AG8/AG10 bounded synthesis of a NEW pure arithmetic tool from examples.

No arbitrary code, eval, filesystem, network or permissions. This is an early
self-built-tool capability, NOT a general code-writing agent. Candidate creation
is independent of Age; activation is an explicit user action and ToolRegistry
continues to enforce enablement, per-call policy, and Age rights.
"""
from .base import StateBox
from .tools import ToolSpec

KEY='G10_TOOL_BUILDER';REVISION='g10-tool-builder-v1'
MAX_EXAMPLES=64


def _programs():
    yield 'identity',lambda x:x
    yield 'abs',lambda x:abs(x)
    yield 'negate',lambda x:-x
    for k in range(-20,21):
        if k:yield 'add:'+str(k),lambda x,k=k:x+k
    for k in range(-10,11):
        if k not in (0,1):yield 'mul:'+str(k),lambda x,k=k:x*k
    for k in range(2,11):
        yield 'mod:'+str(k),lambda x,k=k:x%k


def _compile(program):
    for name,fn in _programs():
        if name==program:return fn
    raise ValueError('Unknown bounded tool program')


def _text_programs():
    # Reuse AG7's audited, finite DSL rather than executing model-generated code.
    from .abstraction import PRIMS
    for name,fn in PRIMS:
        yield name,fn


def _text_examples(items):
    if not isinstance(items,(list,tuple)) or not 4<=len(items)<=MAX_EXAMPLES:
        raise ValueError('4..64 text examples required')
    pairs=[]
    for item in items:
        if not isinstance(item,(list,tuple)) or len(item)!=2:
            raise ValueError('Text example must be [input, output]')
        x,y=item
        if type(x) is not str or type(y) is not str or len(x)>256 or len(y)>256:
            raise ValueError('Only bounded strings supported')
        pairs.append((x,y))
    if len({x for x,_ in pairs})!=len(pairs):raise ValueError('Repeated inputs')
    return pairs


def _compile_kind(kind,program):
    if kind=='integer':return _compile(program)
    if kind=='text':
        for name,fn in _text_programs():
            if name==program:return fn
    raise ValueError('Unknown bounded tool program')

def _examples(items):
    if not isinstance(items,(list,tuple)) or not 4<=len(items)<=MAX_EXAMPLES:
        raise ValueError('4..64 examples required (train and heldout)')
    pairs=[]
    for item in items:
        if not isinstance(item,(list,tuple)) or len(item)!=2:
            raise ValueError('Each example must be [integer input, integer output]')
        x,y=item
        if type(x) is not int or type(y) is not int or abs(x)>1000000 or abs(y)>10000000:
            raise ValueError('Only bounded integer examples are supported')
        pairs.append((x,y))
    if len({x for x,_ in pairs})!=len(pairs):raise ValueError('Repeated inputs do not establish independent evidence')
    return pairs


class ToolBuilder:
    def __init__(self,store,registry):
        self.s=store;self.registry=registry
        self.box=StateBox(store,KEY,REVISION,lambda:{'candidates':{}})

    def propose(self,name,examples,origin='SELF'):
        """Synthesize a minimal program, then verify on a disjoint heldout set.

        Caller must provide heldout examples independently; these are not proof
        of broad generalization. No tool is registered by this method.
        """
        from ..transaction import valid_name
        name=valid_name(name)
        if name in self.registry.tools:raise ValueError('Tool already registered')
        pairs=_examples(examples)
        # Deterministic split prevents searching the heldout examples for a fit.
        train=pairs[::2];heldout=pairs[1::2]
        solutions=[(label,fn) for label,fn in _programs() if all(fn(x)==y for x,y in train)]
        if not solutions:raise ValueError('No bounded program matches training examples')
        label,fn=solutions[0]
        if not all(fn(x)==y for x,y in heldout):raise ValueError('Heldout generalization failed')
        record={'name':name,'program':label,'kind':'integer','origin':origin,'status':'CANDIDATE',
                'train_count':len(train),'heldout_count':len(heldout),
                'examples':[[x,y] for x,y in pairs]}
        def save(st):
            if name in st['candidates']:raise ValueError('Tool candidate already exists')
            st['candidates'][name]=record
        self.box.mutate(save)
        return dict(record)

    def propose_text(self,name,examples,origin='SELF'):
        """Induce a pure text-transform tool from examples, with heldout check."""
        from ..transaction import valid_name
        name=valid_name(name)
        if name in self.registry.tools:raise ValueError('Tool already registered')
        pairs=_text_examples(examples)
        train=pairs[::2];heldout=pairs[1::2]
        matches=[]
        for label,fn in _text_programs():
            try:
                if all(fn(x)==y for x,y in train):matches.append((label,fn))
            except (ValueError,TypeError,OverflowError):continue
        if not matches:raise ValueError('No bounded text program fits')
        label,fn=matches[0]
        try:passed=all(fn(x)==y for x,y in heldout)
        except (ValueError,TypeError,OverflowError):passed=False
        if not passed:raise ValueError('Heldout generalization failed')
        record={'name':name,'kind':'text','program':label,'origin':origin,'status':'CANDIDATE',
                'train_count':len(train),'heldout_count':len(heldout),
                'examples':[[x,y] for x,y in pairs]}
        def save(st):
            if name in st['candidates']:raise ValueError('Tool candidate already exists')
            st['candidates'][name]=record
        self.box.mutate(save)
        return dict(record)

    def activate(self,name,origin='USER'):
        """Explicit human activation; never callable as SELF/SYSTEM.

        This registers a pure tool but does NOT enable it for execution.
        """
        if origin!='USER':raise PermissionError('Human activation required')
        record=self.box.load()[0]['candidates'].get(name)
        if not record or record['status'] not in ('CANDIDATE','ACTIVE'):
            raise ValueError('Unknown tool candidate')
        if name in self.registry.tools:raise ValueError('Tool already registered')
        fn=_compile_kind(record.get('kind','integer'),record['program'])
        kind=record.get('kind','integer')
        self.registry.register(ToolSpec(name,lambda x:fn(x),risk='READ_LOCAL',reversible=True,
            right='simple_tool_choice',description='Synthesized bounded arithmetic: '+record['program'],
            schema={'x':'int' if kind=='integer' else 'str'},effects=({'COMPUTE'},{'CALCULATOR'})))
        def save(st):st['candidates'][name]['status']='ACTIVE'
        self.box.mutate(save)
        return name

    def restore(self):
        """Re-register previously human-activated pure tools after restart.

        Still disabled by default unless separately enabled in ToolRegistry.
        """
        for name,record in self.box.load()[0]['candidates'].items():
            if record['status']!='ACTIVE' or name in self.registry.tools:continue
            fn=_compile_kind(record.get('kind','integer'),record['program'])
            kind=record.get('kind','integer')
            self.registry.register(ToolSpec(name,lambda x,fn=fn:fn(x),risk='READ_LOCAL',
                right='simple_tool_choice',description='Synthesized bounded arithmetic: '+record['program'],
                schema={'x':'int' if kind=='integer' else 'str'},effects=({'COMPUTE'},{'CALCULATOR'})))

    def report(self):
        return {'revision':REVISION,'candidates':[
            {'name':v['name'],'program':v['program'],'status':v['status']}
            for v in self.box.load()[0]['candidates'].values()],
            'claim_limit':'Pure bounded integer transforms only; no arbitrary code generation'}
