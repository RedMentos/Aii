# Run406 — inspect observed Run401 native stage1 ZIP before restore (2026-10-26)

Base: Run405/PR400 exact `f8896c8ff219f8dd4a1b3717db43fe681c68e3f5`, review branch only, not main. Owner: GPT scheduled continuation; files owned: `.github/workflows/run406-stage1-archive-inventory.yml` and this Run406 proof directory. No concurrent native inference or modification to frozen sources, model/seed hashes or gates.

**Observed, not inferred:** GitHub Actions Run401 `40250662450` completed SUCCESS 2026-10-26 01:05:47Z, native 42-row O_s20, artifact ID `12620379581`, SHA256 `65ac00a8cd2013ebab76828ed3bc25dee5433d1d55a995573387f19de29b530a`, GitHub artifact size `1461613972` bytes. Run402 restore code has `MAX_TOTAL=90000000` and `MAX_MEMBER=16000000`, so the actual archive needs independent inventory before changing caps or starting Run404 stage2. Artifact bytes are not yet independently audited.

Plan: download exact observed ZIP in an isolated read-only GitHub Actions job (no model download/inference), enforce exact SHA and source head, inventory member metadata without extraction, reject unsafe paths, symlinks, duplicates, forbidden model-weight filenames and oversized total; emit bounded top-size table, member counts and raw hashes, preserve all negative gates. Never upload source ZIP again. A failing inventory is retained as RED and must not be bypassed. After inventory, implement a streaming, hash-bound restore/audit with safe disk/memory bounds if necessary, then verify native stage1 raw and proceed to opt-in Run404 preview. No native stage2 until observed validated artifact and exclusive owner.

Acceptance: workflow exact-head PASS and uploaded raw inventory artifact with SHA closure, no false gate promotion. No claim of full STEP2/Redmi/Body-JEPA/AGI.
