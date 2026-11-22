# Research & Perception handoff — RAW EYE visual A5 ingress
Date: 2026-11-22
PR: #2363
Base: `gpt6/v13-private-remote-bridge-20261111` at `c4eb82deec915f65894c20d6ebbaf0ebf58fa335`
Branch: `research-perception/v14-vision-a5-ingress-20261122`

## Code

- Module commit: `f2ae689950357e51692f644f77f4eb0ca5ab0bc2`
- Test commit: `fd26b886710af75af5e3211c688cb5731b5531fe`
- Combined existing Perception CI/workflow update commit: `a77b841f250dab597c127d9ddecd86278c4d0ef4`
- Current PR head at the time of this handoff: `a77b841f250dab597c127d9ddecd86278c4d0ef4`

The adapter accepts only an exact existing IMAGE SourceRef from the local `:image add` path, requires explicit per-call consent and an active Runtime turn event, then emits global + 16 tile RAW EYE summaries with exact pixel-box SourceRefs. It uses existing 37-D handcrafted features and border-relative salience, sends the summaries to A4 attention with file requests disabled, and produces a bounded A5ContextEnvelope/C3 candidate while preserving the exact current prompt.

## Authority and data

- Local user-supplied image only; no arbitrary path, camera, MediaProjection, AccessibilityService, live video or Android capture.
- No teacher/VLM, student projector, model inference, weight changes or training.
- No raw pixel bytes are copied into the PerceptPacket. The original image remains in the existing Store blob; derived packet/context are ephemeral and are not persisted.
- Static image timestamp is unknown and explicitly marked `STATIC_UNTIMED`.
- A4 truth authority 0; learning/action authority false. Dominant color is a heuristic channel descriptor, not object recognition.
- A4 high-resolution file requests are disabled because no visual high-resolution provider is wired.
- A5 budgets are byte/character prefilters, not a native tokenizer.

## Tests

LOCAL_LINUX CPython 3.13.5 with NumPy 2.3.5 and Pillow 12.3.0: isolated synthetic reproduction 3/3 PASS using a stub Store/A4 boundary and copied vision feature math. Twenty 64x64 synthetic runs: median 5.852 ms, p95 7.870 ms. This is not the full Aii Store/A4 test suite.

Committed regression tests use actual Store, vision ingest/read, A4 Attention, PerceptAdmission and A5ContextEnvelope, and run alongside existing `tests/test_vision.py` in the combined Perception workflow. Exact PR CI is pending; do not report it as passed until read back.

## Next integration owner

Core must call `consume_visual_source(runtime, source_ref, consent=True, current_source=...)` from an active Runtime turn when a consented local image source is attached, then route the returned PerceptPacket/context to the correct organ consumer. Add source-revocation regression before persisting derived visual data. Default text path remains unchanged.

No Runtime core file changed, no deployment/release, no Redmi proof, and no user action required.
