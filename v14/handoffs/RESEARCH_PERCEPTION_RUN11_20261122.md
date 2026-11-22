# Research & Perception handoff — 2026-11-22, run 11

## Code checkpoint

- Release base read before work: gpt6/v13-private-remote-bridge-20261111 at c4eb82deec915f65894c20d6ebbaf0ebf58fa335.
- Own branch: research-perception/v14-vision-runtime-submit-20261122-run11.
- Code commit: 789b6c5676b76ace2d63b8d8a40af76db22009f5.
- New runtime consumer: v13/code/v13/vision_runtime_bridge.py; entry point :image ask <id|last> <Frage> in the existing vision.operator_command.
- Existing image source is hash-verified before use. The teacher caption must be bound to the same source and retain REFERENCE_NOT_FACT; only the caption, source metadata and four highest border-contrast regions are passed as bounded text to the normal Runtime.submit() path. Raw image bytes remain in the existing local image blob.
- A canonical image PerceptPacket is published under the same event/generation while holding Runtime's existing RLock, so the worker cannot claim the event before the packet is visible. A4 receives only the low-level contrast novelty score. Packet/attention errors are logged and returned as partial status rather than reported as success.
- Learning and action authority remain false. The bridge explicitly reports that C3 receives caption+metadata, not native image pixels or native visual activations. It does not claim native vision, a trained image latent path, Android screen capture or camera access.
- No model, weight, dependency, permission, updater setting or user data was changed. The existing configured LFM2.5-VL-450M teacher is reused only when the user invokes the image command; no download is triggered.

## Tests and evidence

- LOCAL_LINUX isolated CPython 3.13.5 x86_64: python -m py_compile and focused stubbed-runtime tests 4/4 PASS in the local harness. The tests cover source binding, event/generation-bound A5 persistence, A4 novelty routing, normal Runtime submit under the RLock, oversized-question rejection, cross-source teacher-caption rejection and packet-persistence failure reporting.
- LOCAL_FULL_REPOSITORY: BLOCKED. No Aii checkout is mounted; git ls-remote still fails because GitHub DNS is unavailable in the local container. Do not represent the isolated harness as full-repository tests.
- GitHub focused workflow added: v14-vision-runtime-submit.yml; it runs the exact repository test on Python 3.13 and 3.14. Exact-head Actions result must be read after the PR is opened; until then CI is PENDING / NOT_VERIFIED.
- TERMUX/REDMI: REDMI_UNVERIFIED for this change. The installed phone was independently reported at c4eb82..., but this branch is not merged or installed. No image was sent to the phone and no Android screen/camera permission was used.
- Release/deployment: NOT_RELEASED. A GitHub push is not a deployment.

## Canon mapping

- V14 A0/A1/A4/A5 visual source intake, source-bound PerceptPacket, active attention and C3 output: CODE_PRESENT / WIRED_SYNTHETIC / PR_CI_PENDING.
- Existing vision.py teacher/student lab remains LAB_SHADOW_ONLY; this bridge is caption-mediated, not native visual-token exchange or trained image latent coupling.
- Android UI observation, MediaProjection, AccessibilityService and camera provider remain OFF / NOT_IMPLEMENTED / REDMI_UNVERIFIED.
- Existing A-plane RAW EAR caller-supplied PCM16 path remains separate; no microphone provider, ASR decoder/vocoder, full duplex or speaker identity is added.

## Cross-lane defect found (Core owner)

The current release v13/code/v13/runtime.py has Runtime.submit(self, text) only. The existing audio_input.submit_audio_only() calls runtime.submit(..., audio_window=...). Therefore that adapter cannot reach the actual Runtime through this API; its unit test uses a permissive stub and does not establish the real consumer. The RAW EAR direct consumer functions exist, but the normal chat submission path is not wired through this API. Core is currently editing runtime.py in PR #2338 and Boss is coordinating the exact source-pin rebind, so this lane did not edit that shared file. Core should add an explicit audio-window queue/consumer or dedicated submit method after the current #2338 composition is stable, then rerun staged/integrated and full audio lease tests. No AudioRecord provider or Redmi microphone test exists.

## Research note

R-080 records tuya/nomo-pvad release-1.1 as an optional target-speaker research alternative: Apache-2.0 repository/declared fine-tuned weights, approximately 35-MB bundled model, 16-kHz stream and 160-ms output, but requires informed-consent voiceprint enrollment and is not an identity-authentication model. It is not selected for default RAW EAR because V14 currently needs anonymous acoustic/turn-change evidence, not enrolled identity. FASTDIAR remains R-075 with its existing Threadripper/960-ms/overlap caveats. No download or weight change.

## Next executable step

1. Boss/QA review this PR and read the exact Python 3.13/3.14 workflow result.
2. If CI is green, merge only after independent review; then update the shared V14_USER_NEXT_ACTION.md through its owner without colliding with QA's current #2340 handoff PR.
3. After integration, use an explicit local test image to measure teacher latency/RSS and confirm the image PerceptPacket is visible to the same Runtime event. Native pixels/latents and Android UI input remain separate future work.
4. Coordinate the verified Runtime.submit(audio_window=...) gap with Core before touching runtime.py.

User action: none. No Termux command, update request, model download/swap, permission change or device action is needed.
