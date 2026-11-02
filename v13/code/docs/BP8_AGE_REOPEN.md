# WP-BP8: Age-Wiederöffnen mit unabhängigem Rauschsignal (G-AGE-REOPEN-001), Stand 2026-10-27

## Voraussetzungsprüfung
- Schwäche von `noise_aware` (2026-10-10): Das Rauschband ist die MAD der **Kompetenz selbst**, also zirkulär. Ein echter Kompetenzverlust weitet das Band mit und wird teils als Rauschen gelesen. Folge in der Messung vom 10.10.: Zielwechsel langsamer (0,079 gegen 0,053 bei boot).
- Fehlte: ein Rauschsignal, das **nicht** aus der beurteilten Zahl stammt. Gebaut: `age.record(..., metrics['noise_signal'])`, die Streuung einer Wiederholungsmessung desselben Nachweises (zwei unabhängige Hälften derselben Prüfmenge). `noise_aware` nimmt das Signal, sobald es ≥ 4 Nachweise gibt, sonst die alte MAD. Kein neuer Schalter, `age_plasticity_policy` bleibt `boot | stable_reopen | noise_aware`.
- Echtes Gewichts-Lernen (BP2) gibt es noch nicht. Deshalb läuft die Messung auf dem §99-Aufbau (lineare Lerner, synthetischer Strom, echte `AgeControl`), ergänzt um eine **verrauschte Messung** der Kompetenz mit zwei Wiederholungshälften. Das ist Software-Evidenz. Der Anschluss an den BP2-Messaufbau (echtes Training) bleibt offen; der Eingang `noise_signal` ist dafür schon da.

## Vorab-Registrierung (vor dem ersten Lauf, `scripts/bp8_age_reopen.py`, Seeds 401–405)
Strom wie `ablation99.age_stream` (learn 0–400, noisy 400–1000, shift 1000–1500). Alle 50 Schritte ein Nachweis: Kompetenz = 1 − normierter Fehler auf 24 Prüfpunkten mit dem Etiketten-Rauschen der Phase, zwei Hälften à 12; `noise_signal` = |Hälfte A − Hälfte B| / 2.
Arme: `boot`, `stable_reopen`, `noise_mad` (noise_aware ohne Signal), `noise_indep` (noise_aware mit Signal), `no_reopen`, `fixed_conservative` (0,45), `fixed_permissive` (1,0).
Kriterien (Mittel über 5 Seeds, alle müssen gelten, keine Schwellenänderung nach dem Lauf; A = noise_indep, B = boot, C = noise_mad):
1. Fehler in der noisy-Phase: A ≤ 0,85 · B.
2. Fehler in der shift-Phase: A ≤ 1,10 · B.
3. Schritte bis Fehler < 0,1 nach dem Zielwechsel: A ≤ 1,25 · B.
4. Falsche Herabstufungen in der noisy-Phase: A ≤ min(B, C).
5. Fehler in der shift-Phase: A ≤ C.
6. Age hilft gegenüber festen Werten: A noisy-Fehler ≤ fixed_conservative und A shift-Fehler ≤ 1,25 · fixed_permissive.
Wenn alle gelten: `BP8_AGE_REOPEN_SOFTWARE_PASS`. Das schließt G-AGE-REOPEN-001 **nicht**; das Gate bleibt offen, bis dasselbe mit echtem Gewichts-Training (BP2) gemessen ist. Standard `noise_aware` bleibt Nutzerentscheidung (2026-10-22 entschieden).

## Ergebnis v1 (Seeds 401–405): `BP8_AGE_REOPEN_SOFTWARE_FAIL` (3 von 7 bestanden)
Beleg `bench-results/bp8-age-reopen-v1-20261027/result.json`. Mittel: noisy-Fehler boot 0,176 / noise_mad 0,088 / **noise_indep 0,124** / fixed_conservative 0,091; shift-Fehler boot 0,062 / noise_mad 0,100 / **noise_indep 0,093**; Erholung boot 33 / noise_indep 51 Schritte. Bestanden: Krit. 1 (noisy ≤ 0,85·boot), 4, 5 (besser als die zirkuläre MAD beim Zielwechsel). Durchgefallen: 2, 3 (Zielwechsel noch zu langsam), 6a, 6b.
Diagnose (Seed 401, Plastizität je Fenster): Im Zielwechsel liegt die Plastizität bei 0,56–0,72 statt bei etwa 0,8–1. Ursache: `noise_aware` dämpft die Plastizität **nach** der Neuheits-Anhebung (`novel_domain` → ≥ 0,8), mit Faktor 0,5+0,5·damp; das noch nachwirkende Rauschband (sd 0,07 nach der noisy-Phase) drückt damit auch die echte Wiederöffnung. Die Idee „unabhängiges Signal“ allein reicht also nicht, die Reihenfolge der Dämpfung ist der Fehler.

## v2 (neue Idee, vorab registriert vor dem Lauf, frische Seeds 411–415, gleiche Kriterien 1–6b, keine Schwelle geändert)
Änderung nur in `AgeControl.plasticity` und nur, wenn das unabhängige Rauschsignal vorliegt (≥ 4 Nachweise): Neuheits-/Modalitäts-Anhebung (`novel_domain` ≥ 0,8, `new_modality` = 1) gilt **nach** der Rausch-Dämpfung. Ohne Signal bleibt das Verhalten (MAD-Weg) bytegleich. Lauf: `--out bench-results/bp8-age-reopen-v2-20261027 --seeds 411,412,413,414,415`. Urteil `BP8_AGE_REOPEN_SOFTWARE_PASS` nur bei allen sieben; sonst bleibt FAIL stehen und wird so berichtet.

## Ergebnis v2 (Seeds 411–415): `BP8_AGE_REOPEN_SOFTWARE_FAIL` (3 von 7 bestanden)
Beleg `bench-results/bp8-age-reopen-v2-20261027/result.json`. Mittel: noisy-Fehler boot 0,171 / noise_mad 0,081 / **noise_indep 0,114** / fixed_conservative 0,087; shift-Fehler boot 0,032 / noise_mad 0,049 / **noise_indep 0,044** / fixed_permissive 0,029; Erholung nach Zielwechsel boot 25 / noise_mad 46 / **noise_indep 37** / fixed_permissive 23 Schritte. Bestanden: 1, 4 (trivial: alle Age-Arme stufen an der Phasengrenze gleich oft ab), 5. Durchgefallen: 2, 3, 6a, 6b.

**Urteil:** Das unabhängige Rauschsignal verbessert gegenüber der zirkulären MAD den Zielwechsel (Fehler 0,044 gegen 0,049, Erholung 37 gegen 46 Schritte) und halbiert den Fehler in der verrauschten Phase gegenüber boot nicht ganz (0,114 gegen 0,171), bleibt aber hinter beiden festen Werten und hinter boot beim Zielwechsel. Der Zielkonflikt „Rauschen dämpfen, echten Wechsel schnell wieder öffnen“ ist in diesem Aufbau nicht gelöst. G-AGE-REOPEN-001 bleibt offen. Nicht wiederholt, weil ohne neue Idee sinnlos. Offene Ansätze: Neuheit nur nach nachgewiesenem Einbruch über dem unabhängigen Band zählen (Signal-zu-Rausch statt fester Dämpfung); Messung mit echtem Gewichts-Training im BP2-Aufbau, wo das Rauschen aus echten Etiketten-Wiederholungen kommt. Standard bleibt, wie vom Nutzer am 22.10. entschieden, `noise_aware`; `noise_signal` wird in der Laufzeit noch von niemandem geliefert, das Verhalten dort ist unverändert.
