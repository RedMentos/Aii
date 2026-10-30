# Run11K full unfiltered integrated review-chain regression — verified RED 2026-10-30

Owner GPT-6, exact tested HEAD **`645c70e8c28fb9e016eaa5d068c2d3977075184d`**, branch of draft PR #1240, incorporating JEF #1238, ContextOS #1239 and opt-in Body-JEPA #1240. This is a **full unfiltered** test discovery, not the 121-test focused GREEN and not a production merge.

GitHub Actions **41028701239**, artifact **12964813103**, original ZIP SHA256 **`670025f22c1928724b081e7aff7f94f31670c4f9173d4e7d19591ba318f14989`**, CRC clean, **32/32 inner SHA256SUMS**. Source Canon blob pinned `218464b12a2d27d92524c751922fa8e1c3fb0ea7`. Original native artifact **12951963045**, SHA256 `98a61f622b64b792f38d766da3ef50e9101571b7e616f2c587d6e89ab5e31c46`, exact source HEAD `5e802d235c9501879a3aff07e5134c1455e1769b`, fetched/verified as prerequisite; token never forwarded to redirected artifact host or dependency installs. 15 stage receipts: CANON/NATIVE_FETCH/VENV/DEPS/TORCH/TRANSFORMERS/PEFT/PIP_CHECK/TORCH_IMPORT/TRANSFORMERS_IMPORT/PEFT_IMPORT/COMPILE/PRIVACY/DIFF **exit0**, FULL **exit1**.

**3,719 tests in 387.967 seconds: 2 errors, 14 skipped, zero additional failures.** Both errors are the same pre-existing frozen historical source-pin preflights:
- `test_run34_c3_native_quote_intervention_pilot.Run34NativePilotPreflight.test_pinned_source_model_runner_and_negative_gates`
- `test_run37_c3_rule_use_native_pilot.Run37NativePreflight.test_pinned_source_model_runner_and_negative_gates`

They are not waived, patched or interpreted as GREEN. The test count increased from Run11G 3,698 to 3,719 due new preregistered JEF/ContextOS/Body-JEPA tests; all other tests completed. This full-suite run does **not** include later Sleep A #1241, which was developed on a separate child while this run was executing.

Original raw ZIP privately backed to `/V13-Checkpoints/2026-10-30/Run11K-CurrentChain-FullUnfiltered/` and materialized byte-exact. No unverified native execution is claimed; native ZIP was a pinned **input** from an earlier run, not a fresh Redmi run.

**Next command:** `cd v13/code && PYTHONPATH=.:tests:scripts python -m unittest discover -s tests -p 'test_*.py'`. Independently review Sleep A #1241 focused GREEN and new 350M EMA eval-vs-train prereg #run11m. Run native follow-up only after this full-suite owner terminal and its separate source-only CI verified. Maintain Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 NO_PROMOTION, Body-JEPA UNAVAILABLE, jepa_weight=0, Redmi UNMEASURED, whole V13 INCOMPLETE. No main merge.
