# Run417 — exact token counting after the actual Context OS plan

2026-10-26 · independent GPT cross-review of Claude WP-Z5d/PR407 and Run414/PR410 · branch `codex/run417-context-final-token-gate-20261026` stacked on PR410 at `94be24431d447ad146ad5fb5f107fbc28f6134c0`. Not on active Run413 native STEP2 chain or main.

## Reproduced source gap

Run414's optional `context_fit_exact_count=1` invokes the real tokenizer on the pre-plan volatile/history view. Afterwards, `ctxos.controller(...).plan` can replace `messages` with a different packet, and the old runtime immediately generated from that replacement without recounting it. Thus the original `fits=True` is not a guarantee for the final prompt. Also a strict counter exception was logged and swallowed, allowing generation with the unverified view. A C3 same-causal output path has its own 512-token prefill ABI and template; the server runner's count cannot be claimed exact for that separate consumer.

## Implementation

Add `require_final_exact(messages,count,limit)` with integer/overflow/error fail-closed semantics; call it **after** the Context OS plan and **before** output adapter/native generation only when the operator opted into exact mode. Log measured final count and stop the turn with the existing `Unavailable` system-report path on failure, rather than generating with an unverified prompt. Strict pre-plan tokenizer errors now stop the turn instead of silently continuing. `require_native_count_compatible` rejects the unverified C3 same-causal modes in exact opt-in, preserving the default legacy behavior unchanged. Tests use a fake tokenizer whose pre-plan view fits but whose planned view exceeds budget, plus error/invalid count and causal mode controls.

## Claims and gates

Software-only checks, not a native tokenization benchmark. No evidence yet of improved end-to-end accuracy or latency. Native paired Context OS and Redmi measurements required before enabling strict mode by default; the historical PR407 300-row benchmark is untouched. No change to Age, learning, tools, frozen models, Run394/397 cohort, STEP2 UTILITY_FAIL, B3 FAIL, Body-JEPA UNAVAILABLE or `jepa_weight=0`.

## Next

Run exact-head GitHub Actions source tests and privacy scan; independently inspect final runtime diff and one counterexample. Keep this PR separate from active Run413 native owner. If source checks pass, record hashes, raw artifact and explicit unmeasured limitations. Next substantive package: measure/resolve actual planner-tokenization parity on a native host and compare latency with the default, without modifying the frozen STEP2 cohort.
