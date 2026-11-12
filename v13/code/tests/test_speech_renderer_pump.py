"""Synthetic SQLite tests for injected C3 speech renderer transport."""
from v13.speech_intent import SpeechIntentQueue
from v13.speech_renderer_pump import SpeechRendererPump

class Renderer:
    def __init__(self):
        self.calls = []
        self.cancelled = []
        self.on_render = None
    def render(self, intent_id, text, digest):
        self.calls.append((intent_id, text, digest))
        if self.on_render:
            self.on_render()
        return (intent_id, digest, "native")
    def cancel(self, intent_id):
        self.cancelled.append(intent_id)

class Verifier:
    def __init__(self, accept=True):
        self.accept = accept
    def verify(self, intent_id, digest, receipt):
        return self.accept and receipt == (intent_id, digest, "native")

def test_disabled_no_claim(tmp_path):
    q = SpeechIntentQueue(tmp_path / "q.sqlite")
    intent = q.submit("hello", source_id="c3:evt")
    renderer = Renderer()
    pump = SpeechRendererPump(q, renderer=renderer, verifier=Verifier())
    assert pump.run_one().status == "OFF"
    assert q.status(intent.intent_id) == "QUEUED"
    assert not renderer.calls
    q.close()

def test_verified_render_restart(tmp_path):
    path = tmp_path / "q.sqlite"
    q = SpeechIntentQueue(path)
    intent = q.submit("hello", source_id="c3:evt")
    renderer = Renderer()
    pump = SpeechRendererPump(q, renderer=renderer, verifier=Verifier(), enabled=True)
    assert pump.run_one().status == "RENDERED"
    assert q.status(intent.intent_id) == "RENDERED"
    assert pump.run_one().status == "EMPTY"
    q.close()
    q = SpeechIntentQueue(path)
    assert q.status(intent.intent_id) == "RENDERED"
    q.close()

def test_unverified_receipt_never_marks_rendered(tmp_path):
    q = SpeechIntentQueue(tmp_path / "q.sqlite")
    intent = q.submit("hello", source_id="c3:evt")
    renderer = Renderer()
    pump = SpeechRendererPump(q, renderer=renderer, verifier=Verifier(False), enabled=True)
    assert pump.run_one().status == "UNVERIFIED"
    assert q.status(intent.intent_id) == "INTERRUPTED"
    assert renderer.cancelled == [intent.intent_id]
    assert pump.run_one().status == "EMPTY"
    q.close()

def test_stop_during_render_cannot_ack(tmp_path):
    q = SpeechIntentQueue(tmp_path / "q.sqlite")
    intent = q.submit("hello", source_id="c3:evt")
    renderer = Renderer()
    pump = SpeechRendererPump(q, renderer=renderer, verifier=Verifier(), enabled=True)
    renderer.on_render = pump.stop
    assert pump.run_one().status == "INTERRUPTED"
    assert q.status(intent.intent_id) == "INTERRUPTED"
    assert renderer.cancelled == [intent.intent_id]
    q.close()

def test_renderer_exception_uncertain_no_retry(tmp_path):
    q = SpeechIntentQueue(tmp_path / "q.sqlite")
    intent = q.submit("hello", source_id="c3:evt")
    renderer = Renderer()
    pump = SpeechRendererPump(q, renderer=renderer, verifier=Verifier(), enabled=True)
    def fail():
        raise RuntimeError("device died")
    renderer.on_render = fail
    assert pump.run_one().status == "FAILED_UNCERTAIN"
    assert q.status(intent.intent_id) == "INTERRUPTED"
    assert pump.run_one().status == "EMPTY"
    q.close()

def test_stop_during_receipt_verification_cannot_commit(tmp_path):
    q = SpeechIntentQueue(tmp_path / "q.sqlite")
    intent = q.submit("hello", source_id="c3:evt")
    renderer = Renderer()
    class StoppingVerifier:
        def verify(self, intent_id, digest, receipt):
            pump.stop()
            return True
    pump = SpeechRendererPump(q, renderer=renderer, verifier=StoppingVerifier(), enabled=True)
    assert pump.run_one().status == "INTERRUPTED"
    assert q.status(intent.intent_id) == "INTERRUPTED"
    assert renderer.cancelled == [intent.intent_id]
    q.close()

def test_committed_c3_operator_to_verified_render_end_to_end(tmp_path):
    import json
    import sqlite3
    from v13.speech_operator import LocalSpeechHandoff
    event = "evt_" + "a" * 28
    class Store:
        def __init__(self):
            self.db = sqlite3.connect(":memory:")
            self.db.row_factory = sqlite3.Row
            self.db.execute("CREATE TABLE messages (id INTEGER PRIMARY KEY, event_id TEXT, role TEXT, text TEXT, status TEXT, metadata TEXT)")
            self.db.execute(
                "INSERT INTO messages(event_id,role,text,status,metadata) VALUES (?,?,?,?,?)",
                (event, "assistant", "spoken text", "FINAL",
                 json.dumps({"model_generated": True, "speech_source_role": "C3_LANGUAGE"})))
            self.db.commit()
        def one(self, query, args):
            return self.db.execute(query, args).fetchone()
    handoff = LocalSpeechHandoff(Store(), tmp_path / "speech.sqlite")
    renderer = Renderer()
    try:
        from v13.speech_intent import SpeechIntentError
        import pytest
        with pytest.raises(SpeechIntentError, match="opt-in"):
            handoff.enqueue(event)
        queued = handoff.enqueue(event, local_user_opt_in=True)
        with pytest.raises(SpeechIntentError, match="opt-in"):
            handoff.render_one(renderer=renderer, verifier=Verifier())
        assert handoff.render_one(renderer=renderer, verifier=Verifier(),
                                  local_user_opt_in=True).status == "RENDERED"
        assert handoff.queue.status(queued.intent_id) == "RENDERED"
        assert renderer.calls[0][1] == "spoken text"
    finally:
        handoff.close()
