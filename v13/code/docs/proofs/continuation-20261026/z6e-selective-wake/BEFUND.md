# WP-Z6e BEFUND: §24.22 C-native vs. selective body wake (real C3/B1/B2)

Verdict: **Z6E_SELECTIVE_WAKE_FAIL** (prereg `PREREG.md`, committed 4e381a2 before the run; seed 37, 60 tasks, 5 arms).
Data: `v13/bench-results/z6e-selective-wake-20261026/z6e.json`.

| arm | passed /60 | mean time to answer | easy | exact | long | mixed | conflict |
|---|---|---|---|---|---|---|---|
| C_native only (`disabled`) | **40** | **2.8 s** | 4 | 9 | 12 | 4 | 11 |
| A only (`detail`, new) | 31 | 7.8 s | 3 | 2 | 12 | 5 | 9 |
| B only (`gist`, new) | 31 | 7.3 s | 1 | 7 | 11 | 4 | 8 |
| A+B (`max`) | 31 | 14.6 s | 4 | 4 | 11 | 3 | 9 |
| adaptive | 28 | 7.1 s | 2 | 6 | 10 | 3 | 7 |

- E1 easy tasks stay cheap: adaptive wakes a body on 12/12 easy tasks, 2 fewer passes than C_native. FAIL
- E2 unnecessary wakes: 40/40 tasks C_native already solves get a body. FAIL
- E3 escalation recall: 7 rescuable tasks, adaptive woke a passing body set on 5 (71 %). PASS
- E4 adaptive 28 vs best fixed arm 40 (C_native). FAIL
- E5 adaptive 7.1 s vs A+B 14.6 s (49 %). PASS

## What it shows
- On this bench the large bodies cost more than they bring: each body arm fixes 3-4 tasks C_native fails and breaks
  12-13 that C_native solved (mostly exact totals and conflicts: the body offer pulls C3 to a wrong number).
- The shipped adaptive policy never stays on the cheap path (wake rate 100 % in every class) — same failure as Z6a A3.
- The blueprint success condition ("easy stays cheap, demanding tasks reliably get the right bodies") is not met. The
  measured best policy here is `none`; any future wake policy must first beat C_native alone, not A+B.
- New user modes `:effort detail` / `:effort gist` (one body) were added for this measurement; limits still bind.

## Next
Wake only on a signal that predicts *rescue*, not difficulty (R4 part 3: C3 uncertainty predicts C3 errors, but bodies
rarely fix them), and fix the uptake path that lets a body offer overwrite a correct C3 number before any wake
default changes. No default changed. Claim limit: generated English tasks, regex checks, one seed, cloud, no energy.
