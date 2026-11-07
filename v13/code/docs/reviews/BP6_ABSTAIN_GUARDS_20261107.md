# BP6 abstention input guard review — 2026-11-07

Owner: GPT review-only branch `codex/bp6-abstain-input-guards-20261107`, parent `dd0b9a844562b5bb6ffc1085aac7e8fa43ab5a8b` (PR #1592, child of #1589). Not integrated with `codex/resume-20261106` or `main`.

## Change and reason
`abstain_utility` previously divided by `steps` without validating its domain, and accepted invalid confidence/outcome and nonfinite costs. The resulting failure or misleading gain could contaminate the BP6 consumer. The candidate rejects invalid steps, normalizes pairs through the existing BP6 validator, and rejects nonfinite cost inputs. Valid signed finite cost settings are deliberately preserved rather than silently reinterpreted. New focused regression file tests invalid steps, pairs, costs and one valid expected payoff.

## Evidence and limits
GitHub source and tests are remotely saved. The working container could not resolve github.com/api.github.com/raw.githubusercontent.com; no full checkout, test invocation, privacy scanner or independent execution was possible. **No tests are claimed passing.** No original DS3b inputs, frozen preregistration, model weights, native cohorts or gates were changed. Existing STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0, whole-system INCOMPLETE stay unchanged. Review-only, not an authorization to integrate.

## Next exact commands (isolated full checkout with DNS)
`PYTHONPATH=v13/code python -m unittest discover -s v13/code/tests -p 'test_metaeff*py' -v`
`python v13/code/scripts/public_repo_privacy_scan.py --base dd0b9a844562b5bb6ffc1085aac7e8fa43ab5a8b --head codex/bp6-abstain-input-guards-20261107`
Then run BP6 consumer tests, compare #1586/#1589/#1592 against the current resume chain, cross-review one counterexample per guard, and only integrate after dependency and ownership checks. Do not trigger heavy native jobs.
