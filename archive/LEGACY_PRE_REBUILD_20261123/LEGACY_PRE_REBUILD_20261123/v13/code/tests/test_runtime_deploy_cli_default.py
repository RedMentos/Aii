"""Regression for the actual Redmi runtime checkout used by phone update."""
from pathlib import Path
import json

from v13 import runtime_deploy


def test_cli_defaults_to_phone_runtime_source(monkeypatch, tmp_path, capsys):
    calls = []

    def fake_deploy(source, *, home):
        calls.append((source, home))
        return {"status": "UP_TO_DATE", "commit": "a" * 40}

    monkeypatch.setattr(runtime_deploy.Path, "home", lambda: tmp_path)
    monkeypatch.setattr(runtime_deploy, "deploy", fake_deploy)
    runtime_deploy.main([])
    assert calls == [
        (str(tmp_path / ".v13-runtime-source"), str(tmp_path / "v13"))
    ]
    assert json.loads(capsys.readouterr().out)["status"] == "UP_TO_DATE"


def test_cli_explicit_source_override_preserved(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(runtime_deploy.Path, "home", lambda: tmp_path)
    monkeypatch.setattr(runtime_deploy, "deploy",
                        lambda source, *, home: calls.append((source, home)) or {"status": "UP_TO_DATE"})
    custom = str(tmp_path / "approved-checkout")
    runtime_deploy.main(["--source", custom])
    assert calls == [(custom, str(tmp_path / "v13"))]
