# JEF→C3 typed two-source envelope SHADOW preregistration — 2026-10-31 UTC

**Owner:** GPT-6; isolated branch `assistant/v13-jef-c3-typed-envelope-gpt6-20261031` based on JEF live-current verified head `8774987507f8082a7fdf0a65e8e37c82a08910dd`. Preregister **before** implementation, tests or workflow. Original JEF historical diagnostic, Run47, P2X cohort, source/model/seed/scorer unchanged.

## Goal / new functional path

The existing typed JEF F1/F5 policy/sheet source admission can propose `A|B|NONE` but is not connected to a current-turn C3 language prompt. Implement a **default-OFF, software SHADOW-only** C3 envelope builder that binds the *latest authoritative USER event*, two independently human-verified F1/F5 fact SourceRefs, exact JEF typed action and current source, and rechecks the decision after constructing the prompt. C3 remains a local formatter, not a new decision authority. A pure post-decoder validator accepts only one exact uppercase `A|B|NONE` token matching the source-verified JEF proposal, otherwise RED. This is not a production Runtime installation or real TTY output.

## Frozen software cohort and controls

Reuse the existing 36 P2X calibration cases (original 36 known typed JEF decisions) as **engineering integration**, not a new disjoint utility cohort. Each creates real SQLite HumanDecision policy/sheet sources and current USER event, builds a two-message C3 envelope with exact verified source text, source hashes and the JEF action, then tests a synthetic exact-match formatter output. **Expected 36/36** valid envelopes and synthetic exact matches. **Negative controls:** stale USER after newer event, revoked/hidden/conflicting policy or sheet, wrong session/ref, swapped source IDs, forged approval, missing opt-in/integer 1, mutated source during prompt creation, C3 output wrong choice, extra text, lowercase, JSON, whitespace, empty, no oracle leakage, and no writes/model calls. Preserve original 36/144 JEF source suite and 36/36 live-current suite.

## Security and scope

Source facts are from verified Store refs; never treat B1/B2 hypotheses, C3 output or JEF self-labels as human facts. The builder returns messages **only to an explicitly opted-in local model consumer** and cannot itself call a model, dispatch tools, commit output, approve TTY or train. Source and prompt hashes are not permission tokens. No model/seed/fixture changes or native/Redmi/STEP2/B3/Body-JEPA/age promotion. A separate preregistered disjoint native C3 evaluation is required to claim actual model receiver fidelity.

**Acceptance:** real SQLite positive/negative software tests, original regression, exact source pins, privacy CLEAN, compile, closed raw SHA256 manifest and private byte-verified backup. If any negative admits a prompt or post-decoder match, preserve RED and do not enable. Planned check: `cd v13/code && PYTHONPATH=.:tests:scripts python -m unittest -v tests.test_jef_c3_typed_envelope_candidate tests.test_jef_f1f5_live_current_candidate tests.test_jef_f1f5_source_admission`.
