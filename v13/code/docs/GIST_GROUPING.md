# WP-G (G1B part): B2 gist grouping

Module: `code/v13/gist.py`. Hooks are in `cognition.offer` (B2 role with the B2 policy only) and `operator.py` (`:gist`).

- **Groups and slots.** B2 reads the source as groups of ~8 native-token-equivalents in up to 12 slots (§1.2.2 BOOT). Tokens are an estimate (one unit per ~5 letters, one per symbol); the native tokenizers stay unchanged (§1.2.3).
- **Resolution.** `age.gist_resolution` sets the group size. Age and maturity may widen it. Code or literal text (4), novelty, conflict (re-entry with a peer message) and low boundary confidence narrow it again (§17.6).
- **Boundary-aware grouping.** Groups are cut at sentence or clause ends within 0.6–1.5× the target size. Exact spans (numbers, dates, code, URLs, quotes) are never cut through, and punctuation stays with its word.
- **Lossless.** Every slot carries its exact SourceRef span, so gist points back to exact/fine text (G1B). When there are more than 12 groups, the oldest are merged first (`scale` > 1): old context gets coarser, recent context stays fine, nothing is dropped.
- **Modes.** SHADOW (default) records the plan in the B2 `QueryPacket.gist`. With `:gist active` (explicit human), B2 receives `gist_slots` instead of the 960-character segments. `:gist preview <text>` shows the grouping.

Bench (`scripts/gist_grouping_bench.py`, result `bench-results/gist-grouping-20261009/report.json`, 5 fixed texts, structural metrics only):

| Mode | Groups ending at sentence/clause | Exact spans cut | Lossless |
|---|---|---|---|
| boundary-aware | 84 % | 0 | yes |
| fixed (8) | 49 % | 2 | yes |

Open: whether B2 answers get better with gist slots needs the model bench (WP-N12, same 70 cohort as STEP2). The C3 candidate benchmark of WP-G is still open.

Tests: `tests/test_gist.py` (5).

## WP-U7 Cross-scale-Kopplung (§3.2A)

**Gist → fein:** Jeder Gist-Slot (`gist.plan`) trägt diese Felder:
- `source_span_refs`: die Fein-Gruppen, die er bündelt,
- `covered`: Quelle und Zeichenbereich,
- `compression_ratio`: Token-Äquivalente pro Slot,
- `boundary_confidence`: das Minimum der gebündelten Grenzen,
- `fallback`: `EXACT_STORE`, wenn der Slot exakte Spans wie Zahlen, Daten oder Code enthält, sonst `B1_DETAIL`.

Im QueryPacket stehen diese Felder unter `gist.slot_coupling`. Die Prompt-Slots bleiben unverändert.

**Fein → lokaler Gist:** Beim Re-entry von B1 (JEF-Frage oder eigenes `needs_reentry`) bündelt `gist.local_bundle` die Fein-Gruppen rund um frühere Zitate und Detail-Fenster zu vorläufigen lokalen Gists:
- ±16 Token, höchstens 96 Token,
- Autorität `PROVISIONAL_LOCAL_GIST`, Rückfall B1_DETAIL.

Das Ergebnis wird immer im QueryPacket als `local_gist` protokolliert. In den Prompt gelangt es nur mit `:gist active`. Die feine Sicht wird nie ersetzt.

**Tests:** `tests/test_cross_scale.py`.
