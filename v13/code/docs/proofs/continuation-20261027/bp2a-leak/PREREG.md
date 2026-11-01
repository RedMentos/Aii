# WP-BP2a Vorregistrierung: Gewichts-Lernen ohne Lecken (Blueprint §14.5, §21, §29 Nr. 18; Forschung WP-FS2 Subspace Tuning)

**Vorabüberlegung (Nutzerregel 27.10.).** Vorstufen vorhanden: B1-Adapter-Lernweg, gleicher Messaufbau wie WP-BJ1, KL-Anker. Platz für Gewinn ist groß: heutiger Weg
(ce-Arm in BJ1) lernt zu 1,00 aber **lecken 0,81** auf Fragen zu anderen Personen und vergisst 1-2 von 16 Allgemeinfragen ("Hauptstadt Italiens: Trompe").
Ein Gewinn ist ab ~0,25 Punkten Leck sichtbar (16 Fakten, 16 Leck-Fragen je Arm und Seed). Es fehlt noch (vermerkt): Einbindung in den AG6-Alltagsweg, Q4/Handy.
Ortsanker-Fragen im Training stammen aus Personen, die in der Messung NICHT vorkommen (Training: Freund, Mutter, Vater, Chef, Cousin, Onkel, Kollege, Nachbar, Oma, Sohn, Pferd, Hamster;
Messung: Hund, Schwester, Frau, Neffe, Kaninchen, Echse, Igel, Schildkröte, …).

**Arme** (gleiche Fakten pro Seed, 30 Schritte, gleiche Ankerzahl je Schritt 10, jepa_weight 0): ce | locality (+32 Nah-Trainingsfragen, KL zur Basis) | minor (LoRA nur in den r=8 kleinsten
Singulärrichtungen jedes Gewichts, MiLoRA-Form von Subspace Tuning) | both. Einstell-Vorlauf (NICHT für das Urteil): Seed 99, 8 Fakten, nur ob minor die Fakten überhaupt lernt (gelernt >= 0,9);
kleinste Lernrate aus {5e-4, 2e-3, 8e-3} die das schafft, gilt für minor/both.
**Kriterien** (Seeds 1 und 2, Mittel, gegen ce desselben Seeds):
- K1 Leck: bester Arm <= ce - 0,25.
- K2 Lernen: gelernt >= 0,9 und Umformulierung >= 0,85 im besten Arm.
- K3 Behalten: Allgemeinfragen im besten Arm >= ce (nicht schlechter; Toleranz 1 Frage).
- K4 beide Seeds gleiche Richtung (best arm Leck < ce in beiden).
Urteil: BP2A_PASS (K1-K4); BP2A_PARTIAL (K1 oder K3 für einen Arm, aber nicht alles); sonst BP2A_NO_GAIN. Je Arm einzeln berichtet (locality, minor, both), damit klar ist, welcher Teil wirkt.
Nichts wird aktiviert; Ergebnis ist Evidenz für das AG6-Tor (Tor-Schwellen werden NICHT verschoben).
