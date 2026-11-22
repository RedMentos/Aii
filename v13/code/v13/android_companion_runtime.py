"""Local TTY orchestration for the separate Android companion.

No model or chat-turn path can invoke this module: operator.py gates it to
OPERATOR_TTY. The companion independently pairs Termux, requires a visible
per-action approval, and signs a non-authoritative receipt.
"""
from __future__ import annotations

import base64
import hashlib
import json
import re
import time
from pathlib import Path

from .android_control import AndroidControlBroker, ControlDenied
from .android_companion_transport import AndroidCompanionTransport, CompanionTransportError
from .android_companion_ecdsa import ECDSAReceiptVerifier
from .android_outcomes import accept_and_persist_companion_receipt
from .contracts import packet
from .common import atomic_write, dumps


_HELP = (
    ":android status|capabilities|pair|trust <key-id> --confirm|"
    "launch <package> --confirm|poll <action-id>|cancel <action-id>|pending|history [1..50]|stop"
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
        if hashlib.sha256(point).hexdigest() != info["key_id"]:
            raise ControlDenied("companion public-key fingerprint mismatch")
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
        try:
            intent = packet(
                "ActionIntent", "C5_ANDROID_COMPANION", event["event_id"],
                event["brain_generation_id"], [event["source_ref"]],
                action_id=proposal.action_id, action_type="launch_app",
                permission="OPERATOR_TTY_AND_ANDROID_COMPANION_UI",
            )
            self.runtime.store.add_packet("ActionIntent", intent)
        except Exception:
            self.broker.cancel(proposal.action_id)
            raise
        self.broker.approve(proposal.action_id, confirmed_by_local_ui=True)
        envelope = self.broker.dispatch_approved(proposal.action_id)
        try:
            response = self.transport.submit(envelope)
            if (response.get("status") != "PENDING_USER_APPROVAL"
                    or response.get("action_id") != proposal.action_id):
                raise ControlDenied("companion did not acknowledge the exact action id")
        except Exception as submit_exc:
            # A timeout can happen after Android committed the request. Only a
            # matching, explicit remote CANCELLED receipt permits local finalization.
            try:
                remote_cancel = self.transport.cancel(proposal.action_id)
            except Exception as cancel_exc:
                remote_cancel = {"status": "UNAVAILABLE", "error": type(cancel_exc).__name__}
            if (remote_cancel.get("status") == "CANCELLED"
                    and remote_cancel.get("action_id") == proposal.action_id):
                self.broker.cancel(proposal.action_id)
                raise
            self.broker.mark_submit_uncertain(proposal.action_id)
            return dumps({
                "status": "SUBMIT_UNCERTAIN",
                "action_id": proposal.action_id,
                "package": package,
                "submit_error": type(submit_exc).__name__,
                "companion_cancel": remote_cancel,
                "next": ":android poll " + proposal.action_id,
            })
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
        state = self.broker.action_state(action_id)
        if state in {"RECEIPT_VERIFIED", "RECEIPT_REJECTED", "CANCELLED", "EXPIRED", "DROPPED_ON_RESTART"}:
            return dumps({"status": "ALREADY_FINAL", "action_id": action_id, "action_state": state})
        trust, public_key, _ = self._pinned_key()
        self.broker.start()
        response = self.transport.outcome(action_id)
        if response.get("status") != "READY":
            if state == "SUBMIT_UNCERTAIN":
                return dumps({
                    "status": "SUBMIT_UNCERTAIN",
                    "action_id": action_id,
                    "companion_status": response.get("status", "UNKNOWN"),
                    "next": ":android cancel " + action_id + " after checking the companion",
                })
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
        state = self.broker.action_state(action_id)
        if state == "RECEIPT_CONSUMED":
            return dumps({
                "status": "RECEIPT_PENDING_STORE",
                "action_id": action_id,
                "next": "retry :android poll; the signed receipt has already been consumed",
            })
        if state in {"DISPATCHED", "SUBMIT_UNCERTAIN"}:
            try:
                remote = self.transport.cancel(action_id)
            except Exception as exc:
                remote = {"status": "UNAVAILABLE", "error": type(exc).__name__}
            if (remote.get("status") == "CANCELLED"
                    and remote.get("action_id") == action_id):
                local = self.broker.cancel(action_id)
                return dumps({"status": "CANCELLED", "local_cancelled": local, "companion": remote})
            self.broker.mark_submit_uncertain(action_id)
            return dumps({"status": "SUBMIT_UNCERTAIN", "action_id": action_id,
                          "local_cancelled": False, "companion": remote})
        local = self.broker.cancel(action_id)
        return dumps({"status": "CANCELLED_LOCAL_ONLY", "local_cancelled": local,
                      "companion": "NOT_DISPATCHED"})

    def pending(self):
        return dumps(self.transport.pending())

    def history(self, limit=20):
        """Read-only current-session C5 journal with exact event/source joins."""
        if type(limit) is not int or isinstance(limit, bool) or not 1 <= limit <= 50:
            raise ValueError("history limit must be an integer from 1 to 50")
        session = self.runtime.session
        if not session:
            return dumps({"status": "OK", "session_scoped": True, "count": 0, "actions": []})
        intent_rows = self.runtime.store.rows(
            "SELECT p.payload,p.created,p.event_id AS packet_event_id,"
            "e.brain_generation_id AS event_generation_id,e.packet AS event_packet "
            "FROM packets p JOIN events e ON e.id=p.event_id "
            "WHERE p.kind='ActionIntent' AND e.session_id=? ORDER BY p.rowid DESC LIMIT ?",
            (session, limit),
        )
        outcome_rows = self.runtime.store.rows(
            "SELECT p.payload,p.created,p.event_id AS packet_event_id,"
            "e.brain_generation_id AS event_generation_id,e.packet AS event_packet "
            "FROM packets p JOIN events e ON e.id=p.event_id "
            "WHERE p.kind='ActionOutcome' AND e.session_id=? ORDER BY p.rowid DESC LIMIT ?",
            (session, limit * 4),
        )
        actions = {}
        bindings = {}
        for row in intent_rows:
            try:
                value = json.loads(row["payload"])
                event = json.loads(row["event_packet"])
            except (TypeError, ValueError):
                continue
            if value.get("producer_component") != "C5_ANDROID_COMPANION":
                continue
            action_id = value.get("action_id")
            if (type(action_id) is not str or len(action_id) != 32
                    or any(ch not in "0123456789abcdef" for ch in action_id)):
                continue
            event_id = row["packet_event_id"]
            generation_id = row["event_generation_id"]
            source_ref = event.get("source_ref")
            provenance = value.get("provenance")
            if (type(event_id) is not str or type(generation_id) is not str
                    or value.get("event_id") != event_id
                    or value.get("brain_generation_id") != generation_id
                    or event.get("event_id") != event_id
                    or event.get("brain_generation_id") != generation_id
                    or not isinstance(source_ref, dict)
                    or not isinstance(source_ref.get("source_id"), str)
                    or provenance != [source_ref]
                    or value.get("action_type") != "launch_app"
                    or value.get("permission") != "OPERATOR_TTY_AND_ANDROID_COMPANION_UI"
                    or action_id in actions):
                continue
            try:
                action_state = self.broker.action_state(action_id)
            except Exception:
                action_state = None
            bindings[action_id] = {
                "event_id": event_id,
                "brain_generation_id": generation_id,
                "source_ref": source_ref,
                "provenance": provenance,
                "action_type": value["action_type"],
            }
            actions[action_id] = {
                "action_id": action_id,
                "event_id": event_id,
                "action_type": value["action_type"],
                "permission": value["permission"],
                "action_state": action_state or "UNKNOWN",
                "outcome_status": None,
                "observed": False,
                "evidence_level": "NO_COMPANION_RECEIPT",
                "t8_authoritative": False,
                "world_learning_eligible": False,
                "created": row["created"],
            }
        allowed_statuses = {
            "COMPANION_ATTESTED_NOT_DEVICE_VERIFIED",
            "COMPANION_USER_DENIED",
            "COMPANION_DISPATCH_FAILED",
            "COMPANION_OUTCOME_UNKNOWN",
        }
        for row in outcome_rows:
            try:
                value = json.loads(row["payload"])
                event = json.loads(row["event_packet"])
            except (TypeError, ValueError):
                continue
            actual = value.get("actual")
            if (value.get("producer_component") != "C5_ANDROID_COMPANION"
                    or not isinstance(actual, dict)
                    or actual.get("outcome_kind") != "ANDROID_COMPANION_RECEIPT"
                    or actual.get("observed") is not False
                    or actual.get("evidence_level") != "COMPANION_RECEIPT_ONLY"
                    or actual.get("t8_authoritative") is not False
                    or actual.get("world_learning_eligible") is not False
                    or actual.get("trusted_transition_eligible") is not False
                    or value.get("status") not in allowed_statuses
                    or type(value.get("action_id")) is not str):
                continue
            action_id = value["action_id"]
            entry = actions.get(action_id)
            binding = bindings.get(action_id)
            if entry is None or binding is None:
                continue
            event_id = row["packet_event_id"]
            generation_id = row["event_generation_id"]
            if (value.get("event_id") != event_id
                    or value.get("brain_generation_id") != generation_id
                    or event.get("event_id") != event_id
                    or event.get("brain_generation_id") != generation_id
                    or event_id != binding["event_id"]
                    or generation_id != binding["brain_generation_id"]
                    or event.get("source_ref") != binding["source_ref"]
                    or value.get("provenance") != binding["provenance"]
                    or value.get("provenance") != [event.get("source_ref")]
                    or actual.get("capability") != binding["action_type"]):
                continue
            entry.update(
                outcome_status=value["status"],
                observed=False,
                evidence_level="COMPANION_RECEIPT_ONLY",
                t8_authoritative=False,
                world_learning_eligible=False,
            )
        ordered = sorted(actions.values(), key=lambda item: item.get("created", 0), reverse=True)[:limit]
        return dumps({
            "status": "OK",
            "session_scoped": True,
            "count": len(ordered),
            "actions": ordered,
            "claim_limit": "Companion receipts attest dispatch/consent only; they are not device observation or T8 learning evidence.",
        })

    def stop(self):
        remote = {"status": "UNAVAILABLE"}
        try:
            pending_response = self.transport.pending()
            if pending_response.get("status") != "OK":
                remote = {"status": "UNAVAILABLE", "reason": "PENDING_STATUS_UNCONFIRMED"}
            else:
                results = []
                for item in pending_response.get("pending", []):
                    action_id = item.get("action_id")
                    if type(action_id) is not str or re.fullmatch(r"[0-9a-f]{32}", action_id) is None:
                        continue
                    try:
                        result = self.transport.cancel(action_id)
                    except Exception as exc:
                        result = {"status": "UNAVAILABLE", "error": type(exc).__name__}
                    results.append(result)
                    if (result.get("status") == "CANCELLED"
                            and result.get("action_id") == action_id):
                        try:
                            self.broker.cancel(action_id)
                        except ControlDenied:
                            pass
                    else:
                        try:
                            self.broker.mark_submit_uncertain(action_id)
                        except ControlDenied:
                            pass
                remote = {"status": "CANCEL_ATTEMPTED", "results": results}
        except Exception as exc:
            remote = {"status": "UNAVAILABLE", "reason": type(exc).__name__}
        self.broker.stop()
        uncertain = sorted(
            action_id for action_id in self.broker.dispatched
            if self.broker.action_state(action_id) == "SUBMIT_UNCERTAIN"
        )
        return dumps({
            "status": "LOCAL_BROKER_STOPPED",
            "companion_cancellations": remote,
            "uncertain_action_ids": uncertain,
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
    if command == "history" and len(args) in (1, 2):
        try:
            limit = int(args[1]) if len(args) == 2 else 20
        except (TypeError, ValueError, OverflowError):
            raise ValueError(_HELP) from None
        return controller.history(limit)
    if command == "stop" and len(args) == 1:
        return controller.stop()
    raise ValueError(_HELP)
