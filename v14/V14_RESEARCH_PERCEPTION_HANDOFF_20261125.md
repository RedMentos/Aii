# Research & Perception — V14 handoff 2026-11-25

## Result

Draft PR [#2506](https://github.com/RedMentos/Aii/pull/2506), branch `research-perception/v14-native-input-bridge-20261125-run19`, current PR/branch head `7f33772b6434c3ec019562a48a3d77ca3b85ebaa` (code/test SHA `c4b73ab2d792b4be6d4c673d23233f8fb07c9274`), stacked on Research/Perception #2503. Adds an executable typed bridge from Core's native selected-row extractor wrapper output to the existing Perception receiver input-embedding manifest builder.

### Code and tests

- `v13/code/v13/native_input_embedding_tap.py`: `build_native_input_embedding_tap_manifest_from_extractor_output()` validates exact output keys, COMPLETE status, installed model SHA and extractor binary SHA agreement with the native receipt, then delegates to the existing source/token/event/generation manifest builder.
- `v13/code/tests/test_native_input_embedding_tap.py`: positive path plus negatives for incomplete status, extra fields, missing rows, model hash drift, extractor hash drift and receipt drift.
- `/.github/workflows/v14-latent-token-alignment.yml`: exact branch trigger added for this stack.
- Module blob `36c03f2cb76eca55f5751d8cee944697a8f1c17d`; test blob `22e6f1780686eec05f905d203d21ce48df0787f4`; workflow blob `0a8e37e344043bbadb84cc3dc3179b1cee52900d`.

### Verification

- LOCAL_LINUX isolated helper reproduction: 7/7 PASS; builder dependency was stubbed, so this is not the full package suite.
- Exact GitHub Actions run [45673125410](https://github.com/RedMentos/Aii/actions/runs/45673125410): 73/73 PASS on Python 3.13 and 73/73 PASS on Python 3.14; compile PASS; public privacy scan CLEAN.
- Staged/integrated regression [45673125502](https://github.com/RedMentos/Aii/actions/runs/45673125502) completed SUCCESS: integrated 424 passed / 3 skipped / 58 subtests; staged runtime 255 passed / 10 skipped / 47 subtests; two-checkout migration sub-suite 39 passed / 17 subtests. GitHub-hosted synthetic/Linux only, not Redmi deployment.
- Full local Aii checkout/pytest NOT_RUN: no checkout mounted; `git ls-remote` failed due unavailable GitHub DNS.
- Core PR #2505 head `298b96efba5bdbd07ac845b5e22e799ef742350d`: CI [45665062470](https://github.com/RedMentos/Aii/actions/runs/45665062470) PASS for Python 3.13/3.14 wrapper tests, pinned llama.cpp Linux native compile, and Android arm64-v8a cross-compile. No actual GGUF row read.
- No Android device/Termux/Redmi test; B3 OFF; NOT_RELEASED.

## Integration contract and next owner

Core must compose #2505 with #2503/#2506, call the new bridge from actual `LlamaRunner.tap`/`Cognition.tap` after the native extractor wrapper, and persist the manifest with trusted SourceRef, event/generation, sender/receiver model and tokenizer/tap revisions, model/binary hashes and blob identity. Then run a real small GGUF row read, source-disjoint pairs, receiver utility, exact-message/no-message/zero/shuffle/repeat/OOD controls, and later retention/restart/rollback. Keep sender final-RMSNorm activations, receiver input-embedding rows and event-pooled LATENT_PREFIX_V1 distinct. B3 stays OFF until independent review and utility gates pass.

## Research

R-150: Marincat, arXiv:2609.11365v1 (2026-09-10), abstract and public artifact README reviewed; full paper not reviewed. The reported cross-initialization failures and one negative-transfer factorial support per-pair adapter binding, not a universal latent coordinate assumption. Artifact code repository is MIT; separate checkpoint/weight license not verified; no reuse.

## Release and device

Release-development branch `gpt6/v13-private-remote-bridge-20261111` HEAD `8d93236c753f0194224c19edc7411d8d7082b1d6`, with 22/22 observed GitHub Actions workflows SUCCESS. Private V13OBS #115 (2026-11-24 09:28:11 UTC) reports that SHA installed and auto-update enabled, but AI runtime STOPPED_BY_USER, autostart false, model process stopped, B1/B2 zero valid offers and native latent exchange unproven. Read-only requests #915–917 had no response at last poll. Keep current functional status REDMI_UNVERIFIED. No device command, restart, update request, model/weight/permission/data change. No user action required.

## Known unrelated integration failure

Perception #2483 remains DRAFT. Staged/integrated run 45633224199: 19 failed / 236 passed / 10 skipped / 2 errors / 47 subtests; stale `audio_voice_cues.py` and `runtime.py` source pins dominate. Two-checkout migration run 45633224662 returned PARTIAL instead of UPDATED. Do not weaken hash gates; coordinate the cross-owner repair.

## Run timing

Automation start was 2026-11-25 19:01 CET. Exact completion time is UNKNOWN.
