# Run109 — actual pinned Linux b10964 runner activation, prereg 2026-10-31

Owner GPT-6. Review-only child of Run108 PR #1478 exact parent `4e0ace8463885edfecf78d162ac9a37197379070`. Run108 helper shell-based model-free 10/10 GREEN does NOT prove real pinned ELF execution. Original Run107 pinned tar compatibility 41209969115 GREEN only checked ELF header/extraction, never executed it.

## Fixed test before implementation
- On Ubuntu 24.04, use current original `specs/models.json` exact b10964 Linux x86_64 binary archive URL/size/SHA256 (no substituted binary, no model download). The archive is independently hash checked by production `download_file`; keep its original bytes and report SHA.
- Exercise the actual production `install_llama_runner(home)` with an existing old shell-fixture symlink + old runner manifest, real `safe_tar.extract`, real ELF candidate `--version` (bounded 15 s), and new `runner_activation`. Check prior target remains intact, new live symlink points to isolated staging, runner.json SHA equals actual binary, nonempty native version output, and a second identical install is no-op with same target/manifest/staging count. Do not launch GGUF inference, C3/Body, Needle, training or Redmi.
- Re-run from extracted actual phone source ZIP using same exact archive cache; compare checkout and extracted report (normalized paths only) and validate all ZIP manifest hashes. Keep raw stdout/stderr, stage exit codes, original HEAD, SHA256SUMS, privacy/diff, and preserve RED on failure. A failed ELF `--version` is a real install blocker, not proof of broken model.
- No change to production runtime, pinned models/catalog, registered cohorts, source hash, Canon, or original negative gates. This is Linux-native **runner version proof only**, not runner inference, model utility, phone proof or whole-system completion.

Next after original raw audit: pursue current C3/B1/B2 second-attempt utility and actual Redmi installation; do not repeat isolated installer work without a newly observed failure.
