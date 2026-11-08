"""Bounded AG10 tool synthesis: real program induction, gates, and restart."""
import pytest
from v13.agi.tool_builder import ToolBuilder

class Box:
    def __init__(self):self.data={'candidates':{}}
    def load(self):return self.data,0
    def mutate(self,fn):return fn(self.data)

class Registry:
    def __init__(self):self.tools={}
    def register(self,spec):self.tools[spec.name]=spec


def builder():
    reg=Registry();b=ToolBuilder(None,reg);b.box=Box()
    return b,reg


def examples():return [[x,x+7] for x in (-8,-5,0,3,12,18)]


def test_synthesizes_new_tool_without_activating_it():
    b,reg=builder()
    p=b.propose('plus_seven',examples())
    assert p['status']=='CANDIDATE' and p['program']=='add:7'
    assert p['train_count']==3 and p['heldout_count']==3
    assert reg.tools=={}


def test_activation_is_human_only_and_tool_starts_disabled():
    b,reg=builder();b.propose('plus_seven',examples())
    with pytest.raises(PermissionError):b.activate('plus_seven',origin='SELF')
    assert reg.tools=={}
    b.activate('plus_seven',origin='USER')
    spec=reg.tools['plus_seven']
    assert spec.risk=='READ_LOCAL' and spec.schema=={'x':'int'}
    assert spec.fn(x=5)==12
    assert spec.fn(x=-2)==5


def test_restart_only_restores_previously_activated_tools():
    b,reg=builder();b.propose('plus_seven',examples())
    new=ToolBuilder(None,Registry());new.box=b.box
    new.restore()
    assert new.registry.tools=={}
    b.activate('plus_seven')
    new.restore()
    assert new.registry.tools['plus_seven'].fn(x=4)==11


def test_bad_or_conflicting_examples_are_rejected():
    b,reg=builder()
    with pytest.raises(ValueError):b.propose('bad',[[1,2],[2,3],[3,100],[4,5]])
    with pytest.raises(ValueError):b.propose('duplicate',[[1,2],[1,2],[2,3],[3,4]])
    with pytest.raises(ValueError):b.propose('short',[[1,2]])
    with pytest.raises(ValueError):b.propose('float',[[1,2],[2,3],[3,4],[4,5.0]])
    assert reg.tools=={}


def test_no_auto_activation_or_unbounded_program():
    b,reg=builder()
    with pytest.raises(ValueError):b.propose('large',[[x,x**3] for x in range(4)])
    with pytest.raises(ValueError):b.activate('missing')


def test_name_conflict_and_duplicate_proposal():
    b,reg=builder();b.propose('plus_seven',examples())
    with pytest.raises(ValueError):b.propose('plus_seven',examples())
    b.activate('plus_seven')
    with pytest.raises(ValueError):b.activate('plus_seven')
