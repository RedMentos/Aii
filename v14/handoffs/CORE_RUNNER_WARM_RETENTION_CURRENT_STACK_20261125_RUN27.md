# Core & Harness — Runner warm-retention on current fair-budget stack — Run 27

Date: 2026-11-25

## Ownership and dependency

- Owner: Core & Harness.
- PR: https://github.com/RedMentos/Aii/pull/2493
- Parent: https://github.com/RedMentos/Aii/pull/2490, exact base head cb3b8c16ea4061bc9ed2ef33cbff3c179b9bb406.
- Current branch: core/v14-runner-warm-retention-current-stack-20261125-run1.
- Current code/docs head at this handoff: ced17d1a60156c6ea353672f0b3e7c88e24bd62d.
- State: DRAFT / NOT_RELEASED / REDMI_UNVERIFIED.

## Defect and implementation

The existing runner's non-FINAL finalizer always unloaded its llama-server process, while both completion watchdogs killed the child immediately on deadline. If the server had become idle by the time the caller deadline was observed, the next turn still had to cold-load the model.

The new path is restricted to status DEADLINE. It closes the HTTP request, checks the same process object and _loaded_stamp, polls /slots for at most 350 ms (each request bounded to at most 120 ms), validates a non-empty list of dictionaries with exact boolean is_processing, and retains only if every slot is idle and the same process/lifecycle is still current. Otherwise it unloads. Cancellation and native errors still unload immediately. No /slots response, prompt or slot text is persisted.

## Exact source-pin repair

The first staged/phone-offer CI run failed at integrated_native_latent_receiver_candidate_20261122.py because BASE_PINS for v13/runners.py still expected the previous source.

Verified current values:

- v13/runners.py Git blob: 8a17b6cd46103965df74eeec5b2d3b99c371a362; SHA-256: 8c95128d9704586ad1a7fdb48bd6359d569dc60b0e4f7ac98b980e7f5a93ea34.
- Native receiver candidate Git blob after pin update: d4b3eedff89f4093a63c43765270ce9cff2301de.
- Recovery-21 builder Git blob after rebinding NATIVE_RECEIVER_BLOB_SHA1: 133b664938fa2cefafb51856f4cb4fda7e4a4486; SHA-256: 2f9de7c4cc48639f93e581c486c3e982e65817b1885634626f345d5a5ab742b6.
- Integrated stage Git blob after updating BUILDER_SHA: a65600122b9563d5ec2a8dbabf27d9130fed6066; SHA-256: cacd197014ad3bedc9463836a8f1a64059fe08669852dcb1991967a67d15cf93.
- RuntimeDeploy Git blob after updating STAGER_SHA256: e9d871b2019184f7420a14c4dd5179f17cb9cd1e.

Readback confirmed the complete chain. No wildcard or relaxed source pin was added.

## Tests and evidence

- LOCAL_LINUX isolated harness: 6/6 PASS, 0.47 s. This exercises the exact retention decision logic, not the complete Aii source tree.
- Dedicated exact-source CI on the earlier code-only head b09b6734716a30f41a0743df0bb9ff2be886fd54: Python 3.13 and 3.14 both PASS. The current source-pin-rebound head is ced17d1a60156c6ea353672f0b3e7c88e24bd62d; fresh workflows are pending.
- Initial current-stack CI exposed the stale receiver pin, not a warm-retention test failure. The exact source-pin chain was repaired; the post-repair staged/integrated/migration CI must be checked before claiming green.
- Parent #2490 exact head cb3b8c16: 7/7 exact workflow runs SUCCESS before this child.
- Full local Aii checkout: BLOCKED / NOT_RUN; git ls-remote fails because this environment cannot resolve github.com.
- Redmi/Termux: REDMI_UNVERIFIED. No private receipt, native model run, device action or update request.

## User effect and claim boundary

This may avoid a cold model reload when the native server is demonstrably idle after a deadline. It does not improve model prefill throughput, prove an answer is correct, prove B1/B2 offers, prove learned latent coupling, or demonstrate lower Redmi TTFT. V14-001 remains IN_PROGRESS_PARTIAL.

No model/weight, permission, user data, updater, Android companion or device state was changed. A GitHub push/PR is not deployment.

## Next exact actions

1. Poll the exact-head CI runs associated with ced17d1a60156c6ea353672f0b3e7c88e24bd62d.
2. If a new pin/consumer failure appears, repair the exact dependency chain bottom-up and rerun the failing plus staged/integrated/migration checks.
3. Request independent Boss/QA review of #2493.
4. Rebase/compose #2493 with #2492's B1/B2→C4→C3 telemetry on one reviewed base; do not merge parallel chains blindly.
5. After a verified release and fresh consented device receipt, measure actual process reuse, model load time, TTFT and PSS on Redmi. Do not issue an update request or run a native model probe without the required device receipt and separate user approval.

User action: NONE.