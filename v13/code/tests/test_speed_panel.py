"""V13 organ speed panel: real Store telemetry, synthetic private benchmark."""
import json
from types import SimpleNamespace

import pytest

from v13.operator import Operator
from v13.speed_panel import observed_models
from v13.store import Store


@pytest.fixture
def runtime(tmp_path):
    for folder in ("data", "data/db", "data/blobs"):
        (tmp_path / folder).mkdir(parents=True, exist_ok=True)
    store = Store(tmp_path)
    session = store.new_session()
    calls = []
    def require_idle():
        calls.append("idle")
    run = SimpleNamespace(store=store, home=tmp_path,
                          session=session, require_idle=require_idle)
    yield run, calls
    store.close()


def test_multi_organ_telemetry_never_implies_phone_or_model_training(runtime):
    r, _ = runtime
    event = r.store.event(r.session, "Task")["event_id"]
    r.store.log("body_B1_decode", event, {
        "role": "B1_DETAIL", "predicted_n": 50,
        "stream_s": 2.0, "ttft_s": .25,
    })
    r.store.log("native_C3_decode", event, {
        "role": "C3_LANGUAGE", "predicted_per_second": 71.5,
        "prefill_to_first_token_s": .12,
    })
    result = json.loads(Operator(r).run(":brain speed"))
    assert result["scope"] == "CURRENT_SESSION"
    sample = {item["role"]: item for item in result["organs"]}
    assert sample["B1_DETAIL"]["latest_decoded_tokens_per_s"] == 25.0
    assert sample["B1_DETAIL"]["latest_ttft_s"] == .25
    assert sample["C3_LANGUAGE"]["latest_decoded_tokens_per_s"] == 71.5
    assert sample["C3_LANGUAGE"]["latest_ttft_s"] == .12
    assert sample["B2_GIST"]["status"] == "NO_CURRENT_SESSION_MEASUREMENT"
    assert sample["B2_GIST"]["latest_decoded_tokens_per_s"] is None
    assert all(x["native_phone_verified"] is False for x in result["organs"])
    assert result["model_calls"] == 0 and result["state_mutation"] is False
    assert "NOT" not in result["kind"]


def test_no_cross_session_or_nonfinite_or_redacted_data_leak(runtime):
    r, _ = runtime
    secret = r.store.new_session()
    other = r.store.event(secret, "PRIVATE SOURCE")["event_id"]
    r.store.log("native_C3", other, {
        "role": "C3_LANGUAGE", "predicted_per_second": 200.5,
    })
    e = r.store.event(r.session, "Session A")["event_id"]
    # Deliberately insert legacy/corrupt telemetry that normal Store.log()
    # would reject (dumps has allow_nan=False). This is a negative control.
    with r.store.tx() as db:
        db.execute(
            "INSERT INTO telemetry(kind,event_id,metrics,created) VALUES (?,?,?,0)",
            ("native_C3", e, json.dumps({
                "role": "C3_LANGUAGE",
                "predicted_per_second": float("nan"),
                "ttft_s": float("inf"),
            })),
        )
    r.store.log("unknown", e, {"role": ["B1_DETAIL"], "predicted_per_second": 10.0})
    report = observed_models(r.store, r.session)
    assert all(a["latest_decoded_tokens_per_s"] is None for a in report["organs"])
    assert all(a["latest_ttft_s"] is None for a in report["organs"])
    assert "PRIVATE" not in json.dumps(report)
    report2 = json.loads(Operator(r).run(":speed models"))
    assert report2["organs"] == report["organs"]


def test_local_fastpath_benchmark_is_explicit_idle_no_model(runtime):
    r, called = runtime
    before = r.store.rows("SELECT * FROM updates")
    perf = json.loads(Operator(r).run(":speed fastbatch 2048"))
    assert called == ["idle"]
    assert perf["fixture"]["rows"] == 2048
    assert perf["fixture"]["model_calls"] == 0
    assert perf["stream"]["verified_same_sha256"] is True
    assert perf["writer"]["rows_per_second"] > 0
    assert perf["organ"] == "compiled_fast_output"
    assert perf["command"] == "LOCAL_OPERATOR_ONLY"
    assert r.store.rows("SELECT * FROM updates") == before
    dynamic = json.loads(Operator(r).run(":speed fastbatch-values 2048"))
    assert called == ["idle", "idle"]
    assert dynamic["fixture"]["kind"] == "SYNTHETIC_IMPORTED_VALUES"
    assert dynamic["fixture"]["rows"] == 2048
    assert dynamic["fixture"]["model_calls"] == 0
    assert dynamic["stream"]["verified_same_sha256"] is True


@pytest.mark.parametrize("arg", [
    ":speed fastbatch 0", ":speed fastbatch 50001", ":speed fastbatch bad",
    ":speed fastbatch 10 11", ":speed fastbatch-values 0", ":speed fastbatch-values nope", ":speed unknown", ":speed models extra"
])
def test_wrong_or_expensive_speed_commands_refused(runtime, arg):
    r, called = runtime
    with pytest.raises(ValueError):
        Operator(r).run(arg)
    assert called == []


def test_idle_gate_refuses_competing_native_work(runtime):
    r, calls = runtime
    def busy():
        calls.append("busy")
        raise ValueError("model is in progress")
    r.require_idle = busy
    with pytest.raises(ValueError, match="model is in progress"):
        Operator(r).run(":speed fastbatch 128")
    assert calls == ["busy"]
    assert not (r.home / "procedures").exists()


def test_only_real_operator_can_start_speed_benchmark(runtime):
    r, called = runtime
    with pytest.raises(ValueError, match="lokale Operator"):
        Operator(r).run(":speed fastbatch 256", origin="MODEL")
    assert not called
