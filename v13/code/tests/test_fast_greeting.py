import pytest

from v13.fast_greeting import is_text_only_event, match, match_unclaimed


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("hi", "Hi."),
        ("HI!", "Hi."),
        ("  Hallo…  ", "Hallo."),
        ("Guten Morgen.", "Guten Morgen."),
        ("good evening?", "Good evening."),
    ],
)
def test_exact_standalone_greetings(text, expected):
    result = match(text)
    assert result is not None
    assert result["reply"] == expected
    assert result["rule_id"] == "BUILTIN_GREETING_ACK_V1"


@pytest.mark.parametrize(
    "text",
    [
        "hi there",
        "hi, can you calculate 2+2?",
        "hello, open settings",
        "guten  morgen",
        "what's up?",
        "yes",
        "",
        None,
        12,
        "hi" + (" " * 63),
    ],
)
def test_non_greetings_and_requests_fall_through(text):
    assert match(text) is None


def test_policy_validation_and_user_rule_precedence_are_mandatory():
    assert match_unclaimed("hi", policy_match_ok=False, fixed_policy=None) is None
    assert match_unclaimed("hi", policy_match_ok=True, fixed_policy={"rule_id": "user"}) is None
    assert match_unclaimed("hi", policy_match_ok=True, fixed_policy=None)["reply"] == "Hi."


def test_text_guard_rejects_audio_and_audio_backed_transcript():
    assert is_text_only_event({"source_ref": {"modality": "text"}})
    assert not is_text_only_event({"source_ref": {"modality": "audio"}})
    assert not is_text_only_event({
        "source_ref": {"modality": "text"},
        "_audio_window": {"pcm16": b"\x00\x00"},
    })
    assert not is_text_only_event({"source_ref": None})
    assert not is_text_only_event(None)
