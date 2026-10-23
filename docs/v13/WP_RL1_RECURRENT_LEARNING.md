# V13 — WP-RL1: Controlled neural re-entry and continuous learning

## BINDING COMPLETE-BLUEPRINT SCOPE RULE (V13)
**The ENTIRE V13 master blueprint v10.16.1 is the binding, unabridged target.** Neither components discussed here, illustrative lists, individual work packages nor partial implementations constitute an exhaustive selection or replacement. **Every** prescribed organ, subsystem, state layer, learning path, information flow, interaction, operational safeguard, proof and acceptance gate remains in scope even when not mentioned in this note or not yet implemented. Before acting, examine the full current canon together with decisions, roadmap, build state, evidence and active owners. New hypotheses are additions only: never silently omit, collapse or reinterpret a canonical requirement. Sequencing and experimental feature flags affect when/how something is tested or activated, **not whether it remains part of the complete target architecture**. Surface conflicts explicitly, reconcile before changing scope, and do not claim system completion from partial progress.

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


## Clarified existing JEF / small-language-model learning requirement
- Preserve four distinct functional roles: `B1_DETAIL` and `B2_GIST` are the two larger learning bodies; **JEF** is the executive/control subsystem (including `C2_CONTROL`); **`C3_LANGUAGE` is a separate small LLM** for fast language responses and cheap common-case interaction.
- JEF's trainable neuronal parts **and** C3 are intended to learn as well, alongside the two bodies, rather than being permanent frozen-only routers or an immutable text renderer. They need role-specific learning paths, update gates, retention evidence and potentially different adaptation time scales. Do not infer a shared JEPA loss is appropriate for every module.
- Smaller components may learn from verified body outcomes, corrections, and carefully sourced/distilled knowledge. Large-body agreement or self-produced text alone does not prove factual correctness. Keep independent checks/teacher provenance and measured held-out transfer.
- Goal of C3 quick path: avoid waking/decoding through both large bodies for every simple reply; the JEF route can escalate when needed. Whether this saves real latency and preserves quality is a separate runtime/phone measurement, not an accomplished performance claim.
- This clarification restates planned target functionality, **not** a claim of current end-to-end implemented online gradient updates for JEF/C3/B1/B2. No new personal context has been included.


## Blueprint primacy and **full-system** integration (explicit correction)
**The authoritative V13 MASTER-BLAUPAUSE / v10.16.1 single-source-of-truth governs the complete end-to-end architecture.** Previous B1/B2–JEF–C3 descriptions are a *partial role overview*, not a replacement specification, not a reduced implementation scope, and not a request to rebuild from scratch. Before implementing this WP, re-read the canonical blueprint, actual current ROADMAP, ABDECKUNG, BUILD_STATE, active branch owners and proofs. If a shorthand description conflicts with canon, flag the conflict and preserve canon pending explicit user decision.

The integrated target additionally includes (non-exhaustive): A-PLANE perception/ingress; B-PLANE detail/gist learning bodies; C-PLANE/JEF workspace, thalamus/focal coalition, executive and action gating; **Context OS** with active KV states, multi-level episodic/condensed memory, retention, source/provenance and re-entry versus re-prefill; Callosum/latent bidirectional communication and complementarity; World/Self JEPA; eligibility-based local plasticity, neuromodulation, selective experts, EMA and slow/fast learning timescales; sleep/dream/replay/consolidation; reasoning effort, reflex/fast-forward and predictive action/corollary pathways; persistent interaction, ages/rights/approvals, fail-safe stop, checkpoints, cross-model swaps and rollback. Do not treat this enumeration as exhaustive—the blueprint remains the reference.

**Interaction constraint:** a layer re-entry experiment must not silently replace the existing Context OS re-entry mechanism; these are different concepts and must be integrated/tested separately. A proposed shared self-state must first be compared to the already specified Selfmodel/Context/Callosum components. Existing target capabilities remain required even when current measurements are partial, missing or failing. Do not substitute context retrieval, heads-only training or router learning for proven end-to-end body plasticity. New research features must be optional additions with independent gates and baseline/retention/regression tests; protect active STEP/WP gates and workloads.
