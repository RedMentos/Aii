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
    def call(self,name,args,origin,intent):
        self.calls.append((name,args,origin,intent))
        return {'id':'replay','status':'EXECUTED','result':4}

def library(risk='READ_LOCAL'):
    registry=FakeRegistry(risk)
    lib=SkillLibrary(None,tools=registry)
    lib.box=FakeBox()
    return lib,registry

def trace(status='EXECUTED',expression='2+2'):
    return [{'id':'original','tool':'calc','args':{'expression':expression},'status':status}]

def test_successful_trace_creates_candidate_and_replays_through_registry():
    lib,registry=library()
    lib.propose_from_trace('add_two',trace(),trigger='calculate')
    skill=lib.get('add_two')
    assert skill['stage']=='CANDIDATE'
    assert skill['source_traces']==['original']
    result=lib.run('add_two',{},origin='USER')
    assert result['status']=='DONE' and result['value']==4
    assert registry.calls==[('calc',{'expression':'2+2'},'USER','skill:add_two')]

def test_denied_and_unapproved_traces_cannot_become_skills():
    for status in ('DENIED','PROPOSED','FAILED'):
        lib,_=library()
        with pytest.raises(ValueError):lib.propose_from_trace('bad_skill',trace(status=status))
        assert not lib.box.load()[0]['skills']

def test_side_effecting_tools_are_not_automatically_composed():
    lib,_=library('WRITE_LOCAL')
    with pytest.raises(ValueError):lib.propose_from_trace('write_skill',trace())

def test_trace_arguments_are_copied_and_templates_rejected():
    lib,_=library()
    t=trace()
    lib.propose_from_trace('safe_skill',t)
    t[0]['args']['expression']='999'
    assert lib.get('safe_skill')['steps'][0]['args']['expression']=='2+2'
    with pytest.raises(ValueError):lib.propose_from_trace('template_skill',trace(expression='{prev}'))
