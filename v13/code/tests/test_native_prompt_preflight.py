"""Synthetic contract checks; NOT native Redmi measurements."""
import pytest
from v13.prompt_admission import Segment, PromptAdmissionError
from v13.native_prompt_preflight import verify_native_prompt

def source(text):
    return Segment("USER_EXACT", text, "SOURCE", essential=True)

def test_exact_native_render_budget_success():
    result = verify_native_prompt([source("hi")],context_tokens=128,
        output_tokens=16,prompt_cap_tokens=64,count_rendered=lambda parts: 12)
    assert result.status == "VERIFIED"
    assert result.exact_prompt_tokens == 12

def test_template_overhead_fails_closed_without_dropping_user():
    result = verify_native_prompt([source("hi")],context_tokens=128,
        output_tokens=16,prompt_cap_tokens=64,count_rendered=lambda parts: 70)
    assert result.status == "RENDERED_OVER_BUDGET"
    assert result.admission.accepted[0].text == "hi"

def test_bad_native_counter_refused():
    with pytest.raises(ValueError):
        verify_native_prompt([source("hi")],context_tokens=128,
            output_tokens=16,prompt_cap_tokens=64,count_rendered=lambda parts: True)

def test_essential_source_over_budget():
    with pytest.raises(PromptAdmissionError):
        verify_native_prompt([source("x"*100)],context_tokens=128,
            output_tokens=16,prompt_cap_tokens=64,count_rendered=lambda parts: 1)
