"""Same-causal C3 must report only an exact native prompt-prefill binding.

The session and model are synthetic test doubles. This verifies Runtime-side
receipt wiring and negative controls; it is not a native model or Redmi test.
"""
import json
from pathlib import Path
import threading
import time
from types import SimpleNamespace
from unittest.mock import patch

from v13.brain_panel import status as brain_status
from v13.common import digest, dumps
from v13.runners import CausalStreamRunner


SECRET = "PRIVATE_QUOTE_MUST_NOT_LEAK"


def _offer(role, packet_id):
    source_ref = {
        "source_id": "source-1",
        "sha256": "a" * 64,
        "char_start": 0,
        "char_end": len(SECRET),
        "modality": "text",
    }
    return {
        "role": role,
        "offer_packet_id": packet_id,
        "hypothesis": {"summary": "untrusted", "uncertainty": "low", "needs_reentry": False},
        "verified_quotes": [{
            "text": SECRET,
            "source_ref": source_ref,
            "verification": "EXACT_SOURCE_SUBSTRING_ONLY",
        }],
    }


def _messages():
    offers = [_offer("B1_DETAIL", "b1"), _offer("B2_GIST", "b2")]
    system = "fixed rules\nInternal hypotheses: " + json.dumps(
        offers, ensure_ascii=False, sort_keys=True
    )
    return [{"role": "system", "content": system},
            {"role": "user", "content": "Compare the two supported points."}]


def _render(messages):
    return "<START>" + "".join(item["content"] for item in messages) + "<ASSISTANT>"


class FakeTemplate:
    def __init__(self, home, role, model, cfg, approval_store=None):
        self.home = home
        self.role = role
        self.model = model
        self.cfg = cfg
        self.binary = None

    def load(self, cancel, deadline):
        return None

    def _json(self, method, endpoint, payload, deadline):
        if endpoint == "/apply-template":
            return {"prompt": _render(payload["messages"])}
        if endpoint == "/tokenize":
            return {"tokens": [11, 12, 13]}
        raise AssertionError(endpoint)

    def unload(self):
        return {"process_reaped": True}


class FakeSession:
    mismatch_prefill = False

    def __init__(self, binding, context, out, cancel, deadline, **kwargs):
        self.context = context
        Path(out).mkdir(parents=True, exist_ok=True)
        self.context_sha = digest(dumps(context))
        self.metrics = {"process_reaped": True}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()

    def pause(self):
        ids = list(self.context["token_ids"])
        if self.mismatch_prefill:
            ids.append(99)
        return {
            "native_prompt_token_ids": ids,
            "prompt_sha256": digest(self.context["prompt"]),
            "native_context_binding": {
                "scope": "EXACT_SAME_CAUSAL_PREFILL",
                "live_generation_kv_tap": True,
                "context_source_sha256": self.context_sha,
                "pid": 123,
                "features_sha256": "b" * 64,
                "handle_id": "a" * 64,
            },
        }

    def resume(self, rows):
        yield {"event": "TOKEN", "text": "answer"}
        yield {
            "event": "COMPLETE",
            "native_token_ids": [17],
            "raw_result": {
                "stop_reason": "EOS",
                "resume_prefill_calls": 0,
                "resume_decode_calls": 0,
                "unbiased_continuation_steps": 0,
                "same_context_lifetime": True,
            },
        }

    def close(self):
        self.metrics["process_reaped"] = True


class EvidenceStore:
    def __init__(self, metadata, selected_ids=("b1", "b2")):
        self.message = {
            "event_id": "event-1",
            "status": "FINAL",
            "metadata": json.dumps(metadata),
        }
        self.telemetry = {"metrics": json.dumps({
            "role": "C3_LANGUAGE",
            "status": "PASS",
            "count": len(selected_ids),
            "selected_offer_ids": list(selected_ids),
        })}

    def one(self, sql, args=()):
        if "FROM messages" in sql:
            return self.message
        if "FROM telemetry" in sql:
            return self.telemetry
        raise AssertionError("unexpected evidence query")


def _run(tmp_path, mismatch=False):
    home = Path(tmp_path)
    (home / "tmp").mkdir(exist_ok=True)
    model_path = home / "models" / "c3.gguf"
    server_path = home / "bin" / "llama-server"
    model = SimpleNamespace(name="c3-test", resolve=lambda: model_path)
    cfg = {
        "answer_tokens": 64,
        "temperature": 0.1,
        "c3_decode_mode": "same_causal_zero",
        "answer_language": "en",
    }
    runner = CausalStreamRunner.__new__(CausalStreamRunner)
    runner.home = home
    runner.role = "C3_LANGUAGE"
    runner.model = model
    runner.cfg = cfg
    runner.approval_store = None
    runner.template = None
    runner.session = None
    runner.last_metrics = {}
    runner.bias_provider = None
    runner.prune_completed = lambda keep=8: []

    binding = {
        "identity": {
            "model_path": str(model_path),
            "server_path": str(server_path),
        },
        "feature_abi": {"stream_abi": "SYNTHETIC_TEST_ONLY"},
    }
    FakeSession.mismatch_prefill = mismatch
    with patch("v13.causal_prepare.check_prepared", return_value=binding), \
         patch("v13.runners.LlamaRunner", FakeTemplate), \
         patch("scripts.native_prefill_stream_client.StreamingOutputSession", FakeSession), \
         patch("v13.runners.shutil.disk_usage",
               return_value=SimpleNamespace(free=64 * 1024 * 1024)):
        output = "".join(runner.generate(
            _messages(), threading.Event(), time.monotonic() + 20, max_tokens=64
        ))
    return runner, output


def test_same_causal_stream_receipt_requires_exact_native_prefill_binding(tmp_path):
    runner, output = _run(tmp_path, mismatch=False)
    runner.last_metrics["synthetic"] = True
    receipt = runner.last_metrics["native_offer_prompt_receipt"]
    assert output == "answer"
    assert receipt["status"] == "RENDERED_WITH_QUOTES"
    assert receipt["native_prompt_prefill_verified"] is True
    assert receipt["native_template_submitted"] is True
    assert receipt["native_stream_completed"] is True
    assert receipt["native_completion_http_200"] is False
    assert receipt["native_prompt_sha256"] == digest(_render(_messages()))
    assert receipt["native_token_ids_sha256"] == digest(dumps([11, 12, 13]))
    assert receipt["native_prompt_tokens"] == 3
    assert receipt["native_tokenizer"] == "LLAMA_SERVER_TOKENIZE"
    assert receipt["native_prefill_observed"] is True
    assert receipt["native_generation_completed"] is True
    assert receipt["native_attention_or_semantic_use_proven"] is False
    assert SECRET not in json.dumps(runner.last_metrics)

    runtime = SimpleNamespace(
        cfg={"learning_mode": "RECORD_ONLY"},
        current=None,
        store=EvidenceStore({"runner": runner.last_metrics}),
    )
    latest = brain_status(runtime)["latest_turn"]
    assert latest["evidence_environment"] == "SYNTHETIC"
    assert latest["offer_flow"]["status"] == "SYNTHETIC_TEMPLATE_SUBMITTED_MATCHED_C4"
    assert latest["offer_flow"]["native_prompt_prefill_verified"] is True
    assert latest["offer_flow"]["native_stream_completed"] is True
    assert latest["offer_flow"]["native_completion_http_200"] is False
    assert latest["offer_flow"]["native_prompt_sha256"] is None
    assert latest["offer_flow"]["native_prompt_tokens"] is None
    assert latest["offer_flow"]["semantic_use_proven"] is False


def test_brain_status_exposes_native_prompt_fingerprints_without_prompt_text():
    # A constructed runner-receipt fixture tests status serialization only;
    # it is not evidence that a native model or Android device ran.
    metrics = {
        "role": "C3_LANGUAGE",
        "actual_model": "c3-test",
        "prompt_tokens": 3,
        "generated_tokens": 1,
        "ttft_s": 0.2,
        "duration_s": 1.0,
        "native_offer_prompt_receipt": {
            "status": "RENDERED_WITH_QUOTES",
            "native_completion_http_200": False,
            "native_template_submitted": True,
            "native_prompt_prefill_verified": True,
            "native_prefill_observed": True,
            "native_stream_completed": True,
            "native_generation_completed": True,
            "native_prompt_sha256": "a" * 64,
            "native_token_ids_sha256": "b" * 64,
            "native_prompt_tokens": 3,
            "native_tokenizer": "LLAMA_SERVER_TOKENIZE",
            "offers": [
                {"role": "B1_DETAIL", "packet_id": "b1", "rendered_quote_count": 1},
                {"role": "B2_GIST", "packet_id": "b2", "rendered_quote_count": 1},
            ],
        },
    }
    runtime = SimpleNamespace(
        cfg={"learning_mode": "RECORD_ONLY"},
        current=None,
        store=EvidenceStore({"runner": metrics}),
    )
    runtime.store.message["metadata"] = json.dumps({
        "runner": metrics, "model_revision": "test-model-revision"
    })
    latest = brain_status(runtime)["latest_turn"]
    assert latest["model_revision"] == "test-model-revision"
    assert latest["offer_flow"]["model_revision"] == "test-model-revision"
    assert latest["offer_flow"]["status"] == (
        "NATIVE_PREFILL_VERIFIED_AND_GENERATION_COMPLETED_MATCHED_C4"
    )
    assert latest["native_prompt_sha256"] == "a" * 64
    assert latest["native_token_ids_sha256"] == "b" * 64
    assert latest["native_prompt_tokens"] == 3
    assert latest["offer_flow"]["native_tokenizer"] == "LLAMA_SERVER_TOKENIZE"
    assert latest["offer_flow"]["native_generation_completed"] is True
    assert latest["offer_flow"]["semantic_use_proven"] is False
    assert SECRET not in json.dumps(latest)


def test_same_causal_stream_rejects_prompt_token_mismatch(tmp_path):
    runner, output = _run(tmp_path, mismatch=True)
    receipt = runner.last_metrics["native_offer_prompt_receipt"]
    assert output == "answer"
    assert receipt["native_prompt_prefill_verified"] is False
    assert receipt["native_template_submitted"] is False
    assert receipt["native_stream_completed"] is True
    assert receipt["native_attention_or_semantic_use_proven"] is False
