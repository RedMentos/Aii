# Research & Perception Run 69 — handoff (2026-11-27)

## Current change

- PR: https://github.com/RedMentos/Aii/pull/2563 (DRAFT / NOT_RELEASED)
- Branch: research-perception/v14-npy-preflight-on-audio-session-20261127-run69
- Base: #2561 branch, base SHA c43bd2a84f3329704b80a237bb23e61e6d614c78
- Code/test head: 09e8cee23fab4fe9144253f93bab0a62c3119882
- Code commit: 6712c1517275a91357a95b5e6e51545c1654f02e
- Test commit: 09e8cee23fab4fe9144253f93bab0a62c3119882
- Source blob: 6572cd4a3516824b1b5f7618c6fdf7a090f74807
- Test blob: 5de9aa5d1a1446e496f9bfb0215fe9fd0209fea5

## Why this exists

Core #2562 imported the current A5/A4 Perception receiver and failed two NPY-header negatives on Python 3.13/3.14: (38,256) with truncated payload and (38,100000000) with a tiny archive. The optional local LAB_SHADOW_ONLY A3 projector was sent to np.load before its NPY shape and payload were checked. ZIP/NPZ byte limits alone do not bound the array size declared in the NPY header.

## Change

- Added _validate_projector_npy_headers() using existing NumPy public read_magic, read_array_header_1_0, and read_array_header_2_0 APIs.
- Exact four-member archive; float64 only; fixed mu/sd/meta shapes; W must be 38 × [1..4096]; exact header+payload bytes must fit the existing 8 MiB cap.
- Preflight runs before np.load. Malformed/unsupported/truncated/oversized members return PROJECTOR_TENSOR_HEADER_INVALID. The handcrafted RAW-EYE path still continues; no model, weights, persistence, permissions or dependencies changed.

## Test evidence

- LOCAL_LINUX CPython 3.13.5 / NumPy 2.3.5 isolated helper harness: py_compile PASS, 4/4 PASS (valid archive, huge declared shape, truncated payload, wrong fixed shape). The malformed cases prove np.load is not reached.
- Full local Aii checkout/pytest: BLOCKED / NOT_RUN; no checkout mounted and GitHub DNS unavailable.
- Exact code/test head 09e8cee23fab4fe9144253f93bab0a62c3119882, final docs-only CI head f46e38841913667055a16fa7826a5f41923cb0c9: MediaProjection ingress 46038637335 PASS (py_compile + 31/31 on Python 3.13 and 31/31 on Python 3.14); RuntimeDeploy integrity 46038637336 PASS on Python 3.11 and 3.14.
- Shared staged/integrated 46038637341 FAIL: staged 20 failed / 233 passed / 10 skipped / 2 errors / 41 subtests; integrated 1 failure on Core Recovery audio-composer blob pin 831080bceec90711bd42e0fa4eba47c669975c98. Other staged failures are Core arithmetic/observer pins and QA migration assertions expecting UPDATED while the safe result is PARTIAL. No Perception ingress test failed.
- Redmi/Android/Termux: REDMI_UNVERIFIED. No device access or update. Release NOT_RELEASED.

## Integration owners

- Core: rebase #2562 onto #2563, refresh exact Recovery → Stage → RuntimeDeploy pins, and rerun shared staged/integrated.
- QA: repair and verify the separate PARTIAL-vs-UPDATED migration assertions; no Perception-owned change made.
- Boss/Integrator: sync V14-023 in V14_WORK_BOARD.json. Board was not edited by this lane because it is Boss-owned.
- Perception: exact ingress and RuntimeDeploy CI are green; repair only any new Perception-owned failure, and keep projector LAB_SHADOW_ONLY. Earlier sibling #2558 was closed as superseded by #2563.

## User and Canon boundary

This is optional A3 local-projector input hardening within the A5 RAW-EYE path. It does not prove normal Runtime/C3 consumption, Android MediaProjection, learned visual semantics, B1/B2 delivery, native B3 latent coupling or P0 basic chat. No device deployment, model download/swap, permission change or user-data action occurred. No user action is required.

## Research note

R-188 records NumPy 2.3 public NPY header APIs and the BSD-3-Clause project license. This was upstream API review, not a new empirical paper; no model/data/code/dependency was reused.
