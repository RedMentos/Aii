"""B1/B2 prefill admission: bounded native input without source truncation.

These tests exercise the production reducer and its soft-limit policy. They do
not claim native GGUF performance or Redmi timing.
"""
import json

from v13.native_prompt_admission import reduce_once, soft_limit


def test_b1_and_b2_keep_a_soft_prefill_target_on_long_deadlines():
    assert soft_limit("B1_DETAIL", {}, 90.0) == 520
    assert soft_limit("B2_GIST", {}, 90.0) == 520
    assert soft_limit("B1_DETAIL", {}, 55.0) == 520
    assert soft_limit("B2_GIST", {}, 55.0) == 520


def test_body_target_tightens_with_short_deadline_and_c3_policy_is_unchanged():
    assert soft_limit("B1_DETAIL", {}, 30.0) == 273
    assert soft_limit("B2_GIST", {}, 30.0) == 273
    assert soft_limit("C3_LANGUAGE", {}, 30.0) == 260
    assert soft_limit("C3_LANGUAGE", {}, 90.0) == 520


def test_metadata_only_reduction_preserves_source_peer_jef_quotes_and_b3():
    exact = "The current source fixes the budget at 120 euros."
    peer = {"role": "B2_GIST", "summary": "Check the broader rule."}
    jef = {"question": "Which budget applies?", "kind": "FILL_GAP"}
    quotes = [{"id": 1, "text": exact}]
    b3 = {
        "from": "B3_CALLOSUM",
        "channel": "CONTROL",
        "authority": "CONTROL_ONLY",
        "semantic_cue_not_fact": "Peer requests a contradiction check.",
        "exact_sources": [],
    }
    original = {
        "source_segments": [{
            "text": exact,
            "source_ref": {
                "source_id": "src-1",
                "sha256": "a" * 64,
                "char_start": 0,
                "char_end": len(exact),
            },
        }],
        "peer_message": peer,
        "prior_hypothesis": "",
        "jef_query": jef,
        "quote_choices": quotes,
        "detail_windows": [exact],
        "executive_broadcast": {
            "goal": exact,
            "source_refs": [{"source_id": "src-1", "sha256": "a" * 64}],
            "state_version": 7,
        },
        "body_state": {
            "authority": "STATE_NOT_FACT",
            "role": "B1_DETAIL",
            "world": {"mode": "LOCAL", "observed_actions": 2, "debug": "x" * 900},
            "self": {"external_tools": False, "learning": "SHADOW", "system_stage": 0},
            "skills": ["unused-skill"] * 80,
        },
        "enlightened_space": {
            "representation": "SYMBOLIC_MESSAGE_SPACE_NOT_NATIVE_JEPA",
            "messages": [
                {
                    "from": "STREAM_A",
                    "channel": "EXACT",
                    "authority": "SOURCE_POINTER",
                    "semantic_cue_not_fact": exact,
                    "exact_sources": [{
                        "exact_source_text": exact,
                        "source_ref": {"source_id": "src-1", "sha256": "a" * 64},
                        "verification": "RECHECKED_EXACT_BYTES",
                    }],
                    "coactivations": 1,
                },
                b3,
            ],
        },
        "self_corollary": {
            "recent_own_action_outcomes": [
                {"action_id": "a1"},
                {"action_id": "a2"},
                {"action_id": "a3"},
            ],
        },
    }
    messages = [
        {"role": "system", "content": "Internal B1 instructions."},
        {"role": "user", "content": json.dumps(original, ensure_ascii=False, sort_keys=True)},
    ]
    working = [dict(item) for item in messages]
    reasons = []
    for _ in range(10):
        candidate = reduce_once(working, "B1_DETAIL", {})
        if candidate is None:
            break
        working, reason = candidate
        reasons.append(reason)
    else:
        raise AssertionError("body metadata reducer did not converge")

    final = json.loads(working[1]["content"])
    assert final["source_segments"][0]["text"] == exact
    assert final["peer_message"] == peer
    assert final["jef_query"] == jef
    assert final["quote_choices"] == quotes
    assert any(row.get("from") == "B3_CALLOSUM" for row in final["enlightened_space"]["messages"])
    assert "source_ref" not in final["source_segments"][0]
    assert "BODY_SOURCE_ADDRESS_METADATA" in reasons
    assert "BODY_DUPLICATE_STREAM_SOURCE" in reasons
    assert original["source_segments"][0]["source_ref"]["sha256"] == "a" * 64


def test_protected_source_overflow_is_not_silently_truncated():
    exact = "source evidence " * 1200
    messages = [
        {"role": "system", "content": "Internal B2 instructions."},
        {"role": "user", "content": json.dumps({
            "gist_slots": [{"slot": 0, "text": exact, "scale": "fine"}],
            "peer_message": None,
            "jef_query": {"question": "What is stated?"},
        })},
    ]
    before = messages[1]["content"]
    assert soft_limit("B2_GIST", {}, 90.0) == 520
    assert reduce_once(messages, "B2_GIST", {}) is None
    assert messages[1]["content"] == before
    assert json.loads(messages[1]["content"])["gist_slots"][0]["text"] == exact
