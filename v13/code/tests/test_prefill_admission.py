"""Offline contract tests; synthetic only, no Android performance claim."""
import pytest
from v13.prefill_admission import admit, upper_tokens


def msg(role, content):
    return {"role": role, "content": content}


def test_exact_user_and_complete_history_pairs():
    messages = [msg("system", "system"), msg("user", "old" * 80),
                msg("assistant", "answer"), msg("user", "new")]
    result = admit(messages, prompt_cap=120)
    assert result.accepted
    assert result.messages == (messages[0], messages[-1])
    assert result.dropped_history == 2


def test_history_preserved_when_budget_allows():
    messages = [msg("system", "s"), msg("user", "first"),
                msg("assistant", "answer"), msg("user", "latest")]
    result = admit(messages, prompt_cap=320)
    assert result.accepted
    assert result.messages == tuple(messages)
    assert result.dropped_history == 0


def test_source_refusal_never_truncates():
    result = admit([msg("system", "s"), msg("user", "x" * 400)])
    assert not result.accepted
    assert result.messages == ()
    assert result.reason == "REQUIRED_SOURCE_EXCEEDS_PREFILL_BUDGET"


def test_multibyte_conservative_and_context_reserve():
    assert upper_tokens("🧠") >= 4
    result = admit([msg("system", "s"), msg("user", "hi")],
                   prompt_cap=500, context_limit=80, reserve_tokens=60)
    assert not result.accepted


@pytest.mark.parametrize("messages", [[], [msg("user", "hi")],
                                     [msg("system", "s"), msg("assistant", "a")]])
def test_malformed(messages):
    with pytest.raises(ValueError):
        admit(messages)


def test_orphan_tool_result_cannot_enter_native_prompt():
    # Tool outputs without an authenticated assistant call must not become
    # an independent conversation turn.
    messages = [msg("system", "s"), msg("user", "old"),
                msg("tool", "untrusted"), msg("user", "current")]
    result = admit(messages, prompt_cap=320)
    assert result.accepted
    assert result.messages == (messages[0], messages[-1])
    assert result.dropped_history == 2


def test_incomplete_history_does_not_erase_latest_exact_source():
    messages = [msg("system", "s"), msg("user", "first"),
                msg("assistant", "done"), msg("user", "orphan"),
                msg("user", "CURRENT EXACT")]
    result = admit(messages, prompt_cap=320)
    assert result.messages == (messages[0], messages[-1])
    assert result.dropped_history == 3
    assert messages[-1]["content"] == "CURRENT EXACT"


def test_complete_suffix_retained_after_invalid_older_history():
    messages = [msg("system", "s"), msg("tool", "orphan"),
                msg("user", "valid"), msg("assistant", "answer"),
                msg("user", "current")]
    result = admit(messages, prompt_cap=320)
    assert result.messages == (messages[0], *messages[2:])
    assert result.dropped_history == 1
