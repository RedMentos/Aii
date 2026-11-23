# Privater STEP2-Pilot — nativer Lauf 2026-10-20 (Claude-Thread „Privater STEP2-Pilot“)

**Status: gelaufen, 18/18 Zeilen abgedeckt, Kohorte `NOT_CONFIRMED` (1 Zeile ERROR), 0/18 exakt.
Diagnostik, kein Gate. Historisches STEP2 `UTILITY_FAIL` und B3 L1 `FAIL` unverändert.**

## Ablauf
1. GPTs read-only Auditor (Drive `V13_PRIVATE_PILOT_AUDIT_RUN7_DELTA_20261019.zip`, alle 10 Manifest-Hashes geprüft) eingebunden: `../audit_private_pilot.py`, `../test_audit_private_pilot.py` (11/11 OK).
2. Original-Registrierung `pilot/native-registration.json` hier nicht ausführbar (Gerät/Pfade, siehe `REGISTRATION_NOTE.md`); bleibt unverändert `REGISTERED_NOT_RUN`.
3. Neues Home aus dem gepinnten Katalog (`setup_pilot_home.py`): B1/B2/C3-GGUF, Runner b10964 und alle 39 Bibliotheken **byte-identisch** zur Original-Registrierung.
4. Zweite Registrierung `native-registration-20261020.json` **vor** dem Lauf veröffentlicht (Commit `abc5dc4`), Quellen = exakt `a1973d4`.
5. Auditor-Preflight: `PREPARED_NOT_RUN`, 0 Fehler, nichts unverifiziert (`audit-preflight.json`).
6. Lauf: `runtime_adapter.py run` seriell, 19:27–19:30 UTC, 188 s Zeilenzeit, Linux x86_64, 4 CPUs, Peak-RSS 1408 MB pro Runner. Rohdaten: `run/` (report.json sha256 `50ed2226…`).
7. Auditor nach dem Lauf: `REFUSED` (`audit-after-run.json`) — genau wegen der einen ERROR-Zeile; Registrierung, Zeilenreihenfolge, Hashes, FINAL-Aufrufe, Quell-/Modellbytes sonst konsistent.

## Ergebnis (`summary.json`)

| Arm | Zeilen RECORDED | exakt | Aktion richtig | mittlere Feld-Utility |
| --- | ---: | ---: | ---: | ---: |
| b1_model_quotes | 3/3 | 0 | 0 | 0.667 |
| b2_model_quotes | 3/3 | 0 | 0 | 0.639 |
| paired_model_quotes | 3/3 | 0 | 0 | 0.639 |
| same_policy_dual | 3/3 | 0 | 0 | 0.639 |
| no_message | 2/3 | 0 | 0 | 0.361 |
| exact_source_control | 3/3 | 0 | 0 | 0.667 |

Fehlende Felder über alle Zeilen: `remaining` 30×, `action` 17×, `eligible` 15×, `project` 12×.

## Befunde
- **Flaschenhals ist C3 (LFM2.5-350M), nicht der Zitat-Transport.** Auch die Exakt-Quellen-Kontrolle (C3 bekommt beide privaten Regeln wortgleich) liefert 0/3 exakt und in **jeder** Zeile `action: "UNKNOWN"`. C3 rechnet `remaining` nicht (setzt das Budget selbst ein, z. B. 70 statt 70−51=19) und wählt nie eine Option.
- Produzenten-Transport funktioniert meist: B1 zitiert seine Budget-Regel exakt mit korrekter SourceRef; validierte Zitate kamen in allen Modell-Armen an (1 pro Produzent, 2 im Paar-Arm). Mehr Zitate verbessern C3 nicht (paired = b1 = Kontrolle).
- **ERROR-Zeile** `private_bfzwzwww / no_message`: B2 (Qwen3.5-0.8B) hat statt seiner privaten Regel den **öffentlichen** Aufgabentext unter seiner privaten SourceRef zitiert → Adapter lehnt korrekt ab („Quotation differs from Store bytes“), Zeile scheitert, C3 wurde nicht aufgerufen. Der Validator prüft auch im no_message-Arm, wo die Zitate sowieso verworfen würden — das ist die registrierte, strenge Regel, kein Bug. Gleiches B2-Muster wie früher (Offer-Hijack, Thread O).
- `project`-Feld: Orakel erwartet `"BFZWZWWW"`, C3 schreibt oft `"Project BFZWZWWW"` → Formatverlust in 12/17 Antworten; Prompt-/Schema-Thema, nicht verändert (registriert).

## Grenzen
Drei Fälle, ein Seed, Linux-Cloud-CPU statt Redmi; keine Utility-Promotion möglich; Auditor-PASS wäre ohnehin nur Artefakt-Konsistenz. Kein Nachlauf derselben Registrierung (Regel: keine Reparatur durch Wiederholung).

## Nächster sinnvoller Schritt (neue, eigene Registrierung nötig)
C3-Konsument isoliert testen: gleiche Exakt-Quellen-Kontrolle mit (a) größerem Konsumenten (z. B. B1 als Konsument) oder (b) deterministischem Rechen-/Regel-Tool (WP-W2 calc/eligibility) vor C3 — misst, ob STEP2-Nutzen am Konsumenten statt am Transport hängt.
