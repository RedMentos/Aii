import pytest

from v13.audio_input import AUDIO_ONLY_SOURCE_TEXT, submit_audio_only


class RuntimeStub:
    def __init__(self):
        self.calls = []

    def submit(self, text, *, audio_window=None):
        self.calls.append((text, audio_window))
        return "evt-audio-1"


def make_window(**changes):
    value = {
        "pcm16": b"\x01\x00" * 160,
        "sample_rate": 16000,
        "start_ms": 120,
        "source_id": "mic-local-1",
        "consent_receipt": "opaque-local-receipt",
        "consent_check": lambda source, receipt: (
            source == "mic-local-1" and receipt == "opaque-local-receipt"
        ),
        "consent_guard": lambda source, receipt: None,
        "consent_revocation_subscribe": lambda *args: (lambda: None),
        "finality": "FINAL",
    }
    value.update(changes)
    return value


def test_audio_only_submits_fixed_no_transcript_marker_and_original_window():
    runtime = RuntimeStub()
    window = make_window()

    event_id = submit_audio_only(runtime, window)

    assert event_id == "evt-audio-1"
    assert runtime.calls == [(AUDIO_ONLY_SOURCE_TEXT, window)]
    assert "no transcript supplied" in AUDIO_ONLY_SOURCE_TEXT
    assert "do not infer or invent spoken words" in AUDIO_ONLY_SOURCE_TEXT


@pytest.mark.parametrize("finality", ["PROVISIONAL", "FINAL"])
def test_audio_only_preserves_provisional_or_final_provenance(finality):
    runtime = RuntimeStub()
    window = make_window(finality=finality)

    submit_audio_only(runtime, window)

    assert runtime.calls[0][1]["finality"] == finality


def test_revoked_or_failing_consent_never_submits():
    runtime = RuntimeStub()
    with pytest.raises(PermissionError, match="not active"):
        submit_audio_only(runtime, make_window(consent_check=lambda *_: False))
    with pytest.raises(PermissionError, match="preflight failed"):
        submit_audio_only(
            runtime,
            make_window(consent_check=lambda *_: (_ for _ in ()).throw(RuntimeError("provider down"))),
        )
    assert runtime.calls == []


def test_two_phase_revocation_subscription_is_mandatory():
    runtime = RuntimeStub()
    window = make_window()
    window["consent_revocation_subscribe"] = None

    with pytest.raises(ValueError, match="two-phase revocation"):
        submit_audio_only(runtime, window)

    assert runtime.calls == []


def test_malformed_or_oversized_pcm_is_rejected_before_submission():
    runtime = RuntimeStub()
    with pytest.raises(ValueError, match="PCM16"):
        submit_audio_only(runtime, make_window(pcm16=b"\x01"))
    with pytest.raises(ValueError, match="one-second"):
        submit_audio_only(runtime, make_window(pcm16=b"\x00\x00" * 16001))
    assert runtime.calls == []


def test_incompatible_runtime_fails_with_an_explicit_contract_error():
    class TextOnlyRuntime:
        def submit(self, text):
            raise AssertionError("must not be called")

    with pytest.raises(RuntimeError, match="staged RAW EAR"):
        submit_audio_only(TextOnlyRuntime(), make_window())
