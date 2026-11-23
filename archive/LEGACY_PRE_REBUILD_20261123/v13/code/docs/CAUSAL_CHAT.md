# Opt-in same-causal C3 chat

Fresh/default installations use the established server decoder. `bash STARTEN.sh` respects the persisted decoder choice, including a previous explicit causal opt-in. From the extracted source directory, run `bash STARTEN_CAUSAL.sh` to install/check the existing runtime, prepare the pinned causal worker, explicitly select this decoder and open the same persistent chat. An already installed runtime can use:

```bash
bash VORBEREITEN_CAUSAL.sh --enable
bash STARTEN.sh
```

Preparation performs actual compilation and protocol guards, without model inference. It writes a source/model/library/executable-bound preparation marker. An outdated/missing marker or modified model is rejected with a visible diagnosis; the decoder does not silently switch to a different model. Preparation must run while chat is closed. While idle, use `:decode server` to return, `:decode same_causal_zero` for the strict zero baseline or `:decode same_causal` for the individually approved current-ABI output-head consumer. See `CAUSAL_OUTPUT_LIFECYCLE.md` for shadow import/approval controls.

Only turns whose selected answer body is `C3_LANGUAGE` use this path. B1/B2 generation, taps, teacher, replay and approved exact C5 rules keep their existing behavior. For a direct first test, use the chat's simple route (`:route simple`) and ask a short question. The same chat history, source references, source-bound output corrections and partial-output storage still apply.

The temporary pinned llama server applies the actual model template and tokenizer. It performs no feature/generation prefill and is unloaded/reaped before the causal worker starts. The causal worker runs one prefill, exposes the checked actual last hidden state and complete native first-token distribution, accepts one zero-bias resume, then streams actual token pieces from that same native context. UTF-8 pieces are assembled incrementally and stored through the existing C5 report path. Cancellation, absolute user deadline, the worker's 90-second ceiling and 768 MiB RSS bound remain active. Both temporary processes are included in pressure monitoring and reaped on completion/failure.

This ABI admits an exact untrimmed prompt of at most512 native tokens and64 or128 output tokens; EOG can finish sooner. These are native limits, not quality/performance measurements. Preparation chooses64 output tokens when the old setting is incompatible. Longer context gets an explicit diagnostic, preserving all history/rules rather than silently dropping them. The worker uses pinned2048 context,2 threads,128-token batches and deterministic greedy sampling. Telemetry records these actual parameters and requested settings separately; a configured temperature/seed does not change this deterministic decoder.

The package contains no genuinely user-trained approved same-causal head. This explicit zero baseline never loads one; the separate `same_causal` mode has the guarded consumer in `CAUSAL_OUTPUT_LIFECYCLE.md`. Existing separate-prefill output heads are explicitly excluded, with `UNAVAILABLE_NO_APPROVED_SAME_CAUSAL_HEAD` recorded in the turn and decision packet. Human references remain explicit and can be exported by the existing causal dataset exporter. No body training, semantic-truth authority or higher-age permission is gained.

The last eight completed/reaped raw diagnostic directories are retained; active processes and unrelated temporary folders are excluded. Source-bound chat/feedback in Store and permanent exported proofs/checkpoints are preserved. Actual per-turn native artifacts are recorded under the installed `tmp/c3-causal-stream-*` folder. Turn metadata includes token count/IDs, stop reason, same-context identity, zero extra-prefill count, measured template/load/prefill latency, pressure samples and actual process cleanup. This opt-in path is production-connected but experimental; native Linux validation is separate from historical Redmi smoke and sustained target-phone proof.

A controlled native coordinator proof can be run after preparation, with chat closed:

```bash
python3 tests/integration_causal_stream.py --home "$HOME/v13"
```

It uses an isolated Store with exact original pinned model/library/binary references, submits through the real coordinator, checks actual native output/verified completion and unchanged model bytes, records an explicitly authored test-operator reference, verifies a real approved exact C5 rule and answer persistence after restart. Original installed settings and chats remain outside that isolated Store. It does not fit or activate learned weights.
