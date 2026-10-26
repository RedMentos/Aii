# Run621 — B2-only train-fitted diagonal metric: NO_B2_READOUT_GAIN

2026-10-26. Review-only child of Run620 PR615 at exact observed base `ac25ca8728c3a6b4cb9182ef4f9139438579b9c0`. The frozen exploratory protocol `PREREG.md` was committed as `beb345b908967968b433aab95489edf6dcd9421b` **before this new offline fit**, but original Run614 heldout states had already been inspected in prior runs; this is explicitly **retrospective/posthoc**, not independent prospective evidence.

Actual original SHA-closed prior Linux-native B2 states (no new inference) `RUN614_STATES.npz` SHA256 `cb535df87749c0cf5d698d26268e6b03f3d6f57690b95434aebc6c875a3ea189` and report SHA256 `42ac6d22ef6c9cc59622572f233b2e7b83094af7a9fdd227cfe2fff15e0666e4`. Existing `run615_crosscohort_shadow.load(...,'614')` validates original source, model, gates, dimensions and train/test isolation. Train-only 30 B2 A/B pairs; 20 heldout prompts from unseen topics; fixed positive diagonal readout, 200 seeded shuffled-pair controls. This trains a small **offline retrieval metric**, not body weights, JEPA, receiver injection, automatic memory authority or C3.

## Executed Linux result

- Raw B2 cosine heldout top1 **0.85**, MRR **0.90**.
- Train-mean-centered B2 cosine top1 **0.85**, MRR **0.9167**.
- Learned diagonal B2 metric top1 **0.85**, MRR **0.90**.
- Gain over best baseline **0.00**; 200 shuffled train-pair controls null mean top1 **0.8445**, empirical p **0.89055**. **NO_B2_READOUT_GAIN**, no promotion.
- Actual original-artifact + synthetic/adversarial tests **5/5 PASS**, Linux NumPy 2.3.5, source-only; original tampered report correctly refused and ERROR report persisted. Local raw log, weights and report closed separately.
- Report SHA256 `581edc072b1ba7d1c8d6c8f77c65c0d1b194a7f905a1f3b12771e900e21da7ca`, fitted weights NPZ SHA256 `1e5fbfbdf778b93d180aaad602fd54e4cbaea5317b77c924406a222f74c25363`.
- Source Git blob `f08429acfccd6bac13f469119f1b76131a1967df`; tests blob `7253c4045fe5bf0aa5bbed6eab354215b9c3561b`, remote readback verified.
- GitHub Actions original-artifact source-only CI configured with original Run614 artifact run 40407777217, SHA checks, tests, privacy and raw closure. **Actions status UNVERIFIED** until exact run/artifact can be inspected; local executed Linux results are distinct.

**Claim limits:** no prospective new heldout, no new native model inference, no body update, no measured semantic improvement, no actual Redmi, no end-to-end second-attempt utility. STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; jepa_weight=0; Redmi UNMEASURED; V13 INCOMPLETE. Canon unchanged. Independent review requested; no main merge.

Next: verify exact CI source/head/artifact and raw; record negative result and move to a different Canon learning/utility path rather than tuning this failed diagonal helper on the same heldout.
