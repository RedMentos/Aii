# STEP2 long-note native-runner preflight — preregistration, 2026-10-28

## Parent and ownership
Independent review-only child of fixture PR #817 head `3fe15a5ed1856a7b87bc5346d28932727b65e70d` (fixture software CI PENDING at prereg time). Do not treat parent as GREEN until exact Actions evidence. This branch owns only `scripts/step2_longnote_runner_preflight.py`, its new tests, workflow and handoff. It must not modify frozen Z2/Z2b/Z2c scripts, fixtures, seeds, models, Canon or production runtime.

## Registered future experiment design, not native execution
Four paired arms with identical fresh ten-fixture corpus and new sampling seeds **27, 28, 29**:
- **TC**: two distinct B1/B2 bodies, B2 pointer OFF, JEF question ON.
- **TP**: two distinct B1/B2 bodies, B2 pointer ON, JEF question ON.
- **SC**: shared-body dual-state B1/B2, B2 pointer OFF, JEF question ON.
- **SP**: shared-body dual-state B1/B2, B2 pointer ON, JEF question ON.

Existing `z2b.run_one` is the candidate harness, but this package must only provide a **dry-run/preflight** spec and temporary reversible configuration binding; it must **not** call real inference or `run_one` from tests or CLI. Native execution requires a separately approved and hash-bound registration, installed model/runner pins, resource/owner check, preregistered workload budget, and a separate execution package. No paid provisioning. Preserve original negative cohorts.

## Predeclared software tests
Verify exact arm-to-control mapping, pointer OFF/ON, shared/two-body and JEF question ON, seeds 27–29 disjoint from 13–19, 10 new fixtures bound, all original `z2b.ARMS`, `z2b.SEEDS`, `z2b.settings`, `z2.FIXTURES` restored after context exit including exception path. CLI `--dry-run` prints deterministic manifest with source/fixture hashes and `native_execution=false`; no inference calls or external model downloads. Fail closed for any attempt to run native without future registration. Run focused+full Linux software tests, privacy/compile/diff raw evidence and private backup.

## Gate and next command
Future native metrics: TP vs TC, TP vs SP, TP vs best single, same-policy dual, prompt-only dual, error profile criterion 3 unchanged, revision current-rule precedence, latency/RSS and source-provenance checks; cluster bootstrap by episode and seed, no post hoc threshold changes. No gate promotion from dry-run. STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; LP3 heldout 0/12; jepa_weight=0; Age0/RECORD_ONLY; V13 incomplete. Owner GPT-6 STEP2 runner preflight, source/test-only. Next: implement reversible binding and tests, verify parent fixture CI before calling candidate GREEN. Budget UNKNOWN.
