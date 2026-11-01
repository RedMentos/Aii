# WP-BP2d Vorregistrierung: mehr erzeugte Anker je Fakt (`locality_gen=4`) im AG6-Weg auf C3 350M

**Vorabüberlegung (Nutzerregel 27.10.).** BP2c (`bp2c-ag6-wiring/BEFUND.md`): erzeugte Anker (2 je Fakt) senken das Q4-Tor-Leck von 0,52 auf 0,20, knapp an der Tor-Schwelle (0,2; Seed 1 0,214, Seed 2 0,179).
Vorstufen vorhanden (Pipeline, Generator, Tor). Platz: von 0,20 auf <= 0,15 sind nur wenige Fragen (28 Nah-Fragen je Lauf, 1 Frage = 0,036), also ist das Signal klein; deshalb eine einzige vorab festgelegte Änderung (4 statt 2 Anker je Fakt),
**neue Seeds 3 und 4** (nicht die, an denen BP2c gesehen wurde), nicht auf alten Seeds nachgestellt. Subspace bleibt aus (schadet bei 350M, BP2c). Fehlt noch: Handy, echte Nutzerfakten.

**Arme** (echte Pipeline wie BP2c, alle `gate_held_out=true`, body-Zusätze wie BP2c: max_steps 120, min_steps 20, target_loss .05): live | gen2 (`locality_gen=2`) | gen4 (`locality_gen=4`). Seeds 3, 4.
**Kriterien** für gen4: K1 Tor-Status PENDING_USER in beiden Seeds; K2 Leck am Tor <= 0,2 in beiden; K3 Vergessen <= 0,02 und KL <= 0,05 in beiden; K4 gen4-Leck <= gen2-Leck (nicht schlechter durch mehr Anker). Kontrolle: live scheitert im Tor an Spezifität (bestätigt Spielraum).
Urteil: BP2D_PASS (K1-K4); BP2D_PARTIAL (K2 und K4 erfüllt, aber Tor scheitert an Vergessen/KL/Frozen-Drift: dann wird die Ursache berichtet); sonst BP2D_FAIL. Standard bleibt unverändert.
