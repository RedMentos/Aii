import json
import sqlite3
import pytest

from v13.speech_intent import SpeechIntentQueue, SpeechIntentError
from v13.speech_runtime_bridge import SpeechRuntimeBridge
from v13.speech_store_binding import enqueue_committed_c3

EVENT = "evt_" + "b" * 28

class Store:
    def __init__(self):
        self.db = sqlite3.connect(":memory:")
        self.db.row_factory = sqlite3.Row
        self.db.execute("CREATE TABLE messages (id INTEGER PRIMARY KEY, event_id TEXT, role TEXT, text TEXT, status TEXT, metadata TEXT)")
    def one(self, query, args):
        return self.db.execute(query, args).fetchone()
    def put(self, *, text="hello", status="FINAL", organ="C3_LANGUAGE", generated=True):
        self.db.execute("DELETE FROM messages")
        self.db.execute("INSERT INTO messages(event_id,role,text,status,metadata) VALUES (?,?,?,?,?)",
            (EVENT, "assistant", text, status, json.dumps({"model_generated":generated,"speech_source_role":organ})))
        self.db.commit()

def test_authoritative_store_to_speech_queue_restart(tmp_path):
    store = Store()
    store.put()
    path = tmp_path / "speech.sqlite"
    q = SpeechIntentQueue(path)
    bridge = SpeechRuntimeBridge(q, enabled=True)
    intent = enqueue_committed_c3(store, EVENT, bridge)
    assert intent.text == "hello"
    assert intent.source_id == "c3:" + EVENT
    q.close()
    q = SpeechIntentQueue(path)
    bridge = SpeechRuntimeBridge(q, enabled=True)
    with pytest.raises(SpeechIntentError, match="already queued"):
        enqueue_committed_c3(store, EVENT, bridge)
    assert q.claim().intent_id == intent.intent_id
    q.close()

@pytest.mark.parametrize("status,organ,generated", [
    ("ERROR", "C3_LANGUAGE", True),
    ("CANCELLED", "C3_LANGUAGE", True),
    ("FINAL", "B1_DETAIL", True),
    ("FINAL", "C3_LANGUAGE", False),
    ("FINAL", None, True),
])
def test_no_speech_for_uncommitted_or_other_organ(tmp_path, status, organ, generated):
    store = Store()
    store.put(status=status, organ=organ, generated=generated)
    q = SpeechIntentQueue(tmp_path / "speech.sqlite")
    with pytest.raises(SpeechIntentError):
        enqueue_committed_c3(store, EVENT, SpeechRuntimeBridge(q, enabled=True))
    assert q.db.execute("SELECT count(*) FROM speech_intents").fetchone()[0] == 0
    q.close()

def test_off_and_missing_store_row(tmp_path):
    store = Store()
    q = SpeechIntentQueue(tmp_path / "speech.sqlite")
    bridge = SpeechRuntimeBridge(q, enabled=True)
    with pytest.raises(SpeechIntentError):
        enqueue_committed_c3(store, EVENT, bridge)
    store.put()
    bridge.enabled = False
    with pytest.raises(SpeechIntentError, match="OFF"):
        enqueue_committed_c3(store, EVENT, bridge)
    q.close()
