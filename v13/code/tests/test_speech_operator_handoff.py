"""Local speech handoff tests: real SQLite persistence, opt-in and stop."""
import json
import sqlite3

import pytest

from v13.speech_intent import SpeechIntentError
from v13.speech_operator import LocalSpeechHandoff

EVENT = "evt_" + "a" * 28


class Store:
    def __init__(self):
        self.db = sqlite3.connect(":memory:")
        self.db.row_factory = sqlite3.Row
        self.db.execute("CREATE TABLE messages (id INTEGER PRIMARY KEY, event_id TEXT, role TEXT, text TEXT, status TEXT, metadata TEXT)")

    def one(self, query, args):
        return self.db.execute(query, args).fetchone()

    def put(self, *, status="FINAL", organ="C3_LANGUAGE"):
        self.db.execute(
            "INSERT INTO messages(event_id,role,text,status,metadata) VALUES (?,?,?,?,?)",
            (EVENT, "assistant", "spoken text", status,
             json.dumps({"model_generated": True, "speech_source_role": organ})),
        )
        self.db.commit()


def test_local_operator_opt_in_stop_and_restart(tmp_path):
    store = Store()
    store.put()
    path = tmp_path / "speech.sqlite"
    operator = LocalSpeechHandoff(store, path)
    with pytest.raises(SpeechIntentError, match="opt-in"):
        operator.enqueue(EVENT)
    assert operator.queue.db.execute("SELECT count(*) FROM speech_intents").fetchone()[0] == 0
    intent = operator.enqueue(EVENT, local_user_opt_in=True)
    assert intent.status == "QUEUED"
    assert operator.bridge.enabled is False
    assert operator.stop() == 1
    assert operator.queue.status(intent.intent_id) == "INTERRUPTED"
    operator.close()
    restarted = LocalSpeechHandoff(store, path)
    with pytest.raises(SpeechIntentError, match="already queued"):
        restarted.enqueue(EVENT, local_user_opt_in=True)
    assert restarted.queue.status(intent.intent_id) == "INTERRUPTED"
    restarted.close()


def test_local_operator_never_enqueues_non_c3(tmp_path):
    store = Store()
    store.put(organ="B1_DETAIL")
    operator = LocalSpeechHandoff(store, tmp_path / "speech.sqlite")
    with pytest.raises(SpeechIntentError, match="C3"):
        operator.enqueue(EVENT, local_user_opt_in=True)
    assert operator.bridge.enabled is False
    operator.close()
