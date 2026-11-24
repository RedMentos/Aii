# Research & Perception — Run 34 — 2026-11-24

**Started:** 2026-11-24 05:00:26 Europe/Berlin  
**Completed:** 2026-11-24 05:09:12 Europe/Berlin  
**Repository:** RedMentos/Aii  
**Working branch:** \`research-perception/v14-audio-duplex-bridge-20261123-run21\`  
**Branch head before this documentation checkpoint:** \`437c72b4c10fd5837aef64a984f61d7da86f627d\`  
**Release-development base:** \`8d93236c753f0194224c19edc7411d8d7082b1d6\`  
**PRs:** #2448 OPEN/DRAFT/NOT_RELEASED; #2463 OPEN/DRAFT/NOT_RELEASED

## 1. Work completed

### Audio duplex review recheck

Re-read the exact current audio code and tests after Boss's two race findings on PR #2448.

- \`duplex.record()\` in \`v13/code/v13/duplex.py\` has per-target first-writer semantics: it rejects a second interrupt for an already-interrupted \`from_event\` or an already-pending target, without replacing the first relation.
- \`audio_duplex_bridge.on_audio_input()\` holds \`duplex.audio_handoff_lock(runtime)\` across the active-turn recheck, durable \`duplex.record()\`, and only then cancellation. \`duplex.handoff()\` and \`rollback_record()\` use the same per-Runtime lock. If the active turn changes during Store I/O, the exact unconsumed relation is rolled back before the lock is released.
- Existing regressions cover first-writer, sequential distinct audio receipts, concurrent distinct receipts, and handoff-reader/cancel ordering:
  - \`test_audio_interrupt_target_turn_claim_is_first_writer_wins\`
  - \`test_distinct_audio_receipts_cannot_replace_the_first_active_turn_handoff\`
  - \`test_concurrent_distinct_audio_receipts_claim_one_active_turn_once\`
  - \`test_audio_handoff_commit_is_visible_before_cancel_and_reader_cannot_win_race\`

No code modification was necessary for those two findings because the current code-tested snapshot already contains the requested controls. A detailed review response was posted on PR #2448 (review ID 6033522645).

### Exact test evidence

- Current Perception branch head before docs: \`437c72b4c10fd5837aef64a984f61d7da86f627d\`.
- Exact Actions run **45322153681**: audio-duplex bridge **179/179 PASS on Python 3.13** and **179/179 PASS on Python 3.14**.
- Other current-head checks: RAW EAR optional NumPy, prosody-to-attention, consent-revocation, runtime deployment integrity, WebRTC/libfvad comparison and public privacy scan PASS.
- Code-tested snapshot: \`c7db1809370fae5ae5a49287e76cba0deedf80e7\`. The later commits through 437c72 changed only board/next-action/handoff documentation, not the audio bridge, duplex or test blobs.

### Cross-lane integration blockers

Exact run **45322153465**:
- staged-runtime fails at Core-owned \`integrated_audio_context_candidate_20261121.py\` with \`ValueError: audio source blob changed: v13/audio_voice_cues.py\`;
- 16 failed, 237 passed, 10 skipped, 2 errors, 47 subtests;
- integrated-regression fails at the same composer.
Exact Core same-turn run **45322153579** fails on Python 3.13 and 3.14 for the same source-composition failure.

Current expected/actual audio source blobs:
- voice cues expected \`b18e450162b062b09368a12b1ca18924ed8c5025\`, actual \`e46a47bb93615126c8ee149baebfb6df9813fbee\`;
- speaker evidence expected \`37aa9c392bbb68d60ccff9749c75b41b8783c539\`, actual \`25474bb202c1209800f5c8a73e36aeca5555efd6\`;
- temporal evidence expected \`098ce2ec6bb0b744166d711a3401b7acf0252de1\`, actual \`e258f5dfecbf79d6f1a9d3adbfaf60631bb9d140\`.

Follow-up coordination comment posted on Core PR #2462 (comment ID 7121776477). The Core-owned pin file was not edited by Perception.

### Vision / RAW EYE

PR #2463 remains current-base and OPEN/DRAFT. Focused CI passes:
- vision source-lineage: 29/29 on Python 3.13 and 3.14;
- MediaProjection RAW EYE frame ingress: 39/39 on Python 3.13 and 3.14.

Staged/integrated remains blocked because Core's lifecycle composer rejects \`vision.py\` with \`ValueError: unsupported lifecycle source: vision.py\`. Core/JEPA owns the lifecycle mapping and source-forget regression. No Perception-side bypass was made.

## 2. New research recorded

- **R-126 FD-VAD** — full paper read, arXiv:2609.35791 (2026-09-16, submitted/preprint). Semantic endpointing uses WavLM-base-plus + a two-layer modality adapter + Qwen2.5-0.5B/LoRA, 2.56-s causal windows and 320-ms steps. Reported 0.853 TurnBench EOT recall at FP 0.097 but 1,019-ms median latency; the separate τ=0.9/K=1 point reports 190-ms delay and 2% false interruption. A100-only 45.8-ms window time is not Android evidence. Official code MIT; WavLM MIT, Qwen2.5 Apache-2.0, Smart-Turn v3.1 BSD-2-Clause. No model or dataset was downloaded.
- **R-127 MJEPA** — paper and official repo read, arXiv:2606.25225 (2026-06-23, preprint). Cross-modal pooled prediction with EMA targets is the key ablated ingredient; shared encoders without cross-modal prediction degrade below unimodal baselines. Official code MIT; three retained third-party files Apache-2.0; no weights in the inspected repository. Its ViT-g is 1B-scale and trained through SLURM; not a Redmi candidate.

Both entries are in \`v14/V14_RESEARCH_LEDGER.md\`. No new model, code dependency or weight was imported.

## 3. Environment and deployment status

- **LOCAL_LINUX:** full repository checkout/test suite BLOCKED. No Aii checkout is mounted; \`git ls-remote https://github.com/RedMentos/Aii.git\` fails because github.com DNS cannot resolve. No local full pytest/compile pass is claimed.
- **GitHub CI:** exact results above; CI is not a local or Android measurement.
- **TERMUX/REDMI:** REDMI_UNVERIFIED for PR #2448 and #2463. No connected handset, microphone provider, AudioRecord, MediaProjection, native speaker model, ARM64 RSS/TTFT, or device UI/action test was performed.
- Last authenticated PIPELINE_STATUS receipt #832 (2026-11-23 17:37:47 UTC) reported auto-update enabled and release base \`8d93236c753f0194224c19edc7411d8d7082b1d6\` installed. It does not prove either open Perception PR is installed. No UPDATE_REQUEST, manual Termux command, model download, permission change or device mutation was sent.
- **Release:** NOT_RELEASED.

## 4. Persistent records updated

- \`v14/V14_RESEARCH_LEDGER.md\`: R-126 and R-127 added.
- \`v14/V14_LIVE_WORKPLAN.md\`: run 34 checkpoint and exact blockers added.
- \`v14/V14_WORK_BOARD.json\`: V14-005/V14-006 evidence, dependencies and next actions updated.
- \`v14/V14_USER_NEXT_ACTION.md\`: latest Perception checkpoint appended; no user action required.

## 5. Next executable work

1. Core/Integrator rebinds the three audio SOURCE_BLOBS in the Core-owned staged composer and reruns staged/integrated/same-turn CI.
2. Core/JEPA adds the reviewed \`vision.py\` source-lifecycle mapping and source-forget regression; then run one combined audio + vision staged/integrated candidate.
3. After exact integration CI is green, Boss/QA may use the existing authorized updater path and request a separate PIPELINE_STATUS receipt. No manual Termux command is currently needed.
4. Perception continues with a SHADOW-only semantic endpoint hypothesis (R-126) and a small pooled audio/vision predictive-loss ablation (R-127); no model download or production authority without explicit approval and measured comparison.

**User action:** none.


## Addendum — V14-018 supersession audit (2026-11-24 04:16 UTC)

A board sweep showed V14-018 still pointed to old PR #2433. The Perception functionality is already present in the newer current-base PR #2448 branch, so no rebase/duplicate implementation was created.

Verified current #2448 blobs:
- audio_speaker_evidence.py: 25474bb202c1209800f5c8a73e36eaca5555efd6
- audio_voice_cues.py: e46a47bb93615126c8ee149baebfb6df9813fbee
- attention.py: 0f6a81e7380aa6716bbac4e4ef5834d108601a70
- test_audio_speaker_evidence.py: 3630e48ecc8b06b1a09d2830ddffaa85ad2a6212

The current tests cover non-voiced embeddings never seeding/replacing speaker history, impulse novelty without speaker/interrupt authority, consent receipt epochs, exact current PCM hash binding, and A5/A4/C3 consumption. Exact run 45322153507 passed py_compile and 128 tests on both Python 3.13 and 3.14. The audio duplex race suite separately passed 179 tests on both versions in run 45322153681.

Comment 7121856464 on #2433 records the supersession and recommends that Boss close the old PR after review. The old branch was not modified. Core's stale audio SOURCE_BLOBS still block staged/integrated composition; no Android microphone or Redmi proof exists.

