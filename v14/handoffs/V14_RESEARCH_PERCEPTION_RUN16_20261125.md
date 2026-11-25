# V14 Research/Perception Run 16 — 2026-11-25

- Started: 2026-11-25 16:04:56 Europe/Berlin (automation context)
- Completed: not independently timestamped
- Lane: Research & Perception
- Base: PR #2501 head 1482156d0f15a7d4e1e1b50c4b9da5da0faee795
- Branch: research-perception/v14-token-span-manifest-integrity-20261125-run16

## Functional change

1. Hardened tokenwise alignment validation in v13/code/v13/latent_adapter.py:
   - Every token pair now carries the complete sender-span manifest and source-span unit.
   - Validator reconstructs the ordered receiver-span manifest, recomputes the alignment SHA-256 and recomputes each overlap-coverage value.
   - A re-hashed pair ID cannot make forged sender spans or coverage pass.
2. Added exact UTF-8 byte-piece provenance:
   - Accepts llama.cpp /tokenize with_pieces=true token objects, including raw byte-array pieces for tokens that split a Unicode code point.
   - Requires add_special=false content pieces to reconstruct the exact source UTF-8 bytes.
   - Derives source SHA-256, byte length and token byte spans; aligns different token segmentations by overlap.
3. Preserved the existing character-span path and authority-zero/non-production adapter gates.

## Why

PR #2501 added source-span alignment, but its validator only checked that alignment IDs were valid/equal and that supplied coverage exceeded 0.80. It did not reconstruct the ID from the full span manifest or recompute coverage. llama.cpp's pinned server supports with_pieces=true, returning UTF-8 strings or raw byte values; byte spans are needed because a token can contain only part of a UTF-8 code point.

## Research

- Adam Deng, Shicheng Liu, Yada Zhu, arXiv:2610.22026, submitted 2026-10-15. Full main-text methods/results/limitations reviewed. Same-family activation replacement depends on oracle layer/position; cross-family transfer collapses in the tested configurations. This is not evidence for V14's current final-RMSNorm-to-input-embedding mapping.
- llama.cpp pinned revision b29c606e28a01b1bc8c1351026a0fa6e616bf6c4: server /tokenize with_pieces API and MIT license verified. No upstream code copied.

## Tests and environment

- LOCAL_LINUX: isolated helper reproduction py_compile PASS; pytest 6/6 PASS.
- LOCAL_LINUX full repository: BLOCKED/NOT_RUN; no local Aii checkout and git ls-remote failed because github.com DNS could not be resolved.
- Exact GitHub Actions: pending on this follow-up branch. Parent PR #2501 had 37/37 adapter tests on Python 3.13/3.14; that result is not attributed to this commit.
- CI != local; Linux != Redmi.

## Consumer and limits

- Existing consumer: fit_adapter(..., projection_scope="TOKENWISE") validates the new manifests and fits the low-rank alignment candidate.
- Missing producer: Cognition.tap/LlamaRunner.tap still does not request with_pieces=true or persist trusted token spans. Core must map the no-special content pieces to exact activation rows while accounting for BOS/special-token offsets, then persist source/tokenizer/event/generation/blob provenance.
- B3 LATENT_PREFIX_V1 event-pooled receiver is a separate contract and must not accept tokenwise rows.
- No native GGUF activation capture, no source-disjoint real cohort, no receiver task utility, no gradients/retention, no Android control or Redmi measurement. B3 remains OFF; REDMI_UNVERIFIED.

## Device/deployment/safety

- No private relay receipt obtained in this run.
- No update request, device restart, shell command, model download/swap, weight edit, permission change or device-data change.
- GitHub push is not deployment.

## Next

1. Run exact branch CI and privacy scan.
2. Ask Core to wire llama.cpp with_pieces=true into the actual tap producer with a verified content-token-to-activation-row mapping.
3. Only after that, collect source-disjoint native B1/B2 pairs and evaluate receiver task utility with exact/no-message/zero/shuffle/repeat/OOD controls.
4. Keep B3 OFF until utility, retention, rollback and independent review pass.

## User action

Keine Aktion nötig. No Termux command, model download, model swap or permission change is requested.


#### Run 16 CI/device follow-up (2026-11-25)

PR #2502 is open as a draft, stacked on PR #2501: https://github.com/RedMentos/Aii/pull/2502. Current code/test SHA: 408c074d3d07339d3d8f4bab47139a5279a13d40. Exact adapter workflow RUN_45643108802: 42/42 PASS on Python 3.13 and 3.14; public privacy scan CLEAN. Runtime-deployment integrity RUN_45643108912: PASS on Python 3.11 and 3.14. The broader staged/integrated regression RUN_45643108732 was still IN_PROGRESS at the last check. The first attempt on 6955caf failed one shuffled-pairing negative fixture; the fixture was corrected and the new exact head passed.

Latest available private V13OBS #115 snapshot updated 2026-11-24T09:28:11Z: updater enabled, pipeline/dashboard/runtime UP_TO_DATE at installed SHA 8d93236c753f0194224c19edc7411d8d7082b1d6, but AI runtime STOPPED_BY_USER, model process STOPPED and autostart false. One last C3 turn: 7 tokens, 2.046 s TTFT, 358 prompt tokens; not a sustained acceptance result. B1/B2 remain failed in the recorded sample; no native latent exchange or C3 semantic use. No newer receipt in this run; REDMI_UNVERIFIED. No device command or deployment was performed.

Next integration owner: Core must wire the trusted token-piece tap producer and preserve the separate event-pooled LATENT_PREFIX_V1 contract. User action: keine Aktion nötig.


## Final code/test checkpoint (2026-11-25)

Current code/test SHA: fa2673340f2dce78dcf7952b802957bf8b2f9212.

- Adapter workflow: 47/47 PASS on Python 3.13 and 3.14; privacy scan CLEAN.
- Runtime-deployment integrity: PASS on Python 3.11 and 3.14.
- Staged/integrated regression: PASS — 424 passed, 3 skipped, 58 subtests; staged runtime 255 passed, 10 skipped, 47 subtests.
- LOCAL_LINUX isolated helper reproduction: 10/10 PASS.
- Full local Aii checkout: BLOCKED/NOT_RUN (no local checkout; github.com DNS unavailable).

Added build_tokenwise_tap_manifest(): checks token-piece IDs against content token IDs, exact source bytes, unique contiguous content-token subsequence in add-special prefill IDs, and selects the exact matching activation rows. The runner and Cognition packet still do not call it. Core integration remains the next step.

Three read-only private relay requests were created: PIPELINE_STATUS #915, DIAGNOSTICS #916, HEALTH #917 (created 2026-11-25T15:25:01Z; 10-minute expiry). No receipt had arrived at the last poll. Latest prior snapshot remains 2026-11-24T09:28:11Z and is historical only.
