# WP-Z11 Befund: STEP4 Referenz-Lehrer — `STEP4_EXIT_FAIL`

Vorregistriert in `PREREG.md` (vor dem Lauf committet). Skript `code/scripts/z11_reference_teacher.py`, Daten
`v13/bench-results/z11-reference-teacher-20261026/` (z11.json, run.log; `run-aborted-1.log` = erster Lauf, durch
einen Neustart der Cloud-Maschine nach 31 Turns abgebrochen, unbewertet, danach vollständig neu gestartet).
Lehrer: Qwen3-4B-Instruct-2507 Q4_K_M (unsloth, Apache-2.0, sha256 3605803b…), nur Cloud, Rolle TEACHER.
Self = C3 allein (Effort `disabled`), 60 Aufgaben utility_bench2 Seed 23; Arme off / on / on_repeat (20).

| Prüfung | Ergebnis | |
|---|---|---|
| T1 Self vor Lehrer festgehalten | 60/60 | PASS |
| T2 Lehrer-Text nie in der Verlaufs-History | 1 Treffer (compare07, ein Stück ≥ 40 Zeichen) | **FAIL** |
| T3 Lehrer an/aus ändert Self nicht | 34/60 gleich | **FAIL** |
| T4 Präferenz und Fakt getrennt | 10/10 Auswahlen mit fact + preference, `HUMAN_SELECTED_NOT_AUTOMATIC_TRUTH` | PASS |
| T5 Experience-Fingerabdruck reproduzierbar | 10/20 | **FAIL** |
| T6 RECORD_ONLY ändert keine Parameter | Generation vor = nach, keine neuen Komponenten | PASS |

Urteil: **`STEP4_EXIT_FAIL`**. FAIL bleibt FAIL.

Beschreibend: Lehrer besteht 37/60, Self 46/60 (on) bzw. 42/60 (off); Lehrer besser 5, schlechter 14; Lehrer 34 s,
Self 11 s je Aufgabe. Der Lehrer ist hier als Referenz meist nicht besser als Self (er antwortet oft deutsch und
widerspricht sich, z. B. compare07).

Ursachen (nach dem Lauf ermittelt, ändern das Urteil nicht):
- **T5 ist ein echter Fehler im Fingerabdruck.** Er schlägt genau auf den 10 Aufgaben mit menschlicher Auswahl fehl;
  Self- und Lehrer-Text sind in on und on_repeat 20/20 identisch. `Memory.experience()` nimmt die Auswahl samt
  `message_id` (Zeilen-ID) und `source_ref.source_id` (Zufalls-ID aus `Store.source`) in den Fingerabdruck auf,
  obwohl der Docstring zusagt, nur unveränderlichen Inhalt zu decken. Behoben (Zeilen-/Zufalls-IDs raus, Inhalt-Hash
  und Span bleiben), Test `test_step4_fingerprint_selection.py`.
- **T3 ist eine Schwäche des Protokolls, kein Durchsickern des Lehrers in Self.** Self ist pro Arm deterministisch
  (on = on_repeat 20/20). Die Abweichungen beginnen erst nach der ersten menschlichen Auswahl (summary01) und
  übernehmen den Stil der als Präferenz gewählten Self-Antwort von summary00 („The calculation is: … The stated total
  of X euros is wrong.“: 14/15 summary-Antworten in on, 1/15 in off). Die Auswahl landet im Gedächtnis und formt
  spätere Self-Antworten (on besteht sogar 46 statt 42). Das Protokoll hat Auswahl und Lehrer-Arm vermischt; der Arm
  off hatte keine Auswahl. Ein Lehrer-Effekt ohne Auswahl ist damit nicht gemessen.
- **T2**: ein gemeinsames Stück ≥ 40 Zeichen in compare07; der Lauf hat das Stück nicht gespeichert. Ob das ein echtes
  Durchsickern oder eine Überschneidung über Zahlen/Ortsnamen ist, bleibt offen.

Nächster Schritt **WP-Z11b** (neu vorregistrieren): gleiche Kriterien; Auswahl erst nach allen Self-Antworten in einem
zweiten Durchgang (so misst T3 nur den Lehrer), Leck-Stücke im Ergebnis speichern, Fingerabdruck-Fix aktiv.
Grenzen: generierte englische Aufgaben, Regex-Prüfung, ein Seed, Cloud.
