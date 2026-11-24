from v13.c3_speech_intent import from_c3_text, verify_intent, SpeechIntentError
import pytest


def test_c3_to_speech_contract_and_tamper():
    value = from_c3_text("Hallo Welt. Noch ein Satz!", language="de").to_dict()
    assert value["status"] == "PROPOSED_NOT_SPOKEN"
    assert len(value["segments"]) == 2
    assert verify_intent(value)
    value["segments"][0]["text"] = "anderer Text"
    assert not verify_intent(value)


def test_bounded_segments_and_restart_serialization():
    import json
    value = from_c3_text("Ja. " * 30).to_dict()
    assert len(value["segments"]) == 16
    assert verify_intent(json.loads(json.dumps(value)))


@pytest.mark.parametrize("text", ["", " ", "\x00", "a" * 2049, None])
def test_invalid_c3_input(text):
    with pytest.raises(SpeechIntentError):
        from_c3_text(text)


def test_untrusted_status_cannot_claim_playback():
    value = from_c3_text("Test").to_dict()
    value["status"] = "SPOKEN"
    assert not verify_intent(value)
