from v13.speech_intent import SpeechCoordinator


class FakeRenderer:
    def __init__(self):
        self.rendered = []
        self.cancelled = []

    def render(self, intent):
        self.rendered.append(intent.text)
        return True

    def cancel(self, intent_id):
        self.cancelled.append(intent_id)


def test_speech_is_off_until_trusted_renderer_enabled():
    q = SpeechCoordinator()
    intent = q.enqueue("Hello", "turn-1")
    assert q.dispatch_one().status == "OFF"
    assert q.receipts()[0].intent_id == intent.id
    renderer = FakeRenderer()
    q.configure(renderer, operator_enabled=True)
    assert q.dispatch_one().status == "RENDERED"
    assert renderer.rendered == ["Hello"]


def test_barge_in_discards_queued_text_and_stop_disables_dispatch():
    q = SpeechCoordinator(max_pending=2)
    a = q.enqueue("one", "t")
    b = q.enqueue("two", "t")
    try:
        q.enqueue("three", "t")
        assert False, "queue should be bounded"
    except OverflowError:
        pass
    assert q.barge_in() == 2
    assert [r.intent_id for r in q.receipts() if r.status == "CANCELLED"] == [a.id, b.id]
    q.configure(FakeRenderer(), operator_enabled=True)
    assert q.dispatch_one().status == "EMPTY"
    q.enqueue("new", "t")
    q.stop()
    assert q.dispatch_one().status == "OFF"


def test_speech_text_not_acoustic_or_os_permission():
    q = SpeechCoordinator()
    for text in ("", " ", "x" * 2049):
        try:
            q.enqueue(text, "t")
            assert False
        except ValueError:
            pass
    assert not hasattr(q, "record_microphone")
