# §99-Ablation: A3-Schüler-Gate für den Fallback (WP-T4) — **PARTIAL**, Gate zu vorsichtig (Thread L, 2026-10-12)

Skript `code/scripts/ablation_aplane_gate.py`, Vorregistrierung `preregistration.json` (Commit `ac40c3d`, vor dem Lauf gepusht), Rohdaten `report.json`.
Echte `student_gate`, `set_student_mode` und `student_fallback` (mit Auto-Rückstufung) und echte StudentEvaluation-Pakete auf SQLite. 3000 Runden je Saat, 5 Saaten. Lehrer verfügbar mit p .90, sonst entscheidet der Fallback: Schüler (Trefferquote = verborgene Genauigkeit) oder Gerüst (.60). Der Schüler steigt von .70 auf .95, dann zwei Einbrüche auf .50 für je 150 Runden. Ein simulierter Nutzer versucht alle 100 Runden die Freigabe.
Primärmaß: Trefferquote in Runden ohne Lehrer (ab Runde 100).

| Arm | Trefferquote | Gate gewinnt |
|---|---|---|
| Gate (echt: n ≥ 50, Übereinstimmung ≥ .90, Retention) | .702 | — |
| immer Schüler | **.882** | 0/5 |
| nie Schüler (Gerüst) | .606 | 5/5 |
| nur Übereinstimmungs-Fenster (ohne Retention) | .760 | 0/5 |

- Das Gate schützt vor dem Gerüst-Niveau nur teilweise: Es lässt den Schüler zu selten ran. Fenster 400 plus .90-Schwelle brauchen nach jedem Einbruch Hunderte saubere Vergleiche; die Retention-Prüfung (letzte 25 vs. davor) wirft zusätzlich bei Zufallsschwankungen zurück.
- In dieser Welt wäre „immer Schüler“ besser, weil die Einbrüche kurz sind (300 von 3000 Runden). Bei längeren oder häufigeren Einbrüchen kann das anders sein: das ist der Preis der Vorsicht, kein Fehler im Code.
- Kandidat für später (getrennt vorregistrieren): kürzeres Fenster und die Retention nur gegen einen klaren Einbruch (z. B. letzte 25 unter der Schwelle), nicht gegen jede kleine Schwankung.
- Offen gelegt: Die Laufzeit wurde vor der Vorregistrierung auf Saat 999 von 1500 auf 3000 Runden verlängert, weil das Gate sonst fast nie öffnete.
- Grenze: synthetischer Übereinstimmungsprozess, Lehrer gilt als richtig, BOOT-Gate-Knöpfe; Destillationskopf und Abhängigkeitskurve nicht getestet.
