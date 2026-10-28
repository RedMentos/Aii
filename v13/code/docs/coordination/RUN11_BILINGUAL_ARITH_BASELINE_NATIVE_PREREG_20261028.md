# Run11 bilingual arithmetic baseline native arm prereg — 2026-10-28

Owner GPT-6, independent review child of #848 at `db7702f151aa951a6f4293f98585687e6ca9c8ae`. This is the **baseline** companion to candidate collector PR #854 and scorer PR #853. No native run yet.

Exact source comparison against candidate #854 at `e94edd495001385702c055b01713017386323da4`:
- `runtime.py` Git blob `68e7ed1352800174972558f1e0b0683a42c8689a` on both.
- `runners.py` `efda7aa1aa5729e974d0d641870d4da05d21c961` on both.
- `models.py` `bd035cf8029850cce00b179edf533e53bf24358a` on both.
- `toolstep.py` `9640b2ce9abfc08cb82f7b550e18d856d9513f08` on both.
- `specs/models.json` `7af05962af41d0bc3f7dd18ef01d4eba55eabf99` on both.
- **Only the frozen prompt source differs among those pinned runtime files**: baseline `v13/prompts.py` Git blob `a74d7517a7ab70e801e177b58da057e57fd3460c` vs candidate `646c6f31b52ca2664c1952af7c7e842fc3e20885`.

Copy the exact immutable **16-row author-defined fixture** `ceda0a5cb506cf09885652b24893cf7d8fdff63b` and the candidate's strict offline scorer/native collector source files *byte-identically*, without changing their evaluation logic. A separate baseline-only test adaptation may switch `CANDIDATE_PROMPT` to `BASELINE_PROMPT` where needed to exercise Age0 config guards on the baseline source. The native collector must be run on a distinct fresh scratch home, with the baseline prompt Git blob, identical model catalog, 120s per turn, frozen row order, fresh session per row, and actual per-row runner file hashes. Record the separate source commit and raw evidence, do not mix baseline/candidate manifests or private homes.

Do not start baseline native concurrently with candidate or another heavy native owner. Preflight, focused software and independent raw verification must precede any quality comparison. Route differences are not silently attributed to the prompt alone; compare `paired_route_changed_ids`. A single global scratch brain per arm does not prove global state isolation.

No AGI/Redmi/whole-system claim. Age0 RECORD_ONLY, jepa_weight0, STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, LP3 heldout FAIL unchanged.
