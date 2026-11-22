import base64
import json
from types import SimpleNamespace

import pytest

from v13.android_companion_transport import (
    AndroidCompanionTransport,
    CompanionTransportError,
    MAX_FRAME_BYTES,
)


def test_read_frame_uses_only_paired_provider_uri_and_binary_content_read():
    frame = b"\\xff\\xd8fixture\\xff\\xd9"
    calls = []

    def runner(command, **kwargs):
        calls.append((command, kwargs))
        return SimpleNamespace(returncode=0, stdout=frame, stderr=b"")

    transport = AndroidCompanionTransport(content_path="/system/bin/content", runner=runner)
    uri = "content://com.redmentos.v14.companion/ui-frame/" + "a" * 32
    assert transport.read_frame(uri, max_bytes=len(frame)) == frame
    command, kwargs = calls[0]
    assert command == ["/system/bin/content", "read", "--uri", uri]
    assert kwargs["text"] is False
    assert kwargs["timeout"] >= 10.0


def test_read_frame_rejects_arbitrary_uri_and_unbounded_size():
    transport = AndroidCompanionTransport(content_path="/system/bin/content")
    with pytest.raises(CompanionTransportError, match="URI"):
        transport.read_frame("content://attacker.example/secret/" + "a" * 32)
    with pytest.raises(CompanionTransportError, match="bound"):
        transport.read_frame(
            "content://com.redmentos.v14.companion/ui-frame/" + "a" * 32,
            max_bytes=MAX_FRAME_BYTES + 1,
        )


def test_read_frame_rejects_oversized_or_empty_payload():
    uri = "content://com.redmentos.v14.companion/ui-frame/" + "b" * 32

    def oversized(command, **kwargs):
        return SimpleNamespace(returncode=0, stdout=b"x" * 9, stderr=b"")

    transport = AndroidCompanionTransport(content_path="/system/bin/content", runner=oversized)
    with pytest.raises(CompanionTransportError, match="byte length"):
        transport.read_frame(uri, max_bytes=8)

    def empty(command, **kwargs):
        return SimpleNamespace(returncode=0, stdout=b"", stderr=b"")

    transport = AndroidCompanionTransport(content_path="/system/bin/content", runner=empty)
    with pytest.raises(CompanionTransportError, match="byte length"):
        transport.read_frame(uri)


def test_screen_frame_status_uses_fixed_content_provider_method():
    payload = {"status": "FRAME_READY", "expires_in_ms": 1000}
    encoded = base64.b64encode(json.dumps(payload).encode("utf-8")).decode("ascii")
    calls = []

    def runner(command, **kwargs):
        calls.append(command)
        return SimpleNamespace(returncode=0, stdout="payload_b64=" + encoded, stderr="")

    transport = AndroidCompanionTransport(content_path="/system/bin/content", runner=runner)
    assert transport.screen_frame_status() == payload
    assert calls == [
        ["/system/bin/content", "call", "--uri",
         "content://com.redmentos.v14.companion", "--method", "screen_frame_status"]
    ]
