# Run60 — §94 Sleep A/B/C + Wake replay authority-separated SQLite candidate

Base PR93 `c252704e2853932b1a01c22327cba60679f31a33`, prereg commit `5e5e2160797bf8505ff0c986cc4fa2693df9c88a`. Owned only `sleep-replay-run60/*`. No production SleepRuntime/Store schema, chat UI, model weights or active-owner code modified.

**Implementation:** source-bound durable replay queue with all §94.1 fields plus explicit old/new age band, bounded TTL and priority, canonical payload SHA256, exact SourceRef validation, idempotent enqueue, `BEGIN IMMEDIATE` transactional claim with unforgeable lease token, deterministic old/new interleaving, user-governor/resource/stop preemption, Wake threshold >=.8, Sleep A candidate-only, Sleep B hypothesis-only with `fact_write_authority=0`, Sleep C expiry marking preserving every raw row. Lease recovery after a process crash revokes old tokens; stale workers cannot complete. All source refs revalidated at completion, and TTL checked again. No facts table writes.

**Evidence:** 12/12 synthetic SQLite/Linux tests PASS, 12/12 Python `-O` PASS, 5 repeat subprocess `os._exit(97)` lease-recovery tests PASS, compileall PASS. Adversarial RED #1: forged claim phase could upgrade counterfactual completion to CANDIDATE_ONLY; fixed by deriving authority from stored replay_type, not caller phase. RED #2: expired leased replay could complete after TTL; fixed by transactional expiry check. Both original RED logs preserved.

**Limitations:** This is an isolated synthetic Store-shaped fixture, not actual V13 SleepRuntime/Context OS/Store or a live scheduler. Sleep A does not perform real retention training, Sleep B does not generate model counterfactuals, Sleep C currently only expires entries (no measured homeostasis or index rebuild). Wake preemption is simulated by caller-provided `user_pending` flag, not measured live user-response governor. No Redmi, full repository suite, official privacy scan, real AGI or canonical utility proof.

**Reproduce:** unpack archive, `cd sleep_replay_run60 && python -m unittest -v test_replay_queue && python -O -m unittest -q test_replay_queue`.

**Next:** independent review in complete PR93 checkout, integrate behind existing Age-0 SleepRuntime with exact Store source/permission contracts and live governor, then measure replay utility/retention and resource budgets without changing registered gates. No fact-write or higher-age promotion.

**Gates unchanged:** STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; `jepa_weight=0`; V13 INCOMPLETE. Canon §94/§95. Primary source: https://www.sqlite.org/lang_transaction.html (2026-10-24).
