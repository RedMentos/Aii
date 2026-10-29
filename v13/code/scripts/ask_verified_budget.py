"""Opt-in, bounded existing-home F1/F5 Memory.recall -> C3 budget query.

Separate operator CLI candidate, NOT wired into the frozen Runtime._turn path.
No autonomous tools, age promotion or background learning.
"""
import argparse
import hashlib
import json
import re
import threading
import time
from pathlib import Path

from v13.common import dumps
from v13.config import initialize
from v13.memory import Memory
from v13.models import ModelManager
from v13.runners import RunnerPool
from v13.store import Store
from v13.source_consumer import verified_recall_messages, BUDGET_VALUE, PROJECT


class BudgetContext:
    """Existing-home operator lane: no Runtime coordinator, sleep or new session."""
    def __init__(self, home):
        self.home = Path(home)
        self.cfg = initialize(self.home)
        self.store = Store(self.home, self.cfg["log_retention_days"])
        try:
            self.models = ModelManager(self.home, self.cfg.get("b2_control", "two_body"))
            self.pool = RunnerPool(self.home, self.models, self.cfg,
                                   approval_store=self.store)
            self.memory = Memory(self.store, self.cfg)
            self.session = self.store.meta("last_session")
            self.paused = self.store.queue_paused()
        except BaseException:
            self.store.close()
            raise

    def idle(self):
        return self.store.one(
            "SELECT 1 FROM accepted_turns WHERE state IN ('PENDING','RUNNING') LIMIT 1"
        ) is None

    def close(self):
        try:
            self.pool.unload()
        finally:
            self.store.close()


def _pinned_c3(models):
    """Deep-hashed installed metadata must also equal the frozen catalog."""
    spec = models.specs["models"]["language"]
    installed = models.installed.get("language")
    if not isinstance(installed, dict):
        return False
    for field, key in (("model_id", "model_id"), ("exact_revision", "revision"),
                       ("main_file", "main_file"), ("license_id", "license_id"),
                       ("quant_format", "quant_format")):
        if installed.get(field) != spec.get(key):
            return False
    name = spec["main_file"]
    files = installed.get("files")
    expected = next((f for f in spec["files"] if f["local_name"] == name), None)
    actual = files.get(name) if isinstance(files, dict) else None
    return (expected is not None and isinstance(actual, dict)
            and actual.get("sha256") == expected["sha256"]
            and actual.get("size") == expected["size"])


def _digest(messages):
    return hashlib.sha256(dumps(messages).encode("utf-8")).hexdigest()


def _age0_only(r):
    if (r.cfg.get("system_stage") != 0
            or r.cfg.get("learning_mode") != "RECORD_ONLY"
            or r.cfg.get("latents_enabled") is not False
            or r.cfg.get("jepa_weight", 0) != 0):
        raise ValueError("AGE0_RECORD_ONLY_REQUIRED")
    if not r.idle() or r.store.queue_paused():
        raise ValueError("RUNTIME_NOT_IDLE")


def _session_exists(r, session):
    return (isinstance(session, str) and bool(session)
            and r.store.one("SELECT id FROM sessions WHERE id=?", (session,)) is not None)


def _preflight(r, query, session):
    _age0_only(r)
    if not _session_exists(r, session):
        return {"status": "CLARIFY", "reason": "SESSION_NOT_FOUND",
                "model_called": False, "native_calls": 0}, None
    packet = verified_recall_messages(r.cfg, query, session, r.memory)
    decision = packet["decision"]
    if decision["status"] != "ADMITTED" or packet["messages"] is None:
        return {"status": decision["status"], "reason": decision.get("reason"),
                "answer": decision.get("answer", ""),
                "model_called": False, "native_calls": 0}, None
    source = decision["source"]
    return {"status": "READY", "reason": "VERIFIED_RECALL",
            "memory_id": source["memory_id"], "source_ref": source["source_ref"],
            "messages_sha256": _digest(packet["messages"]),
            "model_called": False, "native_calls": 0}, packet


def _answer_uses_euro_source(answer, source):
    """Conservative answer gate: no extra numbers or foreign named projects."""
    match = BUDGET_VALUE.fullmatch(source.get("value", ""))
    topic = source.get("topic", "")
    expected = PROJECT.search(topic)
    if not match or not expected or not isinstance(answer, str):
        return False
    # An exact source number inside a negation, uncertain answer, question or
    # competing currency is not an affirmative sourced budget. Reject the
    # whole generated answer even when every numeral equals the source value.
    # This is a conservative veto, not a general semantic truth verifier.
    if ("?" in answer or re.search(
            r"\b(?:not|no|never|wrong|incorrect|unverified|unknown|uncertain|"
            r"cannot|nicht|kein(?:e|en|er|es)?|falsch|unbekannt|unbestätigt)\b",
            answer, flags=re.I)
            or re.search(
                r"(?<!\w)(?:dollars?|USD|CAD|pounds?|GBP|yen|JPY|CHF|francs?)(?!\w)|[$£¥]",
                answer, flags=re.I)):
        return False
    amount = source["value"].split(" ", 1)[0]
    # Exact amount + Euro; never accept a decimal/grouped or negative variant.
    if not re.search(r"(?<![-\d])" + re.escape(amount)
                     + r"(?!\d|[.,]\d)\s*(?:Euro(?:s)?|EUR|€)(?!\w)",
                     answer, flags=re.I):
        return False
    if re.search(r"(?<!\w)-\s*" + re.escape(amount) + r"(?!\d)", answer):
        return False
    # Reject extra unsupported quantities even if the right number also appears.
    numbers = re.findall(r"(?<!\w)\d+(?:[.,]\d+)*(?!\w)", answer)
    if not numbers or any(number != amount for number in numbers):
        return False
    # A named foreign project must never be presented as the verified project.
    return all(name.casefold() == expected.group(1).casefold()
               for name in PROJECT.findall(answer))


# An independent consumer bound protects against a misbehaving streaming
# generator even when the native token limit is already configured.
MAX_NATIVE_OUTPUT_CHARS = 32768


def _collect_bounded_output(chunks):
    """Return text only for finite, string-only native output within the cap."""
    parts = []
    length = 0
    for chunk in chunks:
        if not isinstance(chunk, str):
            return None
        length += len(chunk)
        if length > MAX_NATIVE_OUTPUT_CHARS:
            return None
        parts.append(chunk)
    return "".join(parts)


def query(r, text, session=None, *, native=False, timeout_s=120, max_tokens=64):
    """Return a bounded decision; native execution requires explicit opt-in."""
    session = r.session if session is None else session
    preflight, packet = _preflight(r, text, session)
    if packet is None or not native:
        return preflight
    if not (1 <= int(max_tokens) <= 128 and 1 <= float(timeout_s) <= 120):
        raise ValueError("BOUNDED_NATIVE_LIMIT_REQUIRED")
    if not _pinned_c3(r.models):
        return dict(preflight, status="C3_MODEL_NOT_PINNED",
                    reason="CATALOG_REVISION_AND_HASH_REQUIRED")
    verified = r.models.verify(deep=True)
    language = verified.get("language")
    if not language or not language.get("ok") or language.get("hash_checked") is not True:
        return dict(preflight, status="C3_MODEL_NOT_VERIFIED", reason="C3_DEEP_HASH_REQUIRED")
    r.models.path_for("C3_LANGUAGE")
    runner = None
    calls = 0
    released = None
    output = None
    metrics = {}
    try:
        runner = r.pool.get("C3_LANGUAGE")
        # Loading can take time. Re-read F1/F5, active corrections and SourceRef
        # after model acquisition, immediately before the one native call.
        _age0_only(r)
        current, second = _preflight(r, text, session)
        if (second is None or current["status"] != "READY"
                or current["memory_id"] != preflight["memory_id"]
                or current["source_ref"] != preflight["source_ref"]
                or current["messages_sha256"] != preflight["messages_sha256"]):
            return {"status": "CLARIFY", "reason": "SOURCE_CHANGED_BEFORE_DISPATCH",
                    "model_called": False, "native_calls": 0}
        calls = 1
        output = _collect_bounded_output(runner.generate(
            second["messages"], threading.Event(),
            time.monotonic() + float(timeout_s),
            max_tokens=int(max_tokens), seed=13))
        metrics = dict(runner.last_metrics)
    finally:
        if runner is not None:
            released = r.pool.unload("C3_LANGUAGE")
    if not released or released.get("process_reaped") is not True:
        return {"status": "NATIVE_RELEASE_NOT_PROVEN", "model_called": bool(calls),
                "native_calls": calls}
    # Generation is a TOCTOU window: revoke/contradict during the model call and
    # the answer must not leave this operator lane. Re-read after native teardown.
    try:
        final, final_packet = _preflight(r, text, session)
        unchanged = (final_packet is not None and final["status"] == "READY"
                     and final["memory_id"] == preflight["memory_id"]
                     and final["source_ref"] == preflight["source_ref"]
                     and final["messages_sha256"] == preflight["messages_sha256"])
    except Exception:
        unchanged = False
    if not unchanged:
        return {"status": "CLARIFY", "reason": "SOURCE_CHANGED_AFTER_GENERATION",
                "model_called": True, "native_calls": 1, "process_reaped": True}
    if metrics.get("status") != "FINAL" or not _answer_uses_euro_source(output, packet["decision"]["source"]):
        return {"status": "UNVERIFIED_NATIVE_ANSWER", "reason": "NO_EXACT_EURO_SOURCE_MATCH",
                "model_called": True, "native_calls": 1}
    return {"status": "FINAL", "answer": output,
            "source_ref": preflight["source_ref"],
            "model_revision": r.models.revision("C3_LANGUAGE"),
            "native_status": metrics["status"], "process_reaped": True,
            "model_called": True, "native_calls": 1}



def exact_source(r, text, session=None):
    """Explicit TTY-only deterministic answer from an active F1/F5 budget source.

    This is source copy, not C3 language generation or a learned response.
    Existing semantic recall may use an encoder if configured; no C3 decode.
    """
    session = r.session if session is None else session
    first, packet = _preflight(r, text, session)
    if packet is None:
        return first
    source = packet["decision"]["source"]
    topic, value = source["topic"], source["value"]
    name = PROJECT.search(topic)
    if name is None or not BUDGET_VALUE.fullmatch(value):
        return {"status": "CLARIFY", "reason": "SOURCE_FORMAT_CHANGED",
                "model_called": False, "native_calls": 0}
    german = bool(re.search(r"projekt|wie hoch|finanzrahmen", text, re.I))
    answer = ("Projekt " if german else "Project ") + name.group(1) + ": " + value + "."
    second, second_packet = _preflight(r, text, session)
    if (second_packet is None or second["status"] != "READY"
            or second["memory_id"] != first["memory_id"]
            or second["source_ref"] != first["source_ref"]
            or second["messages_sha256"] != first["messages_sha256"]):
        return {"status": "CLARIFY", "reason": "SOURCE_CHANGED_BEFORE_EXACT_OUTPUT",
                "model_called": False, "native_calls": 0}
    # The standalone BudgetContext deliberately does not attach a semantic
    # encoder; Runtime may attach one. Do not require an optional organ to
    # deliver a deterministic lexical source copy.
    keys = getattr(r.memory, "semantic_keys", None)
    return {"status": "FINAL_SOURCE_EXACT", "answer": answer,
            "source_ref": source["source_ref"], "authority": "EXACT_SOURCE",
            "model_called": False, "native_calls": 0, "learned": False,
            "semantic_encoder_may_run": keys is not None and keys.mode() != "off"}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--home", required=True)
    p.add_argument("--query", required=True)
    p.add_argument("--session", default=None)
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--native", action="store_true",
                      help="explicitly invoke one pinned C3 native generation")
    mode.add_argument("--exact", action="store_true",
                      help="copy the current verified F1/F5 source without C3 generation")
    p.add_argument("--timeout", type=float, default=120)
    p.add_argument("--max-tokens", type=int, default=64)
    args = p.parse_args(argv)
    home = Path(args.home).expanduser().resolve()
    if not home.is_dir() or not (home / "config/settings.json").is_file():
        print(json.dumps({"status": "ERROR", "reason": "EXISTING_HOME_REQUIRED"}))
        return 2
    r = None
    try:
        r = BudgetContext(home)
        result = (exact_source(r, args.query, args.session) if args.exact else
                  query(r, args.query, args.session, native=args.native,
                        timeout_s=args.timeout, max_tokens=args.max_tokens))
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0 if result["status"] in {"READY", "FINAL", "FINAL_SOURCE_EXACT",
                                         "CLARIFY", "NOT_APPLICABLE"} else 2
    except Exception as exc:
        print(json.dumps({"status": "ERROR", "reason": type(exc).__name__}, sort_keys=True))
        return 2
    finally:
        if r is not None:
            r.close()


if __name__ == "__main__":
    raise SystemExit(main())
