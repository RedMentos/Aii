# Run360 — exact human route labels before external head optimization

Parent: Run359/PR354 `2708ea54640f4bc789e3e001bafdd0ed71f8e147`. Review: PR355. Owner: `assistant/run360-route-label-exact-20261025`. Scope: `v13/code/v13/learning_worker.py`, new test, new isolated workflow. Runtime, original native model/source cohorts, human approval/age gates and the binding Canon remain untouched.

## RED, measured before patch

Exact-head [Actions 40229364950](https://github.com/RedMentos/Aii/actions/runs/40229364950) on `1a527294eb74c6a50c47b12ae4420c73b88abe8a`: **5 tests; 11 failed subtests and 2 errors**. `np.asarray(labels,dtype=int)` silently converted `True`, `1.9` and `"1"` into route class 1; scaffold labels were not checked before writing candidate weights. Source-only raw artifact ID 12612024100, ZIP SHA256 `3e36bb85a74ea472f8c771390b8feb98c7bfdb1b9d161a86ee5583962d49e5c2`.

## GREEN, prospective source-only fix

The worker now accepts only exact JSON integer route IDs 0..3 for both human and scaffold labels; mismatched scaffold lengths or invalid types fail before optimization/checkpoint creation. Original valid integer training remains executable. Exact-head [Actions 40229418244](https://github.com/RedMentos/Aii/actions/runs/40229418244) on `36af5992c03a31f6d0024fbbf83d63aa4bff6054`: **5/5 PASS**, privacy scan **CLEAN**. Raw artifact ID 12611878213, ZIP SHA256 `a59b72fda762dd92be7e3ec51864adff694775131a6f809feef412a785508a10`. Exact Git blob SHAs, central BUILD_STATE snapshot, current owner and next command: `BUILD_STATE_RUN360.json`.

Independent review boundary: checked the PR diff for preservation of numerical optimization and metrics on valid labels; source-only tests cover original valid training and all invalid type families. No separate external agent review was performed.

## Remaining work

This protects input integrity; it does **not** establish route-head utility, source-disjoint generalization, JEPA-weight learning, native model training or Redmi behavior. Historical native results stay bound to their original worker hash. Next: evaluate source-group-disjoint route-head holdout with explicit source linkage and a registered fresh cohort, and continue other canonical packages. Local rerun: `cd v13/code && python -m unittest -v tests.test_learning_worker_exact_labels_run360 tests.test_learning_worker` with isolated `numpy==2.3.5`, `prompt-toolkit==3.0.52`.
