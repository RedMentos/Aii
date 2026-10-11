# Isolated causal output diagnostic

`tests/integration_causal_output_lifecycle.py` uses the existing Runtime, original F5 feedback, recorded exporter, unchanged numerical trainer and existing individual Generation approval. It adds no production architecture. The 46 query/reference pairs were preregistered before observing native results: the first46 original-order entries from the existing128-row greeting/thanks fixture. They are authored TEST_OPERATOR references, never genuine user training data or approval.

The fixed deterministic partitions contain25 train,13 calibration and8 test sources; each target row has at least2 examples in each partition. The first-token references are exactly `Hallo` and `Danke`. Their IDs come from the pinned real tokenizer, with reusable exact label/model/server/worker/ABI receipts. The collector refuses colliding IDs instead of selecting replacement references.

The installation must already have passed explicit causal preparation. Stop its chat before preparation. Commands below operate on an isolated Store under the proof folder, preserving the installed weights and settings:

```sh
python tests/integration_causal_output_lifecycle.py prepare --installed-home "$HOME/v13" --out /path/to/diagnostic
python tests/integration_causal_output_lifecycle.py collect --out /path/to/diagnostic --row-limit 2
python tests/integration_causal_output_lifecycle.py check --out /path/to/diagnostic
python tests/integration_causal_output_lifecycle.py collect --out /path/to/diagnostic --row-limit 46
python tests/integration_causal_output_lifecycle.py fit --out /path/to/diagnostic
```

`--row-limit` is an absolute prefix length, making collection resumable between completed rows without repeating native prefill. Every accepted event, actual completed/reaped answer, original explicit test feedback and portable export is checkpointed. Actual checked native artifacts are copied outside Runtime's last8-folder retention before the next turn. Each portable export revalidates the original context, observation hash, native protocol and current permission, and performs zero native prefill. Exact code, corpus, configuration, installed source, library, tokenizer, model and worker bindings must match on resume. A separate attempt lock excludes concurrent collectors; the normal Store lock excludes concurrent chat/export.

An interrupted accepted native turn is preserved. SIGINT/SIGTERM unwind through Runtime cleanup; a failed or ambiguous native result is terminal and is never silently retried or skipped. Completed prefixes can resume after reopening the app/process. A source/configuration change refuses continuation. Copying these diagnostic files does not recreate missing native installation files.

`fit` requires all46 original rows and uses the unchanged utility, calibration, source-disjoint support, gradient, repeat, reload, retention and first-token gates. It preserves every evaluated failure and stops without prompt/scorer/gate changes. A passing offline candidate is independently replayed by the existing import path into a pending update; it remains unapproved. An interrupted fit is retained for inspection, not automatically rerun.

Only after all original gates pass, this separate explicit command simulates TEST_OPERATOR approval in the isolated Store:

```sh
python tests/integration_causal_output_lifecycle.py consume --out /path/to/diagnostic --test-approval
```

It uses existing `:approve`, restarts the Runtime, measures all8 original held-out consumers with actual native first-token IDs and unbiased remaining positions, and stops on an evaluated consumer failure. Successful consumers are followed by source-permission revocation and rollback, each measured through a real zero-fallback Runtime turn. The installed model hash and Store integrity are checked. This is a targeted first-token diagnostic, with no general answer-quality, semantic OOD, body-learning, genuine user approval or full-architecture claim.

Software guards are in `tests/test_causal_diagnostic_collector.py`; they use explicitly synthetic seams and make no native model calls. Native collection, fitting and consumption reports are separate evidence, never inferred from these software tests.
