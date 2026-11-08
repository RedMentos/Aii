"""AG4 candidate creation from verified tool transactions; no model or Android proof."""
import pytest
from v13.agi.skills import SkillLibrary

class FakeBox:
    def __init__(self):self.state={'skills':{},'outcomes':{}}
    def load(self):return self.state,0
    def mutate(self,fn):return fn(self.state)

class FakeTool:
    def __init__(self,risk='READ_LOCAL'):
        self.risk=risk;self.schema={'expression':'str'}

class FakeRegistry:
    def __init__(self,risk='READ_LOCAL'):
        self.tools={'calc':FakeTool(risk)}
        self.calls=[]
        self.box=FakeBox()
        self.box.state={'calls':[]}

    def call(self,name,args,origin,intent):
        self.calls.append((name,args,origin,intent))
        return {'id':'replay','status':'EXECUTED','result':4}

def library(risk='READ_LOCAL'):
    registry=FakeRegistry(risk)
    lib=SkillLibrary(None,tools=registry)
    lib.box=FakeBox()
    registry.box.state['calls']=trace()
    return lib,registry

def trace(status='EXECUTED',expression='2+2'):
    return [{'id':'original','tool':'calc','args':{'expression':expression},'status':status}]

def test_successful_trace_creates_candidate_and_replays_through_registry():
    lib,registry=library()
    lib.propose_from_trace('add_two',['original'],trigger='calculate')
    skill=lib.get('add_two')
    assert skill['stage']=='CANDIDATE'
    assert skill['source_traces']==['original']
    result=lib.run('add_two',{},origin='USER')
    assert result['status']=='DONE' and result['value']==4
    assert registry.calls==[('calc',{'expression':'2+2'},'USER','skill:add_two')]

def test_denied_and_unapproved_traces_cannot_become_skills():
    for status in ('DENIED','PROPOSED','FAILED'):
        lib,_=library()
        lib.tools.box.state['calls']=trace(status=status)
        with pytest.raises(ValueError):lib.propose_from_trace('bad_skill',['original'])
        assert not lib.box.load()[0]['skills']

def test_side_effecting_tools_are_not_automatically_composed():
    lib,_=library('WRITE_LOCAL')
    with pytest.raises(ValueError):lib.propose_from_trace('write_skill',['original'])

def test_trace_arguments_are_copied_and_templates_rejected():
    lib,_=library()
    t=trace()
    lib.tools.box.state['calls']=t
    lib.propose_from_trace('safe_skill',['original'])
    t[0]['args']['expression']='999'
    assert lib.get('safe_skill')['steps'][0]['args']['expression']=='2+2'
    lib.tools.box.state['calls']=trace(expression='{prev}')
    with pytest.raises(ValueError):lib.propose_from_trace('template_skill',['original'])

def test_spoofed_status_and_unknown_trace_cannot_create_skill():
    lib,_=library()
    lib.tools.box.state['calls']=trace(status='DENIED')
    with pytest.raises(ValueError):
        lib.propose_from_trace('spoofed',[{'id':'original','status':'EXECUTED','tool':'calc','args':{'expression':'2+2'}}])
    with pytest.raises(ValueError):lib.propose_from_trace('missing',['not-in-ledger'])
    assert not lib.box.load()[0]['skills']

def test_duplicate_transaction_not_counted_twice():
    lib,_=library()
    with pytest.raises(ValueError):lib.propose_from_trace('duplicate',['original','original'])

def test_proposed_steps_do_not_alias_caller_mutations():
    lib,_=library()
    steps=[{'tool':'calc','args':{'expression':'3+4'}}]
    lib.propose('copy_skill',steps)
    steps[0]['args']['expression']='999'
    assert lib.get('copy_skill')['steps'][0]['args']['expression']=='3+4'

def test_replay_respects_live_tool_denial():
    lib,registry=library()
    lib.propose_from_trace('restricted',['original'])
    def denied(name,args,origin,intent):
        return {'id':'denied-replay','status':'DENIED','result':None}
    registry.call=denied
    assert lib.run('restricted',{},origin='USER')['status']=='DENIED'

def test_discover_recent_intent_creates_candidate():
    lib,_=library()
    lib.tools.box.state['calls'][0]['intent']='arithmetic'
    lib.propose_recent('arithmetic_skill','arithmetic')
    assert lib.get('arithmetic_skill')['source_traces']==['original']

def test_discover_recent_rejects_interleaved_and_failed_intents():
    lib,_=library()
    a=dict(trace()[0],id='a',intent='same')
    b=dict(trace()[0],id='b',intent='other')
    c=dict(trace()[0],id='c',intent='same')
    lib.tools.box.state['calls']=[a,b,c]
    with pytest.raises(ValueError):lib.propose_recent('bad_sequence','same')
    lib.tools.box.state['calls']=[a,dict(c,status='FAILED')]
    with pytest.raises(ValueError):lib.propose_recent('bad_outcome','same')

def test_candidate_cannot_autonomously_execute_unvalidated_recipe():
    lib,registry=library()
    lib.propose_from_trace('candidate',['original'])
    result=lib.run('candidate',{},origin='SELF')
    assert result['status']=='PROPOSED'
    assert result['reason']=='SKILL_NOT_TRUSTED'
    assert registry.calls==[]

def test_skill_candidate_survives_sqlite_restart(tmp_path):
    import sqlite3
    import json
    from v13.agi.base import StateBox

    class SQLiteState:
        def __init__(self,path):
            self.db=sqlite3.connect(path)
            self.db.execute('CREATE TABLE IF NOT EXISTS states (key TEXT PRIMARY KEY, version INTEGER, payload TEXT)')
        def state(self,key,default=None):
            row=self.db.execute('SELECT version,payload FROM states WHERE key=?',(key,)).fetchone()
            return (json.loads(row[1]),row[0]) if row else (default,0)
        def set_state(self,key,value,expected=None):
            _,version=self.state(key)
            if expected is not None and expected!=version:raise ValueError('Stale state write')
            self.db.execute('INSERT OR REPLACE INTO states VALUES (?,?,?)',(key,version+1,json.dumps(value)))
            self.db.commit()
        def close(self):self.db.close()

    path=tmp_path/'brain.sqlite3'
    store=SQLiteState(path)
    registry=FakeRegistry()
    registry.box.state['calls']=trace()
    lib=SkillLibrary(store,tools=registry)
    lib.propose_from_trace('persisted_skill',['original'])
    store.close()
    reopened=SQLiteState(path)
    again=SkillLibrary(reopened,tools=registry)
    assert again.get('persisted_skill')['source_traces']==['original']
    assert again.run('persisted_skill',{},origin='USER')['status']=='DONE'
    reopened.close()
