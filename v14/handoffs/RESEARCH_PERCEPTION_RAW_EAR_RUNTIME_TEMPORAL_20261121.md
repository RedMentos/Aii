# Research & Perception handoff — RAW EAR temporal Runtime state, comparator and VAD research

Date: 2026-11-21 11:43 CET  
Queue: V14-006 / Research & Perception  
Release code base: e18c664d954fa5a44a1b2e5bec76850d5a40f89f  
Branch: research-perception/v14-raw-ear-runtime-temporal-state-20261121  
Status: DRAFT / NOT_RELEASED / REDMI_UNVERIFIED

## Rebase correction

The earlier candidate tree was accidentally based on the separate documentation checkpoint d4834ebb6e550064409fc146dbd59d47d7259bb5, which contained Boss-owned Workplan, Coverage, Board, Next-Action and Boss-handoff edits. This commit reconstructs the candidate tree from the actual code/release branch e18c664d954fa5a44a1b2e5bec76850d5a40f89f and reapplies only the Perception-owned source, tests, experiments, workflows, research-ledger append and this handoff. Boss-owned shared documents and Boss handoff are not part of this PR diff. Historical V13 source and the V14 master remain unchanged.

## Functional change

1. RAW EAR V3 keeps voiced-frame energy dynamics, F0/voicing, pause-robust voiced energy and activity cues. The default caller path attaches a bounded per-Runtime TemporalVoiceEvidenceRegistry keyed by source/generation; it retains scalar evidence/timestamps only, has a 16-stream LRU bound and explicit reset.
2. First-use get/create/set is guarded by a short module-level lock and a second read. Eight simultaneous first-use callers must all receive the same registry, preventing split temporal history.
3. Consent revocation clears runtime-held and caller-supplied temporal state before later input resumes.
4. The offline comparator reports signed onset/offset delay from the actual smoothed state-changing window, supports libfvad sample-rate retuning, rejects partial 20 ms tails, and keeps WebRTC test-only.

## Exact code/test evidence (unchanged by documentation/rebase commits)

- Code/test head previously tested: f09717f478497d5eebf2e24bd4147e4663ec7202; code/test blobs are preserved exactly in this rebase.
- RAW EAR → A4 → C3 run 44895064274: PASS, 29/29 on Python 3.11 and 29/29 on Python 3.13.
- RAW EAR vs WebRTC/libfvad comparator run 44895064174: PASS, 7/7 on Python 3.13 and 7/7 on Python 3.14; exact source hash pins, compile, WebRTC wrapper smoke and fake libfvad C-ABI tests.
- Model-lab 44895064140 PASS; public privacy scan 44895064171 PASS; integration-event workflow 44895064121 PASS.
- Safe-additive gate 44895064129 FAIL: its own contract accepts only newly added inert modules/tests/handoffs, while this PR modifies the existing audio producer/test and includes experiment/workflow files. Existing-module candidates require manual Boss review; no gate was bypassed.
- Staged-context/integrated regression run 44895064150 was still in progress at the last readback. Re-read the exact current PR head before review.

## Exact source pins

- audio_voice_cues.py: 4ddb61865deb56b0048390740d35770d4d89316e
- audio_temporal_evidence.py: 098ce2ec6bb0b744166d711a3401b7acf0252de1

## Research

R-024 in V14_RESEARCH_LEDGER records the full kiloVAD paper (arXiv:2607.25870v1, accepted INTERSPEECH 2026), PulseVAD MIT candidate and dataset/reproducibility caveats, Silero ONNX/30 ms baseline, and why VoxRT's proprietary runtime is not reusable. No model or weights were downloaded. PulseVAD's 200 ms context is a possible low-power coarse gate, not a barge-in detector; RAW EAR prosody/non-speech cues remain first-class.

## Environment / integration boundaries

- Exact local Aii checkout is BLOCKED because this worker cannot resolve github.com; no local exact-source compile/pytest PASS is claimed.
- CI is GitHub Linux/synthetic evidence, not local Termux, Bionic-native libfvad, actual microphone or model-quality proof.
- Redmi/Termux remains REDMI_UNVERIFIED: no handset connection, microphone consent receipt, installed SHA, updater receipt, CPU/RSS/PSS/battery measurement or deployment.
- No model, weights, runtime, dependency, Age, permission or user data changed.
- Core #2158 remains based on an older release ancestor. Source handoff comment 7061363867 supplies both exact blob pins and the required full A5→B1/B2→C4→C3 integration tests. It must preserve text PerceptPacket separately from AudioPerceptPacket.
- This is still a caller-supplied PCM16 adapter. Microphone capture, trained VAD, ASR, speech decoder/vocoder, full-duplex, native B1/B2 inference, trained B3 latent coupling and whole-Canon acceptance remain open.
- The V3 producer/comparator surfaces from #2177/#2187 are present here with temporal-state additions. Those older drafts remain open until Boss decides the safe integration path; this PR did not close them.

## Next

1. Re-read the exact current PR check suite, especially staged-context/integrated regression.
2. Boss reviews this non-additive current-code-base candidate and synchronizes shared board/next-action files.
3. Core rebinds #2158 to both exact source blobs and proves its staged Runtime path.
4. Only after integration review can QA request a separate owner-consented Redmi test. No user action is needed now.
