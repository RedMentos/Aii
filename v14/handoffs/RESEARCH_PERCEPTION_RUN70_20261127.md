# Research & Perception Run 70 — A3 tile-projector OOD abstention

**Run window:** started 2026-11-27 19:29:41 Europe/Berlin; completion checkpoint is recorded in the chat report.  
**Owner:** Research & Perception.  
**Repo:** RedMentos/Aii.  
**Branch:** `research-perception/v14-a3-tile-ood-abstention-20261127-run70`.  
**PR:** https://github.com/RedMentos/Aii/pull/2565 (stacked on #2563).  
**Current code head at this checkpoint:** `66b6dda83ec4d9c013f225573ce4b9a5c46a9503`.  
**Parent:** #2563 branch `research-perception/v14-npy-preflight-on-audio-session-20261127-run69`.

## What changed

The optional A3 tile projector used by the explicit `:image find` operator now computes a source-disjoint descriptor threshold from leave-one-image/source-out folds. It abstains on OOD tile rows, preserves in-domain scores, leaves unknown heat-map cells null and reports explicit status/region IDs. The gate is optional and shadow-only. Existing projector files/Store records without the new metadata retain the previous behavior.

`Projector.load` also uses `allow_pickle=False` and validates the ridge metadata and tensor geometry. The change does not modify the Core-owned `vision_ui_frame_ingress.py` file currently under #2562, does not change A5 provider acceptance, and does not claim a normal C3 consumer.

## Research

R-189 records the full read of PMA (arXiv:2607.26947, submitted 2026-07-29, accepted ACM MM 2026). PMA's descriptor-triggered projector expansion motivates monitoring projector shift, but its LLaVA/InternVL 7B and 4×80GB A100 evaluation is not mobile evidence. The linked PMA repository has no root LICENSE file; no code or weights were reused. This PR implements only a small RMS-z abstention guard, not PMA's autoencoder, anchor, expert expansion or soft router.

## Tests and evidence

- LOCAL_LINUX: CPython 3.13.5, NumPy 2.3.5, Pillow 12.3.0.
- Scratch `py_compile`: PASS.
- Source-disjoint threshold + standardized distance: PASS.
- Six-source synthetic UI fixture: threshold 1.546; held-out in-domain two-object frame 16/16 tiles retained; black and checkerboard shifts 0/16 retained.
- Full local Aii repository pytest: NOT_RUN / BLOCKED (no mounted checkout; `git ls-remote` failed because github.com DNS could not resolve).
- Exact updated-head CI: pending final readback at this checkpoint. Runs: visual bridge 46051827002; MediaProjection ingress 46051826940; shared staged/integrated 46051827046.

These are synthetic/local helper and hosted CI categories only. No native model, Android capture, microphone, Redmi, weight update, or deployment proof.

## Product / Canon effect

- Improved: explicit A3 tile-projector `:image find` abstention under obvious distribution shift.
- Not improved/proven: A5 MediaProjection receiver adoption, normal Runtime/C3 consumer, B1/B2, B3 native learned latent coupling, JEPA, persistent learning, voice, Android control, install/update/rollback or whole-system acceptance.
- Current A5 provider path remains WIRED_SYNTHETIC; B3 remains SYMBOLIC_ONLY for native latent coupling. Product is NOT_RELEASED.
- Device: REDMI_UNVERIFIED. Updater/install status UNKNOWN; no update was attempted.

## Coordination / next step

1. Boss/Integrator: add PR #2565 to the whole-Canon epic #1984 and update the shared board/coverage index after review; this lane did not edit Boss-owned files.
2. Read exact CI on head `66b6dda...`; do not infer success from an in-progress run.
3. Resolve #2563's shared staged/integrated gate failures on Core/QA-owned pins before merging this stacked PR.
4. After Core completes #2562, coordinate a separate A5 frame-ingress adoption of the same descriptor threshold; keep the normal Runtime/C3 callsite with Core and Android lifecycle with QA.
5. No user action is required.