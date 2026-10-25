# Run160 first exact-source CI failure, retained

GitHub Actions run 40162856977, job 121077863768, head `5eee8a33e5b146668dbca60c352b529bcb21e981`, 2026-10-25. Focused synthetic parser tests passed. Pinned B1 body GGUF HTTP 206 prefix parsed: **148 tensors, 55 F32**, training authority 0. The pinned B2 gist Qwen3.5-0.8B metadata exceeded the originally registered 8 MiB prefix, so the parser correctly failed with `ValueError: truncated_or_oversize` while parsing an array of metadata strings. The B2 failure is a **bounded prefix limitation**, not evidence of a malformed or unavailable model.

Original first run failed, privacy step was skipped; archived B1 partial report artifact ID 12587281300. Do not delete or relabel it PASS. Source URL, exact revision and model full SHA remain registered; no full model downloaded or trained. Job: https://github.com/RedMentos/Aii/actions/runs/40162856977/job/121077863768
