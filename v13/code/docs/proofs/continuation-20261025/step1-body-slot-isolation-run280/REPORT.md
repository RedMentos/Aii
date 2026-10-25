# Run280 — STEP1 no-B proof must mask AG0 slots (2026-10-25)

## Discovery and ownership
- Base: verified Run279 PR279 checkpoint `a503f4d5d254b548d5a0a5da888a0c391ba77d69`; review chain PR270→…→PR280, not independent main merge.
- Owner: `v13/code/v13/proofs.py`, new Run280 test/workflow and this proof directory. No native model downloads or other owners' files touched.
- Canon unchanged Git blob `218464b12a2d27d92524c751922fa8e1c3fb0ea7`; original global BUILD_STATE unchanged Git blob `fdf0827d7c4af5cdb85b69cbe651ed52784a07b5`.
- Source finding from exact PR269 actual-weight Linux acceptance artifact `12597232047`, SHA256 `eac321b4f8119f0ce10cbd65c050c87e56f11b94ec8d56322f450014f13054d0`: JEF combined C3 FAIL, STEP12 C3-without-B FAIL, executive first C3 FAIL. Archived JEF combined turns have `output_metadata.runner.role=B1_DETAIL` although the probe removed `body`/`gist` from `ModelManager.installed`. `BodyFabric.path_override` can still serve committed AG0 slots; manifest-only removal is not a valid no-B test. PR269 native run overall 12 PASS / 8 FAIL, exit 2; this remains unchanged. Review comment on PR269 `6397511605`.

## RED
- New test `45498c86e517c69f67d40830cda1c4dc05e9d1e6`, CI workflow finalized at `419b2c5703b3d3f0ed5ebe340157485c04fa4012`.
- Exact-head Linux-software CI `40192224815`: **38 tests; 2 FAIL, 2 ERROR, 34 PASS**. The manifest-only leakage control passed, both proof functions lacked slot masking, helper missing. No native inference; tiny synthetic GGUF path files are not executable weights.
- Closed RED raw artifact `12598203530`, ZIP SHA256 `b18a2f2aea06dc4b19bc06f8a470144d6a23e6d6b9bab5c1b67cf573e1a5973d`.
- Raw: https://github.com/RedMentos/Aii/actions/runs/40192224815/artifacts/12598203530

## GREEN
- Production commit `5c23c570cd07aa999f32cb1be79698ccc615d3a2`: disposable STEP1 test homes now mask both B1/B2 installed model entries and committed AG0 slot paths; resident runners unloaded. Snapshot/restoration of original model entries and slot states before STEP2; survives restart. C3 remains accessible. Both JEF and STEP12 proofs call the helper. Existing no-B manifest check retained and an additional no-B-slot check added (no acceptance weakening).
- Exact-head Linux-software CI `40192307167`: **38/38 PASS**, compileall PASS, official public privacy scan CLEAN. No native/Redmi proof; PR269's negative result remains.
- Closed GREEN raw artifact `12598198596`, ZIP SHA256 `64d645b9b772829e3baff5eea5418eb6d6e1ec5cff7249ae9b54b65c49435acb`.
- Raw: https://github.com/RedMentos/Aii/actions/runs/40192307167/artifacts/12598198596
- Remote source blob `a4bf9d9247dcbff727a2ccd12c979596658692cb`; tests `e28876b966db6427e09624198c95cd64a3814747`; CI `5d3ec7685aad1fd2703af8c79cf516ff5c7f4255`.

## Limits and exact next step
- PR269 actual native full acceptance remains `IMPLEMENTED_PATHS_PARTIAL` (12 PASS / 8 FAIL); no native rerun on this patch. PR277 offline diagnostic exact-head CI remains FAIL. Original STEP2 `UTILITY_FAIL`, B3 L1 `FAIL`, Body-JEPA `UNAVAILABLE`, `jepa_weight=0`, V13 `INCOMPLETE`. No Redmi.
- Independent external agent unavailable; adversarial RED/GREEN and Run112/Run107/Run269 raw review used; full-suite not claimed.
- Next package: separate owner `v13/code/tests/integration_executive.py` uses the same manifest-only removal and was the third actual native no-B failure. Reuse tested private mask helper in a disposable proof home, assert slot absence in its `body_not_required` check, write RED-first software tests and exact-head CI. Do not weaken any original check or claim native pass without rerun. Serialize any future actual-weight native work.
