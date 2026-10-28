"""Read-only Store EventEnvelope source integrity adapter for Run19 SHADOW.

A valid USER_TEXT EventEnvelope is NOT an F5 HumanDecision, not a verified
binding rule, and never authorizes a native model, Runtime output or learning.
"""
import hashlib
import json
import re

PROJECT = re.compile(r"\b(?:Projekt|Project)\s+([A-Z][A-Za-z0-9]*)\b")
REVISION = "run24-event-source-message-lineage-shadow-v2"


class Refusal(ValueError):
    pass


class EventSourceReader:
    def __init__(self, store, session, project, roles):
        if (not isinstance(session, str) or not session or
                not isinstance(project, str) or re.fullmatch(r"[A-Za-z]+", project) is None or
                not isinstance(roles, dict) or set(roles) != {"old", "sheet", "current"} or
                any(not isinstance(v, str) or not v for v in roles.values()) or
                len(set(roles.values())) != 3):
            raise Refusal("role_scope_or_identity")
        self.store = store
        self.session = session
        self.project = project
        self.roles = dict(roles)
        self.kind_by_ref = {v: ("current" if k == "current" else "history")
                            for k, v in roles.items()}
        old, sheet, current = (self._load(self.roles[k]) for k in
                               ("old", "sheet", "current"))
        if not old["seq"] < sheet["seq"] < current["seq"]:
            raise Refusal("event_source_order")

    def _load(self, ref):
        if ref not in self.kind_by_ref:
            raise Refusal("unregistered_source_ref")
        event_sql = (
            "SELECT e.rowid AS seq,e.id AS event_id,e.session_id,e.source_id,"
            "e.generation_id,e.experience_id,e.packet,s.deleted,s.hash,"
            "s.bytes,s.chars,s.kind AS source_kind "
            "FROM events e JOIN sources s ON s.id=e.source_id WHERE e.id=?")
        message_sql = (
            "SELECT id,session_id,role,text,status,metadata FROM messages "
            "WHERE event_id=? ORDER BY id")
        row = self.store.one(event_sql, (ref,))
        if (not row or row["session_id"] != self.session or row["deleted"] != 0 or
                row["source_kind"] != "USER" or type(row["seq"]) is not int):
            raise Refusal("event_source_scope_or_revocation")
        try:
            packet = json.loads(row["packet"])
            src = packet["source_ref"]
            if (packet.get("event_id") != ref or
                    packet.get("schema_version") != "1.0" or
                    packet.get("producer_component") != "A0_SOURCE" or
                    packet.get("brain_generation_id") != row["generation_id"] or
                    packet.get("experience_id") != row["experience_id"] or
                    packet.get("authority") != "AUTHORITATIVE" or
                    packet.get("kind") != "USER_TEXT" or
                    not isinstance(src, dict) or
                    set(src) != {"source_id", "sha256", "char_start",
                                 "char_end", "modality"} or
                    packet.get("provenance") != [src] or
                    src.get("source_id") != row["source_id"] or
                    src.get("sha256") != row["hash"] or
                    src.get("char_start") != 0 or
                    src.get("char_end") != row["chars"] or
                    src.get("modality") != "text"):
                raise Refusal("event_packet_source_mismatch")
            # Capture both ends of the Store input lineage before the blob read.
            # A valid event/source alone does not establish an original user turn.
            before_messages = self.store.rows(message_sql, (ref,))
            text = self.store.read_source(src)
        except Refusal:
            raise
        except Exception as exc:
            raise Refusal("event_source_unreadable") from exc
        # Recheck the persisted event/source and user-message snapshots after
        # reading the blob. This detects revocation or metadata changes during
        # the read; it does NOT guarantee the source stays live after return.
        after_row = self.store.one(event_sql, (ref,))
        after_messages = self.store.rows(message_sql, (ref,))
        if after_row != row or after_messages != before_messages:
            raise Refusal("event_lineage_changed_during_read")
        user_messages = [m for m in after_messages if m["role"] == "user"]
        if len(user_messages) != 1:
            raise Refusal("event_user_message_missing_or_ambiguous")
        user = user_messages[0]
        try:
            metadata = json.loads(user["metadata"])
            self.store.generation(row["generation_id"])
        except Exception as exc:
            raise Refusal("event_message_or_generation_unverified") from exc
        if (user["session_id"] != self.session or
                user["status"] != "FINAL" or
                not isinstance(text, str) or user["text"] != text or
                not isinstance(metadata, dict) or
                set(metadata) != {"source_ref"} or
                metadata["source_ref"] != src):
            raise Refusal("event_user_message_source_mismatch")
        if (type(row["bytes"]) is not int or type(row["chars"]) is not int or
                len(text.encode("utf-8")) != row["bytes"] or
                len(text) != row["chars"] or
                hashlib.sha256(text.encode("utf-8")).hexdigest() != row["hash"] or
                {x.lower() for x in PROJECT.findall(text)} != {self.project.lower()}):
            raise Refusal("event_source_hash_or_project")
        return {"ref": ref, "text": text, "sha256": row["hash"],
                "project": self.project, "session": self.session,
                "kind": self.kind_by_ref[ref], "seq": row["seq"],
                "verified": True, "active": True, "authority": False,
                "verification_scope": "EVENT_SOURCE_INTEGRITY_ONLY"}

    def __call__(self, ref):
        return self._load(ref)

    def revalidate(self, ref, expected_sha256):
        row = self._load(ref)
        if row["sha256"] != expected_sha256:
            raise Refusal("event_source_changed")
        return True
