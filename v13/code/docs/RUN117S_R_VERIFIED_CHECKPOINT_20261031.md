# Run117S-R — source-bound prior USER + untrusted hypothesis integrity, verified checkpoint

## Ownership and exact state

Review-only child of Run117S PR #1499 at frozen parent `dc0851db19a9872d580460dd67e650d247b7b6f2`. Branch `assistant/v13-run117s-prior-source-binding-review-20261031-1915`. Owns only the Run117S isolated selector candidate, new adversarial tests, workflow and scoped docs. No modification to frozen Cognition, Runtime, seed1061 fixture, Body/C3 models, runner or prior original evidence. Run117T native branch is separately owned.

Preregistration `1b94928dcb36d867c3f239f9d753d7b20ca70cea` predates all adversarial tests. Original source RED: Actions 41228679323 at `bbc744407dd03ec0a3d1ba3b674521dcc0b9495d`, **4/4 newly preregistered counterexamples FAILED** as expected; 11/11 inherited PASS, all other exits 0. Original RED artifact 13052741730 SHA256 `acdf28b066eae811d5d1ff175168758a86ba484a7f5b37c1aa10811294166f5c`, ZIP CRC and 16/16 inner SHA PASS, private backup verified present.

First implementation attempt `e18f8f6aa1d97643ae36091e6cb7a79cd5dd5186` and test extension `69fc68871bbaa94decf153fc210317b3265504b8` had a **real NameError** (`current` vs `bound`); original Actions 41228826979 RED (5 test errors, inherited 1 fail + 8 errors), artifact 13052951525. Do not erase or reinterpret that failure. Fixed in `39a9a127721de4b50c605393cf37275b68431e51`.

## Verified final software evidence

**GitHub Actions 41228874590 terminal SUCCESS**, exactly `39a9a127721de4b50c605393cf37275b68431e51`. **5/5** new real SQLite adversarial tests and **11/11** inherited Run117S tests PASS; dependencies, compileall, public privacy scan CLEAN and diff check all exit 0. Original GREEN artifact 13052587101 SHA256 `6275e53cc72dc665cf7752067ddbf2b2a6ff3c54fc702fc298afd83e41389954`, ZIP CRC PASS, **16/16** SHA256SUMS verified against original bytes; private Library byte copy at `/V13-Checkpoints/2026-10-31/Run117S-R-Prior-Binding/run117s-r-prior-binding-green-39a9a127.zip` (3872 bytes). Original RED byte copy remains in the same private folder.

Verified Git blobs on review branch: selector `b3d756eff9b1dbd7079b220ab0e0f20eded340c0`, adversarial tests `a009d8a53daa0354e57a3bb2f3dfb553157dc758`, workflow `a606dff4980f15982b431fa1785b79fdc4649f6e`. The selector now checks prior `_bound_user_event`, exact source/generation and prior durable USER message ID < current; rejects mutated prior message/event and forged hypothesis or authority, using exact persisted OfferPacket summary[:120]. No new semantic truth or model authority.

Evidence class: **software + real SQLite + deliberately synthetic Body**, no native B1/B2/C3/JEF/C2 inference, no Redmi test, no live output, tools, learning or age promotion. `STEP2_EXIT=EVIDENCE_NOT_PASSING`, B3 no promotion, Body-JEPA unavailable, `jepa_weight=0`, whole V13 incomplete.

## Next exact commands / prerequisites

Review-only PR against `assistant/v13-run117s-b2-salient-source-shadow-20261031-hourly11`, not main. Re-run on a fresh checkout:
```sh
cd v13/code
PYTHONPATH=. python -m unittest -v tests.test_run117s_r_prior_source_binding_review tests.test_run117s_b2_salient_source_shadow tests.test_run117s_body_complementarity_preflight
python -m compileall -q v13/b2_salient_source_excerpt_shadow_candidate.py tests/test_run117s_r_prior_source_binding_review.py
cd ../..
python v13/code/scripts/public_repo_privacy_scan.py --base dc0851db19a9872d580460dd67e650d247b7b6f2 --head HEAD --no-worktree
git diff --check dc0851db19a9872d580460dd67e650d247b7b6f2 HEAD
```
Next substantive package: seed1061 pinned native B1/B2/C3 three-arm study on independently owned Run117T branch after owner coordination; if still blocked, continue a different canonical package, not repeat this guard. Remaining risk: stale source/user correction during the actual model call is not proved safe by this synchronous selector; requires separate preregistered post-call test. This package is not production-integrated. Budget remaining UNKNOWN.
