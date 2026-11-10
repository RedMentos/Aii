# Boss handoff — verified changed-path overlaps (2026-11-10)

Source: GitHub connector `list_pr_changed_filenames` for PRs #1668, #1672, #1673, #1674, #1676, #1677, #1678, #1680, #1681. This is a **changed-file overlap audit, not proof of textual merge conflicts**, successful tests, PR openness, or correct ancestry.

| Shared path | PRs | Owner and integration action |
|---|---|---|
| `v13/code/v13/body_jepa.py` | #1672, #1676, #1680 | Core B1/B2 + QA: integrate dropout/eval-mode and mixed-mode retention fixes in one candidate, run both regression suites and low-RAM test; preserve module train flags |
| `v13/code/v13/online_world.py` | #1673, #1677, #1681 | JEPA & Memory: verify #1681 ancestry and ensure cursor consistency + preflight batch validation + atomic save all survive; crash-injection and restart tests |
| `v13/code/v13/contract_audit.py` | #1674, #1678 | Boss: confirm #1678 builds on #1674, run both audit test suites, inspect version/organ/reference semantics |

The audit utility at `v13/coordination/pr_overlap_audit.py` is standard-library-only and deterministic. Run `python -m v13.coordination.pr_overlap_audit v13/coordination/pr_snapshot_20261110.json --strict` from repo root (exit code 2 denotes detected overlaps). Run `python -m unittest discover -s v13/coordination/tests -v` for the utility's own tests. This is a review aid, not a merge gate unless deliberately adopted.

Priority: resolve overlapping changes in dependency order, with all relevant tests and native Android status marked UNVERIFIED until real device measurements. The five active scheduled roles cover the blueprint domains, but independent 7+ automation jobs are not active. Canon/AGENTS/ROADMAP/BUILD_STATE must still be verified before any substantive merge. The current container cannot resolve github.com, so full checkout/CI is not locally verified in this run.
