"""Persistent local state. Caller authentication belongs to the owner UI boundary.

Every operation opens its own SQLite connection; no connection is shared across
HTTP or generation threads. Rule proposals are immutable, version-bound records.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_RULES = {
    "system_prompt": "Antworte auf Deutsch, ehrlich und verständlich. Kennzeichne Unsicherheit. Erfinde keine Quellen oder ausgeführten Aktionen.",
    "max_output_tokens": 256,
    "context_tokens": 2048,
    "threads": 4,
    "temperature": 0.6,
    "allow_model_rule_proposals": True,
    "allow_note_write": False,
}
USER_RULE_LIMIT = 32
USER_RULE_KEY = re.compile(r"user\.[a-zA-Z0-9_-]{1,64}\Z")


def _now():
    return datetime.now(timezone.utc).isoformat()


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _validate(key, value):
    if not isinstance(key, str):
        raise ValueError("Regelname muss Text sein")
    if USER_RULE_KEY.fullmatch(key):
        if value is not None and (not isinstance(value, str) or not value.strip() or len(value) > 4000):
            raise ValueError("Eigene Regeln müssen 1 bis 4000 Zeichen enthalten")
        return value
    if key not in DEFAULT_RULES:
        raise ValueError("Unbekannte Regel: " + str(key))
    if key == "system_prompt":
        if not isinstance(value, str) or not value.strip() or len(value) > 16000:
            raise ValueError("system_prompt muss 1 bis 16000 Zeichen enthalten")
    elif key in ("max_output_tokens", "context_tokens", "threads"):
        lower, upper = {"max_output_tokens": (16, 1024), "context_tokens": (512, 4096), "threads": (1, 8)}[key]
        if type(value) is not int or not lower <= value <= upper:
            raise ValueError(f"{key} muss eine Ganzzahl zwischen {lower} und {upper} sein")
    elif key == "temperature":
        if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 1.5:
            raise ValueError("temperature muss eine endliche Zahl zwischen 0 und 1.5 sein")
    elif type(value) is not bool:
        raise ValueError(key + " muss true oder false sein")
    return value


def _changed_rules(values, key, value):
    """Validate an entire change without mutating the supplied current state."""
    _validate(key, value)
    updated = dict(values)
    if USER_RULE_KEY.fullmatch(key):
        if value is None:
            if key not in updated:
                raise ValueError("Eigene Regel existiert nicht")
            del updated[key]
        else:
            if key not in updated and sum(bool(USER_RULE_KEY.fullmatch(k)) for k in updated) >= USER_RULE_LIMIT:
                raise ValueError(f"Höchstens {USER_RULE_LIMIT} eigene Regeln sind erlaubt")
            updated[key] = value
    else:
        updated[key] = value
    return updated


def _title(value):
    if not isinstance(value, str) or not value.strip() or len(value) > 300:
        raise ValueError("Chat-Titel muss 1 bis 300 Zeichen enthalten")
    return value.strip()


def _proposal(row):
    result = dict(row)
    result["before"] = json.loads(result.pop("before_json"))
    result["after"] = json.loads(result.pop("after_json"))
    return result


def _digest(proposal):
    payload = {k: v for k, v in proposal.items() if k not in ("digest", "status")}
    return hashlib.sha256(_json(payload).encode("utf-8")).hexdigest()


class Store:
    def __init__(self, home):
        self.home = Path(home).expanduser().resolve()
        self.home.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.path = self.home / "state.sqlite3"
        with self._connection() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.executescript('''
                CREATE TABLE IF NOT EXISTS chats (
                    id TEXT PRIMARY KEY, title TEXT NOT NULL, created TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY, chat_id TEXT NOT NULL REFERENCES chats(id),
                    role TEXT NOT NULL, content TEXT NOT NULL, status TEXT NOT NULL,
                    created TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS messages_chat ON messages(chat_id, created);
                CREATE TABLE IF NOT EXISTS rules (
                    singleton INTEGER PRIMARY KEY CHECK(singleton=1),
                    version INTEGER NOT NULL, values_json TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS requests (
                    id TEXT PRIMARY KEY, key TEXT NOT NULL, before_json TEXT NOT NULL,
                    after_json TEXT NOT NULL, rule_version INTEGER NOT NULL,
                    digest TEXT NOT NULL, status TEXT NOT NULL,
                    reason TEXT NOT NULL, source TEXT NOT NULL, created TEXT NOT NULL);
                CREATE TRIGGER IF NOT EXISTS immutable_request_payload
                    BEFORE UPDATE OF id, key, before_json, after_json, rule_version,
                    digest, reason, source, created ON requests
                    BEGIN SELECT RAISE(ABORT, 'proposal payload is immutable'); END;
                CREATE TRIGGER IF NOT EXISTS immutable_request_delete
                    BEFORE DELETE ON requests
                    BEGIN SELECT RAISE(ABORT, 'proposal history is immutable'); END;
                CREATE TABLE IF NOT EXISTS logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, event TEXT NOT NULL,
                    details_json TEXT NOT NULL, created TEXT NOT NULL);
            ''')
            db.execute("INSERT OR IGNORE INTO rules VALUES (1, 1, ?)", (_json(DEFAULT_RULES),))
        self.recover()

    @contextmanager
    def _connection(self, write=False):
        db = sqlite3.connect(str(self.path), timeout=30)
        db.row_factory = sqlite3.Row
        try:
            db.execute("PRAGMA foreign_keys=ON")
            db.execute("PRAGMA busy_timeout=30000")
            if write:
                db.execute("BEGIN IMMEDIATE")
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    @staticmethod
    def _rules(db):
        row = db.execute("SELECT version, values_json FROM rules WHERE singleton=1").fetchone()
        return {"version": row["version"], "values": json.loads(row["values_json"])}

    @staticmethod
    def _log(db, event, details):
        db.execute("INSERT INTO logs(event, details_json, created) VALUES (?, ?, ?)", (event, _json(details), _now()))

    def chats(self):
        with self._connection() as db:
            return [dict(r) for r in db.execute("SELECT * FROM chats ORDER BY created DESC, rowid DESC")]

    def new_chat(self, title="Neuer Chat"):
        row = {"id": uuid.uuid4().hex, "title": _title(title), "created": _now()}
        with self._connection(write=True) as db:
            db.execute("INSERT INTO chats VALUES (:id, :title, :created)", row)
        return row

    def rename_chat(self, chat, title):
        title = _title(title)
        with self._connection(write=True) as db:
            row = db.execute("SELECT * FROM chats WHERE id=?", (chat,)).fetchone()
            if row is None:
                raise ValueError("Chat existiert nicht")
            db.execute("UPDATE chats SET title=? WHERE id=?", (title, chat))
            self._log(db, "chat_renamed", {"id": chat, "before": row["title"], "after": title})
            return {**dict(row), "title": title}

    def search_messages(self, query, limit=50):
        if not isinstance(query, str) or not query.strip() or len(query) > 1000:
            raise ValueError("Suchtext muss 1 bis 1000 Zeichen enthalten")
        if type(limit) is not int or not 1 <= limit <= 500:
            raise ValueError("Suchlimit muss eine Ganzzahl zwischen 1 und 500 sein")
        escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        with self._connection() as db:
            return [dict(row) for row in db.execute(
                "SELECT m.*, c.title AS chat_title FROM messages AS m JOIN chats AS c ON c.id=m.chat_id "
                "WHERE m.content LIKE ? ESCAPE '\\' ORDER BY m.created DESC, m.rowid DESC LIMIT ?",
                ("%" + escaped + "%", limit))]

    def delete_chat(self, chat):
        """Owner authentication/confirmation is enforced by the calling UI/API."""
        with self._connection(write=True) as db:
            row = db.execute("SELECT * FROM chats WHERE id=?", (chat,)).fetchone()
            if row is None:
                raise ValueError("Chat existiert nicht")
            if db.execute("SELECT 1 FROM messages WHERE chat_id=? AND status='generating'", (chat,)).fetchone():
                raise ValueError("Laufende Antwort zuerst abbrechen")
            count = db.execute("DELETE FROM messages WHERE chat_id=?", (chat,)).rowcount
            db.execute("DELETE FROM chats WHERE id=?", (chat,))
            self._log(db, "chat_deleted", {"id": chat, "messages": count})
            return {**dict(row), "deleted_messages": count}

    def messages(self, chat):
        with self._connection() as db:
            if not db.execute("SELECT 1 FROM chats WHERE id=?", (chat,)).fetchone():
                raise ValueError("Chat existiert nicht")
            return [dict(r) for r in db.execute("SELECT * FROM messages WHERE chat_id=? ORDER BY created, rowid", (chat,))]

    def add_message(self, chat, role, content, status="complete"):
        if role not in ("user", "assistant", "system", "tool"):
            raise ValueError("Ungültige Nachrichtenrolle")
        if not isinstance(content, str):
            raise ValueError("Nachrichteninhalt muss Text sein")
        if status not in ("complete", "generating", "interrupted", "cancelled", "error"):
            raise ValueError("Ungültiger Nachrichtenstatus")
        row = {"id": uuid.uuid4().hex, "chat_id": chat, "role": role, "content": content, "status": status, "created": _now()}
        with self._connection(write=True) as db:
            if not db.execute("SELECT 1 FROM chats WHERE id=?", (chat,)).fetchone():
                raise ValueError("Chat existiert nicht")
            db.execute("INSERT INTO messages VALUES (:id, :chat_id, :role, :content, :status, :created)", row)
        return row

    def update_message(self, id, content, status):
        if not isinstance(content, str) or status not in ("complete", "generating", "interrupted", "cancelled", "error"):
            raise ValueError("Ungültige Nachrichtenänderung")
        with self._connection(write=True) as db:
            if db.execute("UPDATE messages SET content=?, status=? WHERE id=?", (content, status, id)).rowcount != 1:
                raise ValueError("Nachricht existiert nicht")

    def recover(self):
        with self._connection(write=True) as db:
            count = db.execute("UPDATE messages SET status='interrupted' WHERE status='generating'").rowcount
            if count:
                self._log(db, "recovered_interrupted_generation", {"messages": count})
            return count

    def rules(self):
        with self._connection() as db:
            return self._rules(db)

    def requests(self):
        with self._connection() as db:
            return [_proposal(r) for r in db.execute("SELECT * FROM requests ORDER BY created DESC, rowid DESC")]

    def propose_rule(self, key, value, reason, source="model"):
        _validate(key, value)
        if not isinstance(reason, str) or not reason.strip() or len(reason) > 8000:
            raise ValueError("Eine Begründung mit höchstens 8000 Zeichen ist erforderlich")
        if source not in ("model", "owner"):
            raise ValueError("Unbekannte Vorschlagsquelle")
        with self._connection(write=True) as db:
            rules = self._rules(db)
            if source == "model" and not rules["values"]["allow_model_rule_proposals"]:
                raise PermissionError("Modell-Regelvorschläge sind deaktiviert")
            _changed_rules(rules["values"], key, value)
            result = {"id": uuid.uuid4().hex, "key": key, "before": rules["values"].get(key), "after": value,
                      "rule_version": rules["version"], "status": "pending", "reason": reason.strip(), "source": source, "created": _now()}
            result["digest"] = _digest(result)
            db.execute("INSERT INTO requests VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                       (result["id"], key, _json(result["before"]), _json(value), result["rule_version"], result["digest"], "pending", result["reason"], source, result["created"]))
            self._log(db, "rule_proposed", {"id": result["id"], "digest": result["digest"], "source": source})
            return result

    def decide_request(self, id, approve, digest):
        if type(approve) is not bool:
            raise ValueError("approve muss bool sein")
        with self._connection(write=True) as db:
            row = db.execute("SELECT * FROM requests WHERE id=?", (id,)).fetchone()
            if row is None:
                raise ValueError("Vorschlag existiert nicht")
            result = _proposal(row)
            if not isinstance(digest, str) or digest != result["digest"] or _digest(result) != result["digest"]:
                raise ValueError("Vorschlags-Hash stimmt nicht überein")
            if result["status"] != "pending":
                raise ValueError("Vorschlag wurde bereits entschieden")
            rules = self._rules(db)
            if rules["version"] != result["rule_version"] or rules["values"].get(result["key"]) != result["before"]:
                result["status"] = "stale"
            elif approve:
                rules["values"] = _changed_rules(rules["values"], result["key"], result["after"])
                db.execute("UPDATE rules SET version=version+1, values_json=? WHERE singleton=1", (_json(rules["values"]),))
                result["status"] = "approved"
            else:
                result["status"] = "rejected"
            db.execute("UPDATE requests SET status=? WHERE id=?", (result["status"], id))
            self._log(db, "rule_decided", {"id": id, "digest": digest, "status": result["status"]})
            return result

    def set_rule(self, key, value):
        _validate(key, value)
        with self._connection(write=True) as db:
            rules = self._rules(db)
            before = rules["values"].get(key)
            rules["values"] = _changed_rules(rules["values"], key, value)
            db.execute("UPDATE rules SET version=version+1, values_json=? WHERE singleton=1", (_json(rules["values"]),))
            self._log(db, "owner_rule_changed", {"key": key, "before": before, "after": value})
            return self._rules(db)

    def log(self, event, details):
        if not isinstance(event, str) or not event:
            raise ValueError("Log-Ereignis muss Text sein")
        with self._connection(write=True) as db:
            self._log(db, event, details)

    def logs(self, limit=100):
        if type(limit) is not int or not 1 <= limit <= 10000:
            raise ValueError("Log-Limit muss eine Ganzzahl zwischen 1 und 10000 sein")
        with self._connection() as db:
            results = []
            for row in db.execute("SELECT * FROM logs ORDER BY id DESC LIMIT ?", (limit,)):
                result = dict(row)
                result["details"] = json.loads(result.pop("details_json"))
                results.append(result)
            return results

    def export_chat(self, chat, path):
        with self._connection() as db:
            db.execute("BEGIN")
            row = db.execute("SELECT * FROM chats WHERE id=?", (chat,)).fetchone()
            if row is None:
                raise ValueError("Chat existiert nicht")
            messages = [dict(r) for r in db.execute("SELECT * FROM messages WHERE chat_id=? ORDER BY created, rowid", (chat,))]
            data = {"format": "v13-chat-v1", "chat": dict(row), "messages": messages}
        target = Path(path).expanduser().absolute()
        target.parent.mkdir(parents=True, exist_ok=True)
        # Exclusive creation prevents overwriting existing files, including symlinks.
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(data, handle, ensure_ascii=False, indent=2, allow_nan=False)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
        except BaseException:
            target.unlink(missing_ok=True)
            raise
        return str(target)

    def backup(self, path):
        target = Path(path).expanduser().absolute()
        target.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        os.close(fd)
        try:
            with self._connection() as source:
                destination = sqlite3.connect(str(target))
                try:
                    source.backup(destination)
                    destination.commit()
                finally:
                    destination.close()
        except BaseException:
            target.unlink(missing_ok=True)
            raise
        return str(target)

    def close(self):
        """Connections are closed by each call; retained for app shutdown symmetry."""
