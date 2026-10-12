# Action-JEPA Runde 8: nicht-arithmetisches Werkzeug (`sandbox_note`)

Vorregistriert in `preregistration.json` (GitHub `445158c`, vor Welt und Erfassung). Kandidat `scripts/action_jepa_round6_ridge.py` unverändert, gleiche Gates, Seeds 13/21/34, Arme `full`/`proj`, Taps `l_out-11`/`l_out-23` × letzter Token/Mittel.

Welt: eine Notiz „The note reads: <Inhalt>“ (400 von 600 Kombinationen aus 10 Verben × 10 Objekten × 6 Zeitangaben). Aktionen sind echte `sandbox_note`-Aufrufe über die V13-ToolRegistry: `append_done`, `prefix_urgent`, `uppercase` und `undo` (Kritzel-Schreiben, dann Rücknahme über die Registry). Jeder Schreibaufruf ist WRITE_LOCAL, wird von der Policy als PROPOSED gestoppt und pro Aufruf freigegeben. Das Ergebnis ist der aus dem Sandbox-Ordner zurückgelesene Notizinhalt. Insgesamt 3200 freigegebene Schreib-Transaktionen und 400 Rücknahmen, alle als Quellen gebunden.

## Ergebnis

**24/24 PASS → CONFIRMED.** Median Test-MSE 0.14 × Mittelwert-Delta. Pro Handlung liegt die Vorhersage bei 3–54 % der besten Kontrolle (Kopie, Mittelwert-Delta, gemischt), mit vollem Tap 3–15 %. Retention überall besser als die Kontrolle.

## Grenzen

- Kleiner geschlossener Wortschatz: Test-Notizen sind ungesehene Kombinationen bekannter Wörter, kein offener Text.
- Die Freigaben gab das Experiment-Skript als Nutzer in einem Wegwerf-Store, kein Mensch.
- SHADOW: keine Laufzeit-Integration, keine Redmi-Messung, `canonical_architecture_complete=false`.

Rohdaten `raw-parts/` (ZIP `ff72b0e4…`: Welt mit allen Transaktionen, Erfassung), Ergebnisse `results-parts/` (ZIP `330db432…`). Wiederherstellung mit `scripts/sealed_storage_parts.py restore`.
