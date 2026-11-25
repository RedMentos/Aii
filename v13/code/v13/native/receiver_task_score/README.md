# Native receiver target-score diagnostic

This directory builds a CPU-only llama.cpp receiver that consumes a bounded matrix
of sender/adapter input embeddings, then teacher-forces target token IDs through
the receiver and returns per-token log-probabilities.

- Pinned upstream: ggml-org/llama.cpp b29c606e28a01b1bc8c1351026a0fa6e616bf6c4 (MIT).
- Input: little-endian float32 rows followed by little-endian int32 target token IDs on stdin; no raw text is accepted.
- Output: hashes/counts are bound in the Python wrapper; native stdout contains only geometry, status and token log-probabilities.
- The Python wrapper binds the output to the receiver GGUF SHA, tokenizer revision, exact candidate input digest, source/session/task metadata and the existing native_receiver_utility evaluator. Its probe_anchor_preserving_candidate helper directly consumes the output of build_anchor_preserving_native_receiver_input and refuses changed authority/production flags.
- No vectors, token IDs, text, weights or adapters are persisted. The Core caller must invoke this only under its NATIVE_RECEIVER approval and serial resource gate, with an authorized/public held-out task source. It performs no training, generation, promotion or B3 enablement.
- TEACHER_FORCED_TARGET_LOGPROB_V1 is a likelihood proxy, not generated-answer correctness or semantic-use proof.
- Synthetic injected executables are always marked SYNTHETIC_FIXTURE. Android/Redmi runs require a private execution-receipt digest and runtime build ID; these fields are evidence-shape checks, not attestation.

Build the native target against the exact pinned llama.cpp checkout with LLAMA_CPP_DIR.
For an isolated math/geometry check without llama.cpp, configure with
-DV14_WITH_LLAMA=OFF and run native_receiver_task_score --selftest.
