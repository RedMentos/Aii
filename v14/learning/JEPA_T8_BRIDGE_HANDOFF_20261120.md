# V14 temporal outcome semantics integration handoff — 2026-11-21

**Owner:** Boss & Integration. **Work item:** V14-004 / V14-007.  
**Branch:** boss/v14-temporal-outcome-semantics-20261120. **Base:** 14d7386484dfce6728aa404d89eae98403b4dba0.  
**Candidate HEAD:** 3319a5199602d6d305857dbdc3aad93466b871da. **Status:** DRAFT / NOT MERGED / NOT RELEASED.

## Functional candidate

v14/learning/t8_store_authority.py calls the existing world_model.transitions(store) admission path, then cross-checks each candidate against:
- exactly one persisted action row joined to its event and CorollaryCopy;
- event/generation identity and one source reference;
- Store.read_source(source_ref) for source-row, blob-digest and span validation;
- exactly one matching ActionOutcome packet with matching status and actual outcome;
- the status-derived success target in the world-model row.

The resulting immutable VerifiedT8Transition carries source and outcome digests, not raw source text. TemporalT8Bridge.consume() requires this typed receipt. The previous caller-supplied trusted=True API is removed. The private issuer object prevents accidental construction through the public constructor, but is not a security boundary against arbitrary Python code in the same process.

Temporal outcome semantics:
- OBSERVED: expected outcome inside the predicted time window; error = 1-p.
- MISMATCHED: a different outcome was actually observed; error = -p.
- EARLY / DELAYED: same outcome outside the predicted time window; error = -p.
- OMITTED: only when a complete observation window has source-bound evidence and no event; error = -p.
- CENSORED / CANCELLED: no learning signal.

## QA correction: multi-writer persistence

The earlier atomic-replace implementation had a reproducible lost-update bug: two stale TemporalOutcomes or TemporalReadout instances could overwrite each other's committed records/weights. Both stores now use per-file POSIX fcntl.flock locks, reload and validate the newest file inside the exclusive lock, write via temp + os.replace, and fsync the file and parent directory. Read APIs used by the bridge refresh under shared locks. Bridge replay is idempotent across separate instances; the receiver event-ID check closes the check/update race.

## Local evidence

Environment: LOCAL_LINUX, CPython 3.13.5, x86_64.

Commands executed against an isolated local package with a synthetic v13.world_model stub:
- python -m pytest -q v14/learning — 29 passed;
- py_compile of temporal_outcomes.py, temporal_receiver.py, t8_store_authority.py, t8_temporal_bridge.py, and test_t8_store_authority.py — PASS.

The suite includes correct/mismatched/early/delayed scoring; source-hash tampering; missing/mismatched/duplicate ActionOutcome rejection; exact permission and default-off learning checks; stale two-instance writes for ledger and readout; multiprocessing writers for ledger and readout; and replay through two stale bridge instances with exactly one scalar update.

Four DeprecationWarnings are emitted because the local Python host is multithreaded and the regression uses the fork multiprocessing start method. Tests completed successfully; this warning should be removed by a later spawn-safe fixture where practical.

Evidence classification: SYNTHETIC / LOCAL_LINUX. These are not full repository tests. FakeStore and patched world_model.transitions() do not prove the actual SQLite schema/packet path. No GitHub CI run has been returned for the new HEAD yet.

## Explicit limitations

- The adapter is not yet called by the installed V13 runtime. Runtime Python remains frozen for the current SourceHandoff cohort; integration must be a separate hash-bound stage and must not edit runtime.py or other frozen source files directly.
- No actual Store fixture, full runtime consumer, held-out utility/retention experiment, native inference, Android/Termux test, or Redmi receipt exists for this PR.
- TemporalReadout is a tiny scalar readout only. It is not a JEPA encoder, learned latent coupling, native B1/B2 model adapter, GGUF optimizer, or full model-weight update.
- learning_enabled defaults to False; no product learning permission, Age state, model, weight file, updater, or phone state was changed.
- Temporal omission is only valid when observation coverage is complete; absence of a row alone is not evidence of omission.

## Next gate

1. Exact GitHub CI for this candidate SHA.
2. A real SQLite Store integration fixture creating source/event, CorollaryCopy, ActionSelection and ActionOutcome records.
3. A hash-bound runtime-consumer stage with restart, rollback and negative controls.
4. Separate utility/retention and Redmi tests before any claim of active system learning.

Until those gates pass, V14-004 remains IMPLEMENTING / PARTIAL, not complete.


## Boss verification update — 2026-11-21

Current candidate branch: `boss/v14-t8-temporal-store-integration-20261121`, head `2d8eb79bdefe3c6c3bef63fea7d25563b7f56952` before base retarget. This extends the earlier local-only report with exact CI evidence:
- V14 temporal/real Store workflow PASS: PR run 44846178337 and push run 44846173142.
- V13 private bridge push PASS: 44846173169.
- V13 staged-runtime and integrated-regression PASS: run 44846178374.
- Safe-additive-only scope policy FAIL remains visible; no gate was disabled.
- New fixes: 4096-row complete bounded ActionOutcome scan (over-bound fail closed), CANCELLED/ABORTED vs OUTCOME_UNKNOWN/INTERRUPTED censored semantics with no learning signal, known FAILED remains observed NOT_FINAL, and parent-directory fsync after rollback.
- No normal Runtime consumer, no full JEPA, no native body-weight update and no Redmi proof. The bridge defaults learning off and does not change Age or permissions.
