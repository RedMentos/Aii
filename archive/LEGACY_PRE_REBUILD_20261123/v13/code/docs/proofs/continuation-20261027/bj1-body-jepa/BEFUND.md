# WP-BJ1 Befund: B-JEPA-Term im Körper-Adapter (B1 LFM2.5-1.2B) — `BJ1_NO_SIGNAL`

Vorregistrierung: `PREREG.md` (Commit a116676b). Roh: `bench-results/bj1-body-jepa-20261027/bj1-seed1.json`. Code: `v13/body_jepa.py`, `scripts/bj1_body_jepa.py`, 8 Tests `tests/test_body_jepa.py`.
Nur Seed 1 gelaufen (16 Fakten, 30 Schritte, fp32-Master, 4 Arme je ~15-18 min auf 4 CPUs). Seeds 2/3 absichtlich nicht gestartet: Der vorab festgelegte Sonderfall ist schon in Seed 1 erfüllt.

| Arm | gelernt | Umformulierung | Leck (andere Person) | Allgemeinfragen | Rang Kontext (Basis 12,9) |
|---|---|---|---|---|---|
| ohne Adapter | 0,00 | 0,00 | 0,00 | 1,00 | |
| ce (kein JEPA) | 1,00 | **1,00** | **0,81** | 0,875 | 12,6 |
| ema (kanonisch) | 1,00 | 0,97 | 0,81 | 0,94 | 14,4 |
| base (Basis-Ziel) | 1,00 | 0,97 | 0,81 | 0,94 | 14,4 |
| shuffled (falsches Ziel) | 1,00 | 0,97 | 0,81 | 0,94 | 14,4 |

**Urteil nach Vorregistrierung:** Umformulierung des ce-Arms ist schon 1,00 (>= 0,9) -> `BJ1_NO_SIGNAL`: Für K1 gab es keinen Platz, der JEPA-Term konnte dort nichts verbessern. Die frühere Annahme (Umformulierung 33-83 %) galt für den 230M-Körper und die alte Lernrate, nicht für B1.
**Was trotzdem sichtbar ist (nicht als Gewinn gewertet):**
- Das JEPA-Ziel läuft sauber: EMA-Ziel behält Rang (14,56 gegen 14,62 Basis), kein Kollaps, EMA folgt dem Adapter (Abstand 1,36).
- Der Unterschied bei den Allgemeinfragen (0,875 -> 0,94, eine von 16 Fragen) ist bei EMA, Basis-Ziel und falschem Ziel **identisch** -> kommt vom Zusatzterm/Vorhersager als Regularisierung, nicht vom richtigen Ziel (Kontrolle K4 sagt nein). Eine Frage Unterschied liegt im Rauschen.
- Das Leck ist in allen Armen 0,81: Der Adapter beantwortet „Wie heißt der Hund / die Schwester / die Frau …“ mit dem gelernten Fakt (Beispiel: „Your sister plays the bandoneon“). Das ist **das** offene Problem des Gewichts-Lernens, und der Antwort-JEPA-Term ist dafür nicht gebaut (kein Gegenbeispiel). Dazu: im ce-Arm sagt der Körper „The capital of Italy is Trompe“ (Vergessen).

**Folge:** `jepa_weight` bleibt 0, SHADOW, nichts aktiviert. Der Baustein ist gebaut und lauffähig (§13.1/13.4, IH-H25 jetzt auf echten Körpergewichten statt nur synthetisch wie GPT Run38). Ein Nutzen ist hier nicht zu messen, weil die Aufgabe ohne ihn gelöst ist. Nächstes (aus dem Befund): WP-BP2a Leck und Vergessen des Gewichts-Lernens (Teil von BP2), mit Subspace Tuning (FS2) und breiteren Orts-Anker-Sätzen; JEPA danach mit einem Gegenbeispiel-Term (Nah-Fragen als negatives Ziel) erneut, falls das Leck gesenkt ist.
Grenzen: ein Seed, fp32-Master statt Q4, Fakten sind erfunden und kurz, kein Handy.
