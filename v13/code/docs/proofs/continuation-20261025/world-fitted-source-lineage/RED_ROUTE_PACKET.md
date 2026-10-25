# Independent cross-review found ActionSelection route tamper gap — RED

- Head `9827056c7db79ad75b28f12bb9331298a4d1786f`; CI run https://github.com/RedMentos/Aii/actions/runs/40185112187, job `121144142816`.
- 35 actual-source tests: **1 FAIL** (new `test_action_selection_route_tamper_invalidates_fitted_state`); all 34 earlier tests passed.
- Exact cause: the trained route is read from `ActionSelection` packet, while the first fitted-state binding hashed only the actions row. Modifying the route packet did not invalidate the fitted state.
- Raw artifact `12595427670`, ZIP SHA256 `2a0d91fd95042214a2e423c070ef1efd847d05ce313bad0b9e824470e114eb12`.
- Fix must bind the exact selected ActionSelection packet payload and timestamp using the same selection query as `transitions`; no live source/route rewrite, no gate promotion.
