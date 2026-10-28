# Run11 C2 first validated native route candidate — 2026-10-28

Owner GPT-6, review-only child of #850 at `b454f81da33de9d621af6417ed47ab55cba6263f`. Preregistration commit `40dd6dae4bf433ec0bbfd8a1b0a372660ca79743` preceded the patch. This is **not** integrated into #857's source-frozen transfer64 evaluation, #850's original96 result, or main.

## Source-level defect and isolated change

Prior `scripts/c2_benchmark.py::run_needle` picked the first route-like `arguments.route` from any tool call, then independently validated the native control via `observation(raw)` without using the returned first validated `select_processing` route. A wrong-name tool with a route-like argument preceding a valid `select_processing` could therefore change the scored route. This is a synthetic counterexample; there is **no evidence** that original native 96/transfer64 raw had such extra calls, and those raw benchmark rows did not preserve full function-call traces.

Candidate `scripts/c2_benchmark.py` now uses `pred = observation(raw)['route']` only on success; invalid observations remain `pred=None` and count wrong. Existing `route_of` for other benchmark candidates remains unchanged. New tests include unrelated wrong-name tool first, two valid select_processing proposals (first wins), and unrelated-only refusal. Original benchmark blob `4668d0befe4b06b8713dae49c3619193beaae025` is preserved in existing evaluation branches; candidate benchmark blob `12fe792cacd2dc92c2b3c5c33e01424e20a148e4`, candidate test blob `48554fd86c985fab520888af8bd7910236589683`.

## Evidence status and next steps

This is **software candidate only**. The GitHub Actions exact-source focused/full regression, compile/privacy/diff workflow is staged on this branch; **do not claim GREEN before checking the actual run and raw artifact**. No model loaded, no native inference, no new heldout quality measurement, no source hash rewriting of previous runs. Next command: inspect `.github/workflows/run11-c2-native-validated-route-20261028.yml` run and download its closed evidence; if GREEN, independently review the source diff and only then plan a separately preregistered new-source native cohort. Do not reinterpret #850 or #857 scores as measured under this candidate.

Negative gates unchanged: `STEP2=UTILITY_FAIL`, `B3_L1=FAIL`, `Body-JEPA=UNAVAILABLE`, `LP3_heldout=FAIL`, `jepa_weight=0`, `Age0=RECORD_ONLY`, no Redmi, no whole-system completion.
## Verified Linux software closure

Exact-source GitHub Actions run **40642735294** at `1044a2c53336b665aeab8e0d75291aa5d5b14a66` **GREEN**: **18 focused PASS**, **2217 full PASS, 1 skipped** (228.509 s); source pins, install, compile, privacy scan CLEAN and diff all exit0. Raw ZIP artifact `12796740584` SHA256 `5d6da68607281bdbc6315c10a8cc576f0fb3719fd7286c4dd9739d4bd8ee6cff`, CRC clean, **16/16** internal SHA256SUMS verified. Private Library `/V13-Checkpoints/2026-10-28/Run11-C2-Paired-Audit/C2_NATIVE_VALIDATED_ROUTE_SOFTWARE_PASS_40642735294_sha5d6da686.zip` read back byte-exact at the same SHA256. Later documentation-only commits are not independently retested. **No native C2 inference, Redmi or promotion.**
