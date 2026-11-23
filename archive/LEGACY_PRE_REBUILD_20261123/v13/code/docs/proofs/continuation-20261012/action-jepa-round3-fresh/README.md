# Action-JEPA Runde 3: frische Testthemen, komplette native Neuerfassung

Stand 2026-10-12, Thread „Nächste offene Pakete F“ (Claude). Linux-Cloud, kein Redmi.
Vorregistrierung `preregistration.json` vor Erzeugung und Erfassung gepusht (Commit `d58cf97`).

**Ergebnis: kein Seed und kein Arm besteht das Gate.** Test nur auf Themen, die nie zuvor erzeugt,
erfasst oder bewertet wurden.

| Seed | Arm 1 (Runde-1-Objective) Test | Arm 2 (Residuum) Test | Mittelwert-Delta | translate_de Arm 2 / Delta |
|---|---|---|---|---|
| 13 | .308 | .172 | .184 | .254 / .328 |
| 21 | .321 | .196 | .196 | .250 / .294 |
| 34 | .291 | .186 | .177 | .266 / .282 |

- Gleiches Bild wie Runde 1/2, jetzt ohne exponierte Testdaten: Arm 1 ~1,7× schlechter als Mittelwert-Delta,
  Arm 2 etwa gleich. Nur `translate_de` schlägt Mittelwert-Delta (6–23 %), `negate`/`question` verlieren.
- Ablauf: C3 (LFM2.5-350M) schrieb Sätze und die vier Aktionen; B2 (Qwen3.5-0.8B, llama.cpp b10964 Release)
  erfasste alle 2475 Zeilen (1875 alt + 600 frisch) in einer Laufzeit, 155 Batches, Exit 0, ca. 14 min.
  Train/Kalibrierung/Retention = Plan-v2-Episoden, Test = 120 frische Episoden, 0 ausgeschlossen.
- Abweichung: `beekeeping` und `hospitals` lieferten 0 verwertbare Sätze (nummerierte Zeilen ohne Satzzeichen),
  Reserve `pottery` genutzt, Reserve `rivers and lakes` lieferte 1 → 5 statt 6 Testthemen, wie in der Reserve-Regel vorgesehen.
- Neue Erfassung nötig, weil der Release-Build vom früheren lokalen Build abweicht (48 Kontrollzeilen: max. Abweichung 1,9e-3, cos ≥ .99991).

Dateien: `report.json` (alle Kennzahlen), `raw-native-parts/` (geschlossenes ZIP `2fb808f9…`: alle Rohbatches,
Registrierung, Erzeugungs-Rohlog), `results-parts/` (ZIP `34f7b1a5…`: Datensatz, Metriken, Checkpoints).
Wiederherstellen mit `scripts/sealed_storage_parts.py restore`. Keine Empfänger-, Lern- oder Runtime-Autorität.

Folgerung für den Plan: §99 „JEPA hilft“ für Text-Handlungsfolgen bleibt **nicht belegt**. Ein linearer
Prädiktor über mittlere letzte-Schicht-Taps lernt nur bei Übersetzung echte Kontextabhängigkeit.
