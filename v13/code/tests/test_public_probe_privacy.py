import importlib.util
import json
from pathlib import Path
import shutil

import pytest

from v13.public_probe import public_probe_error_report, public_probe_error_telemetry, public_probe_summary


CODE = Path(__file__).resolve().parents[1]
OVERLAY_PATH = CODE / "scripts" / "integrated_console_probe_privacy_overlay_20261123.py"


def load_overlay():
    spec = importlib.util.spec_from_file_location("v14_console_probe_privacy_overlay_test", OVERLAY_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def copy_overlay_inputs(code_dir, staging):
    for name in ("runtime.py", "__main__.py", "prompts.py", "public_probe.py"):
        source = code_dir / "v13" / name
        target = staging / "v13" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)


def test_public_probe_summary_rejects_wrong_schema_and_redacts_payloads():
    with pytest.raises(ValueError, match="native smoke"):
        public_probe_summary({
            "proof_kind": "OTHER",
            "roles": {"C3_LANGUAGE": {"actual_output": "SECRET_C3"}},
        })

    report = {
        "proof_kind": "NATIVE_SMOKE",
        "status": "SMOKE_PASS",
        "phone_measured": True,
        "full_runner_proof": False,
        "model_revisions": {"C3_LANGUAGE": "revision-c3"},
        "effective_config": {
            "threads": 6,
            "answer_tokens": 48,
            "private_setting": "SECRET_CONFIG",
            "oversized_number": 10 ** 1000,
        },
        "missing_proofs": ["B3 receiver utility"],
        "roles": {
            "C3_LANGUAGE": {
                "ok": True,
                "actual_output": "SECRET_C3_OUTPUT",
                "metrics": {
                    "status": "FINAL",
                    "generated_tokens": 7,
                    "prompt_tokens": 18,
                    "prompt_preview": "SECRET_PROMPT",
                },
            },
            "B1_DETAIL": {
                "ok": True,
                "actual_output": "SECRET_B1_OUTPUT",
                "structured_offer": {
                    "verified_quote_count": 1,
                    "rejected_quote_count": 0,
                    "actual": {"summary": "SECRET_B1_HYPOTHESIS"},
                },
            },
            "B2_GIST": {
                "ok": True,
                "structured_offer": {
                    "verified_quote_count": 2,
                    "rejected_quote_count": 1,
                    "actual": {"summary": "SECRET_B2_HYPOTHESIS"},
                },
            },
            "C2_CONTROL": {
                "ok": True,
                "embedding_dim": 3072,
                "actual_control": {"answer": "SECRET_CONTROL_PAYLOAD"},
            },
        },
    }

    summary = public_probe_summary(report)
    rendered = json.dumps(summary, sort_keys=True)
    for secret in (
        "SECRET_C3_OUTPUT", "SECRET_B1_OUTPUT", "SECRET_B1_HYPOTHESIS",
        "SECRET_B2_HYPOTHESIS", "SECRET_CONTROL_PAYLOAD", "SECRET_PROMPT",
        "SECRET_CONFIG",
    ):
        assert secret not in rendered
    assert summary["roles"]["B1_DETAIL"]["offer"]["verified_quote_count"] == 1
    assert summary["roles"]["B2_GIST"]["offer"]["rejected_quote_count"] == 1
    assert summary["roles"]["C3_LANGUAGE"]["metrics"]["generated_tokens"] == 7
    assert summary["effective_config"]["threads"] == 6
    assert summary["redaction"]["raw_artifact_retained_locally"] is True


def test_probe_summary_uses_closed_allowlists_and_ignores_unhashable_values():
    secret = "SECRET_PROMPT_PATH_AND_MODEL_OUTPUT"
    digest = "a" * 64
    summary = public_probe_summary({
        "proof_kind": "NATIVE_SMOKE",
        "status": secret,
        "phone_measured": "true",
        "full_runner_proof": True,
        "model_revisions": {"C3_LANGUAGE": secret, "B1_DETAIL": digest},
        "missing_proofs": [secret, "sustained thermal/energy", [], {}],
        "effective_config": {"threads": 6, secret: 7},
        "roles": {
            "C3_LANGUAGE": {
                "ok": True,
                "metrics": {
                    "status": secret,
                    "role": secret,
                    "last_phase": secret,
                    "error_kind": secret,
                    "stage_durations_s": {
                        secret: 1.0,
                        "prefill_to_first_token_s": 2.0,
                    },
                    "prompt_admission": {
                        "revision": secret,
                        "status": secret,
                        "removed_layers": [secret, "C3_LAYER_TASK_CONTEXT", {}, []],
                    },
                },
            },
        },
    })
    rendered = json.dumps(summary, sort_keys=True)
    assert secret not in rendered
    assert summary["status"] == "UNKNOWN"
    assert summary["phone_measured"] is False
    assert summary["model_revisions"] == {"B1_DETAIL": digest}
    assert summary["missing_proofs"] == ["SUSTAINED_THERMAL_ENERGY"]
    metrics = summary["roles"]["C3_LANGUAGE"]["metrics"]
    for key in ("status", "role", "last_phase", "error_kind"):
        assert key not in metrics
    assert metrics["stage_durations_s"] == {"prefill_to_first_token_s": 2.0}
    assert metrics["prompt_admission"]["removed_layers"] == ["C3_LAYER_TASK_CONTEXT"]


def test_probe_error_receipts_are_constant_and_do_not_echo_exception_text():
    report = public_probe_error_report()
    telemetry = public_probe_error_telemetry()
    rendered = json.dumps({"report": report, "telemetry": telemetry})
    assert report["status"] == "SMOKE_ERROR"
    assert report["missing_proofs"] == ["PROBE_EXECUTION_ERROR"]
    assert telemetry == {"kind": "probe", "error": "PROBE_ERROR"}
    assert "SECRET_NATIVE_STDERR" not in rendered
    assert "exception" not in rendered.lower()


def test_staged_overlay_patches_runtime_and_cli_once_and_compiles(tmp_path):
    overlay = load_overlay()
    staging = tmp_path / "staging"
    copy_overlay_inputs(CODE, staging)
    expected = {
        "v13/runtime.py": (CODE / "v13" / "runtime.py").read_bytes(),
        "v13/__main__.py": (CODE / "v13" / "__main__.py").read_bytes(),
    }

    replacements = overlay.apply_staged_console_probe_privacy(
        CODE, staging, expected_staged_files=expected,
    )
    assert set(replacements) == {"v13/runtime.py", "v13/__main__.py"}
    for relative, payload in replacements.items():
        (staging / relative).write_bytes(payload)

    runtime = (staging / "v13" / "runtime.py").read_text(encoding="utf-8")
    cli = (staging / "v13" / "__main__.py").read_text(encoding="utf-8")
    assert "public_probe_summary(probe(self))" in runtime
    assert "public_probe_error_telemetry()" in runtime
    assert "probe: PROBE_ERROR" in runtime
    assert "public_probe_summary(probe(r))" in cli
    assert "public_probe_error_report()" in cli
    assert "print(json.dumps(result,ensure_ascii=False,indent=2));return 0" not in cli


def test_staged_overlay_fails_closed_on_source_or_composed_byte_mismatch(tmp_path):
    overlay = load_overlay()
    code_copy = tmp_path / "code"
    stage = tmp_path / "stage"
    copy_overlay_inputs(CODE, code_copy)
    copy_overlay_inputs(CODE, stage)
    expected = {
        "v13/runtime.py": (code_copy / "v13" / "runtime.py").read_bytes(),
        "v13/__main__.py": (code_copy / "v13" / "__main__.py").read_bytes(),
    }

    (code_copy / "v13" / "runtime.py").write_text("# tampered\n", encoding="utf-8")
    with pytest.raises(ValueError, match="source pin mismatch"):
        overlay.apply_staged_console_probe_privacy(
            code_copy, stage, expected_staged_files=expected,
        )

    copy_overlay_inputs(CODE, code_copy)
    expected["v13/runtime.py"] = b"# not the builder output\n"
    with pytest.raises(ValueError, match="exact composed builder output"):
        overlay.apply_staged_console_probe_privacy(
            code_copy, stage, expected_staged_files=expected,
        )
