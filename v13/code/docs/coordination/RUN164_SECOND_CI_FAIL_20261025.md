# Run164 second exact-head CI confirms LP3 blockers (2026-10-25)

Run `40164344635`, full-suite job `121082254337`, head `b5e35e5cf4902bddbdc1f5bb8ae89bc7857f3382`: official privacy PASS; **2358 tests, 4 FAIL, 11 SKIP**. Reproduced three inherited LP3 CLI return-code failures (rc=1 vs 2) and one live descendant remaining after synthetic group cleanup. The Run96 Sleep/Wake pending replay failure from first Run164 run **did not recur**; treat as intermittent, not fixed. First Run164 run `40164058854` remains **2358 tests, 5 FAIL**. No masking, no gate promotion.

Next diagnostic: capture stderr from exact LP3 CLI subprocess and compare isolated vs full-suite process environment. Do not mark cgroup containment proven; Run18 test's synthetic cgroup cannot establish kernel containment. Native LP3 model cohort remains blocked pending actual cgroup delegation and ownership/RAM attestations.
