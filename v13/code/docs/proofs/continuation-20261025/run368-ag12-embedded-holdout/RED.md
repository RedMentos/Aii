# Run368 RED — embedded holdout leakage observed before source fix

- Prereg PLAN `e3db9c85c1d307dc47f8ca7a85231446880f8345`; test commit `1661a5d3558d7861940f7a05cb9e44d62ae603c5`; exact CI head `8f3ab1b7053714b3f157307034ddea85839c9531`.
- Actions `40232384911`, job `121286672401`, expected FAILURE: **35 tests, 6 assertion/subtest failures** (three wrapped holdout strings + teacher answer/reasoning/rejected fields), original 30 inherited AG12 solver/live/trainer tests PASS, privacy CLEAN.
- Source SHA256: `agi/generality.py` `d618c29078511493d0d7a06ac3727c9e33885e4b35893a92628e1b738b633d52`; `agi/teacher.py` `6ecbc41c1468f9f26400f7f595cf018a06d9a81c47e0f6bc3285572bc6cf9f11`.
- Raw artifact `12612934100`, reported ZIP SHA256 `714e3d8439b27b833f9f3f6240913c1d0c7a804b218ee5d009f2b9d54b149704`; download/independent CRC verification pending at this checkpoint.
- Next: current-suite normalized substring check and all returned teacher training fields, then exact-head GREEN. No native/model, Redmi, STEP2/B3/JEPA/learning promotion.
