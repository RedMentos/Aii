# Research & Perception handoff — RAW EAR temporal Runtime state, comparator and VAD research

Date: 2026-11-21 11:40 CET  
Queue: V14-006 / Research & Perception  
Release base: d4834ebb6e550064409fc146dbd59d47d7259bb5  
Branch: research-perception/v14-raw-ear-runtime-temporal-state-20261121  
Current exact head: f09717f478497d5eebf2e24bd4147e4663ec7202  
PR: #2192 — DRAFT / NOT_RELEASED / REDMI_UNVERIFIED

## Functional change

1. RAW EAR V3 keeps voiced-frame energy dynamics, F0/voicing, pause-robust voiced energy and activity cues. The default caller path now attaches a bounded per-Runtime TemporalVoiceEvidenceRegistry keyed by source/generation; it retains scalar evidence/timestamps only, has a 16-stream LRU bound and explicit reset.
2. First-use get/create/set is guarded by a short module-level lock and a second read. Eight simultaneous first-use callers must all receive the same registry, preventing split temporal history.
3. Consent revocation clears runtime-held and caller-supplied temporal state before later input resumes.
4. The offline comparator reports signed onset/offset delay at the end of the state-changing window, supports libfvad sample-rate retuning, rejects partial 20 ms tails, and keeps WebRTC test-only.

## Exact-head CI

- [44895064274 — RAW EAR → A4 → C3](https://github.com/RedMentos/Aii/actions/runs/44895064274): PASS; 29/29 tests on Python 3.11 and 29/29 on Python 3.13. Includes temporal continuity, gaps/overlap, LRU/source-generation replacement, explicit reset, consent revocation and the 8-worker first-use race regression.
- [44895064174 — RAW EAR vs WebRTC/libfvad comparator](https://github.com/RedMentos/Aii/actions/runs/44895064174): PASS; 7/7 tests on Python 3.13 and 7/7 on Python 3.14. Exact source hashes, py_compile, real WebRTC wrapper smoke and fake libfvad C-ABI positive/negative checks.
- [44895064171 — public privacy scan](https://github.com/RedMentos/Aii/actions/runs/44895064171): PASS.
- [44895064140 — V14 model-lab](https://github.com/RedMentos/Aii/actions/runs/44895064140): PASS; compile, candidate-manifest validation, isolated safety/grading and privacy scan.
- [44895064121 — integration-event workflow](https://github.com/RedMentos/Aii/actions/runs/44895064121): PASS.
- [44895064129 — safe-additive candidate gate](https://github.com/RedMentos/Aii/actions/runs/44895064129): FAIL by design/scope: this workflow only accepts newly added inert modules/tests/handoffs, while this PR modifies the existing audio producer and test, and adds experiment/workflow files. Similar existing-module candidates (#2185/#2190/#2191) also required manual Boss review. No gate was bypassed; Boss review is required.
- [44895064150 — staged-context/integrated regression](https://github.com/RedMentos/Aii/actions/runs/44895064150): was still running at this handoff timestamp; re-read before review. Do not infer its result.
- A previous comparator run failed only because its immutable V3 blob pin still named the pre-lock producer SHA. The workflow pin was corrected to 4ddb61865deb56b0048390740d35770d4d89316e; exact rerun 44895064174 passed.

## Local and device boundaries

- LOCAL_LINUX exact Aii checkout: BLOCKED; git ls-remote https://github.com/RedMentos/Aii.git HEAD fails because this worker cannot resolve github.com. No local exact-source compile/pytest PASS is claimed.
- GitHub Actions are Linux CI and synthetic fixtures, not local Termux, Bionic-native libfvad, actual microphone or model-quality evidence.
- TERMUX/REDMI: REDMI_UNVERIFIED. No handset connection, microphone consent receipt, installed SHA, updater receipt, CPU/RSS/PSS/battery measurement or deployment occurred.
- No model, weights, runtime, dependency, Age, permission or user data changed.

## Research result (R-024)

Bauer et al., arXiv:2607.25870v1, submitted 2026-07-28 and accepted INTERSPEECH 2026, reports kiloVAD's 2.1k-parameter causal CNN at 200 ms context and 0.850 ± 0.007 AVA-Speech AUC. PulseVAD's MIT repository packages a 2.1k INT8/26.8 KB ONNX candidate but author-reported results show 200 ms granularity, weaker music/far-field false alarms than Silero and dataset-manifest inconsistencies. Silero upstream is MIT/ONNX and supports 30+ ms chunks, but no Android ABI/Redmi measurement is established. VoxRT reports ~1 ms/32 ms on Redmi 9C but its inference runtime is proprietary, so it is not an OSS reuse candidate. See V14_RESEARCH_LEDGER R-024 for exact limitations and URLs. No model was downloaded.

## Consumer / Canon boundary

- Current source blobs: audio_voice_cues.py = 4ddb61865deb56b0048390740d35770d4d89316e; audio_temporal_evidence.py = 098ce2ec6bb0b744166d711a3401b7acf0252de1.
- All V3 producer functions from #2177 are present in #2192, plus temporal registry/reset and concurrency protection; the comparator from #2187 is also present. #2177/#2187 remain open pending Boss decision; do not close duplicates without owner coordination.
- Core #2158 is still based on old c0ced... and has not pinned the new temporal source. Exact source handoff comment was posted on #2158 (comment 7061363867): rebase to d4834..., pin both blobs through recovery builder/deployer, keep text PerceptPacket distinct from AudioPerceptPacket, and prove B1/B2 → C4 → C3.
- This is still a caller-supplied PCM16 adapter. No microphone capture, trained VAD, ASR, speech decoder/vocoder, full-duplex, actual B1/B2 model offer, native latent coupling or Android control is proved.
- P0 #1904 remains unresolved: last phone evidence still had incorrect 2+2, slow turn and unverified B1/B2 offer delivery; no newer private device receipt was available.

## Next executable step

1. Re-read run 44895064150 and the current PR check suite.
2. Boss reviews #2192 as the current-base consolidated Perception candidate and decides how #2177/#2187 are handled.
3. Core rebinds #2158 to the exact two source blobs and runs its complete staged Runtime regression.
4. After integration approval, QA may request a separate owner-consented Redmi test. Until then, no device update or user action is needed.
