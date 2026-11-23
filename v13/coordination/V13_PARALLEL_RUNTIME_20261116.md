# Parallel V13 runtime work — 2026-11-16

This is a coordination notice for the isolated work branch
`work/v13-coordinated-runtime-20261116`, based on phone release ancestor
`858d83c304bfcdf29455bf055ed740fbc24e016f`. It is not an exclusive lock and
does not claim a release, installation, or Redmi result.

| Work | File ownership in this branch | Integration boundary |
| --- | --- | --- |
| Native prompt/source preservation | `v13/code/v13/native_prompt_admission.py`, `v13/code/v13/runners.py`, new prompt regression | Keep selected offers, exact tools and current source through native admission. |
| Observer progress | New `observer_fairness_candidate_20261116.py` and its test | Hash-bound candidate; do not edit frozen `runtime.py`. |
| Online-world learning permission | New `record_only_runtime_guard_candidate_20261116.py` and its test | Guard both actual Runtime and direct online update; do not edit frozen inputs. |
| Context OS source admission | New `context_offer_budget_candidate_20261116.py` and its test | Hash-bound candidate; preserve selected offers and exact tool evidence. |
| Composition and deployment | `v13/code/v13/runtime_deploy.py`, related deployment tests and CI, owned by coordinator | Apply only reviewed, source-bound candidates; test raw installed path and existing staged path separately. |

Other sessions retain their own branches. Before integration, compare their
exact HEADs and changed paths, reconcile overlaps without overwriting them,
and run the affected tests again on the combined tree. In particular, PRs
#1987 and #1989 change the frozen `runtime.py`: their arithmetic work is a
separate dependency and cannot be considered compatible with the pinned
integrated stage until its source binding is reconciled and tested. The
context, learner and observer candidates here are not a replacement for any
other Canon organ or for native/phone proof.

The phone release branch remains owned by the existing integration/release
process. A GitHub draft, local software tests or `UP_TO_DATE` alone do not
establish that these changes run on the phone.
