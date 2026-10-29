# Preregister C3 streaming generator finalization on fail-closed output (2026-10-29)

Review-only child of full software review branch `codex/v13-full-suite-torch-review-20261029-auto10ak` at `12c3c152a5a183f7dd3899761a62d964854f0a97`.

## Observed source concern
The prior opt-in C3 output collector bounds text accumulation, but returns early on over-limit or non-string chunks without explicitly closing a still-referenced generator. The real `LlamaRunner.generate` uses `finally` to finish its resource sampler/audit window. Relying on CPython reference counting to close a generator is not a deterministic lifecycle contract if an iterator remains referenced.

## Frozen witnesses
1. A retained generator yielding an oversized chunk must have its `finally` run before the bounded collector returns `None`.
2. A retained generator yielding a non-string chunk must likewise be closed.
3. A short normal stream remains byte-for-byte unchanged and closed.
4. Existing fake-native C3 source admission, revocation, output contradiction and 32,768-character cap tests remain green.
5. No additional native calls, model pins, permissions, learning, output authority or gate changes.

Implementation hypothesis: put an explicit `close()` call on closable input iterators in a `finally` of `_collect_bounded_output`. Any close exception remains a fail-closed operator error; the outer `query` already unloads C3 in its own `finally`. No real native resource claim from this software-only test.
