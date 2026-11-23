# Same-prefill C3 test

The existing runtime remains the default. This optional read-only test measures whether a bounded native observer can read C3's final 1024D state and complete 65,536-entry output distribution in the **same causal decode**, while leaving greedy first token and continuation unchanged.

After normal installation with `bash STARTEN.sh`, close the chat and run:

```bash
bash TESTEN_NATIVE_PORT.sh
```

The test automatically obtains the already-pinned llama.cpp b10964 source archive, verifies its size/SHA-256 and required source files, and builds a separate small worker against the installed shared libraries. It reuses a build only when the worker/source, compiler, runner, model and library/backend identities match. No pretrained model or production runner is replaced.

Each attempt writes `report.json`, preregistered fixtures/thresholds, exact template token IDs, build/native logs, raw vocabulary/state artifacts, sampled RSS/PSS and process-reaping evidence under `~/v13/exports/native-prefill-<timestamp>/` (or `$V13_HOME/exports/`). The existing coordinator lock rejects concurrent chat use. Ctrl+C requests cancellation; native workers have CPU abort/deadline checks and a parent watchdog. BOOT bounds are two CPU threads, 2,048 context tokens, at most 512 input tokens, three continuation steps, 90 seconds per native call and 768 MiB worker RSS; these are engineering choices, not Redmi measurements.

Useful commands:

```bash
bash TESTEN_NATIVE_PORT.sh --prepare-only
bash TESTEN_NATIVE_PORT.sh --seconds 120 --rss-limit-mb 768
bash TESTEN_NATIVE_PORT.sh --out-dir "$HOME/native-port-attempt-1"
```

`--prepare-only` builds and verifies identities without inference. Full testing renders two fixed actual C3 templates and tests baseline/observer variants plus native prefix boundaries 127/128/129. The report can pass only when every fixed pair supplies actual finite logits, a normalized full distribution, a finite nonzero 1024D live state, identical greedy continuation, verified loaded libraries and reaped processes. Preview text is decoded from actual greedy native tokens; it is a short diagnostic prefix, not a scored final answer.

A successful result is **observer invariance only**. It does not establish compatibility with older embedding-mode features or learned heads, improved latency, persistent/reused KV, semantic correctness, receiver injection, body training, full Canon completion, or Android performance unless the attempt was actually run on Android. Failed attempts remain failed and retain their raw artifacts; missing dependencies/cache/inference produce explicit errors, never synthetic features.

The retained Linux attempt `docs/proofs/portable-prefill-native-evening-20261008/report.json` passed all five actual pairs (ten native worker calls), including the 231-token exact template and physical-batch boundary prefixes. Observer-on/off logits and full distributions matched exactly in this attempt, with identical greedy continuations and sampled worker RSS up to 307.7 MB. This proves the stated observer-invariance scope on that Linux device only; the Termux path still needs an actual phone run.
