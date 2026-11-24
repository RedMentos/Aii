# Core handoff — current A3 vision source lifecycle composition

Date: 2026-11-24  
Core PR: stacked follow-up to [Perception PR #2463](https://github.com/RedMentos/Aii/pull/2463)  
Branch: `core/v14-vision-source-lifecycle-current-20261124-run2`  
Base: current Perception branch `research-perception/v14-vision-current-20261124-run33` at `18b27e1d639c14f1007d26ecf5c8ebd0b3f71997` (release-development ancestor `8d93236c753f0194224c19edc7411d8d7082b1d6`).

## Concrete integration defect

Perception PR #2463 changes `v13/code/v13/vision.py` to use a versioned Store snapshot/CAS, exact source lineage, and invalidation of both global and tile projectors. The Core source-lifecycle composer still pinned the older `vision.py` and expected obsolete `ingest/forget/load/save` function bodies. It therefore failed closed with `ValueError: unsupported lifecycle source: vision.py` before materializing the new Perception consumer. Forcing the old replacements would also discard newer Perception behavior, including tile-projector invalidation and its versioned state.

Exact current Perception `vision.py` SHA-256 from the source-lineage workflow:  
`350573e65eb445b8b83f5517e3bfe07ece04e036055c55fc3e23c79d5b0cc728`.

## Core change

The updated `source_lifecycle_lock_integration_candidate.py` now:

1. Pins the exact current Perception `vision.py` bytes.
2. Preserves Perception's versioned state, source-disjoint projector lineage, replay gate, and global/tile projector invalidation.
3. Routes image-blob publication through `source_lifecycle_candidate.verify_or_create_blob`, under the existing Store write transaction, so image ingest shares the no-clobber digest-verified publication path.
4. Routes post-tombstone image cleanup through `cleanup_unreferenced`, which rechecks live references under the Store lock and reclaims plain, archived `.z`, and digest-bound crash-pending files. A shared live source remains intact.
5. Leaves projector-artifact invalidation and cleanup in the current Perception implementation.

Added a regression that confirms image forget removes only pending staging files for the forgotten digest. Added a disposable materialization runner and a dedicated Python 3.13/3.14 workflow that exercises the real Runtime/SQLite source-lifecycle consumer without modifying the checkout.

## Code commits

- `3acb77712556bdcdef4c33e169c0e82739f2321d` — compose current A3 vision with source lifecycle locks.
- `e414bbabee1da4394f0464a1074a9efc26c804e3` — selective pending-blob cleanup regression.
- `ced973577c75a7081d552f82ebd642c2b0f70bca` — disposable materialized Runtime test runner.
- `8a6066812cb285ce45624225a984840fe3704c89` — Python 3.13/3.14 targeted workflow.

## Evidence and limits

- LOCAL_LINUX full Aii checkout/tests: **BLOCKED / NOT_RUN**. No checkout is mounted; `git ls-remote https://github.com/RedMentos/Aii.git` failed because `github.com` DNS did not resolve.
- LOCAL_LINUX isolated runner syntax: **PASS**, CPython 3.13.5 `py_compile` on the exact runner source reconstructed from this branch. This does not execute the full candidate.
- The dedicated exact-source materialization workflow is the acceptance test for this Core change; its exact-head result is recorded after readback. No local test is inferred from CI.
- The Perception branch advanced after the first Core attempt; this run-2 branch is based on the newer Perception head `18b27e1d...`, not the earlier `cdd7283...`.
- Full staged/integrated composition still needs the downstream `integrated_memory_world_candidate_20261111.py` lifecycle-builder pin and subsequent consumers rebound by Boss/Integrator. This PR intentionally does not edit that shared downstream builder.
- Android/Termux/Redmi: **REDMI_UNVERIFIED** for this change. The latest stored private receipt in the Perception handoff says the AI runtime is `STOPPED_BY_USER` and autostart is off. No relay command, prompt, update request, shell, restart, permission change, model/weight change, or user-data action was performed.
- No Android image capture, native process, learned visual semantics, trained latent coupling, or whole-system completion is claimed.

## Next exact actions

1. Read back this PR's exact HEAD and targeted Python 3.13/3.14 workflow.
2. If the targeted materialized Runtime tests pass, ask Boss/Integrator to rebind `LIFECYCLE_BUILDER_SHA` and the downstream stage/deployer pins against these exact source bytes; do not weaken pin gates.
3. QA reruns the full staged/integrated and two-checkout migration matrix after the downstream composition.
4. Keep Redmi stopped; no device action is needed for this code-only checkpoint.
