> **SUPERSEDED — 2026-11-24 run 31.** The A4/N10 code port described below was temporarily placed on PR #2448, then reverted to avoid duplicating the already-owned Boss integration in PR #2443. Current PR #2448 no longer contains the A4/N10 files or dedicated workflow. The same reviewed bytes are already present on Boss branch `boss/v14-memory-forget-lifecycle-composition-20261123-run11-clean`: `attention.py` blob `ecaf39b1b8ea0edad7f4a39774230b3cbed1d5eb`, `neuromod.py` blob `fbb02147cbcfff10896736a20838fbce08d7409b`, receipt test blob `200085b88497af331beb49eaf061944ad30542de`, workflow blob `05718e823aa2d5d78aa93a0fe57e8ff2f4dc2c57`; Core's guard blob `ecdbdfa6dc2df7e2cfd0764bdeded8dc9f4911cc` contains the new attention SHA-256 allowlist. PR #2443 is still OPEN / DRAFT / NOT_MERGED, with zero check-runs and current workflow records `startup_failure`/zero jobs; no acceptance or deployment is claimed. This file below is historical evidence of the attempted port, not current PR #2448 contents.

**PR #2448 reversion commits:** attention.py restored `ee08a65644958780c64fd9f6fc1dfb7e972252d5`; neuromod.py restored `214157e7d90ded915087d8e9d6e158ebe7a06b0b`; test_attention.py restored `9fdbfa4e5eb42639d52beeb3f5c3382df42b3c43`; duplicate receipt test deleted `1ddd5109596a3a42ee815e3a67baf7a46a5a7634`; duplicate workflow deleted `3b0416862c75c780b0a3de46d73fce6db72bb010`. PR #2448 continues to own only its RAW EAR/Teacher Ear/duplex changes in this area.

---

# Research & Perception — A4 source-bound outcome → N10 transactional feedback (2026-11-24 run 30)

## Ported functional slice

The separate Perception PR #2433 carried a source-bound A4 outcome path that was still missing from the current release base. Its branch was 42 commits ahead and 82 behind current release, so the entire PR was not merged or copied. The A4/N10-owned files were selectively ported to the current #2448 branch.

- `attention.py`: exact source-bound A4 re-look outcome verification. It requires a granted AttentionResponse tied to the exact AttentionRequest/event/generation, deduplicates SourceRefs, checks the supplied source digest and re-reads the persisted span before calculating source coverage. It stores an exactly-once durable receipt.
- `neuromod.py`: `signal_in_transaction()` inserts the N10 ModulatorPacket through the same active Store transaction as the A4 policy update and receipt. If insertion fails, the policy/receipt/modulator roll back together.
- Negative prediction error remains signed as `reward_error`; surprise is absolute magnitude, and negative usefulness adds `action_error`. `recent_modulators()` carries the signed value into the next event's attention gain/caution path.
- The real Runtime call site already exists at `runtime.py`: after C3 output, it invokes `attctl.controller(self).source_outcome(eid, text, output)`. This port makes that consumer's implementation durable and source-verified; it does not create a new Runtime route.
- Tests cover positive coverage, omission/negative error, tampered source rejection, exactly-once receipt, eviction/replay protection, concurrent duplicate outcome, rollback if N10 insertion fails, restart persistence, and signed reward-error propagation. This is Store/SQLite policy feedback, not body-weight training or JEPA latent learning.

## Why selective port was safe

- PR #2433 was based on `dfa3945b2bbfdb65d932db74e02f402435494e84`; GitHub compare confirms current release base `8d93236c753f0194224c19edc7411d8d7082b1d6` is 82 commits ahead and has **no intervening changes** to `attention.py`, `neuromod.py` or `test_attention.py`.
- The three existing files were copied byte-for-byte from the #2433 implementation and read back; the new receipt test and dedicated workflow were copied as new files. No stale speaker/teacher/audio files from #2433 were copied over the newer #2448 RAW EAR/Teacher Ear/duplex implementation.
- Port commits:
  - `ef3c45b96ed67421f29fa4c34471a589fbba9bed` — attention.py; blob `ecaf39b1b8ea0edad7f4a39774230b3cbed1d5eb`
  - `7a44c2f07c249fb4d4fb9e448fa6717ecbafd58b` — neuromod.py; blob `fbb02147cbcfff10896736a20838fbce08d7409b`
  - `80d7aba94fe264579b4acaee83abac5da87ba63e` — test_attention.py; blob `d6b9004ac0a738cc9f134d90817cba8cdf961316`
  - `73d220fd4af82ab85296d3dbaf2908dba7e7e2b3` — test_attention_outcome_receipt_v14.py; blob `200085b88497af331beb49eaf061944ad30542de`
  - `c708f7970d1757889435516e27370003ae83a6d6` — dedicated workflow; blob `05718e823aa2d5d78aa93a0fe57e8ff2f4dc2c57`
- Exact source SHA-256 already independently reported for Core pin review: `attention.py = 58e68ce790c8754a4b5362e3e26f3ffbbdfe3455db99534ea518d1f58c5c280e`; `neuromod.py = e01f541874f401bf2996603d79e0cf24463aa16ed5c3902534f37678c1c72ce0`.

## Tests and current blocker

- A dedicated workflow `.github/workflows/v14-attention-source-bound-outcomes.yml` now compiles the A4/N10 modules and runs the source-bound receipt tests plus existing Attention/Neuromod tests on Python 3.13 and 3.14.
- LOCAL_LINUX: no full checkout is mounted and GitHub DNS still fails; no local compile/pytest was run for these new bytes.
- CI: the current branch's latest push/PR Actions runs (through head `c708f797...`) ended `startup_failure` with zero jobs. No workflow test process ran; no PASS or code-test FAIL is claimed.
- Known integration pin blocker: Core's `record_only_controller_guard_20261116.py` still allows only the old `attention.py` SHA-256 `0d3c0d00492d809c818874cf83ddd723867e77cfc5c50236dac18eddc8422739`. It must be updated to the exact current `attention.py` bytes (SHA-256 above), then the guard/recovery/stage/deployer nested pins must be recomputed bottom-up. Core owns that guard chain; no pin was weakened or modified here.
- Android/Redmi: no device test, no microphone, no native ASR, no full C3 answer, no weight update. Latest sanitized public #1904 comment 7108089370 still reports base `8d93236` installed, auto-update enabled, Runtime `CI_WAIT`, and AI runtime `STOPPED_BY_USER` / autostart false. Preserve stop state; candidate NOT_DEPLOYED / REDMI_UNVERIFIED.

## Scope classification

- A4 source-bound outcome → N10 signed modulation: CODE_PRESENT / WIRED_TO_EXISTING_RUNTIME_CALLSITE / SYNTHETIC_STORE_TESTS_ADDED_NOT_RUN.
- Durable exactly-once and transaction rollback: test assertions added, not yet executed on this head.
- Numeric model-weight change, cross-organ gradient, JEPA latent utility, Android/Redmi acceptance: NOT_IMPLEMENTED / NOT_VERIFIED by this slice.
- No model, weight, permission, device data or updater state changed.

## Next executable step

1. Core: rebind the controller guard and all dependent recovery/stage/deployer hashes to the exact `attention.py` source SHA above; keep fail-closed checks.
2. Restore runnable exact-head Actions, then run the dedicated A4/N10 workflow on Python 3.13/3.14 plus staged Runtime, integrated regression, migration, privacy and consent-revocation checks.
3. QA/Boss: review that source-outcome heuristic is only a local attention-policy signal, not truth or body-weight learning. Keep official Age 0 and RECORD_ONLY/SHADOW boundaries unchanged.
4. After review, continue the whole-Canon path; do not replace RAW EAR/voice/Android/B1/B2/B3/JEPA scope with this A4 slice.

**User action: none.** Do not restart the stopped phone, request a manual Termux command, change permissions or download a model.
