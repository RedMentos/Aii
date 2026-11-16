"""Authorized exact calculator output through the existing C5 -> C6 runtime lead path.

Software-only regression: does not claim Redmi/native model proof.
"""
from types import SimpleNamespace
from v13.toolstep import ToolStep


def step(enabled=True):
    return ToolStep(SimpleNamespace(cfg={'tool_answer_first': enabled}))


def receipt(value=4, status='EXECUTED', error=None):
    return {'tool': 'calc', 'args': {'expression': '2+2'},
            'result': value, 'status': status, 'error': error}


def test_executed_calc_is_exact_final_not_c3_free_text():
    t = step()
    r = receipt()
    assert t.lead(r) == 'The result of 2+2 is 4.'
    assert t.lead_final(r) == t.lead(r)


def test_shadow_refused_and_untrusted_results_never_become_final():
    t = step()
    for status in ('REFUSED', 'PROPOSED', 'SHADOW', 'FAILED'):
        assert t.lead_final(receipt(status=status)) is None
    assert t.lead_final(receipt(error='failed')) is None
    assert step(False).lead_final(receipt()) is None
    assert t.lead_final(receipt(float('nan'))) is None
    assert t.lead_final(receipt(True)) is None
    assert t.lead_final({'tool':'calc','args':{'expression':'2+2'},'result':'4','status':'EXECUTED'}) is None


def test_other_tools_keep_existing_path():
    t = step()
    assert t.lead_final({'tool':'sandbox_note','status':'EXECUTED','result':'ok'}) is None
