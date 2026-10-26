# Befund: Zweiter Regel-Leser aus einem kleinen Sprachmodell (WP-UR8, LLM-Variante, 2026-10-26)

**Hinweis zur Einordnung.** Parallel hat ein anderer Thread WP-UR8 mit einem *gelernten* Zweitleser (Wort-Statistik, kein
Sprachmodell) gebaut und gemessen (Branch `claude/project-thread-27r15q`, PR #416, `../user-rules-v8/`, Urteil
`SECOND_OPINION_HELPS`). Diese Variante hier prüft dieselbe Idee mit kleinen Sprachmodellen, auf eigenen, eigens versiegelten
Prüfsätzen (eigene `holdout_de5.json`, eigene Runde 8 mit LFM2, AFM, Trillion). Damit sich beide nicht überschreiben, liegt
diese Variante als reiner Beleg unter `user-rules-v8-llm/`, der damals eingefrorene Code unter `code_snapshot/`
(Hashes = `freeze_v8.json`, geladen über `snapshot.py`). Der Laufzeit-Code bleibt der von PR #416.

## Urteil

- Zweitleser: **`SECOND_READER_TOO_COSTLY`** (schon in der Auswahl auf bekannten Sätzen festgestellt, siehe `PREREG.md`
  Nachtrag; die Messung auf frischen Sätzen bestätigt es). Der vorab festgelegte Kandidat Gemma 3 1B mit Auftrag A bringt auf
  Runde 8 **keinen Gewinn** (12 → 12 Fehlersätze). Die Qwen-Modelle halbieren die Fehler, lösen dafür aber bei 56–95 % der
  Sätze ohne Regel eine Rückfrage aus (erlaubt: +10 Punkte über 28 %).
- Fester Leser v8 dieser Variante: **`USER_RULES_V8_UNSAFE`**, etwas besser als v7 (T1 7 statt 8, T2 12 statt 14 Fehlersätze).
- Was gehalten hat: **Z2 = 0** bei allen sechs Kombinationen. Keine einzige Probe wurde durch ein Modell lockerer als beim
  festen Leser allein. **Z4 = 0 %** ungültige Antworten (JSON-Grammatik). Die Sicherheits-Konstruktion „Modell darf nur
  vorsichtiger machen“ funktioniert also, nur der Nutzen pro Rückfrage ist zu klein.

## Zahlen

Fester Leser v8 allein / v7:

| Prüfsatz | Sätze | Fehlersätze v8 / v7 | Sicherheitsfehler v8 / v7 | übersehene Verbote v8 / v7 | Sätze ohne Regel mit Rückfrage |
|---|---|---|---|---|---|
| T1 `holdout_de5` (Autor) | 60 | 7 / 8 | 25 / 28 | 4 / 4 | 31 % |
| T2 Runde 8 (LFM2 2.6B, AFM 4.5B, Trillion 7B; Audit 116 von 360) | 116 | 12 / 14 | 34 / 40 | 8 / 9 | 28 % |

Mit Zweitleser (alle erkundend; ungültig 0 %, lockerer als fest 0 Proben):

| Modell / Auftrag | T1 Fehlersätze | T1 Rückfrage ohne Regel | T2 Fehlersätze | T2 Rückfrage ohne Regel | Z1 | Z3 |
|---|---|---|---|---|---|---|
| Gemma 3 1B / A (vorab gewählt) | 6 | 56 % | **12** | 44 % | nein | nein |
| Gemma 3 1B / B | 6 | 62 % | 9 | 46 % | nein | nein |
| Qwen 2.5 1.5B / A | 3 | 88 % | 6 | 85 % | ja | nein |
| Qwen 2.5 1.5B / B | 4 | 94 % | 5 | 95 % | ja | nein |
| Qwen 2.5 3B / A | 4 | 62 % | 9 | 46 % | nein | nein |
| Qwen 2.5 3B / B | 3 | 56 % | 6 | 64 % | ja | nein |

Keine Kombination erfüllt Z1 und Z3 zugleich. Wer die Fehler halbiert, fragt bei fast jedem harmlosen Satz nach. Das ist in
der Praxis wertlos: Der Nutzer würde jede Rückfrage wegklicken.

## Wo der feste Leser v8 frisch daneben lag

- Verbot als Zustand ohne Verneinung: „Die Galerie bleibt unangetastet / unbeschädigt / unberührt / steht unverändert da“.
- Sperre in Umschreibung: „Surfen fällt heute aus“, „Die Leitung nach draußen bleibt gekappt“, „Signalweg ist abgeschnitten“,
  „Heute ist das Surfen abgeschlossen“, „Bilder entsorgen? Vergiss es.“
- Erst fragen in Umschreibung: „ehe er rausgeht“, „vor seiner Abreise“, „brauchst jedes Mal mein Okay“, „einmal ein Ja von mir“,
  „Was auch immer du anstellst: vorher mich fragen.“
- Holprige Sätze der Modelle („Ich bin beschwert, wenn du auf meine Notizen rumstelle“).

Das deckt sich mit dem parallelen Befund: Ein fester Leser schließt jede Runde die Formen der letzten, die nächste bringt neue.

## Folgerung

1. Laufzeit: Es gilt der parallele WP-UR8 (PR #416) mit dem gelernten Zweitleser. Er ist billiger (kein Sprachmodell nötig)
   und hat auf seiner Runde 8 die Fehler halbiert, bei 23 % Rückfragen auf T2.
2. Ein kleines Sprachmodell als Zweitleser lohnt sich so nicht. Falls je wieder: nur fragen, wenn der feste Leser *gar keine*
   Einschränkung findet (so macht es PR #416), statt bei jeder abweichenden Einschätzung.
3. Diese Prüfsätze (`holdout_de5` dieser Variante, Runde 8 LFM2/AFM/Trillion) sind jetzt bekannt. Sie sind ein guter
   zusätzlicher Lernstoff für den nächsten Schritt WP-UR9 (gelernter Zweitleser auch bei zu engem Ziel), aber kein Prüfstein mehr.
4. Sicherheit hängt weiter nicht am Leser: Alles mit Wirkung nach außen bleibt ein sichtbarer Vorschlag, den der Nutzer pro
   Aufruf freigibt.

## Methode

Jeder Schritt war ein eigener Commit, in dieser Reihenfolge:
1. Vorregistrierung mit `holdout_de5.json`.
2. Runde 8 roh und ungelesen (`c5b2ba7`, SHA-256 `e56d9e47…6747`).
3. Auswahl auf bekannten Sätzen und Einfrieren, mit Nachtrag vor jedem Blick (`380b54a`).
4. Audit von Hand (`d7feef7`).
5. Erst danach die Messung (`run_round8.py`, `result_round8.json`; Modell-Antworten in `measure_cache.json`, Temperatur 0).

Es gab kein Nachbessern nach der Messung. Nach der Messung wurde der Code in `code_snapshot/` verschoben, damit er den
parallelen Laufzeit-Stand nicht überschreibt. `run_round8.py x x score` liefert daraus byte-gleich dasselbe Ergebnis.
`known_check.py` ergibt 0 Fehler auf allen bekannten Sätzen.
