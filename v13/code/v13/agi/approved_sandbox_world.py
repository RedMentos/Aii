"""Opt-in WP-K sandbox_note -> F3/F4 Self/World binding (Run536).

Not attached to production Runtime, operator, or model routes. The caller must
explicitly construct this object, enable the existing tool, propose and
approve from a trusted local operator. The underlying ToolRegistry enforces
its original per-call approval, hard prohibitions and Age policy.
"""
import hashlib
from pathlib import Path
import time

from .file_world_port import SandboxWorldPort
from .tools import ToolRegistry
from ..selfmodel import controller as self_controller
from ..transaction import NAME


class ApprovedSandboxWorldSession:
    """One-event, manually driven actual sandbox-note observation session."""

    def __init__(self, runtime, event_id):
        self.runtime = runtime
        self.event_id = event_id
        row = runtime.store.one("SELECT session_id FROM events WHERE id=?", (event_id,))
        if not row or row["session_id"] != runtime.session:
            raise ValueError("Self/World binding requires an existing current-session event")
        self.port = SandboxWorldPort(Path(runtime.store.home) / "data" / "tool_sandbox")
        self.selfsys = self_controller(runtime)
        self._issued = {}
        self._collected = set()
        # New explicitly scoped registry; never replaces the live hub's hooks.
        self.registry = ToolRegistry(runtime.store, on_pre_execute=self._pre_effect)

    def _pre_effect(self, tx):
        """ToolRegistry invokes only after durable COPY_COMMITTED, before effect."""
        if tx.get("tool") != "sandbox_note" or tx.get("event_id") != self.event_id:
            return None
        args = tx.get("args") or {}
        name, value = args.get("name"), args.get("text")
        action_tx = tx.get("action_tx")
        if (not isinstance(name, str) or NAME.fullmatch(name) is None
                or not isinstance(value, str) or not isinstance(action_tx, str)):
            return None
        expected = hashlib.sha256(value.encode("utf-8")).hexdigest()
        packet = self.selfsys.issue(
            self.event_id, action_tx, "approved sandbox_note local write",
            [{"channel": "file:" + name, "value": expected},
             {"channel": "status:" + name, "value": "EXECUTED"}],
            affected=["listing"], uncertainty=0.2, window_s=30)
        self._issued[action_tx] = name
        return packet["packet_id"]

    def propose(self, name, text):
        """A proposal only; this method never approves or enables a tool."""
        return self.registry.call("sandbox_note", {"name": name, "text": text},
                                  origin="USER", event_id=self.event_id)

    def approve(self, tx_id, *, origin):
        """Only a trusted local operator may explicitly call the approval path."""
        if origin != "OPERATOR_TTY":
            raise ValueError("only local operator approval may enter this binding")
        tx = self.registry.approve(tx_id)
        if tx["status"] not in ("EXECUTED", "FAILED"):
            return {"status": tx["status"], "action_tx": tx.get("action_tx"),
                    "observations": [], "authority": "SHADOW_ONLY"}
        return self.collect(tx)

    def collect(self, tx):
        """Explicitly collect actual effects; never infer execution from input."""
        if not isinstance(tx, dict) or tx.get("tool") != "sandbox_note" or tx.get("event_id") != self.event_id:
            raise ValueError("wrong event/tool for Self/World collection")
        saved = next((c for c in self.registry.box.load()[0]["calls"] if c["id"] == tx.get("id")), None)
        if (not saved or saved.get("status") != tx.get("status")
                or saved.get("action_tx") != tx.get("action_tx")
                or saved.get("status") not in ("EXECUTED", "FAILED")):
            raise ValueError("unverified completed WP-K transaction")
        action_tx = saved["action_tx"]
        if action_tx in self._collected:
            raise ValueError("Self/World outcome already collected")
        # Real file changes first. If scanning fails, retain baseline and do
        # not claim completion; the operator can correct and explicitly retry.
        issued = action_tx in self._issued
        if issued:
            # Attribute the real scan and verified status in one call. The
            # port commits its baseline only after SelfSystem returns; a
            # corrupt state before attribution must not lose the file change.
            name = saved["args"].get("name")
            rows = self.port.observe(
                self.selfsys, self.event_id,
                extra_observations=[
                    {"channel": "status:" + name, "value": saved["status"], "t": time.time()}],
                close=[action_tx])
        else:
            # The tool may execute even if its optional pre-effect hook failed.
            # Never attribute that action using an unrelated old corollary.
            # Consume the real scan, but do not write false Self packets.
            rows = [
                {"channel": o["channel"], "class": "UNCLEAR",
                 "reason": "no_current_corollary", "action_ids": []}
                for o in self.port.poll()
            ]
        self._collected.add(action_tx)
        return {"status": saved["status"], "action_tx": action_tx,
                "authority": "SHADOW_ONLY", "observations": [
                    {"channel": x["channel"], "class": x["class"],
                     "reason": x["reason"], "action_ids": x["action_ids"]}
                    for x in rows],
                "corollary_issued": issued, "learning_authorized": False,
                "age_reopen_authorized": False, "phone_measured": False}
