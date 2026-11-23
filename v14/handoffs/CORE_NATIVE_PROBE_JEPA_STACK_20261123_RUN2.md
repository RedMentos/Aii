# Core & Harness — native-probe Runtime-close lifecycle checkpoint (2026-11-23)

## Persisted source
- Branch: `core/v14-native-probe-jepa-stack-20261123-run3`
- Base: `jepa-memory/v14-temporal-boss-2443-rebase-20261123-run14` at `9a89b30fc360c0257dc6765e58e3871a6f2df1c6`
- Current head: `d636196247f65b7d9cce4e7d817212e1d5ca9330`
- Candidate PR creation: BLOCKED by GitHub API `403 At least one email address must be verified to do that`. No PR number exists. The earlier #2457 branch is 112 commits behind the current #2454 head and is superseded; it was not force-pushed or merged.

## Real code change
- `v13/code/v13/native_probe_approval.py`: tracks the active exclusive probe lease Event and the native receiver Thread on the Runtime instance; registers before start; clears after join; exposes `wait_for_runtime_probe_shutdown`.
- `v13/code/scripts/integrated_native_probe_approval_overlay_20261123.py`: patches the final staged Runtime.close to wait for worker + lease completion before any pool unload or Store close.
- `v13/code/scripts/stage_integrated_candidate.py`: composes the exact operator + Runtime overlay, emits manifest provenance, and verifies exact staged bytes.
- `v13/code/v13/runtime_deploy.py`: exact stage-builder SHA256 pin updated.
- `v13/code/tests/test_native_latent_receiver_approval.py`: positive concurrent close test and negative non-cooperative-worker timeout test.
- Stage, overlay, deployer and workflow tests were extended. The workflow PR trigger no longer excludes the current JEPA base branch.
- The stale stage-builder pin inherited from #2454 was corrected to the exact recovery builder SHA256; deployer pin was then rebound to the resulting exact stage-builder SHA256. No pin was weakened.

## Readback / provenance checks
All of these were checked against exact current branch bytes:
- Recovery builder SHA256 `f87b63bbbb89f28718d627897d4e5495838f6e1ea2884ccd68239003e749a6b5` == stage `BUILDER_SHA`.
- Stage builder SHA256 `852f0c061abd98a325eb033262921a871226ab91a26acfe949dfb1cea9559501` == deployer `STAGER_SHA256`.
- Native-probe overlay blob `344bb717b0309b89d30b26d435c6696b3e3728dd` == stage pin.
- Approval module blob `465824d251c108eeeeb31884ab140ef9005f8df3` and operator blob `8d59efa1bfb7dea7bbb2fd1af2cf7d2e25adebc4` == overlay pins.
- Recovery wrapper's base, audio, C4 receipt and native-receiver pins all match the exact current files.

## Tests / environment
- LOCAL_LINUX / CPython 3.13.5: PASS — isolated helper reproduction: cooperative cancellation joins worker and waits for lease release; non-cooperative worker times out and fails closed before Store teardown. This is not the repository test suite.
- LOCAL_LINUX full repository pytest: BLOCKED / NOT_RUN — no checkout mounted; `git ls-remote` fails because GitHub DNS cannot resolve.
- GitHub push run [45278456774](https://github.com/RedMentos/Aii/actions/runs/45278456774): `startup_failure`, zero jobs; no CI PASS. Workflow-level failure remains unexplained.
- No llama.cpp model inference or native Android execution occurred.

## Consumer / device effect
- The hook is in the final staged Runtime consumed by `stage_integrated_candidate.py` and the pinned `runtime_deploy.py` deployment chain. It prevents teardown while a native probe is active; it does not make the native probe production-capable.
- Canon path: V14-003 / Callosum native receiver diagnostic -> Runtime exclusive lease -> native worker -> bounded close/Store lifecycle.
- Native probe remains SHADOW_REVIEW_ONLY with production route false, training authority 0 and native receiver authority 0.
- Redmi: latest public issue #1904 evidence says STOPPED_BY_USER. No private relay request, restart, chat, UPDATE_REQUEST, shell, permission change, model/weight swap or data operation was performed. REDMI_UNVERIFIED.

## Next
1. User: verify at least one email address on the GitHub account so the connector can create PRs/reviews; the API currently blocks PR creation with 403. No other user action is needed.
2. Once PR creation is permitted, open this branch as a draft stacked on the exact #2454 head and request review of the close barrier.
3. Re-run exact-head Python 3.13/3.14 staged, overlay, deployer, migration and privacy tests; investigate the workflow startup_failure/no-jobs state.
4. Keep the device stopped until the user explicitly authorizes a device action.
