"""P0 #1904 regression: real turn must observe post-ContextOS prompt.

Synthetic source-contract checks only. No device latency or tokenizer proof.
"""
import inspect
from v13 import runtime
from v13.prefill_admission import admit


def test_runtime_admission_after_context_before_native_generation():
    source = inspect.getsource(runtime.Runtime._turn)
    context = source.index("messages=cplan['messages']")
    observe = source.index("admission=prefill_admit(messages)")
    native = source.index("runner.generate(messages,self.cancel_event,deadline")
    assert context < observe < native
    assert "'applied':False" in source
    assert "'source_preserved':True" in source


def test_advisory_never_modifies_source_or_system():
    system = {'role':'system','content':'fixed Context OS header'}
    old = {'role':'user','content':'older ' * 100}
    assistant = {'role':'assistant','content':'prior reply'}
    current = {'role':'user','content':'exact source 🧠'}
    original = [system, old, assistant, current]
    result = admit(original, prompt_cap=120)
    assert result.accepted
    assert result.messages[0] == system
    assert result.messages[-1] == current
    assert original == [system, old, assistant, current]
    assert result.dropped_history == 2


def test_required_source_over_budget_is_explicit_refusal():
    result = admit([{'role':'system','content':'header'},
                    {'role':'user','content':'x' * 800}], prompt_cap=320)
    assert not result.accepted
    assert result.messages == ()
    assert result.reason == 'REQUIRED_SOURCE_EXCEEDS_PREFILL_BUDGET'
