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
