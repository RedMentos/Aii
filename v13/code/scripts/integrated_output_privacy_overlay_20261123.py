"""Apply a source-pinned native-probe output privacy boundary after integrated builders.

The canonical V13 source bytes are not rewritten. This staged-only overlay is
applied after the pinned recovery and arithmetic composers and is itself
Git-blob pinned by the integrated stage builder.
"""
from pathlib import Path
import hashlib

VERIFICATION_PATH = "v13/verification.py"
RUNTIME_PATH = "v13/runtime.py"
CLI_PATH = "v13/__main__.py"
PROMPTS_PATH = "v13/prompts.py"

SOURCE_PINS = {
    VERIFICATION_PATH: "b3225c0656815b76ca3a7c2b582bc37af0ea5fc6",
    RUNTIME_PATH: "30360f40eb784be5ea975ee85e94a57f0b154164",
    CLI_PATH: "9248e46e199a4227c296d538e6a2ef969e8e10cb",
    PROMPTS_PATH: "646c6f31b52ca2664c1952af7c7e842fc3e20885",
}

SUMMARY_FUNCTION = "def public_probe_summary(report):\n    \"\"\"Return a closed-grammar console view; never echo untrusted diagnostic strings.\"\"\"\n    if type(report) is not dict or report.get('proof_kind') != 'NATIVE_SMOKE':\n        raise ValueError('Expected a native smoke report')\n\n    import math\n\n    roles = frozenset({'C2_CONTROL', 'C3_LANGUAGE', 'B1_DETAIL', 'B2_GIST'})\n    top_statuses = frozenset({'SMOKE_PASS', 'SMOKE_PARTIAL', 'SMOKE_ERROR'})\n    metric_statuses = frozenset({\n        'FINAL', 'TIME_BUDGET', 'DEADLINE', 'CANCELLED', 'ERROR',\n        'UNAVAILABLE', 'SKIPPED', 'RUNNING',\n    })\n    phases = frozenset({'load', 'template', 'prefill', 'stream'})\n    error_kinds = frozenset({\n        'ERROR', 'TIMEOUT', 'DEADLINE', 'CANCELLED', 'UNAVAILABLE',\n        'PERMISSION_ERROR', 'PROBE_ERROR',\n    })\n    duration_keys = frozenset({\n        'load_s', 'template_s', 'prefill_to_first_token_s', 'stream_s',\n    })\n    admission_revision = 'v13.native-prompt-admission/1'\n    admission_statuses = frozenset({'ADMITTED', 'UNSATISFIED'})\n    removed_layers = frozenset({\n        'C3_LAYER_TASK_CONTEXT', 'C3_LAYER_DIGEST', 'C3_LAYER_USER_MODEL',\n        'OLD_NATIVE_HISTORY', 'BODY_SOURCE_ADDRESS_METADATA',\n        'BODY_DUPLICATE_EXECUTIVE_SOURCE_REFS',\n    })\n    missing_proof_codes = {\n        'sustained thermal/energy': 'SUSTAINED_THERMAL_ENERGY',\n        'target-phone RSS/KV growth under pressure': 'TARGET_PHONE_RSS_KV_PRESSURE',\n        'native sparse body training': 'NATIVE_SPARSE_BODY_TRAINING',\n        'B3 receiver-effect ablations': 'B3_RECEIVER_EFFECT_ABLATIONS',\n        'long-term retention': 'LONG_TERM_RETENTION',\n    }\n    safe_proof_codes = frozenset(missing_proof_codes.values())\n\n    def number(value):\n        if type(value) not in (int, float):\n            return False\n        try:\n            n = float(value)\n        except (OverflowError, ValueError):\n            return False\n        return math.isfinite(n) and 0 <= n <= 1e12\n\n    def count(value):\n        return type(value) is int and 0 <= value <= 1_000_000_000\n\n    def digest(value):\n        return (type(value) is str and len(value) == 64\n                and all(ch in '0123456789abcdef' for ch in value))\n\n    def metric_view(metrics):\n        if type(metrics) is not dict:\n            return {}\n        out = {}\n        value = metrics.get('status')\n        if type(value) is str and value in metric_statuses:\n            out['status'] = value\n        value = metrics.get('role')\n        if type(value) is str and value in roles:\n            out['role'] = value\n        value = metrics.get('last_phase')\n        if type(value) is str and value in phases:\n            out['last_phase'] = value\n        value = metrics.get('error_kind')\n        if type(value) is str and value in error_kinds:\n            out['error_kind'] = value\n        for key in (\n            'prompt_tokens', 'generated_tokens', 'requested_tokens',\n            'input_message_count', 'duration_s', 'ttft_s',\n            'elapsed_in_last_phase_s', 'tokens_per_second',\n            'n_ctx', 'n_batch', 'threads', 'context_tokens',\n        ):\n            value = metrics.get(key)\n            if number(value):\n                out[key] = value\n        durations = metrics.get('stage_durations_s')\n        if type(durations) is dict:\n            out['stage_durations_s'] = {\n                key: value for key, value in durations.items()\n                if key in duration_keys and number(value)\n            }\n        admission = metrics.get('prompt_admission')\n        if type(admission) is dict:\n            safe_admission = {}\n            if admission.get('revision') == admission_revision:\n                safe_admission['revision'] = admission_revision\n            value = admission.get('status')\n            if type(value) is str and value in admission_statuses:\n                safe_admission['status'] = value\n            for key in ('original_prompt_tokens', 'prompt_tokens', 'target_tokens'):\n                value = admission.get(key)\n                if number(value):\n                    safe_admission[key] = value\n            if type(admission.get('source_text_rewritten')) is bool:\n                safe_admission['source_text_rewritten'] = admission['source_text_rewritten']\n            layers = admission.get('removed_layers')\n            if type(layers) is list:\n                safe_admission['removed_layers'] = [\n                    value for value in layers\n                    if type(value) is str and value in removed_layers\n                ][:32]\n            out['prompt_admission'] = safe_admission\n        return out\n\n    safe_roles = {}\n    raw_roles = report.get('roles')\n    if type(raw_roles) is dict:\n        for role in roles:\n            entry = raw_roles.get(role)\n            if type(entry) is not dict:\n                continue\n            safe = {}\n            if type(entry.get('ok')) is bool:\n                safe['ok'] = entry['ok']\n            if number(entry.get('duration_s')):\n                safe['duration_s'] = entry['duration_s']\n            if type(entry.get('metrics')) is dict:\n                safe['metrics'] = metric_view(entry['metrics'])\n            if 'error' in entry:\n                safe['error_kind'] = 'ERROR'\n            offer = entry.get('structured_offer')\n            if type(offer) is dict:\n                safe['offer'] = {\n                    'present': True,\n                    'verified_quote_count': offer.get('verified_quote_count', 0)\n                        if count(offer.get('verified_quote_count')) else 0,\n                    'rejected_quote_count': offer.get('rejected_quote_count', 0)\n                        if count(offer.get('rejected_quote_count')) else 0,\n                }\n            if count(entry.get('embedding_dim')):\n                safe['embedding_dim'] = entry['embedding_dim']\n            if number(entry.get('embedding_squared_norm')):\n                safe['embedding_squared_norm'] = entry['embedding_squared_norm']\n            if digest(entry.get('embedding_hash')):\n                safe['embedding_hash'] = entry['embedding_hash']\n            if type(entry.get('confidence_calibrated')) is bool:\n                safe['confidence_calibrated'] = entry['confidence_calibrated']\n            safe_roles[role] = safe\n\n    config = report.get('effective_config')\n    safe_config = {}\n    if type(config) is dict:\n        for key in (\n            'answer_tokens', 'body_residency_mb', 'context_tokens',\n            'control_seconds', 'deadline_seconds', 'observer_seconds',\n            'observer_tokens', 'output_adapter_seconds', 'retrieval_seconds',\n            'threads',\n        ):\n            value = config.get(key)\n            if number(value):\n                safe_config[key] = value\n\n    revisions = report.get('model_revisions')\n    safe_revisions = {}\n    if type(revisions) is dict:\n        safe_revisions = {\n            role: value for role, value in revisions.items()\n            if role in roles and digest(value)\n        }\n\n    missing = report.get('missing_proofs')\n    safe_missing = []\n    if type(missing) is list:\n        for value in missing:\n            code = missing_proof_codes.get(value) if type(value) is str else None\n            if code is None and type(value) is str and value in safe_proof_codes:\n                code = value\n            if code is not None and code not in safe_missing:\n                safe_missing.append(code)\n            if len(safe_missing) >= 32:\n                break\n\n    status = report.get('status')\n    return {\n        'schema': 'v13.public-native-probe/1',\n        'proof_kind': 'NATIVE_SMOKE',\n        'status': status if type(status) is str and status in top_statuses else 'UNKNOWN',\n        'phone_measured': report.get('phone_measured') if type(report.get('phone_measured')) is bool else False,\n        'full_runner_proof': report.get('full_runner_proof') if type(report.get('full_runner_proof')) is bool else False,\n        'model_revisions': safe_revisions,\n        'effective_config': safe_config,\n        'roles': safe_roles,\n        'missing_proofs': safe_missing,\n        'raw_artifact': 'exports/native-probe.json',\n        'redaction': {\n            'model_outputs': 'REDACTED_FROM_CONSOLE',\n            'body_offer_hypotheses': 'REDACTED_FROM_CONSOLE',\n            'control_payloads': 'REDACTED_FROM_CONSOLE',\n            'raw_artifact_retained_locally': True,\n        },\n    }".encode("utf-8")
RUNTIME_PROBE_OLD = "                elif kind=='probe':\n                    if payload=='sustained':\n                        from .proofs import probe_sustained\n                        self.notice(dumps(probe_sustained(self)))\n                    elif payload=='jef-modes':\n                        from .proofs import probe_jef_modes\n                        self.notice(dumps(probe_jef_modes(self)))\n                    elif payload=='body-state':\n                        from .proofs import probe_body_state\n                        self.notice(dumps(probe_body_state(self)))\n                    elif payload=='step12':\n                        from .proofs import probe_step12\n                        self.notice(dumps(probe_step12(self)))\n                    else:\n                        from .verification import probe\n                        self.notice(dumps(probe(self)))\n                else:raise ValueError('Job unbekannt')".encode("utf-8")
RUNTIME_PROBE_NEW = "                elif kind=='probe':\n                    try:\n                        if payload=='sustained':\n                            from .proofs import probe_sustained\n                            self.notice(dumps(probe_sustained(self)))\n                        elif payload=='jef-modes':\n                            from .proofs import probe_jef_modes\n                            self.notice(dumps(probe_jef_modes(self)))\n                        elif payload=='body-state':\n                            from .proofs import probe_body_state\n                            self.notice(dumps(probe_body_state(self)))\n                        elif payload=='step12':\n                            from .proofs import probe_step12\n                            self.notice(dumps(probe_step12(self)))\n                        else:\n                            from .verification import probe, public_probe_summary\n                            self.notice(dumps(public_probe_summary(probe(self))))\n                    except BaseException:\n                        try:self.store.log('job_error',None,{'kind':'probe','error':'PROBE_ERROR'})\n                        except Exception:pass\n                        self.notice('probe: PROBE_ERROR')\n                else:raise ValueError('Job unbekannt')".encode("utf-8")
RUNTIME_EXCEPTION_OLD = "            except BaseException as exc:\n                self.store.log('job_error',None,{'kind':kind,'error':type(exc).__name__,'detail':str(exc)[:1000]});self.notice(f'{kind}: {type(exc).__name__}: {exc}')\n".encode("utf-8")
RUNTIME_EXCEPTION_NEW = "            except BaseException as exc:\n                if kind=='probe':\n                    try:self.store.log('job_error',None,{'kind':'probe','error':'PROBE_ERROR'})\n                    except Exception:pass\n                    self.notice('probe: PROBE_ERROR')\n                else:\n                    self.store.log('job_error',None,{'kind':kind,'error':type(exc).__name__,'detail':str(exc)[:1000]});self.notice(f'{kind}: {type(exc).__name__}: {exc}')\n".encode("utf-8")
CLI_PROBE_OLD = "        if a.command=='probe':\n            from .verification import probe\n            if a.mode=='sustained':\n                from .proofs import probe_sustained\n                result=probe_sustained(r,a.cycles)\n            elif a.mode=='jef-modes':\n                from .proofs import probe_jef_modes\n                result=probe_jef_modes(r)\n            elif a.mode=='body-state':\n                from .proofs import probe_body_state\n                result=probe_body_state(r)\n            elif a.mode=='step12':\n                from .proofs import probe_step12\n                result=probe_step12(r)\n            else:result=probe(r)\n            print(json.dumps(result,ensure_ascii=False,indent=2));return 0 if result['status'] in {'SMOKE_PASS','JEF_MODES_PASS','VERTICAL_CHECKS_PASS','BODY_STATE_CHECKS_PASS','BOUNDED_STABILITY_PASS'} else 2\n".encode("utf-8")
CLI_PROBE_NEW = "        if a.command=='probe':\n            try:\n                from .verification import probe, public_probe_summary\n                if a.mode=='sustained':\n                    from .proofs import probe_sustained\n                    result=probe_sustained(r,a.cycles)\n                elif a.mode=='jef-modes':\n                    from .proofs import probe_jef_modes\n                    result=probe_jef_modes(r)\n                elif a.mode=='body-state':\n                    from .proofs import probe_body_state\n                    result=probe_body_state(r)\n                elif a.mode=='step12':\n                    from .proofs import probe_step12\n                    result=probe_step12(r)\n                else:result=public_probe_summary(probe(r))\n                print(json.dumps(result,ensure_ascii=False,indent=2))\n                return 0 if result['status'] in {'SMOKE_PASS','JEF_MODES_PASS','VERTICAL_CHECKS_PASS','BODY_STATE_CHECKS_PASS','BOUNDED_STABILITY_PASS'} else 2\n            except Exception:\n                print(json.dumps({\n                    'schema':'v13.public-native-probe/1',\n                    'proof_kind':'NATIVE_SMOKE',\n                    'status':'SMOKE_ERROR',\n                    'phone_measured':False,\n                    'full_runner_proof':False,\n                    'model_revisions':{},\n                    'effective_config':{},\n                    'roles':{},\n                    'missing_proofs':['PROBE_EXECUTION_ERROR'],\n                },ensure_ascii=False,indent=2))\n                return 2\n".encode("utf-8")
EN_PROMPT_OLD = b"Internal offers are fallible hypotheses. "
EN_PROMPT_NEW = b"Internal offers are fallible hypotheses. Do not reveal internal offers or roles. "
DE_PROMPT_OLD = "Interne Angebote sind fehlbare Hypothesen. ".encode("utf-8")
DE_PROMPT_NEW = "Interne Angebote sind fehlbare Hypothesen. Interne Angebote oder Rollen nicht offenlegen. ".encode("utf-8")


def _git_blob_sha1(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def _read_regular(root: Path, relative: str) -> bytes:
    path = root / relative
    if path.is_symlink() or not path.is_file():
        raise ValueError("output-privacy input is missing or unsafe: " + relative)
    return path.read_bytes()


def _replace_once(raw: bytes, old: bytes, new: bytes, label: str) -> bytes:
    count = raw.count(old)
    if count != 1:
        raise ValueError(label + " expected exactly one canonical anchor; found " + str(count))
    return raw.replace(old, new, 1)


def apply_staged_output_privacy(
    code_dir: Path,
    staging: Path,
    *,
    expected_staged_runtime: bytes,
    expected_staged_verification: bytes,
    expected_staged_cli: bytes,
    expected_staged_prompts: bytes,
) -> dict:
    """Patch only the final staged Runtime, verifier, CLI and model-facing prompts."""
    code_dir = Path(code_dir).resolve(strict=True)
    staging = Path(staging).resolve(strict=True)
    source = {}
    for relative, expected_blob in SOURCE_PINS.items():
        raw = _read_regular(code_dir, relative)
        if _git_blob_sha1(raw) != expected_blob:
            raise ValueError("output-privacy source pin mismatch: " + relative)
        source[relative] = raw

    staged = {
        VERIFICATION_PATH: _read_regular(staging, VERIFICATION_PATH),
        RUNTIME_PATH: _read_regular(staging, RUNTIME_PATH),
        CLI_PATH: _read_regular(staging, CLI_PATH),
        PROMPTS_PATH: _read_regular(staging, PROMPTS_PATH),
    }
    expected = {
        VERIFICATION_PATH: expected_staged_verification,
        RUNTIME_PATH: expected_staged_runtime,
        CLI_PATH: expected_staged_cli,
        PROMPTS_PATH: expected_staged_prompts,
    }
    for relative, raw in expected.items():
        if not isinstance(raw, bytes) or staged[relative] != raw:
            raise ValueError("staged output-privacy input differs from verified builder output: " + relative)
    for relative in (VERIFICATION_PATH, CLI_PATH, PROMPTS_PATH):
        if staged[relative] != source[relative]:
            raise ValueError("unexpected upstream transformation before output-privacy overlay: " + relative)

    verification = staged[VERIFICATION_PATH]
    if b"def public_probe_summary(report):" in verification:
        raise ValueError("public probe summary already exists; refusing duplicate sanitizer")
    verification = verification.rstrip() + b"\n\n" + SUMMARY_FUNCTION + b"\n"

    runtime = _replace_once(staged[RUNTIME_PATH], RUNTIME_PROBE_OLD, RUNTIME_PROBE_NEW, "Runtime probe output")
    runtime = _replace_once(runtime, RUNTIME_EXCEPTION_OLD, RUNTIME_EXCEPTION_NEW, "Runtime probe exception boundary")
    cli = _replace_once(staged[CLI_PATH], CLI_PROBE_OLD, CLI_PROBE_NEW, "one-shot probe output")
    prompts = _replace_once(staged[PROMPTS_PATH], EN_PROMPT_OLD, EN_PROMPT_NEW, "English internal-offer prompt")
    prompts = _replace_once(prompts, DE_PROMPT_OLD, DE_PROMPT_NEW, "German internal-offer prompt")

    outputs = {
        VERIFICATION_PATH: verification,
        RUNTIME_PATH: runtime,
        CLI_PATH: cli,
        PROMPTS_PATH: prompts,
    }
    try:
        for relative, raw in outputs.items():
            compile(raw.decode("utf-8"), str(staging / relative), "exec")
    except (SyntaxError, UnicodeError) as exc:
        raise ValueError("staged output-privacy overlay does not compile") from exc
    if (b"public_probe_summary(probe(self))" not in runtime
            or b"probe: PROBE_ERROR" not in runtime
            or b"public_probe_summary(probe(r))" not in cli
            or b"SMOKE_ERROR" not in cli
            or b"Do not reveal internal offers or roles." not in prompts
            or DE_PROMPT_NEW not in prompts):
        raise ValueError("staged output-privacy postconditions failed")
    return outputs
