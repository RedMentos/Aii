# Kompetenz-Signal v2 — COMPETENCE_SIGNAL_CONFIRMED

Stand 2026-10-13, Thread „Nächste offene Pakete M“, Linux-Cloud (nicht Redmi). Vorregistriert `673e3fb` vor dem Lauf, Pilot offen ausgewiesen. 420 Live-Aufrufe, alle SCORED, Live-Check LIVE_PATH_CONFIRMED.

v2 nutzt aus demselben Prefill zusätzlich den Token-Mittel-Tap von `l_out-11` als zweiten kNN-Test mit eigener Schwelle. Ein Zustand gilt als außerhalb der Domäne, wenn einer der beiden Tests anschlägt. Beide Schwellen stammen nur aus Train/Kalibrierung.

| Welt | AUROC | In-Welt markiert | Außer-Welt markiert | Gate |
|---|---|---|---|---|
| calc_counter | .98 | 3 % | **90 %** (v1: 37 %) | PASS |
| note_edit | 1.00 | 0 % | 100 % | PASS |

Nur Bericht: markierte Aufrufe sind tatsächlich schlechter vorhergesagt. Anteil an der besten Kontrolle: Rechnen .50 markiert gegenüber .14 unmarkiert, Notizen .72 gegenüber .07.

Folge: Der Lernmodus `region` von `:toolforecast learn` nutzt jetzt v2 und bekommt dadurch für Zahlen deutlich mehr Lernbeispiele. Die bestätigte Lern-Runde 2 (`5760bc7`) lief noch mit v1; eine Wiederholung mit v2 ist eine neue Messung.

Dateien: `preregistration.json`, `plan.json`, `report.json`, `live-report.json`, `rows.json`.
