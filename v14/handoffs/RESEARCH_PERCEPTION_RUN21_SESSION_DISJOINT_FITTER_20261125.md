# Research & Perception Run 21 — Session-disjoint native tokenwise fitter

Date: 2026-11-25
Branch: `research-perception/v14-native-tokenwise-session-fit-20261125-run21`
PR: [#2508](https://github.com/RedMentos/Aii/pull/2508)
Exact code/test head at handoff creation: `c246a56a50f06ca6d8e1ee560e6caa6fcd426a99`
Parent PR: #2507; branch base at creation `7e79ebb6b1ccf001da9ac5cb8d019694c93ef430`

## Functional change

- `v13/code/v13/latent_adapter.py`: TOKENWISE schema v4; session ID is required per pair, must remain constant within a source, is bound into the alignment digest, and cannot cross train/holdout. At least two independent sessions are required on both sides. The adapter records `SOURCE_AND_SESSION_DISJOINT`.
- `v13/code/v13/native_tokenwise_pairing.py`: each source-bound pair record now carries its session ID. New `fit_adapter_from_native_pair_records()` verifies the record envelope/digest, SourceRef/session bindings, unique source IDs/hashes, and consistent sender/receiver role/tap/model/tokenizer bindings. It returns an in-memory PCA+ridge alignment candidate plus a digest-bound fit manifest.
- Tests cover session leakage and pair-record session/digest tampering; existing source-span, UTF-8 byte-piece, activation digest and native input contract tests remain in the workflow.

## Verification

- LOCAL_LINUX CPython 3.13.5 isolated stub-bound wrapper harness: 3/3 PASS (positive split, session-overlap rejection, session-tamper rejection).
- Full local Aii checkout: NOT_AVAILABLE (no checkout mounted; local GitHub DNS resolution fails).
- Exact repository `py_compile` and pytest: NOT_RUN.
- Exact PR #2508 Actions run: NOT_OBSERVED at last poll. Parent #2507 latent workflow run 45683997775 succeeded, but is not evidence for this child. Parent staged/integrated run 45683997887 was still in progress.
- GitHub readback: branch ref resolves to `c246a56a50f06ca6d8e1ee560e6caa6fcd426a99`; PR #2508 remains DRAFT / NOT_RELEASED.

## Consumer and evidence boundary

This is an offline alignment fitter, not JEPA gradient learning, not semantic receiver utility and not native inference. It does not persist vectors, load models, update installed weights, grant authority or enable B3. Core still must wire the selected-row extractor and Cognition.read_tap into the pair builder, then call this fitter only under explicit local consent. A native receiver must later beat exact/no-message/zero/shuffle/repeat/OOD task controls and pass retention/restart/rollback.

No real GGUF extraction, native receiver task, Android/Termux/Redmi test, deployment or release. B3 OFF; REDMI_UNVERIFIED.

## Device and relay

Private V13OBS issue #115 was last updated 2026-11-24T09:28:11Z. No newer receipt was available. Latest recorded turn showed C3 output but did not attempt B1/B2; earlier B1 attempts failed and native latent exchange was unproven. Read-only relay requests #925–927 were created with a 10-minute expiry and had no response at last poll. No LOG_PAGE request was made. No device command, restart, model/weight/permission/data change or UPDATE_REQUEST was sent.

## Next action

1. Obtain exact #2508 CI or run the full repository checkout when available; fix any failure and read back the tested SHA.
2. Coordinate Core's Cognition.tap wiring of native tokenizer pieces, stored sender tap and receiver selected rows.
3. With explicit local consent, build a real source/session-disjoint cohort and test receiver-task utility with all required controls, retention, restart and rollback.
4. Keep event-pooled LATENT_PREFIX_V1 separate; keep B3 OFF until actual receiver utility is demonstrated.
