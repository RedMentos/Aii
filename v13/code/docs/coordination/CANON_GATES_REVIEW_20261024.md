# V13 canon/gates and phone-measurement review — 2026-10-24

Reviewed base: `cb959052433e01c29afc007e02b93aef373deb7f` (PR #38).
Scope: canonical blueprint **lines 7001–13773 read completely**, roadmap, `ZIELABGLEICH.md`, current handoff, and
`scripts/handy_pflicht.py`, `scripts/train_runner_proof.py`, `scripts/z7_residency_bench.py` plus relevant tests.
This is the second-half canon review, not a claim that this reviewer read its first half.
Canon SHA-256: `3423906b01b24443fcef733fb5c7ef47296963df63e603d8f843c99d544877ee`.
No native/model run and no phone measurement were performed for these findings.

## Findings and fixes in the assigned wrapper

1. **Confirmed: missing evidence accepted as completed.** A legacy `zustand.json` containing only
   `{"steps":{"ram":{"status":"DONE"}}}` and no RAM report caused exit 0 and zero measurement calls.
   Source/config/runner/model changes were likewise not checked before skipping.
   Fixed: a V2 state binds source/test/specification/shell bytes, installed JSON configuration/model manifests,
   runner bytes and model-file identity; a step skips only when its required nonempty JSON report and recorded
   report/log hashes still match. Exactly four generated tap/worker binary/marker paths are allowlisted as
   tool-measurement outputs, avoiding a false INPUT_CHANGED after legitimate first-time build. The completed tool
   stage binds those output bytes separately and refuses reuse if they change. Native children retain ownership of actual model integrity checks: the wrapper
   explicitly reports that large model payloads use size/mtime/ctime identity rather than a new full-payload hash.
   Configuration values are not copied into the binding; only their hashes are stored.
2. **Confirmed: crash window and implicit lost-attempt repetition.** State was written in place only after the child
   exited. A process death could tear the JSON; death before that write left no durable RUNNING marker, allowing an
   implicit rerun of a partial native cohort.
   Fixed: use the existing fsync/atomic writer before launching a child and after it ends. Missing/changed/legacy or
   corrupt run bindings are refused unchanged. Partial or altered step evidence is retained and not implicitly
   repeated. Explicit `--neu` archives the entire old cohort to a distinct sibling before starting a new attempt;
   no old report is merged into the new run's result ZIP.
3. **Confirmed: measurement inputs could change during a successful child run.** A zero exit code alone was accepted.
   Fixed: compare the input binding again after a successful child; changes produce INPUT_CHANGED, stop further
   stages and cannot be reused. A missing/invalid primary report produces MISSING_EVIDENCE.
4. **Confirmed: Ctrl+C could block indefinitely** if a child ignored SIGINT (`proc.wait()` had no timeout).
   Fixed: bounded process-group shutdown with SIGKILL escalation; a process already gone is tolerated.
5. **Concurrency race prevented:** a nonblocking per-home package lock prevents two package invocations from racing
   over state or launching competing heavy measurement jobs. It supplements, rather than replaces, the existing
   running-chat precheck.
6. **User-facing receipt corrected:** the original summary said nothing had been enabled even though the approved
   eligibility tool was enabled. The summary now states that approved activation and distinguishes finished
   measurements from passed scientific gates. Empty/duplicate step selections are rejected.

Owned implementation changes: `scripts/handy_pflicht.py`, `tests/test_handy_pflicht.py`,
`tests/test_handy_pflicht_resume.py`. No frozen production runtime file was edited by this reviewer.

Verification command (from `v13/code`):

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:tests python -m unittest tests.test_handy_pflicht tests.test_handy_pflicht_resume
```

Result: **16 tests, OK**. Includes real small subprocess orchestration/deadline tests plus software counterexamples
for corrupt/legacy state, absent/tampered/added artifacts, input changes, durable RUNNING, explicit separate retry,
concurrent invocation, atomic-write failure, bounded signal escalation and preserved research FAIL verdicts.
The `/proc` helper test initially failed in the sandbox; the separate residency reviewer corrected PID-namespace
resolution rather than weakening the test. Three changed Python files compile; scoped `git diff --check` passes.

## Findings handed to the other owners

- **Training proof integration can false-PASS:** the original wrapper selected only four integration checks plus
  rollback, ignoring `actual_learned_route_use`, F7 checks, the integration exit and `proof_status`. A partial integration
  result with those selected checks true could produce TRAIN_RUNNER_PROOF_PASS. Root owns the correction and tests.
- **Training phase claims exceed evidence:** timing-based SIGKILL rows do not record actual worker phase or whether the
  child was killed; a pre-import interruption or already-finished child can satisfy cancellation/checkpoint checks.
  Root owns phase-attribution correction. Own-process peak RSS is not the worker's per-phase peak RSS and must be named
  honestly; absent power/phase metrics remain unavailable.
- **Residency evidence loss:** original residency/repeat scripts saved the report only after all arms/turns; an
  interruption discarded already measured rows while disposable Runtime state disappeared. The residency owner is
  implementing durable per-attempt rows and explicit refusal to fake continuation of a lost session.
- **Residency resource/latency distortion:** unknown `answer_s` was averaged as zero, and a dictionary keyed by executable
  name collapsed simultaneous llama-server processes. The residency owner is correcting missing-value semantics and
  retaining per-PID plus sampled aggregate measurements. Aggregate RSS still is not PSS/energy or a proof of phone fit.

## Canon reconciliation and next executable work

The read canon requires the complete source-preserving A plane, complementary fine/gist B1/B2, direct gated B3,
distributed B4 and composite C1–C7/JEF, attention/salience, Context OS/episodic/procedural/parametric memory, World/Self,
corollary/action outcomes, eligibility and typed modulators, local prediction/EMA, metaplasticity/homeostasis,
replay/consolidation/dream separation, age/user control, reversible updates and independent hard response governor.
Communication and learning remain separate controls. C2 and C3 retain separate role-specific learning paths; neither
heads-only adaptation nor source retrieval proves body plasticity. Dream has zero direct fact authority.
Optional neural layer re-entry is distinct from Context OS source re-entry and cannot replace it.

The controlling completion rules are §29, §96, §99, §100, §105 and the B3 addendum. A software test or scaffold existence
cannot turn their missing measured utility into a passed gate. B3 L1 evidence is task-specific and failed replication
cannot license L2 escalation; unknown receiver compatibility means zero authority. TrainRunnerProof is parameter-path
specific. Mobile scheduling may be sequential; this never removes canonical functions.

Highest-priority cloud work after these integrity fixes:

1. Reconcile the newest native evidence and integration branches with the four §85.1/STEP2 controls; preserve the
   complementarity gate until the original criterion passes. Quote transport gains do not by themselves prove
   two-body necessity or a timescale-specific gain.
2. WP-Z6a follow-up: preregister a conservative uncertainty-triggered wake candidate against disabled/fixed effort,
   measure already-solved false wakes and hard-task recovery on fresh paired tasks. The measured adaptive policy
   currently wastes body wakes on all 42/42 already-solved cases and has no authority to be called better.
3. WP-LP3 / Z12: use the existing C3 training path to test whether an attributable predictive state actually improves
   answers, with correct/shuffled/no-predictor and equal-compute controls, component gradients, retention and restart.
   LP1/LP2 alignment gains are not answer utility. B1/B2 require their own genuine training port before claiming body
   updates. Register and commit the protocol before native measurement.
4. WP-Z11 already has a teacher protocol in this branch; execute it only after model/runner artifacts and budget are
   available, keeping SELF frozen first and REFERENCE provenance separate. Do not silently download/substitute a new
   model for an active cohort.
5. Ship the repaired bounded phone package and collect actual device measurements. Simulated days are not weeks of
   real mobile stability; no cloud task can honestly supply Redmi thermal/energy/long-run proof.

The current roadmap's Z8/Z9 explanatory tail still contains older prospective wording after reporting new FAIL
results; status updates should preserve those failures and remove ambiguous promises of automatic gate closure.
`canonical_architecture_complete` and `user_full_scope_complete` remain false.
