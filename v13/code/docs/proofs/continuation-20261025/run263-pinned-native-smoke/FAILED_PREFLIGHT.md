# Run263 initial Linux CI preflight failure — preserved (2026-10-25)

- Initial head `bd8cc1a2ce34f139edaee43f4793899d9fb7daa0`, GitHub Actions run https://github.com/RedMentos/Aii/actions/runs/40185883125, job `121146493801`: **FAIL**, exit 1 in "Verify exact source and fresh Linux native prerequisites".
- Cause: `actions/checkout` defaulted to the pull request's synthetic merge commit; the preregistered exact-source assertion compared `git rev-parse HEAD` to `github.event.pull_request.head.sha` and correctly refused. The assertion ran before the preflight tee, so no artifact was uploaded. The GitHub Actions raw job log remains the failure evidence.
- **No model was downloaded, no native runner built, no native probe run.** This failure is workflow checkout wiring only, not a model result or native readiness proof.
- Fix commit `5b1900666e6a8ba3186c19a93b5507e811012fb1`: explicitly checkout `ref: ${{ github.event.pull_request.head.sha }}`; keep exact-source assertion and all hash pins unchanged. No force push.
- Next: check rerun exact head, preserve every download/hash/build/probe error and closed raw artifacts. Negative STEP2/B3/Body-JEPA/jepa_weight/full-system gates unchanged.
