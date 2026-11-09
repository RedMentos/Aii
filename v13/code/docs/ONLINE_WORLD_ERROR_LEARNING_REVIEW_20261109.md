# Online world and error-learning review — 2026-11-09

Status: **source-hash-bound review candidate only**. This is a child of the other
workstream's PR [#1619](https://github.com/RedMentos/Aii/pull/1619), exact head
`0c8ccbaf34e44cec1f6220401eec3f1cac508a8c`; it does not modify that branch or
the frozen runtime sources. It must not be treated as already deployed. Source
conflicts with other candidates must be reviewed in a separate composed copy.

## What was independently checked

The #1619 runtime diff and original 14 focused tests were read and exercised.
The learner is a real, small NumPy gradient model over own committed T8 action
transitions. Its targets include duration, output length and **technical
completion** (`FINAL` versus a terminal error), not whether an answer is
factually correct. Rehearsal-set loss is a training-buffer diagnostic, not an
independent generalization or retention result. This is neither a full JEPA
nor direct editing of a language model's pretrained GGUF weights.

Four initial counterexamples were reproduced on the exact #1619 source:

1. The automatic after-turn hook trained under default `RECORD_ONLY` without
   explicit activation.
2. A crash after the NPZ write but before the separate cursor write caused the
   same action to be learned again after restart.
3. A processed action with altered content was silently treated as identical.
4. A failed checkpoint left uncommitted parameter/reservoir/RNG changes in
   memory.

The review candidate addresses these paths: opt-in defaults off, Age and
learning-mode/resource/pause/queue gates apply, and one-shot runs require an
explicit operator command. A single atomic checkpoint binds parameters,
replay, RNG and action-content receipts; failures restore a committed or prior
in-memory snapshot. The candidate refuses to guess how to migrate an old
unpaired cursor/checkpoint. Newly eligible sources are checked and rechecked
against the real event, live source references, final output and committed C5
selection. Detected stale, previously learned recent rows quarantine the
in-memory candidate; they are not silently scored. Training checks for a stop
between samples. Policy status and enable/disable are available through
`:growth onlineworld`; this command exists only in the disposable candidate.

`scripts/online_world_integration_candidate.py::build_sources` verifies the
input, relevant dependency and output SHA-256 hashes, applies the pinned patch
in a temporary directory, and returns bytes to place in a separate source copy.
It refuses changed source or an already occupied destination. The tracked files
under `candidates/online_world_20261109/` are review assets, not live modules.

## Verification and limits

* `PYTHONPATH=. /tmp/v13-online-review-venv/bin/python -m pytest -q tests/test_online_world_integration_candidate_20261109.py`: **2 passed**. The isolated child run inside the second test reports **30 passed**, including real Runtime/SQLite tests with a synthetic C3 seam, technical-error and revoked-source cases, stop/restart, atomic checkpoint and content-change counterexamples. The other tests deliberately patch fabricated T8 rows; those are labeled synthetic.
* A separately materialized candidate passed **77 tests and 8 subtests** across `test_world_model.py`, `test_worldmodel_realstore_integration_20261029.py`, `test_worldmodel_stage_binding_20261029.py`, `test_age.py`, `test_age_rights.py`, `test_inputs.py`, `test_growth.py`, `test_runtime_queue.py`, `test_runtime_queue_audit.py`, and `test_world_state.py`.
* `public_repo_privacy_scan.py --base 5e964146579deb22c5ba89a2a03a52a9e4d8aab8 --head 0c8ccbaf34e44cec1f6220401eec3f1cac508a8c`: **CLEAN** for #1619.
* Full unfiltered #1619 pytest initially stopped during collection with 10 errors because Torch was missing. A pinned CPU rerun (`torch==2.5.1+cpu`, `numpy==2.2.6`, `transformers==4.44.2`, `peft==0.13.2`; offline model settings) in the sparse checkout ended **609 failed, 4,733 passed, 51 skipped, 166 errors, 2,614 subtests passed** in 405.80 s. Raw local log SHA-256 `df6cfa13f8864a0ed897097943e1ff723bca3a562e509c4ff4b2ec2fca04ba12`. Many *tracked* fixture/proof/bench paths were absent from that checkout, so it was not a clean classification.
* After expanding the separate checkout to the full tracked `v13/code`, root-level pytest collection initially stopped on 6 duplicate module-name errors because it also collected archived frozen tests in `docs/proofs` (local log SHA-256 `dcdce5911bf2c8581554b161ccdc68be0a335c8645c0cf0045ae77fef7687cc2`). The complete regular test directory was then run, without test exclusions: `HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 PYTHONPATH=.:tests:scripts OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 timeout 1200 /tmp/v13-online-review-venv/bin/python -m pytest -q tests`. Result: **55 failed, 5,350 passed, 51 skipped, 94 errors, 3,022 subtests passed**, 424.11 s, exit 1. Local raw log SHA-256 `8c42aa25896a2bda72c20afa36f0cf16f8ff00fd53fd6ab1859cf7e8db4bd3a2`. Repeated failures include exact SourceHandoff/native-firing source-hash mismatches because #1619 changes frozen runtime bytes; many errors require unavailable original native ZIPs. Other failures remain individually unclassified. This is **RED**, not a full-suite pass, and no raw-log backup is claimed.

Remaining work is material: checks and NPZ replacement are not an atomic
transaction with source revocation; older receipts outside the bounded T8
window are not fully revalidated or unlearned, and restart itself does not
recheck all historical sources. Multiple processes sharing a model directory
are not serialized. Receipt storage is bounded at 65,536 and no reviewed
archival/migration exists. Each checkpoint and source scan can consume time;
only between-sample interruption is tested, not a Redmi latency/resource bound.
No real model, native Android/Redmi, downstream answer benefit, full-system
utility or safe production promotion is proven. `STEP2 UTILITY_FAIL`, B3 L1
FAIL, JEPA gates and Age0 restrictions remain unchanged.

Semantic corrections and genuine ratings are separate source-bound work in
[#1612](https://github.com/RedMentos/Aii/pull/1612),
[#1616](https://github.com/RedMentos/Aii/pull/1616) and
[#1629](https://github.com/RedMentos/Aii/pull/1629); they are not yet connected
to this numeric gradient target. The weight-space paper and its proposed
mapping were recorded separately in
[#1602](https://github.com/RedMentos/Aii/pull/1602). PRs #1620–#1628 and the
new independent Body-port review [#1630](https://github.com/RedMentos/Aii/pull/1630)
remain separate workstreams, not already integrated here.

Next: classify remaining full-suite failures, design source-revocation
invalidation/rebuild with an explicit performance bound, then test a
source-bound composition with the semantic-feedback candidates in a new copy.
Measure actual answer benefit and retention separately before any activation.
