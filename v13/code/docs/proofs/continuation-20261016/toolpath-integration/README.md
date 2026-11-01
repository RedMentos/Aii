# K/M toolpath integration — 2026-10-16

K's measured `list_arith` path now coexists with M's calculator forecast and
note-edit proposal/approval path in the coordinator checkout. Original owner
branches and preregistered experimental evidence were not changed.

## Source and scope

M base: `1941d07afeb57299d7d5a466fd1eb44ec2569dfe`.
K feature: `4ed1539fb9fd6ea961fc6145bd98745e5f63adac`, including its explicit
parallel-merge handoff. `upstream-provenance.json` binds exact Git blob identities
for the copied module/test and three supporting rule scripts; each matches.

Semantic changes: add K's typed-value proposer and readable result layer to M's
ToolStep, preserving M's note edits and `_forecast`; register `list_arith` without
enabling it; add K's concise Broker correction. Copy `agi/listarith.py`, its
upstream tests and supporting R3/rule/head experiment scripts unchanged.
Those experiment scripts are dependencies of the upstream regression tests;
their native experiments were not rerun or newly accepted.

Two missing prerequisites were discovered in this M-only snapshot:

* H WP-W2c `text` arguments were absent. The minimal contract from pinned H
  `b65e730447c4589ca3ae755d50bafa441da7d1f7` was ported into `transaction.py`,
  with H's READ_LOCAL-only ToolSpec restriction. Text remains length/type
  bounded data; ordinary `str` shell-string guards remain intact. H's separate
  eligibility feature is not part of this integration.
* G's fix from `c13a281e5a74b0f889cb087d5f580259c2401136` was absent:
  human-approved effects after a terminal proposing turn must reach AG2 directly
  instead of waiting in that turn's abandoned provisional buffer. The real
  software regression failed before this port and passes afterwards.

`before-prerequisite-port.log` preserves the two text-contract errors and the
failed ended-turn grounding check after K was added but before those ports.
`baseline-check.json` separately proves the pinned M base had no list module,
registry entry or proposer. This package does not edit M's `toolforecast.py` or
AGI hub; their existing binding/lifecycle behavior and direct approval scoring
remain in the combined path. During receipt preparation a separate peer changed
`toolforecast.py` for an observation-binding fix, so its current bytes are
explicitly not certified as identical to the base. Parent must bind and test the
final combined peer changes. AGI hub bytes still match M at receipt preparation.

## Validation

`focused-tests.log` and `test-summary.json`: **102 checks run, 101 passed,
one native-tool check skipped**, no failures/errors. No new model or native
inference run. Suites cover:

* All seven copied K tests, including unchanged operations on 360 R4 tasks and
  rule families D/E, exact source-number guards and recipe/correction rendering.
* Five combined tests: disabled/irrelevant requests incur no extraction or taps;
  Age-0 list proposals stay SHADOW; permitted execution goes through real
  schema/enablement/ActionGate/transactions, then Broker correction and AG2;
  calculator and pending-note forecasts survive interleaved list calls and
  restart; approvals after FINAL reach grounding; text stays data-only and
  disallowed for write/network/effect tools.
* Existing M forecast tests, ToolStep/transaction/Broker suites, SourceHandoff
  transport/binding guards and merged native-firing candidate guards.

Only typed C3 extraction, deterministic tap vectors and a narrow Age verdict
are test seams. The policy/enablement/confirmation/transaction path is real.
`list_arith` is explicitly outside the measured forecast worlds: its invocation
records `TOOL_WITHOUT_WORLD` and performs no tap, rather than assigning it a
forecast or extrapolating M's quality results.

No source-binding guard was rebased or weakened. Parent owns full-suite checks,
packaging, current statuses and durable commit/push. `source-manifest.json`
records integrated source hashes; `integration.patch` covers tracked-file edits.
Exact K source snapshots are under `k-source/` for review only, not imported.

## Claim limits

This is software integration evidence, with tools still disabled by default,
Age ceiling unchanged, forecast OFF by default and write calls requiring
per-call approval. No new numerical/model-quality result, Redmi proof, B3
promotion or STEP2 utility pass is claimed. Current competence-v2 learning
quality still needs a separately bound experiment; old v1 results are preserved.
