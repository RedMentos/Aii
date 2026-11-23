# Research/Perception handoff — A3 lifecycle CAS

Date: 2026-11-23 02:11 UTC

## Branch / PR

- PR: https://github.com/RedMentos/Aii/pull/2404 (DRAFT, stacked on PR #2401).
- Branch: `research-perception/v14-vision-lifecycle-cas-20261123-run17`.
- Verified branch HEAD at handoff: `8ff6f344c05852266fcdcb219ede00af41ab32c2`.
- Base: `research-perception/v14-a3-ui-lineage-consumer-20261123-run16` at `21b0c05219629fa6b29833ba60647e133cd0acda`.
- Not a release and not deployed.

## Functional change

Addresses the race identified in the A3 source-forget review: a global or tile projector could be fitted from a source snapshot, then be published after a concurrent forget had cleared that source. Direct image ingest/forget also split registry/source/blob lifecycle operations across transactions.

- `vision.load()` returns a Store-bound versioned snapshot. `vision.save()` performs a version compare-and-swap and validates live IMAGE source, caption and projector lineage before publishing.
- `train()` and `train_tiles()` remove a just-written artifact if their CAS commit is stale; they cannot restore a projector after a forget changed the state version.
- `ingest()` serializes content-addressed blob verification, source-row insertion and vision-registry publication under the Store write transaction.
- `forget()` serializes registry removal, projector invalidation and source tombstoning; last-live-source check plus safe blob unlink share the Store write lock with ingest.
- Malformed legacy projector metadata is cleared fail-closed on forget.
- `vision_ui_frame_ingress.py` now accepts the versioned dict-subclass returned by `vision.load()`; the previous exact `type(state) is dict` check incorrectly rejected the new snapshot and disabled A3 at the UI consumer.
- Learning authority remains `LAB_SHADOW_ONLY`; no Age, weight, model, consent, or release gate changed.

## Exact CI evidence

At HEAD `8ff6f344c05852266fcdcb219ede00af41ab32c2`:

- `V14 vision source-lineage and forget regressions`: PASS, Python 3.13: 27 passed; Python 3.14: 27 passed. Exact `py_compile` step passed.
- `V14 MediaProjection RAW EYE frame ingress`: PASS, Python 3.13: 30 passed; Python 3.14: 30 passed.
- `v13-private-remote-bridge-tests`: PASS on push.
- `V13 staged context and integrated regression`: FAIL/BLOCKED by the downstream QA lifecycle pin. `source_lifecycle_lock_integration_candidate.py` rejects the new exact `vision.py` bytes with `ValueError: unsupported lifecycle source: vision.py`. The full staged-runtime job reported 19 failed, 231 passed, 10 skipped, 2 errors, 41 subtests passed; these failures are downstream of the pin gate, not proof that the A3 tests failed.
- A previous CI attempt failed on the UI consumer's strict dict type check; that consumer was corrected, and the subsequent exact-head frame-ingress suite passed 30/30 on both Python versions.

## Exact staged-source hashes (CI sha256sum)

- `v13/code/v13/vision.py`: `b42b4ceddc04021b968bbf60940b5346c360903887a8de7b58fc532b800cec2d`
- `v13/code/v13/vision_source_lineage.py`: `bb63636c9ae84d345fe1f4e37254de3be87c26990cb320ca058859fd0b51b72f`
- `v13/code/v13/vision_ui_frame_ingress.py`: `4dfde9bc4cde8d555054c353c4636af3d5eb55e24330f2f19f73a6704ece6f0a`

QA must rebind its `vision.py` pin to the exact reviewed hash when this Perception change is integrated; do not weaken the pin or bypass the staged gate.

## Local/device boundary

- LOCAL_LINUX: a separate isolated SQLite/CAS + cleanup-serialization harness passed 2/2. This is a mechanism probe, not a local Aii checkout test.
- Full local Aii checkout/pytest: BLOCKED; no repository checkout is mounted in this worker and GitHub DNS resolution from the container fails.
- TERMUX/Redmi: `REDMI_UNVERIFIED`. No live device receipt, phone test, updater invocation, model download, weight swap or user-data mutation occurred.

## Research connection / next action

- R-101 in `V14_RESEARCH_LEDGER.md` already records the full-reviewed ECML PKDD 2026 ridge-head unlearning paper (arXiv:2603.12977v3). The immediate safe step is concurrency correctness and source revocation, not a claim of exact model unlearning.
- After QA pin-chain acceptance, prototype per-source fp64 sufficient statistics for the standardized A3 ridge head. Measure exact delete/add-back equivalence, numerical drift, disk/RAM cost, restart and rollback before replacing conservative projector invalidation.
- Next integration action: QA updates the staged `vision.py` pin to the exact hash above and reruns the staged migration/source lifecycle chain; then independent review of #2404 and #2401 before any merge.

Status: DRAFT / NOT_RELEASED / REDMI_UNVERIFIED.