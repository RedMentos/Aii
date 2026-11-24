# Core handoff — current A3 vision source lifecycle composition

Date: 2026-11-24  
Core PR: stacked follow-up to [Perception PR #2463](https://github.com/RedMentos/Aii/pull/2463)  
Branch: `core/v14-vision-source-lifecycle-current-20261124-run1`  
Base: Perception branch `research-perception/v14-vision-current-20261124-run33` at `cdd7283fb30f0bccdd8ca8a2df46541a17aca3d5` (itself based on release-development SHA `8d93236c753f0194224c19edc7411d8d7082b1d6`)  
Current branch HEAD at this handoff: `7a364ef0895a8c808386f8de678ce4996b211e26`

## Concrete integration defect

Perception PR #2463 changes `v13/code/v13/vision.py` to use a versioned Store snapshot/CAS, exact source lineage, and invalidation of both global and tile projectors. The Core source-lifecycle composer still pinned the older `vision.py` and expected obsolete `ingest/forget/load/save` function bodies. It therefore failed closed with `ValueError: unsupported lifecycle source: vision.py` before materializing the new Perception consumer. Forcing the old replacements would also discard newer Perception behavior, including tile-projector invalidation and its versioned state.

Exact current Perception `vision.py` SHA-256 from its workflow:  
`350573e65eb445b8b83f5517e3bfe07ece04e036055c55fc3e23c79d5b0cc728`.

## Core change

The updated `source_lifecycle_lock_integration_candidate.py` now:

1. Pins the exact current Perception `vision.py` bytes.
2. Preserves Perception's versioned state, source-disjoint projector lineage, replay gate, and global/tile projector invalidation.
3. Routes image-blob publication through `source_lifecycle_candidate.verify_or_create_blob`, under the existing Store write transaction, so image ingest shares the no-clobber digest-verified publication path.
4. Routes post-tombstone image cleanup through `cleanup_unreferenced`, which rechecks live references under the Store lock and reclaims plain, archived `.z`, and digest-bound crash-pending files. A shared live source remains intact.
5. Leaves projector-artifact invalidation and cleanup in the current Perception implementation.

Added a regression that confirms image forget removes only pending staging files for the forgotten digest. Added a disposable materialization runner and a dedicated Python 3.13/3.14 workflow that exercises the real Runtime/SQLite source-lifecycle consumer without modifying the checkout.

## Exact code commits

- `8b3f1d55606fa8b9fcf77a9ab33cda0cda8ba026` — compose current A3 vision with source lifecycle locks.
- `b51444437d565ecdd1d29835cd103f783ea2b439` — selective pending-blob cleanup regression.
- `6c44cb7642a101c79b4d19c3ef56fdcb8142d7c4` — disposable materialized Runtime test runner.
- `7a364ef0895a8c808386f8de678ce4996b211e26` — Python 3.13/3.14 targeted workflow.

## Evidence and limits

- LOCAL_LINUX full Aii checkout/tests: **BLOCKED / NOT_RUN**. No checkout is mounted; `git ls-remote https://github.com/RedMentos/Aii.git` failed because `github.com` DNS did not resolve.
- The dedicated exact-source materialization workflow is the acceptance test for this Core change; its result is recorded after exact-head readback. No local test is inferred from CI.
- Perception's separate A3 source-lineage workflow on base head `cdd7283` still has one independent failing test: `test_retraining_scales_projector_delta_against_previous_replay`, where the current new-source validation returns `NO_HELDOUT_UTILITY_GAIN`. This Core PR does not change that Perception admission policy or test.
- The full staged/integrated chain still needs the downstream `integrated_memory_world_candidate_20261111.py` lifecycle-builder pin and subsequent consumers rebound by Boss/Integrator. This PR intentionally does not edit that shared downstream builder.
- Android/Termux/Redmi: **REDMI_UNVERIFIED** for this change. The latest stored private receipt in the Perception handoff says the AI runtime is `STOPPED_BY_USER` and autostart is off. No relay command, prompt, update request, shell, restart, permission change, model/weight change, or user-data action was performed.
- No Android image capture, native process, learned visual semantics, trained latent coupling, or whole-system completion is claimed.

## Next exact actions

1. Read back this PR's exact HEAD and targeted Python 3.13/3.14 workflow.
2. If the targeted materialized Runtime tests pass, ask Boss/Integrator to rebind `LIFECYCLE_BUILDER_SHA` and the downstream stage/deployer pins against these exact source bytes; do not weaken pin gates.
3. Ask Perception to resolve its independent `NO_HELDOUT_UTILITY_GAIN` test against unseen source groups.
4. QA reruns the full staged/integrated and two-checkout migration matrix after both changes are composed.
5. Keep Redmi stopped; no device action is needed for this code-only checkpoint.
