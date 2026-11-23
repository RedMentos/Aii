# ToolForecast: Codex-Review-Befunde im Live-Code behoben (Thread M, 2026-10-13)

Herkunft: GPT/Codex-Review auf `codex/continuation-review-20261013` @ `bdeb4f6`
(`docs/proofs/continuation-20261013/toolforecast-binding-review/`). Codex hat Thread Ms Dateien nicht verändert,
sondern fünf Defekte reproduziert und einen isolierten Kandidaten gebaut. Thread M (Besitzer) hat die Befunde direkt in
`v13/toolforecast.py` und `scripts/install_tool_forecast.py` behoben; der Codex-Kandidat bleibt unverändert auf dem
Codex-Branch (er prüft den alten Quell-Hash und greift deshalb nicht mehr).

| # | Befund (Codex) | Behebung |
|---|---|---|
| 1 | Bestandene Adaption nicht an Kompetenz-Referenz/Encoder/Retention gebunden | `adaptation_binding` (Checkpoint, Modell, Layer, Pooling, Tap-Tool, Retentions-Hash, Kompetenz- bzw. Replay-Hash, `LEARN_RULE`) im Lern-Beleg; `load_adapted(home, ck, enc)` lädt nur bei exakter Gleichheit. Alte Belege ohne Bindung laden nie. Erfahrungspuffer trägt `experience_binding`; fremde/alte Puffer werden beiseitegelegt (umbenannt, nicht gelöscht), `learn` meldet `EXPERIENCE_BINDING_MISMATCH`. |
| 2 | Fehlgeschlagene Neuinstallation überschreibt Retention; `encoder.json` nicht atomar | Retention in neue Generationsdateien `retention-<welt>-<gen>.npz`; erst wenn alle Welten bestehen, `encoder.json` atomar umgeschaltet, danach unreferenzierte Generationen entfernt. Fehlschlag oder Abbruch: neue Dateien weg, alte Installation bytegleich. |
| 3 | Pending-Vorhersage prüft Checkpoint-Hash nicht beim Bewerten | `observe` schließt mit `CHECKPOINT_CHANGED_SINCE_FORECAST` (auch Modell-Hash), keine Bewertung, keine Erfahrung. |
| 4 | Kaputte `encoder.json` lässt Status abstürzen | `load_encoder` → `ENCODER_CONFIG_INVALID` / `ENCODER_CONFIG_UNREADABLE`, auch bei fehlenden Pflichtfeldern; keine Vorhersage, kein Tap-Prozess. |
| 5 | Pending-Kappung lässt `.npy`-Dateien zurück | verdrängte IDs aus der erfolgreichen State-Mutation, danach genau deren Dateien gelöscht. |

Belege (synthetisch, keine Inferenz): `recheck_codex_reproduction.py` führt Codex' `reproduce.py` (sha in `report.json`)
gegen den Stand vor der Behebung (`52880fa`: 5/5 reproduziert) und danach (0/5) aus. Befund 1 stoppt danach schon an der
geänderten Signatur; die Bindung selbst prüft `tests/test_toolforecast.py::test_adaptation_bound_to_competence_encoder_and_retention`.
Neue Tests: Bindung, Erfahrungspuffer, kaputte Konfiguration, Checkpoint-Wechsel, Pending-Kappung, Installations-Lebenszyklus.

Nicht übernommen (bewusst): Codex' Schnappschuss-Prüfung aller Assets vor/nach jedem Tap. Grenze: nur Robustheit des
Lebenszyklus; keine Vorhersagequalität, kein Redmi, kein gelernter Nutzen. Nach dem Update braucht ein Gerät eine
Neuinstallation (`install`) und neue Erfahrung; alte Adaptionen laden nicht mehr.
