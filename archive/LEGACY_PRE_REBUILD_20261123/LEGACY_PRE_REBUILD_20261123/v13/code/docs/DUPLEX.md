# WP-N14 Live / Full-duplex im Text

Blueprint: §4A.4 (gemeinsame Zeitachse, provisorisch vs. autoritativ), G10D (Live-Pfad blockiert nicht), §24.30.
Code `v13/duplex.py`, Hooks in `runtime.submit` / `_turn`, Tests `tests/test_duplex.py`, Befehl `:duplex`.

## Verhalten

Kommt eine Nachricht, während V13 noch antwortet, entscheidet der Live-Pfad sofort und ohne I/O unter dem Runtime-Lock:

| Entscheidung | Auslöser (`duplex_mode=auto`) | Folge |
|---|---|---|
| CONTINUE | normale Nachricht | laufende Antwort wird fertig, neue Nachricht wartet (Turn-Taking) |
| INTERRUPT | nur ein Stopp-Wort: stop, wait, never mind, stopp, warte, abbrechen … | laufende Antwort endet sofort |
| REVISE | Korrektur am Anfang: no, actually, I meant, nein, doch, ich meinte … | laufende Antwort endet sofort, die Korrektur wird beantwortet |

`:duplex interrupt` lässt jede überlappende Nachricht unterbrechen, `:duplex off` schaltet auf reines Turn-Taking.

## Garantien (§24.30)

- **Neue Eingabe ändert die folgende Ausgabe.** Der nächste Turn bekommt einen `DUPLEX_HANDOFF`-Block: unterbrochene Frage, Teilantwort (höchstens 600 Zeichen), Beziehung (STOP/CORRECTION/OVERLAP).
- **Media-Loop blockiert nicht.** `submit` wartet nicht auf die laufende Antwort (im Test < 0,5 s, real eine Regex plus ein Event-Signal).
- **Provisorisch wird nicht gelernt.** Die abgeschnittene Antwort bleibt CANCELLED mit `meta.duplex.provisional=true`. Native Historie, implizite Bewertungen und AG6 nehmen nur FINAL, und WP-K beerdigt provisorische Items.
- **Übergabe verliert keine Quelle.** Die Quelle der unterbrochenen Frage und die Teilantwort (als `PROVISIONAL_INTERRUPTED_OUTPUT`) stehen in den `context_source_refs` des neuen Turns.
- **Telemetrie:** `duplex` mit decision, relation, mode und latency_ms.

## Grenzen / offen

- Nur die Text-Zeitachse. Audio/Video-Streams, Barge-in bei Sprache und JEF-Entscheidungen speak/listen/pause mehrmals pro Sekunde bleiben STEP 11.
- Stopp-/Korrektur-Erkennung läuft über Regeln (EN/DE). Ein gelernter Klassifikator (C2) wäre der nächste Schritt; Labels gibt es aus späteren Korrekturen.
- Tiefe Arbeit (A/B-Observer) läuft schon im Hintergrund und wird durch neue Eingaben abgebrochen. Asynchrone Offers, die in eine *laufende* Antwort einfließen, gibt es noch nicht.
