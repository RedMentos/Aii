# Native C3 streaming BodyPort

After the existing phone installation completes, close `v13 chat` and run from the extracted source folder:

```bash
bash TESTEN_NATIVE_STREAM.sh --prompt 'Erkläre kurz, was du ausführen kannst.' --max-tokens 64
```

The default prompt is the unchanged greeting fixture. `--max-tokens 128` increases the bounded output limit. Native EOG ends output sooner. Actual incremental text appears during generation; exact token IDs/bytes, source/model/library bindings, resource samples, stop reason and process cleanup remain in the reported export directory. Each fresh attempt uses its own directory. Cancellation with Ctrl+C reaps the worker. The worker has a 90-second ceiling and the controller enforces an RSS bound (default 768 MiB).

```bash
bash TESTEN_NATIVE_STREAM.sh --prepare-only
bash TESTEN_NATIVE_STREAM.sh --baseline-zero --max-tokens 64
```

Preparation compiles against the existing pinned installation and runs command/client guards without model inference. The second command compares actual unpaused streaming against one paused zero-bias resume: full prefill state, logits and probabilities, generated native IDs/bytes, continuation and stop reason must match. `--pair` instead runs zero and an explicitly authored numeric first-token fixture; it does not demonstrate learned quality. Custom prompts still use the actual model template and native tokenizer, bounded to 512 exact untrimmed prompt tokens.

The adjacent Python client is `scripts.native_prefill_stream_client.StreamingOutputSession`. The caller owns the existing coordinator lock and supplies an exact measured context, a previously prepared `bind_installed(home)` binding, cancellation event and deadline. In a context manager, call `pause()` once and iterate `resume([])` for actual TOKEN events and the final COMPLETE event. A numeric resume permits at most 16 unique vocabulary rows and absolute bias at most 12, only at the first position. All later tokens use unbiased native decoding in the same context, with no reload or additional prefill. Exact piece bytes are authoritative; the client reassembles split UTF-8 incrementally for display.

This port has the explicit ABI `V13_C3_CAUSAL_STREAM_STATE_LOGITS_1024_65536_V2`, bound to worker/client/helper sources, executable and pinned libraries/model. Old approved heads are refused; no learned-head loader exists here. The established four-token session, production chat, approvals and model weights remain unchanged. Compilation/guards alone do not establish native streaming, learned bridge quality, latency improvements or phone performance.
