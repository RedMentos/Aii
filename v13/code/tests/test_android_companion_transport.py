import base64
import json
import subprocess

import pytest

from v13.android_companion_transport import AndroidCompanionTransport, CompanionTransportError


def response(value):
    payload = base64.b64encode(json.dumps(value).encode()).decode()
    return f"Result: Bundle[{{payload_b64={payload}}}]"


def test_submit_uses_fixed_content_provider_and_no_shell():
    seen = []
    request = {
        "schema": "v14.android-action-request/1",
        "action_id": "a" * 32,
        "capability": "launch_app",
        "args": {"package": "com.example.app"},
        "digest": "b" * 64,
        "expires_at": 1030.0,
        "local_approval": "CALLER_ASSERTED_LOCAL_UI_CONFIRMATION",
        "companion_local_consent_required": True,
        "android_os_permission_required": False,
        "permission_bypass": False,
        "model_authority": False,
    }

    def runner(command, **kwargs):
        seen.append((command, kwargs))
        return subprocess.CompletedProcess(command, 0, response({
            "status": "PENDING_USER_APPROVAL", "action_id": request["action_id"]
        }), "")

    client = AndroidCompanionTransport(content_path="/system/bin/content", runner=runner)
    assert client.submit(request) == {"status": "PENDING_USER_APPROVAL", "action_id": request["action_id"]}
    command, kwargs = seen[0]
    assert command[:6] == [
        "/system/bin/content", "call", "--uri",
        "content://com.redmentos.v14.companion", "--method", "submit"
    ]
    assert "--arg" in command
    encoded = command[command.index("--arg") + 1]
    sent = json.loads(base64.b64decode(encoded).decode("utf-8"))
    assert sent["companion_local_consent_required"] is True
    assert sent["android_os_permission_required"] is False
    assert kwargs["timeout"] == 4.0
    assert kwargs["check"] is False
    assert "shell" not in kwargs


def test_outcome_requires_hex_action_id_and_decodes_signed_receipt():
    receipt = {"body": {"status": "DISPATCHED_UNVERIFIED"}, "key_id": "c" * 64, "signature": "AA=="}

    def runner(command, **kwargs):
        return subprocess.CompletedProcess(command, 0, response({"status": "READY", "receipt": receipt}), "")

    client = AndroidCompanionTransport(content_path="/system/bin/content", runner=runner)
    assert client.outcome("d" * 32)["receipt"] == receipt
    with pytest.raises(CompanionTransportError, match="action id"):
        client.outcome("../bad")


def test_missing_binary_timeout_and_bad_envelope_fail_closed():
    missing = AndroidCompanionTransport(content_path=None, runner=lambda *a, **k: None)
    with pytest.raises(CompanionTransportError, match="unavailable"):
        missing.capabilities()

    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], kwargs["timeout"])

    client = AndroidCompanionTransport(content_path="/system/bin/content", runner=timeout)
    with pytest.raises(CompanionTransportError, match="TimeoutExpired"):
        client.capabilities()

    malformed = AndroidCompanionTransport(
        content_path="/system/bin/content",
        runner=lambda command, **kwargs: subprocess.CompletedProcess(command, 0, "no bundle", ""),
    )
    with pytest.raises(CompanionTransportError, match="envelope"):
        malformed.capabilities()


def test_model_authority_and_permission_bypass_are_rejected_before_ipc():
    client = AndroidCompanionTransport(
        content_path="/system/bin/content",
        runner=lambda *a, **k: pytest.fail("must not call Android"),
    )
    request = {
        "schema": "v14.android-action-request/1",
        "permission_bypass": True,
        "model_authority": False,
    }
    with pytest.raises(CompanionTransportError, match="authority"):
        client.submit(request)



def test_cancel_uses_only_paired_companion_method():
    seen = []

    def runner(command, **kwargs):
        seen.append(command)
        return subprocess.CompletedProcess(command, 0, response({"status": "CANCELLED"}), "")

    client = AndroidCompanionTransport(content_path="/system/bin/content", runner=runner)
    assert client.cancel("e" * 32)["status"] == "CANCELLED"
    assert seen[0][5] == "cancel"
    with pytest.raises(CompanionTransportError, match="action id"):
        client.cancel("bad")



@pytest.mark.parametrize("ack", [
    {"status": "PENDING_USER_APPROVAL"},
    {"status": "PENDING_USER_APPROVAL", "action_id": "f" * 32},
])
def test_submit_rejects_missing_or_mismatched_action_acknowledgement(ack):
    request = {
        "schema": "v14.android-action-request/1",
        "action_id": "a" * 32,
        "capability": "launch_app",
        "args": {"package": "com.example.app"},
        "digest": "b" * 64,
        "expires_at": 1030.0,
        "local_approval": "CALLER_ASSERTED_LOCAL_UI_CONFIRMATION",
        "companion_local_consent_required": True,
        "android_os_permission_required": False,
        "permission_bypass": False,
        "model_authority": False,
    }

    client = AndroidCompanionTransport(
        content_path="/system/bin/content",
        runner=lambda command, **kwargs: subprocess.CompletedProcess(
            command, 0, response(ack), ""
        ),
    )
    with pytest.raises(CompanionTransportError, match="action id mismatch"):
        client.submit(request)
