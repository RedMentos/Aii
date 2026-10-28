# Run11 native collector isolation hardening amendment — 2026-10-28

Pre-execution review of the collector candidate, before any native heldout run. A caller-supplied `--home` could point at an existing V13 chat brain; creating benchmark sessions there would contaminate user state and violate the preregistered fresh-home condition. Also a Linux-native evidence label must not silently accept an Android/Termux or non-x86 host.

Before any native run, require Linux x86_64/amd64 with no Android/Termux markers, and reject any home already containing `data/db/brain.sqlite3`. The canonical pinned `v13.bootstrap` installs into a fresh home without creating a chat brain. Existing homes must never be overwritten or used for the benchmark. This is a fail-closed preflight, not a model/runtime change.

Software falsifiers: existing brain.sqlite3 and Android platform markers must refuse before model execution; valid new home is not evidence until the actual native run. Original 16 frozen items, model/prompt/seed pins, age and all negative gates unchanged.
