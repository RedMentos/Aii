"""Local TTY orchestration for the separate Android companion.

No model or chat-turn path can invoke this module: operator.py gates it to
OPERATOR_TTY. The companion independently pairs Termux, requires a visible
per-action approval, and signs a non-authoritative receipt.
"""
from __future__ import annotations

import base64
import json
import re
import time
from pathlib import Path

from .android_control import AndroidControlBroker, ControlDenied
from .android_companion_transport import AndroidCompanionTransport, CompanionTransportError
from .android_companion_ecdsa import ECDSAReceiptVerifier
from .android_outcomes import accept_and_persist_companion_receipt
from .common import atomic_write, dumps


_HELP = (
    ":android status|capabilities|pair|trust <key-id> --confirm|"
    "launch <package> --confirm|poll <action-id>|cancel <action-id>|pending|stop"
)


class AndroidCompanionController:
    def __init__(self, runtime, *, transport=None, clock=None):
        self.runtime = runtime
        self.home = Path(runtime.home)
        self.db_dir = self.home / "data" / "db"
        self.db_dir.mkdir(parents=True, exist_ok=True)
        self.clock = clock or time.time
        self.transport = transport or AndroidCompanionTransport()
        self.broker = AndroidControlBroker(self.db_dir / "android_control.sqlite", clock=self.clock)
        self.trust_path = self.db_dir / "android_companion_trust.json"
        self.verifier_path = self.db_dir / "android_companion_receipts.sqlite"

    def _provider_key(self):
        info = self.transport.public_key()
        if (info.get("schema") != "v14.android-companion-public-key/1"
                or info.get("algorithm") != "ECDSA_P256_SHA256"
                or type(info.get("key_id")) is not str
                or not re.fullmatch(r"[0-9a-f]{64}", info["key_id"])
                or type(info.get("public_key_sec1_base64")) is not str):
            raise ControlDenied("companion public key unavailable or malformed")
        try:
            point = base64.b64decode(info["public_key_sec1_base64"], validate=True)
        except Exception as exc:
            raise ControlDenied("companion public key encoding invalid") from exc
        if len(point) != 65 or point[0] != 4:
            raise ControlDenied("companion public key is not P-256 SEC1")
        return info, point

    def _pinned_key(self):
        try:
            trust = json.loads(self.trust_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise ControlDenied("public key not pinned; run :android pair then :android trust <key-id> --confirm") from exc
        if trust.get("schema") != "v14.android-companion-trust/1":
            raise ControlDenied("invalid companion trust record")
        info, point = self._provider_key()
        if (trust.get("key_id") != info["key_id"]
                or trust.get("public_key_sec1_base64") != info["public_key_sec1_base64"]):
            raise ControlDenied("companion key changed; explicit re-pairing required")
        return trust, point, info

    def status(self):
        trust = None
        try:
            trust = json.loads(self.trust_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            pass
        return dumps({
            "status": "LOCAL_COMPANION_CONTROLLER",
            "broker_stopped": self.broker.stopped,
            "pinned_key_id": trust.get("key_id") if trust else None,
            "pending_local": len(self.broker.pending),
            "approved_local": len(self.broker.approved),
            "dispatched_local": len(self.broker.dispatched) + len(self.broker.consumed),
            "android_device_verified": False,
            "redmi_status": "REDMI_UNVERIFIED",
        })

    def capabilities(self):
        return dumps(self.transport.capabilities())

    def pair(self):
        info, _ = self._provider_key()
        return dumps({
            "status": "COMPARE_BEFORE_TRUST",
            "key_id": info["key_id"],
            "key_storage_status": info.get("key_storage_status", "UNVERIFIED"),
            "instruction": "Compare key_id with the fingerprint shown inside the companion app; then type :android trust <key-id> --confirm.",
            "key_auto_trusted": False,
        })

    def trust(self, fingerprint, confirm):
        if confirm is not True:
            raise ControlDenied("explicit :android trust <key-id> --confirm required")
        if type(fingerprint) is not str or not re.fullmatch(r"[0-9a-f]{64}", fingerprint):
            raise ControlDenied("invalid key fingerprint")
        info, _ = self._provider_key()
        if fingerprint != info["key_id"]:
            raise ControlDenied("fingerprint does not match the paired companion")
        trust = {
            "schema": "v14.android-companion-trust/1",
            "key_id": info["key_id"],
            "public_key_sec1_base64": info["public_key_sec1_base64"],
            "key_storage_status": info.get("key_storage_status", "UNVERIFIED"),
            "trusted_at": int(self.clock()),
            "trust_source": "EXPLICIT_LOCAL_OPERATOR_FINGERPRINT",
        }
        atomic_write(self.trust_path, json.dumps(trust, sort_keys=True, separators=(",", ":")))
        return dumps({"status": "PINNED", "key_id": info["key_id"], "automatic_trust": False})

    def launch(self, package, confirm):
        self.runtime.require_idle()
        if confirm is not True:
            raise ControlDenied("explicit :android launch <package> --confirm required")
        if type(package) is not str or len(package) > 180 or not re.fullmatch(r"[A-Za-z0-9_]+(\.[A-Za-z0-9_]+)+", package):
            raise ControlDenied("invalid Android package name")
        self._pinned_key()
        capabilities = self.transport.capabilities()
        if capabilities.get("enabled") is not True or capabilities.get("termux_paired") is not True:
            raise ControlDenied("companion must be paired and enabled in its own Android UI")
        launch_capability = next(
            (item for item in capabilities.get("capabilities", []) if item.get("capability") == "launch_app"),
            None,
        )
        if not launch_capability or launch_capability.get("status") != "READY_WITH_PER_ACTION_CONSENT":
            raise ControlDenied("launch_app capability is not ready")
        self.broker.start()
        session = self.runtime.session or self.runtime.store.new_session()
        event = self.runtime.store.event(session, "Operator requested launch_app package=" + package)
        proposal = self.broker.propose(
            "launch_app", {"package": package}, ttl=30,
            event_id=event["event_id"], source_ref=event["source_ref"],
        )
        self.broker.approve(proposal.action_id, confirmed_by_local_ui=True)
        envelope = self.broker.dispatch_approved(proposal.action_id)
        try:
            response = self.transport.submit(envelope)
            if response.get("status") != "PENDING_USER_APPROVAL":
                self.broker.cancel(proposal.action_id)
                raise ControlDenied("companion did not accept the action request")
        except Exception:
            try:
                self.transport.cancel(proposal.action_id)
            except Exception:
                pass
            try:
                self.broker.cancel(proposal.action_id)
            except Exception:
                pass
            raise
        return dumps({
            "status": "PENDING_USER_APPROVAL",
            "action_id": proposal.action_id,
            "package": package,
            "source_event_id": event["event_id"],
            "companion_approval_required": True,
            "device_execution_claimed": False,
            "next": ":android poll " + proposal.action_id,
        })

    def poll(self, action_id):
        self.runtime.require_idle()
        trust, public_key, _ = self._pinned_key()
        self.broker.start()
        response = self.transport.outcome(action_id)
        if response.get("status") != "READY":
            return dumps(response)
        receipt = response.get("receipt")
        verifier = ECDSAReceiptVerifier(
            self.verifier_path, public_key, trust["key_id"], clock=self.clock
        )
        verifier.start()
        try:
            outcome, packet = accept_and_persist_companion_receipt(
                self.runtime.store, self.broker, verifier, action_id, receipt
            )
        finally:
            verifier.close()
        return dumps({
            "status": outcome.status,
            "packet_id": packet["packet_id"],
            "observed": outcome.observed,
            "t8_authoritative": outcome.details.get("t8_authoritative", False),
            "world_learning_eligible": outcome.details.get("world_learning_eligible", False),
            "receipt_status": outcome.details.get("receipt_status"),
        })

    def cancel(self, action_id):
        local = False
        try:
            local = self.broker.cancel(action_id)
        except ControlDenied:
            pass
        remote = self.transport.cancel(action_id)
        return dumps({"status": "CANCEL_REQUESTED", "local_cancelled": local, "companion": remote})

    def pending(self):
        return dumps(self.transport.pending())

    def stop(self):
        remote = {"status": "UNAVAILABLE"}
        try:
            pending = self.transport.pending().get("pending", [])
            results = []
            for item in pending:
                action_id = item.get("action_id")
                if type(action_id) is str and re.fullmatch(r"[0-9a-f]{32}", action_id):
                    results.append(self.transport.cancel(action_id))
            remote = {"status": "CANCEL_ATTEMPTED", "results": results}
        except CompanionTransportError as exc:
            remote = {"status": "UNAVAILABLE", "reason": str(exc)}
        self.broker.stop()
        return dumps({
            "status": "LOCAL_BROKER_STOPPED",
            "companion_cancellations": remote,
            "companion_app_stop_switch": "separate; open the Android companion UI if needed",
        })


def _controller(runtime):
    current = getattr(runtime, "_android_companion_controller", None)
    if current is None:
        current = AndroidCompanionController(runtime)
        runtime._android_companion_controller = current
    return current


def operator_command(runtime, args):
    if not args or args[0] == "help":
        return _HELP
    command = args[0].lower()
    controller = _controller(runtime)
    if command == "status" and len(args) == 1:
        return controller.status()
    if command == "capabilities" and len(args) == 1:
        return controller.capabilities()
    if command == "pair" and len(args) == 1:
        return controller.pair()
    if command == "trust" and len(args) == 3 and args[2] == "--confirm":
        return controller.trust(args[1], True)
    if command == "launch" and len(args) == 3 and args[2] == "--confirm":
        return controller.launch(args[1], True)
    if command == "poll" and len(args) == 2:
        return controller.poll(args[1])
    if command == "cancel" and len(args) == 2:
        return controller.cancel(args[1])
    if command == "pending" and len(args) == 1:
        return controller.pending()
    if command == "stop" and len(args) == 1:
        return controller.stop()
    raise ValueError(_HELP)
