# Research & Perception — run 38 handoff (2026-11-24)

## Run record

- Automation turn: 11.
- Started: 2026-11-24 13:27:45 Europe/Berlin.
- Checkpoint timestamp: 2026-11-24 13:47:10 Europe/Berlin.
- Completion timestamp: UNKNOWN; execution did not provide an independently measured stop time.
- Repo: `RedMentos/Aii`.
- Release base readback: `gpt6/v13-private-remote-bridge-20261111` = `8d93236c753f0194224c19edc7411d8d7082b1d6`.
- Candidate branch: `research-perception/v14-vision-current-20261124-run33`.
- Candidate PR: [#2463](https://github.com/RedMentos/Aii/pull/2463), OPEN / DRAFT / NOT_RELEASED.
- Exact branch HEAD: `2fc06a7b41f0c9933b66ff04b93bc2e08d96b86d`.

## Product defect and change

The old A3 evaluation mask treated changed captions as holdout rows even when the old projector had already trained on the same source ID. That made the old-projector baseline non-source-disjoint for changed existing sources.

The shared `_projector_validation_inputs` now validates the prior projector's `training_sources` list and checks exact agreement with source IDs in its saved caption keys. Only current source IDs absent from that verified lineage are eligible for the candidate-vs-old baseline holdout. Changed captions for already-seen sources remain candidate-training data but are excluded from evaluation. Missing/malformed/duplicate/hash-invalid/mismatched lineage or no new source groups fails closed to `NO_NEW_SOURCE_GROUPS`; the old artifact is retained. Both global and tile projector training use this helper. `vision_validation.py` reports `NEW_SOURCE_GROUPS`.

No A0–A5 organ was removed. This is an evaluation-gate correction for the existing ridge projector, not a neural gradient update, trained JEPA, native latent coupling, or a new input modality.

## Commits and readback

- Code/lineage fix: `12f4e70113cc117087960c5b137e1afbc62dd14b`.
- Regression-fixture/no-op correction: `cdd7283fb30f0bccdd8ca8a2df46541a17aca3d5`.
- New-source multi-region test fixture: `3767112e63e9d4e66fdc2ebcddd3555bcd9affdb`.
- Exact dependency hash/compile workflow update: `2fc06a7b41f0c9933b66ff04b93bc2e08d96b86d`.
- GitHub PR head and raw source readback confirmed at `2fc06a7b41f0c9933b66ff04b93bc2e08d96b86d`.

### Exact source SHA-256 (CI Python 3.13 and 3.14 identical)

| Source | SHA-256 |
|---|---|
| `vision.py` | `350573e65eb445b8b83f5517e3bfe07ece04e036055c55fc3e23c79d5b0cc728` |
| `vision_source_lineage.py` | `bb63636c9ae84d345fe1f4e37254de3be87c26990cb320ca058859fd0b51b72f` |
| `vision_validation.py` | `5040c5672dc8cf263fccce132787ae138a29494ab4a67709d7d3689a849f57b6` |
| `vision_temporal_evidence.py` | `f2345aae29b81d7d07925801b7c5ce4c490c872c9e926b6b12837a5f468c5c88` |
| `vision_temporal_adaptation.py` | `a28dc8b9b3860622a2068b96763eb0885d88951a93aaad3e45ed47e593e8b5bb` |
| `vision_ui_frame_ingress.py` | `3ff590921e225e5ecfbdbc6f126e1b036915a03ec8db80b8aa5ca64869d4e905` |

The matching Git blob SHA-1s are: `vision.py` 2a8fce618230544ee389ac77f62e6a201e514965; `vision_source_lineage.py` 8958f1297378653ec1837a215f84a41b14966db9; `vision_validation.py` f3809fe6f532d8da9159462cee4c54557bd4598c; `vision_temporal_evidence.py` 0557d0de0e32a06b40757b94fd1944b53a318e8b; `vision_temporal_adaptation.py` ff8b3b3da958e1e5f685b81865e0ba18af2c4bd3; `vision_ui_frame_ingress.py` c39356249641f65b4deeb82147eb1f3e6f764693.

## Tests

- LOCAL_LINUX, Python 3.13.5: `python -m py_compile /tmp/test_a3_source_holdout.py` PASS; `python -m pytest -q /tmp/test_a3_source_holdout.py` PASS, 3/3. This is an isolated helper harness, not the full Aii checkout.
- CI exact head `2fc06a7b41f0c9933b66ff04b93bc2e08d96b86d`: `py_compile` PASS; vision/source-lineage 39/39 on Python 3.13.18 and 39/39 on Python 3.14.10.
- CI exact head: RAW EYE frame-ingress 39/39 on Python 3.13 and 3.14; offline 3.11/3.14 PASS; privacy PASS; offline-bridge-security PASS; same-repo guard PASS.
- CI exact head: staged-runtime FAIL (19 failed / 234 passed / 10 skipped / 2 errors / 41 subtests); integrated-regression FAIL (1); consumer Python 3.13 FAIL (3 failed / 2 passed). Consumer Python 3.14 was IN_PROGRESS at last poll. Root exception across observed integration failures: Boss-owned `source_lifecycle_lock_integration_candidate.py:172` raises `ValueError: unsupported lifecycle source: vision.py`.
- Full local Aii suite: NOT_RUN; no repository checkout and GitHub DNS/clone access unavailable in this local container. No claim of local full-suite success.

## Research note R-133

Full paper reviewed: Geras & Sutton, “Multiple-source cross-validation,” ICML 2013, PMLR 28:1292–1300. Its source-level holdout methodology supports the correction; the Amazon review-domain experiments are not an image/Android result. No code, data, weights or dependency were imported. Caveat: source IDs alone do not guarantee independence when images are near-duplicates or share an acquisition session; next research should test perceptual/session grouping and source-level uncertainty.

## Runtime, device and deployment

Latest private V13OBS #115 snapshot (updated 2026-11-24 09:28:11 UTC): installed base `8d93236c753f0194224c19edc7411d8d7082b1d6`; auto-update enabled; pipeline/dashboard UP_TO_DATE; last updater error NONE. The AI is STOPPED_BY_USER, model process STOPPED, native residency UNAVAILABLE; B1/B2 still report TIME_BUDGET. Candidate #2463 is NOT_INSTALLED. No new owner receipt, UPDATE_REQUEST, CHAT_SEND, LOG_PAGE, restart, shell command, model/weight/permission change or data mutation occurred. REDMI_UNVERIFIED.

## Next executable step

Boss/Integrator #2443 must update the strict `vision.py` pin to SHA-256 `350573e65eb445b8b83f5517e3bfe07ece04e036055c55fc3e23c79d5b0cc728` and compose the complete imported dependency closure, including the exact source hashes above. Then rerun staged-runtime, integrated-regression, both consumers and migration without relaxing source/forget guards. Perception next investigates near-duplicate/session grouping and source-level uncertainty after the composer passes.

**User action: NONE.** Keep STOPPED_BY_USER; no manual Termux command, update request or model swap.
