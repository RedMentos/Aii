# Research & Perception — run 5 handoff (2026-11-24)

## Execution record

- Started: 2026-11-24 21:07:47 Europe/Berlin.
- Completed: UNKNOWN.
- Repo: RedMentos/Aii.
- Development base: Core branch `core/v14-vision-source-lifecycle-current-20261124-run2`, base SHA `c2fdfab67983cf58c96c89a653122f521eb69429`.
- Perception PR: [#2477](https://github.com/RedMentos/Aii/pull/2477), DRAFT / OPEN / NOT_RELEASED; branch `research-perception/v14-a3-exact-source-forget-core-stack-20261124-run19`.
- Branch head before this handoff commit: `93712a1373bc44d33aab1c52a3c46d36cd9ecc8a`.
- Code-bearing commits: vision runtime `0ea5653125babb39f8715963983001ee4ec39b34`; helper `3b16ad1f4f2bcee4e00fa8861be44e76704e0048`; focused tests `0acc44dca3df4436b24120756ff178ec4f8a4ad2`; Runtime integration tests `8e75fbdcc7260ddf8569187330c21f328d2c69c7`; existing source-lineage workflow extension `70a7321d4d56f1b49ae08e6d886c1814c49cec81`.
- Exact current source hashes: `vision.py` Git blob `53c3b5067a1198eeecea833e7f8347a22c4b4c7b`, SHA-256 `e51e409a2fa2145e2cb9b9b1a3c80c5f5a67cc69d98054f8e46bd21f16f1b71e`; `vision_projector_stats.py` Git blob `137d60dc78278031a2918ef6babc1862759d5d65`, SHA-256 `ea13bc756e4846cfd6fb200ee16330a01a295ae7320c8e4d788f09e9ae3eaf5a`.
- Earlier wrong-base PR #2475 was closed as superseded; no merge or release.

## Implemented candidate: exact A3 source forget

- The actual A3 global and tile projector training paths now write bounded per-source fp64 sufficient-stat artifacts only when the published projector is an exact full ridge fit: gate status INITIAL/APPLIED and scale exactly 1.0.
- A source-bound explicit forget can subtract one image's statistics and reconstruct the remaining standardized+bias ridge head. It removes forgotten-source caption keys and deletes that source's stats artifact.
- Missing, corrupt, symlinked, incomplete, over-limit or mismatched stats fail closed to the existing conservative projector invalidation.
- Replay-blended updates (scale < 1.0) are explicitly UNAVAILABLE_SCALED_UPDATE. They are not treated as exactly reconstructible.
- Post-forget metrics/replay gates are marked NOT_RECOMPUTED_AFTER_SOURCE_DELETE. This is exact only for the A3 linear ridge head; it does not unlearn the image feature extractor, vision teacher, text encoder, other organ weights or GGUF models.
- Stats are derived sensitive data, not raw pixels/captions. They are local, registered in the Store, bounded, mode 0600, no-follow read/write/delete. Cleanup failures are returned explicitly.

## Tests and evidence

- LOCAL_LINUX method reproduction: CPython 3.13.5 / NumPy 2.3.5; 750 synthetic delete/rebuild comparisons at feature dimensions 37/117 and target dimensions 256/768, including zero-variance features. Maximum absolute mean error 2.78e-16, maximum absolute std error 6.66e-16, maximum relative parameter error 2.84e-10 against fresh standardized ridge fits.
- This was an algebra reproduction, not a full Aii repository test.
- Full local Aii checkout: BLOCKED / NOT_RUN. No checkout is mounted; `git ls-remote https://github.com/RedMentos/Aii.git` failed because github.com DNS could not resolve.
- Exact-head GitHub Actions for code commit `190e9356dae8893d4ccb5ea9be40bab842a9ef25`: queued at last readback. Source-lineage run `45480359189`, jobs `138751511342` (Python 3.13) and `138751512073` (Python 3.14) were both QUEUED. Other queued runs: staged/integrated `45480359187`, RAW EYE frame ingress `45480359178`, Core lifecycle composition `45480359190`, runtime deployment integrity `45480359184`. No CI PASS is claimed yet.
- The existing source-lineage workflow was extended to compile/run the new helper and Runtime regressions and print both exact SHA-256 values. A redundant new workflow was removed.

## Cross-agent integration required

- PR #2477 is stacked on Core PR #2465's source-lifecycle branch.
- Core must add `vision_projector_stats.py` to the materialized source/dependency closure and pin its exact SHA-256, then rebind the changed `vision.py` SHA-256. The helper imports the existing `common` and `vision_source_lineage` modules; no new external package is introduced.
- Strict source pins must remain. Do not weaken the composer.
- A comment with both exact hashes was added to #2465.

## Parallel Perception lane: RAW EAR / A4

- PR #2472 head `d77b06bc23837c52c52cffa98a4c61b2bf5b4ae9`, code SHA `8df6a16fd5dced71a2643eae141f9f204fc66855`.
- FASTDIAR diagnostic: 92/92 on Python 3.13 and 92/92 on Python 3.14. A4 source-bound outcomes, optional RAW EAR NumPy, consent-revocation and privacy scan PASS.
- Controller guard fails before feature tests: recovery builder expects guard SHA-256 `86ad7838d15eb9a038fec629c340936edde78d65d921507e10cec29fed74b9d9`; current guard SHA-256 is `9c901c4e5e3d3fd17c113a8e9458bcb32a30646593483202f1f472763435fa96`. Audio composer also needs the exact temporal module pin. Core/QA own those builder rebinding changes.
- No AudioRecord provider or live microphone capture; no Redmi audio evidence.

## Research and next useful step

- No new paper is claimed as read in this run. The implementation reuses the full R-101 review: Quan, Wu & Montana, *Exact Federated Continual Unlearning for Ridge Heads on Frozen Foundation Models*, arXiv:2603.12977v3 / ECML PKDD 2026, DOI 10.1007/978-3-032-37673-2_7.
- Next Perception research/implementation: near-duplicate image/source grouping and source-level uncertainty for A3 source-disjoint validation. Distinct SourceRefs are not automatically independent; add perceptual/session grouping and a negative control before claiming out-of-source generalization.
- Keep the larger V14 gaps open: real multimodal Android input, audio provider, A/B/C consumer path, native latent exchange, true JEPA/gradient learning, B1/B2 response quality, sleep/replay and verified updater.

## Device and user action

- REDMI_UNVERIFIED. No Android hardware was available to this run; no Termux command, UPDATE_REQUEST, CHAT_SEND, model/weight swap, permission change or user-data mutation was performed.
- No release/deployment is claimed. GitHub push is not deployment.
- User action required: NONE.
