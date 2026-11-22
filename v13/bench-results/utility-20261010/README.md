# WP-T3 Nutzen-Messung der JEF-Steuerung mit echten Modellen (2026-10-10)

Skript `code/scripts/utility_bench.py`. Modelle: C3 LFM2.5-230M, B1 LFM2.5-1.2B, B2 Qwen3.5-0.8B (Cloud-CPU, llama.cpp b10964).

Aufbau:
- 12 kurze englische Aufgaben mit Regex-Prüfung der Endantwort (kein Modell-Richter).
- Je Arm ein frisches Gehirn mit warmen Prozessen und neuer Sitzung pro Aufgabe.
- Die Baseline lief dreimal, um das Lauf-zu-Lauf-Rauschen zu messen.

| Arm | bestanden | Assertions | Ø Turn (s) |
|---|---|---|---|
| baseline (3 Läufe) | 0,42 / 0,42 / 0,58 | 0,53 / 0,49 / 0,61 | 20–22 |
| effort_low (Fokusschleife praktisch aus) | 0,50 | 0,68 | 21 |
| effort_high | 0,50 | 0,57 | 20 |
| no_inquisition | 0,58 | 0,65 | 20 |
| no_coalition | 0,42 | 0,57 | 20 |
| gist_active | 0,50 | 0,57 | 22 |
| attention_active | 0,58 | 0,65 | 20 |
| coupling_gain 0 / 1 (BOOT 0,5) | 0,50 / 0,58 | 0,61 / 0,65 | 20 / 18 |

## Befund
- **Kein Arm liegt außerhalb des Rauschbands der Baseline** (bestanden 0,42–0,58). Damit gilt für alle vier Mechanismen „hilft“ = nein, auch für `uncertainty_coupling_gain`. Das steht in `utility.json` unter `verdict`.
- **Rauschen:** Die identische Baseline reproduziert nur 4–5 von 12 Antworten wörtlich. Ursache ist das Timing: Observer-Fristen bestimmen, welche Offers rechtzeitig kommen. Bei 12 Aufgaben sind Unterschiede unter etwa ±0,17 nicht messbar.
- **effort_low:** Hier läuft die Fokusschleife praktisch nicht (Entscheidung immer IGNORE, keine Koalition), und das Ergebnis wird nicht schlechter. Auf diesen Aufgaben trägt die JEF-Steuerung messbar nichts bei. Die Antwortqualität begrenzt der kleine C3 (Rechnungen wie 18+27 → 50−45 scheitern in allen Armen).
- **Koalition:** Sie ist fast immer belegt, aber Gerüst-Entscheidungen und Koalitionen ändern sich zwischen den Armen kaum. `attention_active` und `coupling_*` lassen die Entscheidungen gleich.
- **G-FOCAL-CAPACITY-003** hat jetzt echte Daten und eine Ablation. Das Verdikt `focal_coalition_helps` ist False, das Gate bleibt deshalb EVIDENCE_NOT_PASSING.

## Grenzen / Übergabe
- Eine Saat und 12 Aufgaben, nur lexikalische Prüfungen. Für einen echten Unterschied bräuchte es etwa 60 bis 100 Aufgaben und mehrere Wiederholungen, oder deterministische Observer-Fristen (Offers abwarten statt Zeitlimit).
- Nächster sinnvoller Schritt: im Bench-Modus Observer-Fristen festlegen (`observer_seconds` hoch, Tokens fest), damit die Arme deterministisch vergleichbar werden. Danach die Aufgaben auf Fälle ausrichten, in denen B1 und B2 sich widersprechen, denn nur dort kann die Koalition wirken.
