# BP2b first-step diagnostic implementation — 2026-10-27

**Review-only candidate** `codex/automation11-bp2b-first-step-diagnostic-20261027` from integration PR #724 exact `5323f65e2b37144c81820a9a250e87c6add8fbc7`. See `PREREG.md` for new diagnostic scope and unchanged original frozen experiment.

Added `scripts/bp2b_first_step_diagnostic.py`: exact official master preflight, original seed41 legacy source selection, isolated new 1-step config, owner lock, durable new-only STARTED/RESULT/FAILED receipts, RSS samples fsynced, and a deliberate exception after the **real** `body_jepa_checkpoint.save` completes. The opt-in checkpoint must be committed before the probe claims `FIRST_STEP_COMMITTED`. No 30-step training/heldout scoring, no model/optimizer artifact in public evidence. Fake injected tests are labeled `SOFTWARE_FAKE_TEST`.

Six synthetic negative/positive controls and focused no-model workflow `.github/workflows/bp2b-first-step-software.yml` were added. **Exact-head CI pending at this checkpoint; do not claim tests PASS.** No native job launched yet. Original BP2b seed41 Actions `40506115941` timed out at 35 minutes; original negative evidence preserved.

**Next:** verify software CI, independently review checkpoint interception and failure receipt path, then prepare a separate new native Actions workflow under this preregistration (20m CPU limit, 35m job, exact pinned source, serial owner). If native is blocked, continue other Canon work rather than altering the original registered cohort. No STEP2/B3/BJ1/age/Redmi promotion.
