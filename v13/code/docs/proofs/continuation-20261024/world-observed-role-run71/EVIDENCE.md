# Run71 source-bound World Model role evidence

Original `world_model.transitions` admitted FINAL actions with forecast profile role missing or disagreeing with actual output role. The stronger canonical `world.transition` already checks role agreement; the lightweight World Model bypassed it. Exact-function SQLite original **3/6 PASS, 3 RED** (mismatch/missing role).

Fix: only for FINAL, require forecast.profile dictionary, string role and exact match to observed `outcome.role`. Non-FINAL failed actions still supply negative success targets even if role absent. This is a source-integrity guard, not new learning capability.

After fix: 6/6 Run71 isolated SQLite PASS, combined Run70+Run71 **11/11 PASS**, optimized **11/11 PASS**, compileall PASS. Run64 and Run70 synthetic SQLite fixtures updated to include the forecast/observed role fields emitted by the real `world.forecast` / `Runtime.finish_action`. Full checkout, full suite, official privacy, native and Redmi NOT RUN.

Git blobs: world_model.py `153870f7fe1dc4da1166242cc42c3d6be2f981a8`; Run64 fixture `8f8924b684a345fc93a6407cf0f0660db36be8ef`; Run70 fixture `a2471342f7ae37b29281ddeb4ba042073c277a93`; new tests `5abd588e2c10d006278dccf700ea4dea6c012d61`.

Review limitation: this rejects mismatched FINAL fallbacks rather than measuring an alternative action; no causal inference, semantic truth or model weight promotion. STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0, full V13 INCOMPLETE.
