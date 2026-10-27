#!/usr/bin/env python3
"""BP1 genuine QAD C3 FP32 and QAD GGUF smoke; manual, serial, no training."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
import urllib.request

REVISION = "657e078c94084481950a2d555a941481f715536b"
MASTER_SHA = "1d90518482c4ec204bebb4820bbaee4f8a38c5a6df72256f86bcd21fe52ad079"
GGUF_SHA = "3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d"
PROMPTS = (
    "What is 2 + 2?",
    "Say hello in one sentence.",
    "What is the capital of France?",
    "Give one short reason why source evidence matters.",
)
SEED = 13
MAX_TOKENS = 24
GATES = {"STEP2": "UTILITY_FAIL", "B3_L1": "FAIL", "Body_JEPA": "UNAVAILABLE",
         "jepa_weight": 0, "Redmi_measured": False, "V13_complete": False}


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def rss_kib(pid):
    try:
        for line in Path(f"/proc/{pid}/status").read_text().splitlines():
            if line.startswith("VmHWM:"):
                return int(line.split()[1])
    except (OSError, ValueError):
        pass
    return None


def save_exclusive(path, obj):
    with Path(path).open("xb") as f:
        f.write((json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode())
        f.flush()
        os.fsync(f.fileno())


def common(mode, model_sha):
    return {"schema": "V13_BP1_QAD_NATIVE_SMOKE_V1", "mode": mode, "revision": REVISION,
            "model_sha256": model_sha, "prompts": list(PROMPTS), "seed": SEED,
            "max_new_tokens": MAX_TOKENS, "temperature": 0, "gates": GATES,
            "training_executed": False, "model_utility_proven": False,
            "evidence_class": "LINUX_NATIVE_CLOUD_ONLY_IF_ACTUALLY_EXECUTED"}


def tensor_input_ids(value, torch_module):
    """Transformers 5.9 may return BatchEncoding, not a dict or tensor."""
    if not isinstance(value, torch_module.Tensor):
        try:
            value = value["input_ids"]
        except (KeyError, TypeError):
            raise ValueError("tokenizer did not return input_ids tensor") from None
    if not isinstance(value, torch_module.Tensor):
        raise ValueError("tokenizer input_ids is not a torch tensor")
    return value


def hf(model_dir):
    model_dir = Path(model_dir)
    master = model_dir / "model.safetensors"
    if sha(master) != MASTER_SHA:
        raise ValueError("QAD FP32 source master SHA mismatch")
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    torch.set_num_threads(4)
    torch.manual_seed(SEED)
    tokenizer = AutoTokenizer.from_pretrained(str(model_dir), local_files_only=True, trust_remote_code=False)
    model = AutoModelForCausalLM.from_pretrained(str(model_dir), dtype=torch.float32, local_files_only=True)
    model.eval()
    records = []
    for prompt in PROMPTS:
        ids = tokenizer.apply_chat_template([{"role": "user", "content": prompt}],
                                            add_generation_prompt=True, tokenize=True,
                                            return_tensors="pt")
        ids = tensor_input_ids(ids, torch)
        start = time.monotonic()
        with torch.inference_mode():
            output = model.generate(ids, max_new_tokens=MAX_TOKENS, do_sample=False,
                                    use_cache=True, pad_token_id=tokenizer.eos_token_id)
        response = tokenizer.decode(output[0][ids.shape[-1]:], skip_special_tokens=True)
        records.append({"prompt": prompt, "response": response, "seconds": round(time.monotonic()-start, 3),
                        "new_tokens": int(output.shape[-1] - ids.shape[-1]), "vmhwm_kib": rss_kib(os.getpid())})
    result = common("QAD_FP32_TRANSFORMERS", MASTER_SHA)
    result.update({"records": records, "torch_version": torch.__version__,
                   "transformers_version": __import__("transformers").__version__,
                   "observed_process_vm_hwm_kib": rss_kib(os.getpid())})
    return result


def stop(proc):
    if proc.poll() is None:
        proc.terminate()
    try:
        proc.wait(timeout=12)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=12)


def gguf(model, server, log_path, port=8834):
    if sha(model) != GGUF_SHA:
        raise ValueError("QAD deployed GGUF SHA mismatch")
    if not Path(server).is_file() or not os.access(server, os.X_OK):
        raise ValueError("native server binary not executable")
    with Path(log_path).open("ab") as log:
        proc = subprocess.Popen([str(server), "-m", str(model), "--host", "127.0.0.1",
            "--port", str(port), "-c", "2048", "-t", "4", "-np", "1",
            "--no-webui", "--no-warmup"], stdout=subprocess.DEVNULL, stderr=log)
        try:
            healthy = False
            for _ in range(120):
                if proc.poll() is not None:
                    raise RuntimeError("owned QAD GGUF server exited")
                try:
                    with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=1) as r:
                        healthy = json.loads(r.read()).get("status") == "ok"
                    if healthy:
                        break
                except (OSError, ValueError):
                    pass
                time.sleep(1)
            if not healthy:
                raise RuntimeError("QAD GGUF server not healthy")
            records = []
            for prompt in PROMPTS:
                payload = json.dumps({"messages": [{"role": "user", "content": prompt}],
                    "temperature": 0, "seed": SEED, "max_tokens": MAX_TOKENS,
                    "cache_prompt": False, "chat_template_kwargs": {"enable_thinking": False}}).encode()
                req = urllib.request.Request(f"http://127.0.0.1:{port}/v1/chat/completions", payload,
                                             {"Content-Type": "application/json"})
                start = time.monotonic()
                with urllib.request.urlopen(req, timeout=180) as r:
                    result = json.loads(r.read())
                response = result["choices"][0]["message"]["content"]
                if not isinstance(response, str):
                    raise ValueError("invalid native C3 output")
                records.append({"prompt": prompt, "response": response,
                                "seconds": round(time.monotonic()-start, 3),
                                "new_tokens": result.get("usage", {}).get("completion_tokens"),
                                "vmhwm_kib": rss_kib(proc.pid)})
            result = common("QAD_Q4_GGUF_LLAMA_CPP", GGUF_SHA)
            result.update({"records": records, "server_sha256": sha(server),
                           "observed_server_vm_hwm_kib": rss_kib(proc.pid),
                           "server_exit_reaped": True})
            return result
        finally:
            stop(proc)


def _same_preregistered_value(actual, expected):
    """Type-strict recursive equality; Python considers True == 1 otherwise."""
    if type(actual) is not type(expected):
        return False
    if isinstance(expected, dict):
        return (actual.keys() == expected.keys() and
                all(_same_preregistered_value(actual[key], value)
                    for key, value in expected.items()))
    if isinstance(expected, list):
        return (len(actual) == len(expected) and
                all(_same_preregistered_value(a, b) for a, b in zip(actual, expected)))
    return actual == expected


def compare(hf_report, gguf_report):
    if not isinstance(hf_report, dict) or not isinstance(gguf_report, dict):
        raise ValueError("invalid source model arms")
    if hf_report.get("mode") != "QAD_FP32_TRANSFORMERS" or gguf_report.get("mode") != "QAD_Q4_GGUF_LLAMA_CPP":
        raise ValueError("invalid source model arms")
    if hf_report.get("model_sha256") != MASTER_SHA or gguf_report.get("model_sha256") != GGUF_SHA:
        raise ValueError("model source hashes mismatch")
    for report, mode, source_sha in (
        (hf_report, "QAD_FP32_TRANSFORMERS", MASTER_SHA),
        (gguf_report, "QAD_Q4_GGUF_LLAMA_CPP", GGUF_SHA),
    ):
        for key, expected in common(mode, source_sha).items():
            if not _same_preregistered_value(report.get(key), expected):
                raise ValueError(f"preregistered native {mode} {key} mismatch")
    a, b = hf_report.get("records"), gguf_report.get("records")
    if not isinstance(a, list) or not isinstance(b, list) or len(a) != 4 or len(b) != 4:
        raise ValueError("incomplete native paired records")
    rows = []
    for i, (left, right) in enumerate(zip(a, b)):
        if left.get("prompt") != PROMPTS[i] or right.get("prompt") != PROMPTS[i]:
            raise ValueError("prompt pair mismatch")
        if not isinstance(left.get("response"), str) or not isinstance(right.get("response"), str):
            raise ValueError("non-string native answer")
        rows.append({"prompt_index": i, "exact_text_match": left["response"].strip() == right["response"].strip(),
                     "hf_chars": len(left["response"]), "gguf_chars": len(right["response"])})
    return {"schema": "V13_BP1_QAD_NATIVE_SMOKE_COMPARISON_V1", "rows": rows,
            "exact_text_matches": sum(x["exact_text_match"] for x in rows),
            "diagnostic_only": True, "tensor_parity_proven": False,
            "learned_utility_proven": False, "training_executed": False,
            "redmi_measured": False, "gates": GATES}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--mode", required=True, choices=("hf", "gguf", "compare"))
    p.add_argument("--model")
    p.add_argument("--server")
    p.add_argument("--log")
    p.add_argument("--hf-report")
    p.add_argument("--gguf-report")
    p.add_argument("--out", required=True)
    a = p.parse_args()
    if a.mode == "hf":
        if not a.model:
            p.error("hf requires --model QAD directory")
        result = hf(a.model)
    elif a.mode == "gguf":
        if not all((a.model, a.server, a.log)):
            p.error("gguf requires --model --server --log")
        result = gguf(a.model, a.server, a.log)
    else:
        if not all((a.hf_report, a.gguf_report)):
            p.error("compare requires both reports")
        result = compare(json.loads(Path(a.hf_report).read_text()),
                         json.loads(Path(a.gguf_report).read_text()))
    save_exclusive(a.out, result)
    print(json.dumps({"mode": a.mode, "status": "COMPLETED_NATIVE" if a.mode != "compare" else "DIAGNOSTIC_ONLY",
                      "rows": len(result.get("records", result.get("rows", []))),
                      "training_executed": False}, sort_keys=True))


if __name__ == "__main__":
    main()
