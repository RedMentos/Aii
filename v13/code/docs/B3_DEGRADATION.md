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

## Nachtrag WP-N20: B3-H4 Empfänger-Kalibrierungspaket, B3-H5 hartes Tor, B3-H9-Rest

Modul `v13/b3calibration.py`, Tests `tests/test_b3calibration.py` (7), volle Suite 1326 OK / 4 Skips.

- **`compute(native, message, …)`** baut das vollständige `ReceiverCalibration` (alle Canon-Felder) aus Empfänger-Zuständen am Ziel-Tap und den
  in den Empfänger-Raum abgebildeten Nachrichten: Norm-Mittel/-Streuung, Normverhältnis, Mittelwert-Verschiebung, Varianzverhältnis,
  `geometry_error` (TV-Abstand der Varianzanteile auf den Hauptachsen des Empfängers, richtungsbewusst: gleiche Norm auf „stillen“ Achsen fällt auf),
  `calibration_confidence` (BOOT: Stichprobe × (1 − Geometriefehler)), Datensatz-Hash, `valid_until_revision`. Router-/Residual-/Loss-Felder nur,
  wenn gemessen; `manifold_distance` bleibt leer (nicht implementiert und validiert).
- **`validity`**: Paket fehlt, Feld fehlt, Empfänger- oder Sender-Revision veraltet, < 64 Stichproben, MoE-Empfänger ohne Router-Messung → ungültig.
- **`gate` (B3-H5)** in Canon-Reihenfolge: Kalibrierung fehlt → AUS; Empfänger-Revision geändert → AUS; OOD/Router-Drift/Verteilungsbänder
  verletzt → AUS mit Rückfallkanal; Nutzen nach Kosten ≤ Rückfall → Autorität darf nicht steigen. MoE-Empfänger brauchen kalibrierte
  `B3.max_*`-Schwellen (Canon: „TUNE after calibration“), sonst kein Durchlass.
- **B3-H9**: `latent_utility` mit `router_drift_penalty` und `retention_penalty`; `latent_preferred` nur, wenn LATENT gegen jede vorhandene
  einfachere Basis über ein Validierungsfenster (20 gepaarte Episoden, Mittel − 2 SE > 0) gewinnt. Kein globales `latent_first`.
- **Angebunden:** `b3degrade` liest das Paket aus dem Brücken-Manifest (`receiver_calibration`); `CALIBRATION_EXPIRED` heißt jetzt „kein gültiges
  Paket für die aktuellen Revisionen oder älter als 7 Tage“, die Beförderung verlangt zusätzlich das B3-H5-Tor. Ein Sender-Tausch nach der
  Beförderung führt zu `FAIL` und Rückfall auf EXACT/SYMBOLIC.
- **Grenze:** Im Projekt gibt es noch kein Paar echter Empfänger-Tap-Zustände (B1 → B2 am Ziel-Tap), daher wurde kein echtes Paket berechnet.

## Nachtrag WP-N22: B3-H8 Trainingsreihenfolge im Code

Modul `v13/b3order.py`, Tests `tests/test_b3order.py` (4), volle Suite 1333 OK.

- Die 10 Canon-Schritte je Richtung aus Belegen: Körper eingefroren (aktuelle B1/B2-Revision = die im Brücken-Manifest gepinnte),
  ≥ 64 gepaarte Erfahrungen (`train.samples`, jetzt von `b3bridge.fit` ins Manifest geschrieben), Brücke trainiert (sha + Trainingsprotokoll),
  gültiges B3-H4-Paket, dann `l1_gate`, `l2_gate`, `l3_gate`, `co_adaptation_gate`, `router_gate` mit PASS.
- Ein Schritt zählt nur, wenn alle früheren erledigt sind; ein Beleg über einer Lücke ist `ORDER_VIOLATION` (z. B. Empfänger nach dem Training
  verändert). `require` verweigert Sprünge; `check_job` verweigert gemeinsames Bewegen von Sender-Brücke, Empfänger-Backbone und Router,
  Körper-Gewichte vor Schritt 9 und Router-Lernen vor Schritt 10 oder zusammen mit anderem.
- `b3degrade.promote` verlangt den Schritt der Zielstufe (L1 → L1_UTILITY, L2 → L2_SHADOW, L3 → L3_SHADOW, L4 → CO_ADAPTATION);
  `:doctor` zeigt je Richtung `training_order` (erledigt, nächster Schritt, Verstöße, kanonisch gesperrt).
- Folge für ABDECKUNG: B3 L2–L4 bleiben ❌, und das ist jetzt Canon-konform erzwungen: L1 ist FAIL (WP-J), also ist L2 nicht erlaubt.
