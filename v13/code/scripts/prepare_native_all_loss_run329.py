#!/usr/bin/env python3
"""Run329: isolated opt-in all-token loss patch after original Run319 source prep.

No original registered C++ source, cohort or Run319 checkpoint patch is edited.
This is a source-only candidate, not native training evidence.
"""
import argparse
import hashlib
import json
from pathlib import Path

SCHEMA = "V13_RUN329_ALL_TOKEN_LOSS_SOURCE_PREP_V1"
RUN319_PREPARED_SHA = "31f702390553edf017154be48f2f636b3e2d1b86ab56147ba6a751def480f770"
GATES = {"STEP2": "UTILITY_FAIL", "B3_L1": "FAIL", "Body_JEPA": "UNAVAILABLE",
         "jepa_weight": 0, "V13": "INCOMPLETE"}

# Every patch anchor must occur exactly once in the frozen Run319 prepared source.
TRANSFORMS = (
    (
        '    params.cache_type_v = GGML_TYPE_F32;\n',
        '    params.cache_type_v = GGML_TYPE_F32;\n'
        '    // Run329 opt-in: original Run320 loss_mode=all, no answer spans in the stream.\n'
        '    const char * loss_mode_env = std::getenv("V13_LOSS_MODE");\n'
        '    if (loss_mode_env && std::strcmp(loss_mode_env, "all") != 0 &&\n'
        '            std::strcmp(loss_mode_env, "answer") != 0) {\n'
        '        LOG_ERR("V13_LOSS_MODE must be all or answer\\n"); return 15;\n'
        '    }\n'
        '    const bool loss_all = loss_mode_env && std::strcmp(loss_mode_env, "all") == 0;\n'
        '    fprintf(stderr, "V13_LOSS_MODE %s\\n", loss_all ? "all" : "answer");\n',
    ),
    (
        '    if (!tokenize_marked(ctx, params.prompt, tokens, kind)) {',
        '    if (loss_all && params.prompt.find_first_of(std::string("\\x01\\x02\\x03\\x04", 4)) != std::string::npos) {\n'
        '        LOG_ERR("all-token loss refuses answer/KL span markers\\n"); return 16;\n'
        '    }\n'
        '    if (!tokenize_marked(ctx, params.prompt, tokens, kind)) {',
    ),
    (
        '            labels[i*n_ctx + j] = kind[k + 1] == ANSWER ? tokens[k + 1] : -1;\n'
        '            n_supervised += kind[k + 1] == ANSWER;',
        '            labels[i*n_ctx + j] = loss_all ? tokens[k + 1] : (kind[k + 1] == ANSWER ? tokens[k + 1] : -1);\n'
        '            n_supervised += loss_all || kind[k + 1] == ANSWER;',
    ),
)


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def transform(text):
    if not isinstance(text, str):
        raise ValueError("candidate source must be UTF-8 text")
    for original, replacement in TRANSFORMS:
        if text.count(original) != 1:
            raise ValueError("original Run319 candidate anchor missing or ambiguous")
        text = text.replace(original, replacement, 1)
    if text.count('const bool loss_all =') != 1 or text.count('V13_EPOCH_CHECKPOINT') < 2:
        raise ValueError("all-token mode or original checkpoint control missing")
    return text


def prepare(source, out):
    source, out = Path(source), Path(out)
    if not source.is_file() or source.is_symlink() or digest(source) != RUN319_PREPARED_SHA:
        raise ValueError("original Run319 prepared candidate SHA drift")
    if out.exists() or out.is_symlink() or not out.parent.is_dir():
        raise FileExistsError("refusing to overwrite candidate or create unknown parent")
    original = source.read_bytes()
    result = transform(original.decode("utf-8"))
    with out.open("x", encoding="utf-8", newline="") as f:
        f.write(result)
        f.flush()
        import os
        os.fsync(f.fileno())
    if source.read_bytes() != original:
        raise ValueError("original Run319 prepared candidate mutated")
    return {"schema": SCHEMA, "status": "SOURCE_PREPARED_NO_NATIVE_TRAINING",
            "run319_prepared_sha256": RUN319_PREPARED_SHA,
            "run329_candidate_sha256": digest(out),
            "run329_candidate_path": str(out),
            "transform_count": len(TRANSFORMS),
            "loss_mode_default": "answer", "loss_mode_opt_in": "all",
            "original_run320_stream_unchanged": True,
            "native_compiled": False, "native_training_executed": False,
            "model_weights_published": False, "gates": GATES}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--receipt", type=Path, required=True)
    a = ap.parse_args()
    try:
        result = prepare(a.source, a.out)
    except (ValueError, OSError, UnicodeError) as exc:
        result = {"schema": SCHEMA, "status": "FAIL_CLOSED",
                  "error": type(exc).__name__ + ": " + str(exc)[:400],
                  "native_training_executed": False, "model_weights_published": False, "gates": GATES}
    a.receipt.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(json.dumps(result, sort_keys=True))
    raise SystemExit(0 if result["status"] == "SOURCE_PREPARED_NO_NATIVE_TRAINING" else 2)


if __name__ == "__main__":
    main()
