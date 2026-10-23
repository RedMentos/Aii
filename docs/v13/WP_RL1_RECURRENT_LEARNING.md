# V13 — WP-RL1: Controlled neural re-entry and continuous learning
Status: **approved architectural research requirement; feature OFF by default until verified**.
Scope: isolated experimental implementation only. Does not supersede existing blueprint, ownership, STEP/WP gates, or measured results.

## Concept
- Let selected transformer processing stages run additional, budgeted passes on intermediate activations, if and only if the native runner exposes genuine intermediate activation access. Repeating prompts is **not** layer re-entry.
- Existing B1_DETAIL and B2_GIST bodies remain the intended online JEPA learners. Re-entry outputs may feed correctly attributed prediction and eligibility signals; merely firing twice does **not** update weights. EMA target weights follow **actual** online parameter updates only.
- Every inference can potentially contribute to learning under the current V13 authorization/age/learning gates; novelty/uncertainty can modulate effort and plasticity but must not silently replace the continuous-learning requirement.
- Freeze/rollback/resource limits must apply to learning jobs and activated experiments. The unmodified original inference path remains a fallback.

## Experiment controls
- Independent feature gate: `reentry_loops=off|shadow|on`, initially off; bounded depth/time/temperature/memory budgets and divergence cutoff. Exact limits determined by pre-registered test data, not guessed.
- Mark intermediate states with source, body/version, step count, and update provenance. Do not count repeated processing of one observation as multiple independent confirmations.
- Compare original inference+learning; loops without updates; loops with attributable JEPA/eligibility/body weight updates; equal-compute alternatives; and fixed-depth/single-pass baselines.
- Record held-out performance, calibrated abstention, prediction error, causal body-parameter deltas, retention after restart, regression, inter-body complementary utility, energy, latency and memory.
- Missing native layer taps or body training yields `UNSUPPORTED`; do not claim a functioning experiment from scheduler/mock/extra text passes.

## Separate research question, not yet an approved new component
Examine whether an existing Callosum/Selfmodel/Workspace component could carry a small continuously learnable *shared self-state*, instead of adding another LLM. Roles remain distinct: B1/B2 bodies learn and reason; JEF/C2 controls routes and actions; C3_LANGUAGE renders speech/text. Candidate inputs are versioned internal body summaries, provenance, JEPA prediction errors, uncertainty and **verified** consequences. The state would predict reliability, recurring error patterns or needed processing effort. Never treat inter-body agreement as ground truth; compare against existing episodic/context-memory baselines before creating new parameters.

## Repository privacy / handoff rule
Only publish technical design, code, synthetic fixtures, validation and high-level status. Never commit personal profiles, conversations/transcripts, emails, phone numbers, physical addresses, account IDs, precise locations, credentials, private attachments or identifiable raw logs/screenshots. Minimize environment fingerprints and metadata in examples. Scrub data before copying to public branches. GitHub commit identities and timestamps may still correlate with contributor accounts: private and sanitized are **not** guarantees of anonymity.

This is an implementation/research handoff, **not** a claim that the feature is already implemented, validated, or enabled.
