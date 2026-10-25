# Run266 — independent terminal outcome candidate, CI worktree only (2026-10-25)

Base: verified PR261 RED head `23c001652193f4edeaa5342363a7a44ddec527d6`, parent PR259 production WorldModel `db62c761a9b1f3364c951ad6ac82a71d84f`. Exclusive ownership: **new patch file**, workflow, proof directory. Do not edit or overwrite PR259 owner's production `world_model.py` or historical source/seed/model files.

RED evidence: Run261 actual Store 16 tests, **3 FAIL**, exit 1, raw artifact 12595602946 SHA256 `45808be76988bfeea9e4266a4cee21f9f121f191d13773f740f6d92cc9a46f72`: valid ERROR outcomes cause SOURCE_UNVERIFIED, and nonterminal DISPATCHED forged outcome is admitted by `transitions`. No native model or Redmi.

Candidate contract: only observed terminal statuses FINAL, ERROR, DEADLINE, CANCELLED, INTERRUPTED can enter `transitions` and `_action_binding`; status remains hashed with action, selected route and source. Nonterminal DISPATCHED excluded even if outcome payload exists. Keep source revocation/tamper and fitted-state guards unchanged. No automatic activation or authority promotion.

CI must assert exact original production Git blob, apply the patch **only to ephemeral GitHub Actions checkout**, run Run261 RED tests plus existing WorldModel source integrity and Runtime observation suites, preserve complete raw, exact patched Git blob, diff and official privacy scan. This branch contains no production WorldModel edit; owner may integrate after independent review/release. A green candidate is software/actual Store with synthetic action outcomes, not semantic utility or native training.

Next: inspect exact CI result; if green, send PR259 owner a reviewed minimal patch and proof. Then rerun full suite on reconciled source chain with Run264 synthetic scope fix. STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; jepa_weight=0; full V13 INCOMPLETE.
