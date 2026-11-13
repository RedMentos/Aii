"""Regression: an update resume token must never override the owner's AI OFF."""
from unittest.mock import Mock

import pytest

from v13 import chat_service, lifecycle, pipeline_agent


@pytest.mark.parametrize("paused", [False, True])
def test_update_resume_does_not_start_explicitly_disabled_ai(monkeypatch, paused):
    console = Mock()
    console.state.return_value = {"running": False}
    ai = chat_service.ChatService(console=console)
    ai.paused = paused
    ai.pending_lifecycle = paused
    monkeypatch.setattr(chat_service, "_read_desired", lambda: False)
    monkeypatch.setattr(lifecycle, "service_stop", lambda *a, **k: False)
    resume = Mock(return_value=True)
    monkeypatch.setattr(lifecycle, "service_resume", resume)
    monkeypatch.setattr(pipeline_agent, "snapshot", lambda: {"last_result": "UPDATED"})
    monkeypatch.setattr(pipeline_agent, "refresh_requested", lambda *a: False)
    monkeypatch.setattr(lifecycle, "STOP_REQUEST", Mock(is_file=Mock(return_value=False), exists=Mock(return_value=False)))

    ai.tick()
    assert ai.status == "STOPPED_BY_USER"
    resume.assert_not_called()
    console.start.assert_not_called()


@pytest.mark.parametrize("paused", [False, True])
def test_update_resume_restarts_only_when_owner_enabled_ai(monkeypatch, paused):
    console = Mock()
    console.state.return_value = {"running": True}
    ai = chat_service.ChatService(console=console)
    ai.paused = paused
    monkeypatch.setattr(chat_service, "_read_desired", lambda: True)
    monkeypatch.setattr(lifecycle, "service_stop", lambda *a, **k: False)
    resume = Mock(return_value=True)
    monkeypatch.setattr(lifecycle, "service_resume", resume)
    monkeypatch.setattr(pipeline_agent, "snapshot", lambda: {"last_result": "UPDATED"})
    monkeypatch.setattr(pipeline_agent, "refresh_requested", lambda *a: False)
    monkeypatch.setattr(lifecycle, "STOP_REQUEST", Mock(is_file=Mock(return_value=False), exists=Mock(return_value=False)))

    ai.tick()
    resume.assert_called_once_with(console)
    assert ai.status == "RUNNING"
