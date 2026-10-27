# WP-KL2 Befund: stabilere Freigabe-Prüfung — `KL2_STABLE_GATE_FAIL` (1 von 3 Seeds besteht alles)

Vorregistriert in `PREREG.md` (eingereicht als WP-Z6j, Commit 39aa9444; Nachtrag NaN-Fehler 45cdae06, beides vor dem
gültigen Lauf). Seeds 89, 97, 101. Daten `v13/bench-results/kl2-stable-gate-20261027/kl2-seed<S>.json`.

Kopf selbst, Hälfte-Fragen am Ende (Haupt-Prüfsatz) / gesamt / falsche Freigaben:

| Arm | Seed 89 | Seed 97 | Seed 101 |
|---|---|---|---|
| fixed (nur Needle, Kontrolle) | 0,25 / 0,775 / 0 | 0,00 / 0,70 / 0 | 0,00 / 0,75 / 0 |
| fixed+lex+rec (alte Prüfung) | 1,00 / 0,85 / **2** | 1,00 / 0,875 / **1** | 1,00 / 0,975 / **2** |
| fixed+lex+rec+cv (neue Prüfung) | 1,00 / 0,975 / **1** | **0,625** / 0,875 / 0 | 1,00 / 1,00 / 0 |
| adaptive+lex+rec+cv | 1,00 / 0,975 / 0 | **0,625** / 0,90 / 0 | 1,00 / 0,95 / 0 |

Kriterien je Seed: 89 nur **J3 FAIL** (eine falsche Freigabe: gesamt 0,725 -> 0,80, aber unveränderte Fragen
0,906 -> 0,812); 97 **J1 + J6 FAIL** (Hälfte 0,625); 101 alle PASS. Urteil **`KL2_STABLE_GATE_FAIL`** (vorab: alle drei Seeds).

Was gesichert ist (über KL1 hinaus, jetzt 4 Seeds): Der Kopf lernt die geänderte Vorliebe des Menschen selbst — mit
Wort-Kanal + Gewichtung in 4 von 4 Seeds auf 100 % der Hälfte-Fragen (alte Prüfung), die Kontrolle nur mit Needle
nie über 25 %. Die neue Prüfung senkt falsche Freigaben von 5 auf 1 (fixed) bzw. 0 (adaptive) über drei Seeds und
hebt die Endgenauigkeit (Mittel 0,95 gegen 0,90 alte Prüfung, 0,74 Kontrolle). Rücknahme in allen Armen exakt.

Was nicht reicht: (1) Die neue Prüfung ist jetzt zu vorsichtig: Seed 97 lehnte in Phase 2 Kandidaten mit 0,975/100 %
und 0,925/100 % ab, darum blieb der Kopf bei 62,5 %. Vermutete Ursache: der Elternkopf wird auf Korrekturen bewertet,
die er selbst gelernt hat (geschönt), der Kandidat außerhalb der Stichprobe. Die Prüf-Kennzahlen gingen mit den
Wegwerf-Ordnern verloren — nächster Schritt protokolliert sie. (2) Neue Wortlaute übertragen schwach (half_novel
0,375–0,875; detail_near 0,125–0,75): der Kopf lernt teils „Teilungs-Wörter“ statt „Hälfte“. Das ist die Grenze eines
Wort-Kanals ohne Bedeutung; ein besserer Encoder bleibt nötig, damit Lernen über die gesehenen Wörter hinaus trägt.
Nächster Schritt (WP-KL3, neu vorregistrieren): Prüf-Kennzahlen je Job ins Ergebnis, Eltern-Bewertung fair machen
(Eltern und Kandidat beide nur auf Korrekturen, die nach der Eltern-Freigabe kamen), neue Seeds.
Grenzen: nur Routen-Kopf, generierte deutsche Umschreibungen, Mensch durch Harness ersetzt, Cloud, kein Handy.
