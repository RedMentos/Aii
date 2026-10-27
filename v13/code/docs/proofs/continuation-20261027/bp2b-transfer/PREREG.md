# WP-BP2b Vorregistrierung: erzeugte Ortsanker + Übertragung auf andere Formulierungen (Blueprint §14.5, §21)

**Vorabüberlegung (Nutzerregel 27.10.).** Vorstufe BP2a ist da (Ortsanker + Subspace Tuning: Leck 0,75 -> 0,16, kein Vergessen), aber mit von Hand geschriebenen Ankern in derselben Frageform wie die Messfragen.
Im Alltag lehrt der Mensch beliebige Fakten, also müssen die Anker aus der Frage selbst entstehen (neu: `v13/locality_gen.py`, ohne Modell, 6 Tests, deckt alle 24 Testfragen ab). Ob der Gewinn auch bei
anderer Formulierung und anderen Personen ankommt, ist offen und in BP2a nicht gemessen: Platz ist da (ce-Arm leckt 0,75), Ausgang offen. Ein Gewinn ist ab 0,25 Punkten Leck sichtbar (16 Fakten je Seed). Fehlt noch: AG6-Anschluss, Q4/Handy.

**Arme** (gleiche Fakten pro Seed wie BP2a, 30 Schritte, lr 5e-4, 10 Anker/Schritt, jepa_weight 0): ce | hand_both (BP2a-Handanker + minor) | gen_both (erzeugte Anker + minor). Seeds 1, 2.
**Messung:** Leck A (BP2a-Messfragen, andere Person), **Leck B (neue Umformulierung, Personen: Freundin, Frau, Neffe, Stiefbruder, Enkelin, Schwester; keine davon im Training)**, gelernt, Umformulierung, Allgemeinfragen.
**Kriterien** (Mittel beider Seeds, gen_both gegen ce): K1 Leck A <= ce - 0,25; K2 Leck B <= ce - 0,25; K3 gelernt >= 0,9, Umformulierung >= 0,85, Allgemeinfragen >= ce; K4 Leck A(gen) <= Leck A(hand) + 0,15.
Urteil: BP2B_PASS (K1-K4); BP2B_FORM_ONLY (K1, K3, K4 aber nicht K2: wirkt nur in der Form der Anker); BP2B_FAIL sonst.
Nichts wird aktiviert.
