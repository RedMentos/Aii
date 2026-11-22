import pytest

from v13.audio_input import (
    AUDIO_ONLY_SOURCE_TEXT,
    AUDIO_WINDOW_RUNTIME_CONTRACT,
    SecurePCMBuffer,
    submit_audio_only,
)


class RuntimeStub:
    audio_window_contract_version = AUDIO_WINDOW_RUNTIME_CONTRACT

    def __init__(self):
        self.calls = []

    def submit(self, text, *, audio_window=None):
        self.calls.append((text, audio_window))
        return "evt-audio-1"


def make_window(**changes):
    value = {
        "pcm16": SecurePCMBuffer(b"\\x01\\x00" * 160),
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


def test_audio_only_submits_fixed_no_transcript_marker_and_transfers_same_buffer():
    runtime = RuntimeStub()
    window = make_window()
    pcm = window["pcm16"]

    event_id = submit_audio_only(runtime, window)

    assert event_id == "evt-audio-1"
    assert runtime.calls == [(AUDIO_ONLY_SOURCE_TEXT, window)]
    assert runtime.calls[0][1]["pcm16"] is pcm
    assert pcm.zeroized is False
    assert "no transcript supplied" in AUDIO_ONLY_SOURCE_TEXT
    assert "do not infer or invent spoken words" in AUDIO_ONLY_SOURCE_TEXT
    pcm.zeroize()


@pytest.mark.parametrize("finality", ["PROVISIONAL", "FINAL"])
def test_audio_only_preserves_provisional_or_final_provenance(finality):
    runtime = RuntimeStub()
    window = make_window(finality=finality)

    submit_audio_only(runtime, window)

    assert runtime.calls[0][1]["finality"] == finality
    window["pcm16"].zeroize()


def test_revoked_consent_never_submits_and_wipes_buffer():
    runtime = RuntimeStub()
    window = make_window(consent_check=lambda *_: False)
    pcm = window["pcm16"]

    with pytest.raises(PermissionError, match="not active"):
        submit_audio_only(runtime, window)

    assert runtime.calls == []
    assert pcm.zeroized is True
    assert not any(pcm)


def test_runtime_without_audio_contract_rejects_and_wipes_before_submit():
    class LegacyRuntime:
        def submit(self, text):
            pytest.fail("legacy Runtime must not receive raw PCM")

    window = make_window()
    pcm = window["pcm16"]

    with pytest.raises(RuntimeError, match="does not implement"):
        submit_audio_only(LegacyRuntime(), window)

    assert pcm.zeroized is True
    assert not any(pcm)


def test_runtime_must_explicitly_accept_audio_window_not_just_kwargs():
    class KwargsRuntime:
        audio_window_contract_version = AUDIO_WINDOW_RUNTIME_CONTRACT

        def submit(self, text, **kwargs):
            pytest.fail("a generic **kwargs sink is not an accepted audio consumer")

    window = make_window()
    pcm = window["pcm16"]

    with pytest.raises(RuntimeError, match="explicit audio_window"):
        submit_audio_only(KwargsRuntime(), window)

    assert pcm.zeroized is True
    assert not any(pcm)


def test_immutable_pcm_is_rejected_without_claiming_zeroization():
    runtime = RuntimeStub()
    window = make_window(pcm16=b"\\x01\\x00" * 160)

    with pytest.raises(ValueError, match="SecurePCMBuffer"):
        submit_audio_only(runtime, window)

    assert runtime.calls == []


def test_secure_buffer_repr_is_redacted_and_zeroize_is_idempotent():
    pcm = SecurePCMBuffer(b"\\x01\\x02\\x03\\x04")

    assert "SecurePCMBuffer" in repr(pcm)
    assert "\\x01" not in repr(pcm)
    assert "zeroized=False" in str(pcm)
    assert pcm.zeroize() == 4
    assert pcm.zeroized is True
    assert bytes(pcm) == bytes(4)
    assert pcm.zeroize() == 4
    assert pcm.zeroized is True
