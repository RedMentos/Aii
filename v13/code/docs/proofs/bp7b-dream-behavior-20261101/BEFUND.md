# WP-BP7b BEFUND: Traum "nur Strategie" an einer Verhaltensprobe: `BP7b_FAIL` (Seed 3 abgebrochen, Urteil schon fest)

Vorregistrierung `PREREG.md` (+ Nachtrag A1). Roh: `bench-results/bp7b-dream-behavior-20261101/` (Seed 1 in zwei Dateien: facts_only gemessen vor der Entscheidung "lohnt sich", die zwei Traum-Arme danach).
Echter Körper B1, 30 Schritte, 8 erzählte Fakten, 16 Traumeinträge, 12 nie erzählte Fragen. Basis ohne Adapter verweigert 0,92 der nie erzählten Fragen.

| Seed | Arm | verweigert (nie erzählt) | erzählte Fakten beantwortet | Allgemeinfragen | Nah-Fehlgriff |
|---|---|---|---|---|---|
| 1 | facts_only | .67 | 1,0 | .875 | .75 |
| 1 | facts_policy | .58 | 1,0 | 1,0 | .75 |
| 1 | facts_other (Kontrolle) | .42 | 1,0 | .94 | .75 |
| 2 | facts_only | .92 | 1,0 | .94 | .38 |
| 2 | facts_policy | .83 | 1,0 | 1,0 | .75 |
| 2 | facts_other (Kontrolle) | .75 | 1,0 | .94 | .75 |
| Mittel (2 Seeds) | facts_only / policy / other | **.79 / .71 / .58** | 1,0 alle | .91 / 1,0 / .94 | .56 / .75 / .75 |

Kriterium K1 (Verweigern +0,25 über facts_only): **nicht erfüllt** (-0,08). Mit nur noch einem Seed ist es rechnerisch nicht mehr erreichbar (der dritte Seed müsste +0,91 bringen), darum wurde Seed 3 abgebrochen und nicht gelaufen.
Urteil nach Regel: `BP7b_FAIL`.

## Was es zeigt
- Faktenlernen senkt das Verweigern selbst (Basis .92 -> .79 mit nur Fakten, seed-abhängig .67/.92). Das Verhalten "nicht raten" ist also verwundbar und der Traum könnte dort ansetzen.
- Die Strategie-Träume stellen es aber nicht wieder her: policy .71 < facts_only .79. Sie sind besser als die Kontrolle mit unpassendem Inhalt (.71 gegen .58, +0,13): Inhalt zählt etwas, aber nicht genug, um den Verlust durch Fakten auszugleichen. Mehr Traumtext als solcher senkt das Verweigern (facts_other .58), ein Nebenbefund.
- Erzählte Fakten bleiben vollständig beantwortet (kein Über-Verweigern). Allgemeinfragen gehen mit Traum nicht zurück (1,0): anders als in Z9 mit 230M (Retention .22), hier auf B1 kein Schaden.
- Nah-Fehlgriff (Antwort auf Fragen zu anderen Personen) steigt mit Traum-Einträgen von .56 auf .75; eine echte Kosten-Seite, nicht vorregistriert, daher Beobachtung.
- Folge: Sleep B bleibt SHADOW. Ein Traum "nur Strategie" zeigt auch mit Verbraucher keinen Nutzen für Verweigern. Fakt-Autorität bleibt 0. Offen (neue Vorregistrierung, keine Wiederholung): mehr und vielfältigere Strategie-Einträge oder gezielt "Quelle nennen" statt Verweigern.
Grenzen: 2 Seeds, 12 Fragen, erfundene Fakten, englische Probe, Wortmuster-Erkennung, fp32, kein Handy.
