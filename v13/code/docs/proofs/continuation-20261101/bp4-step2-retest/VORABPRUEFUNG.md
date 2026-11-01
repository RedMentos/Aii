# WP-BP4 STEP2-Neutest: Vorabprüfung (2026-11-01)

Vorabüberlegung (Pflichtsatz): Ein neuer STEP2-Test ist jetzt nicht sinnvoll, weil sein Verbraucher (C3 liest die Körper-Angebote, BP1c) und unterscheidbare Körper (gelernte Gewichte, BP2) noch fehlen; der sichtbare Gewinn eines Einzeltests wäre daher wieder nur Rauschen oder eine Wiederholung.

## Was STEP2 fragt
Liefern zwei Körper (B1 Detail, B2 Regel/Verlauf) zusammen mehr als ein Körper, und nutzt die Gehirnmitte (C3) das wirklich?

## Bereits gemessen (nicht wiederholen)
| Befund | Quelle | Aussage |
|---|---|---|
| Z2b/Z2d..Z2l (Claude, Okt 21-22) | memory v13-wp-z2c-b2-rule-quote | Zwei Sichten schlagen eine Sicht (+.30), aber ein Körper mit zwei Zuständen reicht (COMBINATION_ONLY). Das Z2-Paket ist als Standard in config.py (b2_quote_select=pointer, body_question_scope=rule_decision, Eligibility-Wächter). |
| v2/v3 nativ (GPT, Okt 30, Seed 29/41, 27 Zeilen) | STEP2_V3_INDEPENDENT_NATIVE_RAW_AUDIT | nur C3 0/18, beide Körper 10/18, mit Rechenfrage 9/18: Körper helfen, Rechenfrage-Variante nicht besser; Bewertung zählt Rechenausdrücke nicht (Messfehler). |
| Exit-Tor (GPT, Okt 31) | BUILD_STATE_PHONE_C3_STEP2_EXIT_GREEN | STEP2_EXIT = EVIDENCE_NOT_PASSING, STEP2 = PARTIAL. |
| BP1 (Claude, Okt 27) | memory v13-wp-bp1-offer-consumer | C3 lernt Angebote zu lesen (0.64 -> 1.00, synthetisch), Drift-Tor verfehlt (KL 0.76 > 0.05). BP1b/BP1c offen. |

## Voraussetzungen für einen sinnvollen BP4-Test
1. C3 liest echte B1/B2-Angebote (BP1c, native GGUF-Adapter, Drift-Tor): FEHLT.
2. B1 und B2 tragen verschiedene Information, nicht nur verschiedene Prompts (BP2 Gewichtslernen im Alltag; B1->B2 Tap-Paar): FEHLT. Ohne das ist "zwei Körper" nur "zwei Prompts", was Z2l schon gezeigt hat.
3. Bewertung erkennt Rechenausdrücke (ausdrucksbewusster Bewerter, frische disjunkte Aufgaben): bei GPT vorregistriert, nicht fertig.
4. Pro Aufgabe ein Ein-Körper-Arm mit gleichen Gewichten (Kontrolle gegen COMBINATION_ONLY): in v3 nicht enthalten.

## Entscheidung
BP4 wartet auf BP1c und BP2. Kein Lauf jetzt. Sobald 1 und 2 stehen, läuft genau ein Test mit den Armen: nur C3, C3+ein Körper, C3+B1+B2 (gleiche Gewichte), C3+B1+B2 (verschiedene Gewichte), frische deutsche Budget-/Terminaufgaben, drei Seeds, ausdrucksbewusster Bewerter von GPT. Erfolg nur, wenn der Arm mit verschiedenen Gewichten den Arm mit gleichen Gewichten um >=3/18 schlägt (sonst bleibt STEP2 ein Ein-Körper-Befund).
