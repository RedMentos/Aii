# V13 continuation — 2026-11-07

## Scope and source

Continue the complete v10.16.1 Canon and later user decisions, including all
organs, data paths, mobile actions and genuine local weight learning. New
ideas are additive. Local-first Redmi/Termux is the initial target; cloud
testing does not establish phone performance or phone training. Preserve the
registered negative gates and the user's controls. The actual other chat was
not accessible; its preserved repository and Drive handoffs were consulted.

The old `main` branch `1c661ee` is not the current implementation. This
worktree is based on `ab289ef106f67f8c3b3e39375c8e141934e73755`, from
`codex/run117dh-frozen-preflight-20261106`, on the distinct work branch
`codex/resume-20261106`. This is a review/development lineage, not proof that
its changes are merged into production. Fetch current heads and inspect newer
work before making changes. Read `AGENTS.md`, `v13/AGENTS.md`,
`HANDOFF_CURRENT.md`, the Canon and newer decisions before continuing.

## Test environment and evidence

On the unmodified base, the first full Linux software suite completed 5,386
tests with 23 errors and 57 skips. The errors were missing PyTorch imports and
missing original historical native archives; no assertion failures were
reported. PyTorch 2.5.1+cpu, Transformers 4.44.2 and PEFT 0.13.2 were then
installed in an isolated virtual environment. All 13 required historical
archives were recovered from GitHub Actions and verified against original
SHA-256 and ZIP CRC; see `RESTORE_NATIVE_TEST_INPUTS_20261107.md`.

The ten previously unimportable training modules then passed 66 tests. Three
verified original archives supported 30 independent replay/mutation tests;
these are replays of past evidence, not new phone or model runs. A full suite
using the verified archives and optional dependencies was started against a
separate unchanged worktree. Its eventual terminal result must be read from
the actual log; do not infer it from a launch or an old process ID.

The STEP2 expression diagnostic test can now read its exact original archive
from `V13_STEP2_EXPRESSION_ORIGINAL_ZIP` outside the source tree. Ten focused
tests passed with the original archive; a deliberately changed archive was
refused by the unchanged original hash gate.

## Active finding: approval crash/replay

An independent real-Store probe showed that the original ToolRegistry can
execute a previously approved action twice if the process exits after its
effect but before the proposal's final state is saved. A separate, default-off
candidate is under development and is **not yet connected to Runtime**.
Independent counterexamples also identified cross-tool idempotency/undo
collisions, repeated undo after a crash, user-rule changes racing an effect,
loss of open claims under history trimming, recovery concurrency, limited
telemetry and a Notaus/undo policy discrepancy. Each requires an explicit
counterexample and review before any production claim. Work is owned by the
candidate branch; do not edit any frozen experiment or overwrite other workers.

`RESEARCH_PHONE_TRAINING_20261107.md` records current primary-source research
and a bounded next experiment. Prior Linux native C3 training changed real
weights but did not pass retention/leakage gates; no Redmi training result or
unproven Body-JEPA utility is claimed. The supplied YouTube video's transcript
could not be retrieved because the providers blocked the request; no video
claims were inferred.

The user clarified that the desired idea involves Codex directly changing
open-model weights. The original weight-space-programming report describes
such an edit of Qwen3.5-0.8B, V13's B2 model family; the identification with
the unavailable video is not confirmed. See the new section in
`RESEARCH_PHONE_TRAINING_20261107.md`. An isolated probe of its published
BF16 tensor diff is being developed against the exact pinned source revision;
it is not yet a GGUF model, local learning loop, inference result or Redmi
proof. Preserve the existing B2 fallback and actual learning objectives.

STEP2 remains `UTILITY_FAIL`, B3 remains without promotion, Body-JEPA remains
unavailable for production, and the full blueprint and Redmi validation remain
incomplete. Persist and verify each subsequent meaningful checkpoint; continue
with another authorized path if one path is blocked.
