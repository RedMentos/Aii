# B3-H10 automatische Degradation + B3-H11 `:doctor` (WP-N19)

Stand 2026-10-13, Thread „Nächste offene Pakete N“. Modul `v13/b3degrade.py`, angeschlossen in `v13/callosum.py`
(`doctor`, `fields`, `choose`), Tests `tests/test_b3degrade.py` (9), volle Suite 1319 OK / 4 Skips (Linux, Software-Test).

## Was vorher war

Nur ein Auslöser (Empfänger-Revision → Kanal-Nutzen zurücksetzen). `:doctor` meldete immer `PASS`, ohne Basis/aktuell für
Router-KL und Experten-Flip, ohne Runner-Revision und ohne Gültigkeit der Kalibrierung.

## Jetzt

- **Leiter** `L4 → L3 → L2 → L1 → EXACT_SYMBOLIC → NO_MESSAGE` als gespeicherter Zustand je Richtung (`B3_DEGRADE`).
  Herabstufen ist ein Zustands-Schreibvorgang, keine Architekturänderung. Jeder Leser fragt das Modul
  (`level`, `latent_level`, `allowed(store, richtung, stufe)` als Tor für einen künftigen Latent-Pfad).
- **Alle 10 Canon-Auslöser aus Belegen.** Ein nie gemessener Eingang heißt `NOT_MEASURED`: er löst nicht aus und zählt nicht als bestanden.
  - HART (direkt auf EXACT/SYMBOLIC): Empfänger-Revision, Runner-Revision (Hash von `bin/llama-server`), Kalibrierung fehlt oder älter als 7 Tage,
    Projektor-Kollaps (effektiver Rang < max(1,5; ¼ Rang) oder Dimensions-Std < 1e-3).
  - WEICH (eine Stufe je Prüfung): Router-KL bzw. Experten-Flip > max(2 × Basis, Basis + 0,01 bzw. 0,02); Retention-Verlust > Basis + 0,02;
    Latent-Nutzen unter dem besten einfacheren Kanal; Latenz > 250 ms oder §97.2-Modus ORANGE/RED (Latent braucht beide Körper, ORANGE erlaubt einen);
    B1/B2-Rollen-Diversität kollabiert (Wort-Jaccard der Offers zu denselben Events ≥ 0,8 über ≥ 5 Paare).
  - Zwischen EXACT/SYMBOLIC und NO_MESSAGE folgt die Stufe den gemessenen Kanal-Nutzen (alle Nachrichtenkanäle unter NO_MESSAGE → NO_MESSAGE, zurück sobald einer gewinnt).
- **Befördern nie automatisch:** `:callosum promote <Richtung>` (explizit vom Menschen), eine Stufe, nur mit gültiger Kalibrierung, gleicher
  Empfänger-Revision wie im Brücken-Manifest, bestandenem Gate der Zielstufe (`l1_gate`, `l2_gate` … im Manifest) und ohne ausgelösten Trigger.
  Die Basiswerte für Drift kommen aus dem Zeitpunkt der Beförderung. Benches schreiben Messwerte mit `b3degrade.record(...)`.
- **`:doctor` (B3-H11)** je Richtung zusätzlich: `degradation_level`, `calibration_valid`, `body_revisions`, `runner_revision`,
  `router_kl`/`expert_flip` als {baseline, current}, `degradation` (Trigger, letzte Herabstufungen, Modus, Rollen-Diversität, `last_fail`).
  `status = FAIL`, wenn eine Latent-Stufe ohne gültige Kalibrierung angetroffen wird; dabei wird sofort herabgestuft, `last_fail` bleibt sichtbar.
- `:callosum degrade` zeigt nur diesen Teil. Telemetrie `b3_degraded`/`b3_promoted` mit Richtung, Stufen und Triggern (Kettenglied `b3_degrade`).

## Grenzen

Heute besteht keine Brücke L1 (WP-J), daher stehen beide Richtungen auf EXACT/SYMBOLIC, LATENT-Autorität bleibt 0. Alle Schwellen sind BOOT-Werte.
Router-KL/Experten-Flip existieren erst mit einem MoE-Empfänger (WP-N11) und werden bis dahin `NOT_MEASURED` gemeldet. `latent_level` im
`:doctor` bleibt der Gate-Status aus `b3bridge.doctor_fields` (Thread L, `verification.py` nicht angefasst); die Autoritäts-Stufe steht in `degradation_level`.
