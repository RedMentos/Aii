"""WP-AG10 tools and action: registry + per-call transaction, ahead of the real WP-K / IH-H14/H29 path.

A ToolSpec names risk, reversibility and the Age right it needs. Every call is a transaction
PROPOSED → (APPROVED) → EXECUTED|FAILED|DENIED with arguments, result and duration, and its
outcome is handed to AG2 grounding (a grounded outcome beats self-assessment as learning signal).
Policy: only READ_LOCAL tools may run without a per-call human approval, and only if the user
enabled the tool; V13's own choice (SYSTEM/SELF) additionally needs the Age right
(simple_tool_choice, Age 1). Network, local writes and external effects are always
proposal-only here. One safe built-in exists: calc (AST arithmetic, no eval).
"""
import ast
import operator
import time
from ..common import dumps
from .base import StateBox,age_allows,new_id

KEY='G10_TOOLS';REVISION='g10-tools-v1'
RISKS=('READ_LOCAL','WRITE_LOCAL','NETWORK','EXTERNAL_EFFECT')
HISTORY=128

_OPS={ast.Add:operator.add,ast.Sub:operator.sub,ast.Mult:operator.mul,ast.Div:operator.truediv,ast.FloorDiv:operator.floordiv,
      ast.Mod:operator.mod,ast.Pow:operator.pow,ast.USub:operator.neg,ast.UAdd:operator.pos}
def calc(expression):
    def ev(n):
        if isinstance(n,ast.Expression):return ev(n.body)
        if isinstance(n,ast.Constant) and isinstance(n.value,(int,float)) and not isinstance(n.value,bool):return n.value
        if isinstance(n,ast.BinOp) and type(n.op) in _OPS:
            a,b=ev(n.left),ev(n.right)
            if isinstance(n.op,ast.Pow) and (abs(b)>64 or abs(a)>10**6):raise ValueError('Potenz zu groß')
            return _OPS[type(n.op)](a,b)
        if isinstance(n,ast.UnaryOp) and type(n.op) in _OPS:return _OPS[type(n.op)](ev(n.operand))
        raise ValueError('Nur Zahlen und + - * / // % **')
    s=str(expression)
    if len(s)>200:raise ValueError('Ausdruck zu lang')
    v=ev(ast.parse(s,mode='eval'))
    return int(v) if isinstance(v,float) and v.is_integer() else v

class ToolSpec:
    def __init__(self,name,fn,risk='READ_LOCAL',reversible=True,right='simple_tool_choice',description='',schema=None,undo=None,preview=None):
        if risk not in RISKS:raise ValueError('risk')
        if risk!='READ_LOCAL' and any(str(v).rstrip('?')=='text' for v in (schema or {}).values()):raise ValueError('text args only for READ_LOCAL')
        from ..transaction import valid_name
        self.name=valid_name(name);self.fn=fn;self.risk=risk;self.reversible=reversible;self.right=right;self.description=description
        self.schema=schema;self.undo=undo  # WP-K: typed argument schema {'arg':'str|int|float|bool|secret[?]'}, compensating action
        self.preview=preview  # WP-T7: side-effect-free dry run shown before a per-call approval

class ToolRegistry:
    def __init__(self,store,age=None,on_outcome=None,clock=time.time,monotonic=time.monotonic):
        self.s=store;self.age=age;self.on_outcome=on_outcome;self.clock=clock;self.monotonic=monotonic;self.tools={}
        self.box=StateBox(store,KEY,REVISION,lambda:{'enabled':[],'calls':[],'counters':{}})
        self.register(ToolSpec('calc',calc,description='Arithmetik ohne eval',schema={'expression':'str'}))
        from ..transaction import sandbox_note_tool
        self.register(ToolSpec('sandbox_note',*sandbox_note_tool(store.home)))  # WP-K: first WRITE_LOCAL tool, sandboxed + undo
        from . import listarith
        self.register(ToolSpec('list_arith',listarith.tool,description='Summe/Differenz über aufgezählte Werte (Rezept, Zahlen-Wächter)',schema=listarith.SCHEMA))
    def register(self,spec):self.tools[spec.name]=spec
    def enable(self,name,on=True):
        """User permission per tool (§17.3). Default: nothing enabled."""
        if name not in self.tools:raise ValueError('Unbekanntes Werkzeug')
        def f(st):st['enabled']=sorted(set(st['enabled'])|{name}) if on else [t for t in st['enabled'] if t!=name]
        self.box.mutate(f)
    def _policy(self,spec,origin,args,confirmed=False):
        """WP-K IH-H29 contract: schema -> capability -> risk -> confirmation -> C5 (Age right for own choice)."""
        from ..transaction import authorize
        st=self.box.load()[0]
        return authorize(spec,args,origin,spec.name in st['enabled'],age_allows(self.age,spec.right,origin),confirmed)
    def call(self,name,args,origin='USER',intent=None,predicted=None,event_id=None,idempotency_key=None):
        spec=self.tools.get(name)
        if spec is None:raise ValueError('Unbekanntes Werkzeug')
        dumps(args)
        status,why,steps=self._policy(spec,origin,args)
        tx={'id':new_id('tool'),'tool':name,'risk':spec.risk,'origin':origin,'args':args,'intent':intent,'predicted':predicted,'event_id':event_id,
            'idempotency_key':idempotency_key,'status':status,'reason':why,'contract':steps,'created':self.clock(),'result':None,'error':None,'duration_s':None}
        if status=='APPROVED':tx=self._execute(spec,tx)
        elif status=='PROPOSED':tx['preview']=self.preview(name,args)  # WP-T7: what approval would do
        self._save(tx);return tx
    def preview(self,name,args):
        """WP-T7 dry run of a call: never executes, never reads secrets; schema violations return None."""
        from ..transaction import check_args,secrets_in
        spec=self.tools.get(name)
        if spec is None or check_args(spec.schema,args):return None
        base={'tool':name,'risk':spec.risk,'reversible':spec.reversible,'undo_available':spec.undo is not None,'description':spec.description}
        if spec.preview is None or secrets_in(args):return base|{'effect':'UNKNOWN_NO_DRY_RUN'}
        try:return base|spec.preview(**args)
        except Exception as exc:return base|{'effect':'PREVIEW_FAILED','error':type(exc).__name__+': '+str(exc)[:120]}
    def approve(self,tx_id):
        """Human per-call approval for a PROPOSED call; it then runs as a WP-K action transaction."""
        st=self.box.load()[0];tx=next((c for c in st['calls'] if c['id']==tx_id),None)
        if not tx or tx['status']!='PROPOSED':raise ValueError('Kein offener Vorschlag')
        spec=self.tools[tx['tool']];status,why,steps=self._policy(spec,'USER',tx['args'],confirmed=True)
        tx=dict(tx,status=status,reason=why,contract=steps)
        if status=='APPROVED':tx=self._execute(spec,tx)
        self._save(tx,replace=True);return tx
    def undo(self,tx_id):
        """Compensating action for a reversible executed call (WP-K)."""
        from ..transaction import Transactions
        st=self.box.load()[0];tx=next((c for c in st['calls'] if c['id']==tx_id),None)
        if not tx or not tx.get('action_tx'):raise ValueError('Kein ausgeführter Aufruf')
        spec=self.tools[tx['tool']]
        if spec.undo is None:raise ValueError('Werkzeug hat keine Rücknahme')
        return Transactions(self.s,self.clock).undo(tx['action_tx'],spec.undo)
    def _execute(self,spec,tx):
        """Runs through the IH-H14 transaction: copy committed before the effect, EXECUTING persisted, outcome logged."""
        from ..transaction import Transactions,Provisional,SINKS
        T=Transactions(self.s,self.clock)
        a=T.prepare(tx.get('event_id'),spec.name,tx['args'],tx['origin'],spec.risk,spec.reversible,tx.get('idempotency_key'),tx.get('intent'))
        if a.get('deduplicated'):
            return dict(tx,status='DEDUPLICATED',reason='IDEMPOTENCY_KEY',action_tx=a['id'],result=a.get('result'),error=a.get('error'))
        T.commit_copy(a['id'],{'predicted':tx.get('predicted')})
        a=T.execute(a['id'],spec.fn)
        tx.update(action_tx=a['id'],status='EXECUTED' if a['state']=='SUCCEEDED' else 'FAILED',result=a['result'],error=a['error'],duration_s=a.get('duration_s'))
        if self.on_outcome:
            if tx.get('event_id') and not self._turn_ended(tx['event_id']):  # IH-H13: an outcome inside a running turn stays provisional until that turn is FINAL
                SINKS['tool_outcome']=self.on_outcome
                try:Provisional(self.s).put(tx['event_id'],'tool_outcome',dict(tx));return tx
                except Exception:pass
            try:self.on_outcome(tx)
            except Exception:pass
        return tx
    def _turn_ended(self,event_id):
        """Thread G: approved effects after a terminal turn must not wait in its abandoned provisional buffer."""
        return self.s.one("SELECT 1 FROM messages WHERE event_id=? AND role='assistant' AND status IN ('FINAL','CANCELLED','DEADLINE','ERROR','INTERRUPTED') LIMIT 1",(event_id,)) is not None
    def _save(self,tx,replace=False):
        def f(st):
            if replace:st['calls']=[c for c in st['calls'] if c['id']!=tx['id']]
            st['calls']=(st['calls']+[tx])[-HISTORY:];st['counters'][tx['status']]=st['counters'].get(tx['status'],0)+1
        self.box.mutate(f);self.s.log('tool_call',None,{'tool':tx['tool'],'status':tx['status'],'origin':tx['origin']})
    def report(self):
        st=self.box.load()[0]
        return {'revision':REVISION,'tools':{n:{'risk':t.risk,'reversible':t.reversible,'right':t.right,'enabled':n in st['enabled']} for n,t in self.tools.items()},
                'counters':st['counters'],'recent':[{k:c[k] for k in ('id','tool','status','reason','origin')} for c in st['calls'][-8:]],
                'claim_limit':'Read-only local tools may run by policy; write/network/external effects run only after per-call human approval as WP-K transactions'}
