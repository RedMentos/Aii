"""Narrow Termux ContentProvider client for the separately installed Android companion.

This module invokes only the fixed Android `content call` command, without a
shell. It cannot approve, execute, or grant an action; the companion UI does that.
The screen-frame read is a one-use pipe from the paired companion and is bounded
to the signed MediaProjection receipt's maximum size.
"""
from __future__ import annotations

import base64
import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Callable


URI = "content://com.redmentos.v14.companion"
MAX_FRAME_BYTES = 8 * 1024 * 1024
_FRAME_URI = re.compile(r"content://com\.redmentos\.v14\.companion/ui-frame/([0-9a-f]{32})\Z")
_PAYLOAD = re.compile(r"payload_b64=([A-Za-z0-9+/=]+)")


class CompanionTransportError(RuntimeError):
    pass


class AndroidCompanionTransport:
    def __init__(
        self,
        *,
        content_path: str | Path | None = None,
        timeout: float = 4.0,
        runner: Callable = subprocess.run,
    ):
        if not 0.1 <= float(timeout) <= 10.0:
            raise ValueError("companion timeout must be 0.1..10 seconds")
        if content_path is None:
            content_path = "/system/bin/content"
            if not Path(content_path).is_file():
                content_path = shutil.which("content")
        self.content_path = str(content_path) if content_path else None
        self.timeout = float(timeout)
        self.runner = runner

    def _call(self, method: str, value: str | None = None) -> dict:
        if self.content_path is None:
            raise CompanionTransportError("Android content command unavailable")
        if method not in {
            "capabilities", "public_key", "submit", "outcome", "pending",
            "cancel", "screen_frame_status",
        }:
            raise CompanionTransportError("unsupported companion method")
        command = [self.content_path, "call", "--uri", URI, "--method", method]
        if value is not None:
            encoded = base64.b64encode(value.encode("utf-8")).decode("ascii")
            command.extend(["--arg", encoded])
        try:
            result = self.runner(
                command, capture_output=True, text=True, timeout=self.timeout, check=False
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise CompanionTransportError(type(exc).__name__) from exc
        if result.returncode != 0:
            raise CompanionTransportError("Android content call failed")
        output = (result.stdout or "") + "\n" + (result.stderr or "")
        if len(output) > 65536:
            raise CompanionTransportError("companion response too large")
        match = _PAYLOAD.search(output)
        if not match:
            raise CompanionTransportError("companion response envelope missing")
        try:
            raw = base64.b64decode(match.group(1), validate=True)
            decoded = json.loads(raw.decode("utf-8"))
        except Exception as exc:
            raise CompanionTransportError("invalid companion response") from exc
        if type(decoded) is not dict:
            raise CompanionTransportError("companion response must be an object")
        return decoded

    def capabilities(self) -> dict:
        return self._call("capabilities")

    def public_key(self) -> dict:
        return self._call("public_key")

    def submit(self, request: dict) -> dict:
        if type(request) is not dict or request.get("schema") != "v14.android-action-request/1":
            raise CompanionTransportError("invalid action request")
        if request.get("permission_bypass") is not False or request.get("model_authority") is not False:
            raise CompanionTransportError("request authority must remain zero")
        action_id = request.get("action_id")
        if type(action_id) is not str or not re.fullmatch(r"[0-9a-f]{32}", action_id):
            raise CompanionTransportError("invalid action id")
        payload = json.dumps(request, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        response = self._call("submit", payload)
        if (response.get("status") != "PENDING_USER_APPROVAL"
                or response.get("action_id") != action_id):
            raise CompanionTransportError("companion acknowledgement action id mismatch")
        return response

    def outcome(self, action_id: str) -> dict:
        if type(action_id) is not str or not re.fullmatch(r"[0-9a-f]{32}", action_id):
            raise CompanionTransportError("invalid action id")
        return self._call("outcome", action_id)

    def cancel(self, action_id: str) -> dict:
        if type(action_id) is not str or not re.fullmatch(r"[0-9a-f]{32}", action_id):
            raise CompanionTransportError("invalid action id")
        return self._call("cancel", action_id)

    def pending(self) -> dict:
        return self._call("pending")

    def screen_frame_status(self) -> dict:
        """Read metadata for the current one-shot frame; does not consume its bytes."""
        return self._call("screen_frame_status")

    def read_frame(self, frame_uri: str, *, max_bytes: int = MAX_FRAME_BYTES) -> bytes:
        """Read exactly one paired ContentProvider frame pipe, never an arbitrary URI."""
        if self.content_path is None:
            raise CompanionTransportError("Android content command unavailable")
        if type(max_bytes) is not int or not 1 <= max_bytes <= MAX_FRAME_BYTES:
            raise CompanionTransportError("invalid frame byte bound")
        match = _FRAME_URI.fullmatch(frame_uri) if isinstance(frame_uri, str) else None
        if not match:
            raise CompanionTransportError("invalid one-shot frame URI")
        command = [self.content_path, "read", "--uri", frame_uri]
        try:
            result = self.runner(
                command, capture_output=True, text=False,
                timeout=max(self.timeout, 10.0), check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise CompanionTransportError(type(exc).__name__) from exc
        if result.returncode != 0:
            raise CompanionTransportError("Android one-shot frame read failed")
        raw = result.stdout or b""
        if isinstance(raw, str):
            raw = raw.encode("latin-1", errors="strict")
        if type(raw) is not bytes or not 1 <= len(raw) <= max_bytes:
            raise CompanionTransportError("one-shot frame byte length is outside the signed bound")
        return raw
