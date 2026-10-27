# WP-Z6j Vorregistrierung: Freigabe-Prüfung relativ zum aktiven Kopf (vor dem Lauf committet)

Anlass: Z6i `Z6I_LEARN_FAIL`. Der Lernweg selbst trug (Arm „lernt nur bei Bedarf“ erfüllte in beiden frischen Seeds alle
Kriterien), der Arm „lernt nach jeder Runde“ scheiterte an der Freigabe-Prüfung des Workers: feste 75 %-Hürde auf dem
neuesten Viertel (1–4 Fragen je Route) lehnte auf Seed 83 jeden Kandidaten ab, obwohl er besser war als der aktive Kopf.

Neu: Schalter `route_head_gate` = `relative` (Standard bleibt `fixed75` bis zu diesem Urteil). Für einen Wortkanal-Kopf,
der einen aktiven Kopf ablöst, gilt statt „Genauigkeit ≥ 75 %“: Genauigkeit auf denselben Prüffragen ≥ aktiver Kopf UND
auf allen bekannten menschlich gelabelten Fragen strikt mehr richtig als der aktive Kopf; weiterhin keine bekannte
richtige Frage verloren, Prüf-Verlust sinkt, ≥ Gerüst. Der erste Kopf braucht weiter 75 %. `:ersetze pruefe` nennt
den nächsten Schritt (`:ersetze gelernt <Id>` oder `:shadow route`, solange der Kopf einer `--lehre`-Regel widerspricht).

Messung: `z6b_lifecycle_bench.py --policies adaptive+now+words+teach+rel,fixed+now+words+teach+rel,fixed+now`,
**frische Seeds 97, 101, 103** (83/89 sind durch Z6i und die Vorläufe unten bekannt).

Kriterien (`Z6J_PASS` nur, wenn alle in **allen drei** Seeds gelten):
- J1 `adaptive+…+rel`: Kopf allein Hälfte ≥ 80 %, Behalten ≥ 90 %, **0** falsche Freigaben, Rücknahme exakt,
  ≥ 1 Übergabe und Laufzeit-Hälfte ≥ 90 %, nach Rücknahme Laufzeit-Hälfte ≥ 90 %, Laufzeit unveränderte Fragen
  ≥ K1 − 5 Punkte.
- J2 `fixed+…+rel`: Kopf allein Hälfte ≥ 80 % und ≥ 1 Übergabe mit Laufzeit-Hälfte ≥ 90 % (die Prüfung lässt Lernen zu).
- J3 Kontrolle K1 `fixed+now` ist nicht sauber (nicht zugleich Hälfte ≥ 80 %, Behalten ≥ 90 %, 0 falsche Freigaben).
Berichtet, ohne Urteil: falsche Freigaben von `fixed+…+rel` (Vorläufe: je 1 auf 83/89, Rauschen kleiner Prüfsätze
bei „jede geeignete Freigabe annehmen“), unnötige Updates, Hälfte-Fragen ohne Regelwörter.

Entscheidung bei `Z6J_PASS`: Standard `route_head_words=true`, `route_head_gate=relative`; Lernen bleibt manuell
(`:shadow route`) mit Freigabe durch den Menschen, empfohlen wird „lernen, wenn nötig“ (`:ersetze pruefe`).

Vorläufe (nicht gewertet): Seeds 83/89/7 mit `+rel`: Hälfte-Fragen (Kopf allein) 1,00 in allen sechs Arm-Läufen, je
1 Übergabe; `adaptive` 0 falsche Freigaben; `fixed` 1/1/0 falsche Freigaben (83: Phase 2, zwei `gist/both`-Fragen
kippen auf `simple`; 89: Phase 1 vor jedem Hinweis).
Grenzen wie Z6i: nur Routen-Kopf, generierte deutsche Umschreibungen, Mensch durch Harness ersetzt, Cloud.
