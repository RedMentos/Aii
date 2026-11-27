# Research & Perception Run 66 — A3 projector NPY preflight (2026-11-27)

## Starting state and ownership
- Current main HEAD observed: `6856352fa9a67fd42293c2e6cae4cd86d39417ac` (2026-11-26 03:57:04Z). The historical release-development branch `gpt6/v13-private-remote-bridge-20261111` was at `8d93236c753f0194224c19edc7411d8d7082b1d6`; it is not the latest Perception development head.
- Current Perception provider receiver PR #2557 head: `95c6dd27e15de798cb4b69ddc1d1f5abda746386`, stacked on #2556. PR #2557 restores `consume_projected_frame_from_provider` and the scoped downstream lifetime contract.
- This run owns only the optional local A3 projector loader in `vision_ui_frame_ingress.py`; it does not change Core's Runtime/C3 callsite, QA's Android provider or the device permission state.

## Reproduced defect
The optional `LAB_SHADOW_ONLY` projector loader bounded ZIP sizes and used `allow_pickle=False`, but called `np.load(BytesIO(raw))` before validating NPY member shapes. NumPy's ZIP-backed reader derives an element count from the NPY header and allocates the destination array before reading the payload. A sub-4-KiB archive can therefore declare an enormous `W.npy` tensor with no payload and trigger unnecessary memory allocation before truncation is detected.

Primary source reviewed:
- NumPy `read_array_header_1_0` documents header-only parsing and returns shape, order and dtype: https://numpy.org/doc/stable/reference/generated/numpy.lib.format.read_array_header_1_0.html
- NumPy implementation: https://github.com/numpy/numpy/blob/main/numpy/lib/_format_impl.py (`read_array`: parse shape → calculate count → allocate array → read bytes).

## Implementation and PR
- PR [#2558](https://github.com/RedMentos/Aii/pull/2558), DRAFT, child of #2557.
- Branch: `research-perception/v14-a5-projector-npy-header-preflight-20261127-run66`
- Exact branch head: `39b148c28007775139ff75f8d8fd4ff21cbe0a10`
- Runtime module blob: `cfd86b34d4db9cf1e6fb59fc82bc372efaef5aa9`
- Test blob: `6a1b7df21d2d2a4985725c6f2d9cb16538d6f7e3`
- Adds a pre-allocation header check for the four exact members, NPY 1.0/2.0, float64, fixed `mu/sd/meta` shapes, `W=(38,1..4096)`, and exact header+payload byte lengths under the existing 8 MiB cap.
- Invalid, unsupported, oversized or truncated NPY members fail closed with `PROJECTOR_TENSOR_HEADER_INVALID`; the handcrafted RAW-EYE path still runs. No new dependency, model, weight, persistent user state or permission change.

## Tests and evidence
- LOCAL_LINUX CPython 3.13.5 / NumPy 2.3.5 isolated reproduction: **PASS**. Valid headers are accepted; a <4-KiB archive declaring `W=(38,100,000,000)` is rejected before `np.load`; a truncated in-range tensor is rejected too. This is a standalone helper reproduction, not the full repository suite.
- The repository regression parametrizes the huge-shape and truncated-payload cases and monkeypatches `np.load` to fail if it is reached.
- Full local Aii checkout/pytest: **BLOCKED / NOT_RUN**; no checkout is mounted and `git ls-remote` cannot resolve github.com.
- Exact code/test head 39b148c28007775139ff75f8d8fd4ff21cbe0a10: MediaProjection workflow 45992488704 **PASS** (py_compile + 30/30 Python 3.13 and 30/30 Python 3.14). Exact current docs-only head 89634e661afb223d7113a2eff3894bbbd8ad8501: workflow 45992743680 **PASS** (30/30 on both); RuntimeDeploy integrity 45992743691 **PASS** on Python 3.11 and 3.14. Shared staged/integrated workflow 45992743722 **FAIL**: staged 20 failed / 233 passed / 10 skipped / 2 errors / 41 subtests; integrated 1 failure. The failures are the existing Core audio-composer pin, Core arithmetic/observer source pins and QA PARTIAL-vs-UPDATED migration assertions. No Perception ingress test failed. Parent #2557 exact focused CI is green (28/28 on Python 3.13 and 28/28 on Python 3.14; RuntimeDeploy integrity green), while its shared staged/integrated workflow remains failed on existing Core-owned composer/arithmetic/observer pins and QA migration assertions.

## Product and Canon impact
- Improves resource safety for the optional A3 local student-projector read in the A5 UI-frame path.
- Does not provide OCR, semantic GUI grounding, native model inference, trained latent coupling, a normal-turn Runtime/C3 consumer, Android capture or real user-visible screen understanding.
- A5 remains WIRED_SYNTHETIC / FOCUSED_CI_PASS only. The provider stays OFF pending Core's normal-turn lease-scoped consumer and QA's independent Android consent/onStop/process-death/revoke/restart/rollback acceptance.

## Device, updater and release
- Private read-only relay issues #1017 HEALTH, #1018 PIPELINE_STATUS and #1019 DIAGNOSTICS returned zero authenticated comments (NO_LIVE_RECEIPT).
- Latest private V13OBS #115 is historical (updated 2026-11-24): updater reported enabled and UP_TO_DATE at `8d93236`, but runtime STOPPED_BY_USER, model process stopped, autostart false, and B1/B2 still had TIME_BUDGET failures. This does not prove current installation or updater health.
- No UPDATE_REQUEST, CHAT_SEND, LOG_PAGE, shell command, restart, model download/swap, permission change or device-data mutation was performed.
- **REDMI_UNVERIFIED / NOT_RELEASED.** GitHub PR creation is not deployment.

## Next concrete actions
1. Read back PR #2558 exact Python 3.13/3.14 workflow and shared staged/integrated results; repair only measured Perception regressions.
2. Core continues the #2408/#2557 normal Runtime/C3 integration under the same live UIObservationLease; QA independently owns Android consent and lifecycle proof.
3. Keep optional projector promotion and screen capture OFF until review, integration and explicit device acceptance. No user action is required for this code-only candidate.


## Exact CI closeout addendum

- Current PR #2558 head at readback: `89634e661afb223d7113a2eff3894bbbd8ad8501`; code/test head: `39b148c28007775139ff75f8d8fd4ff21cbe0a10`.
- Focused MediaProjection workflow 45992488704 PASS (30/30 Python 3.13 and 30/30 Python 3.14); exact docs-only head workflow 45992743680 PASS (30/30 both). RuntimeDeploy integrity 45992743691 PASS on Python 3.11/3.14.
- Shared staged/integrated workflow 45992743722 FAIL: staged 20 failed / 233 passed / 10 skipped / 2 errors / 41 subtests; integrated 1 failure. Root causes: Core Recovery pinned audio-composer blob mismatch (`831080bceec90711bd42e0fa4eba47c669975c98`), Core arithmetic/observer pins, and QA migration assertions expecting UPDATED while actual safe result is PARTIAL. No Perception ingress test failed.
- PR remains DRAFT / NOT_RELEASED; no normal Runtime/C3 consumer or Redmi proof. P0 #1904 remains open.


## New primary research reviewed during Run 66 (R-185)

- GlassGround (arXiv:2611.33760v1, 2026-11-25, full 27-page preprint): same-state screenshot vs wearable-camera GUI grounding; 94.8% vs 48.5% mean accuracy across ten open-source models. ReGround raises camera accuracy to 59.4%; PairDistill adds 9.4/12.2 pp on 9B/8B backbones over three seeds, but needs paired training captures. Static single-step only; no action sequences. Its GitHub link returned 404; dataset/code license unverified, no reuse.
- Bel (arXiv:2611.27222v1, 2026-11-20, full preprint): render each sampled action on its own image and use a correctness probability plus threshold/margin to override greedy. Reported +2.8 to +12.1 pp offline gains; live runs are emulator-based. Uses Jev 1.14 through OpenRouter, up to nine candidate calls; no local GPU, but remote/proprietary scorer. No implementation repo/license found, no reuse.
- V14 proposal only: preserve native screenshot vs camera provenance; later test marked-action scoring only if a local visual judge exists, with holdout apps/devices and latency/memory/calibration metrics. No current Redmi-suitable model alternative, download, permission or action change.
