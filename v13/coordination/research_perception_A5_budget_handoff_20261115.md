# A5 source-budget candidate, 2026-11-15

Parent: gpt6/v13-private-remote-bridge-20261111. Owner: Research/Perception.
Issue: #1904 native C3 prefill exceeds deadline for 617-634 token prompts.
Hypothesis: bounded source-labelled perception summaries prevent A5 from adding unbounded prompt text. Character budget is deliberately NOT a tokenizer or measured speed improvement.

Candidate: v13/code/v13/perception_budget_candidate.py
Regression: v13/code/tests/test_perception_budget_candidate.py
Run: cd v13/code && python -m unittest discover -s tests -p test_perception_budget_candidate.py -v
Six equivalent standalone Python tests passed in isolated runner; GitHub CI and repo integration pending.
Contract: consent, provenance, modality, source, age and priority; preserves non-speech audio text. No raw audio. Does not activate mic, Android capture, ASR, teacher/student, A3, JEPA or device control.
GATES: SHADOW_CANDIDATE; REDMI_UNVERIFIED; no native C3 latency evidence; official Age0 unchanged.
Low risk: pure bounded projection and tests. Higher risk: connecting to actual C3 message composer requires Core review and real token accounting, adversarial text trust, provenance and UI permission checks.
Next: Core integrate under explicit A5 gate, compare token counts with baseline, CI; Boss review and merge if appropriate; measure C3 prefills on consented Redmi after release.
