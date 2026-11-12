# Research & Perception A2/A3/A5 provenance handoff — 2026-11-12 02:00 CET

Parent PR #1810, branch research-perception/a3-provenance-20261112-0200. No Core, JEPA or QA-owned file modified.

## Added
- `v13/code/v13/a3_evidence_bridge.py`: synthetic A2 TeacherEvidence with deterministic content digest; external source verifier; final+consent gating for training; A3 numeric updates; observation-only A5-like synthetic packet with source/version/step provenance.
- `v13/code/tests/test_a3_evidence_bridge.py`: synthetic holdout improvement, restart persistence, revocation, provisional/consent refusal, digest tampering and invalid numeric input.

## Honest gates
- New tests are WRITTEN; not claimed PASS in repository CI or Android.
- Existing A3 numerical kernel is from PR #1810. This bridge does NOT implement frozen A2 model execution, real source registry, teacher license, production A5 schema, B1/B2/JEF runtime, multimodal sensor, quantized export, voice output, or native Android.
- SHA256 detects accidental payload changes but is NOT a signature; caller-provided verifier must independently check authorization, source existence, revocation and version. A model-controlled verifier is not a hard boundary.
- Observation packets have `android_action_allowed=false`; Android control remains an independent OS-permissioned path.
- The 5.84 GB / 1.78 GB Redmi numbers are historical only; phone measurement UNVERIFIED.

## Follow-up
1. Run `cd v13/code && python -m unittest tests.test_a3_online_projector tests.test_a3_evidence_bridge` in exact-head CI; fix any failures.
2. Reconcile TeacherEvidence and A5 with current canonical production PerceptPacket and Store APIs; no silent schema substitution.
3. Connect verified A2 frozen teacher inference, real source registry and A3→B1/B2/JEF observation route.
4. Add before/after retention, restart, source-revocation and float-master→quantized-export benchmarks; Android Termux test separately.
