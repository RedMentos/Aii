import pytest

from v13.arithmetic_fastpath import RULE_ID, is_text_only_event, match


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("2+2", "4"),
        ("What is 2 + 2?", "4"),
        ("Berechne 17 * 23", "391"),
        ("0.1 + 0.2", "0.3"),
        ("1 / 3", "1/3"),
        ("(12 - 4) * -3", "-24"),
        ("2 ** 12", "4096"),
        ("17 // 5", "3"),
        ("17 % 5", "2"),
    ],
)
def test_exact_single_expression(text, expected):
    result = match(text)
    assert result is not None
    assert result["rule_id"] == RULE_ID
    assert result["scope"] == "EXACT_SINGLE_EXPRESSION_ONLY"
    assert result["exact"] is True
    assert result["result"] == expected
    assert result["reply"] == expected


@pytest.mark.parametrize(
    "text",
    [
        "",
        "2",
        "Compare 2+2 and 3+3",
        "2+2 for my budget",
        "2+2=4",
        "2/0",
        "2**13",
        "2+__import__('os')",
        "True + 1",
        "1e100",
        "9" * 100,
    ],
)
def test_nontrivial_or_unsafe_input_falls_through(text):
    assert match(text) is None


def test_text_only_event_gate_preserves_audio_path():
    text_event = {"source_ref": {"modality": "text"}, "_audio_window": None}
    audio_event = {"source_ref": {"modality": "audio"}, "_audio_window": None}
    mixed_event = {"source_ref": {"modality": "text"}, "_audio_window": {"start": 0}}
    assert is_text_only_event(text_event)
    assert match("2+2", event=text_event)["result"] == "4"
    assert not is_text_only_event(audio_event)
    assert not is_text_only_event(mixed_event)
    assert match("2+2", event=audio_event) is None
    assert match("2+2", event=mixed_event) is None
