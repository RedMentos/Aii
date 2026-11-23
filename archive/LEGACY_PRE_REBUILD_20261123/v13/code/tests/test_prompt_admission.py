"""Software-only prompt admission regression; no Android/native performance claim."""
import pytest

from v13.prompt_admission import Segment, PromptAdmissionError, admit


def segment(role, text, essential=False, authority="HYPOTHESIS", count=None):
    return Segment(role, text, authority, essential, count)


def test_keeps_user_exact_and_both_body_offers_when_budget_allows():
    parts = [
        segment("SYSTEM", "rules", True, "CONTROL", 10),
        segment("USER_EXACT", "2+2?", True, "SOURCE", 10),
        segment("MEMORY", "old", count=60),
        segment("B1_DETAIL", "detail", count=25),
        segment("B2_GIST", "gist", count=25),
        segment("ENLIGHTENED_SPACE", "space", count=15),
    ]
    out = admit(parts, context_tokens=256, output_tokens=32,
                prompt_cap_tokens=90, framing_reserve=16)
    assert [s.role for s in out.accepted] == [
        "SYSTEM", "USER_EXACT", "B1_DETAIL", "B2_GIST", "ENLIGHTENED_SPACE"
    ]
    assert out.omitted == ("MEMORY",)
    assert out.status == "PARTIAL_CONTEXT"
    assert out.estimated_prompt_tokens == 85
    assert parts[1].text == out.accepted[1].text


def test_essential_source_never_truncated_or_dropped():
    parts = [segment("USER_EXACT", "x" * 100, True, "SOURCE")]
    with pytest.raises(PromptAdmissionError):
        admit(parts, context_tokens=128, output_tokens=24,
              prompt_cap_tokens=40)
    assert parts[0].text == "x" * 100


def test_untrusted_hypothesis_cannot_be_essential():
    with pytest.raises(ValueError):
        segment("B1_DETAIL", "invented", True)


def test_exact_user_cannot_be_mislabeled_optional():
    with pytest.raises(ValueError):
        segment("USER_EXACT", "source", False, "SOURCE")


def test_utf8_fallback_is_conservative_and_no_mutation():
    parts = [segment("USER_EXACT", "Ä" * 20, True, "SOURCE")]
    out = admit(parts, context_tokens=128, output_tokens=20,
                prompt_cap_tokens=100)
    assert out.estimated_prompt_tokens >= len(parts[0].text.encode("utf-8"))
    assert out.accepted == tuple(parts)


def test_reserve_rejects_impossible_context_and_invalid_counts():
    with pytest.raises(PromptAdmissionError):
        admit([], context_tokens=32, output_tokens=20,
              prompt_cap_tokens=20, framing_reserve=12)
    with pytest.raises(ValueError):
        segment("B2_GIST", "x", count=-1)
    with pytest.raises(ValueError):
        admit([], context_tokens=True, output_tokens=2,
              prompt_cap_tokens=10)
