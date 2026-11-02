# WP-BP5 Balken: Gedanken-Vektoren, Auswertung und Vorabprüfung (2026-11-01)

Nur Auswertung vorhandener Messungen, keine neue Messung. Keine Zahl hier ist neu; Quellen sind die Befunde unten.

## Teil a: Versuch 7 auswerten (erledigt, Ergebnis festgehalten)
Quellen: `b3-l1-v7-20261027/BEFUND.md` (Saat 20261301 und Wiederholung 20261302), `b3-l2-v8-20261029/BEFUND.md` (WP-Z4f).
- Kanonisches L1: PASS auf private/escalate und private/apologize, auf beiden frischen 3000-Zeilen-Saaten (REPLICATED).
  Gedanken-Vektor 93,9-95,1 % gegen Attribut-Wörter 87,2-92,2 %. Die Stichprobengröße war die Grenze in Versuch 5/6.
- Strenge Regel (gegen SCALAR, zwei Zahlen): FAIL auf beiden Saaten (Unterschied -2,3 bis +0,3 Punkte). Der Vektor trägt etwa so viel wie zwei Zahlen, nicht mehr.
- L2 (Vektor als Präfix durch den eingefrorenen Empfänger): FAIL auf beiden Aufgaben (82,3 / 83,8 gegen 94,1 / 95,1 beim L1-Lesen).
- Stand: B3_LATENT bleibt `L1_shadow`, Autorität 0, L3 gesperrt, G-CALLOSUM-UTILITY-002 bleibt PARTIAL.
- **Abweichung vom Blueprint (festgehalten, wie im Bauplan verlangt):** Der Blueprint erwartet, dass der Gedanken-Vektor mehr trägt als eine Zahl. Gemessen: gleich viel (strenge Regel FAIL, zweimal), und durch den eingefrorenen Empfänger kommt davon nur ein Teil an (L2 FAIL). Das ist kein Software-Fehler, sondern der Messstand mit synthetischen Vorlagen.

## Teil b: Empfänger-Abstimmung mit echtem Paar B1 zu B2: Vorabprüfung (Denk-vor-Test-Regel)
Ein Satz: Der Test ist jetzt nicht sinnvoll, weil (1) er das Freigabe-Tor übergeht, (2) BP3 die Hälften noch austauscht, (3) die Rechenwerkzeuge hier fehlen. Der mögliche Gewinn (bis ca. 11-12 Punkte, Lücke L2 zu L1) ist aber echt, also nicht streichen, sondern vorbereiten.

| Frage | Befund |
|---|---|
| Daten da? | Echte Zustands-Paare B1 (LFM2.5-1.2B) zu B2 (Qwen3.5-0.8B) gab es für Versuch 7 (3000 Zeilen je Saat), liegen aber nur auf der früheren Cloud-Maschine, nicht im Repo (Platzbedarf). GPTs Run606 hat nur 40 Texte (Einfach-Abbildung knapp durchgefallen, p=0,059): für Abstimmung zu wenig. |
| Verbraucher da? | Ja für L1 (Adapter-Lesen). Eine Abstimmung im Empfänger selbst ist L3 und laut Tor erst nach einem L2-PASS erlaubt; L2 ist FAIL. |
| Hälften endgültig? | Nein. BP3 setzt die zwei offenen Experten-Modelle als B1/B2 ein. Eine jetzt abgestimmte Empfänger-Schicht müsste danach neu gemacht werden. |
| Werkzeug da? | Nein: kein torch, kein natives Training für B2 im Repo (Rückwärtslauf im Empfänger); die letzte L2-Messung brauchte 6,6 h auf 4 CPU nur fürs Vorwärts-Lesen. |
| Gewinn sichtbar? | Obergrenze: L1-Lesen 94-95 % (SCALAR gleich). L2 liegt bei 82-84 %. Höchstens ca. 11-12 Punkte holbar, über SCALAR hinaus nichts. |

## Was BP5 Teil b braucht (Reihenfolge, Voraussetzungen vor dem Test)
1. BP3 fertig (Experten-Hälften B1/B2 festgelegt, Revision im Manifest, B3-H10).
2. Neues Zustands-Paar auf diesen Hälften erzeugen und als Hash-Manifest ins Repo (nicht die Rohdaten), mind. 3000 Zeilen je Saat, zwei frische Saaten (wie Versuch 7).
3. Vor der Messung ein Kleinversuch (Vorabprüfung): Bleibt das L1-Lesen auf den neuen Hälften über NO_MESSAGE und über SCALAR-Gleichstand? Wenn nicht, ist eine Abstimmung sinnlos.
4. Neue Vorregistrierung für einen trainierten Empfänger-Zugang (L3-artig, z. B. kleiner Adapter vor der Ausleseschicht des Empfängers, Hälften eingefroren), mit den Kontrollen PREFIX_OFF, SHUFFLED, RANDOM und Attribut-Wörtern; Tor-Freigabe durch dich, weil L3 bisher gesperrt ist.
5. Ablauf der Messung wie WP-Z4f (5 Saaten, 600 Testzeilen je Split). Nicht im Handy-Paket, Cloud.

## Entscheidung
Teil b wird nicht jetzt gemessen. Kein Test, keine Wiederholung. BP5 gilt als: Teil a erledigt und festgehalten, Teil b vorbereitet und wartet auf BP3 (Hälften) und deine Freigabe von L3.
