# WP-FS7 Verfahrens-Schema (2026-11-01)
**Vorabüberlegung:** Voraussetzungen da (Werkzeug `calc`, Skill-Bibliothek). Gewinn: gegen rohes Wiederholen der Episode ist ein Sieg des Schemas fast zwingend (andere Zahlen). Aussagekräftig sind daher die zwei Vergleiche: einfache Zahlen-Ersetzung als Kontrolle und die Frage, ob die Auswahl bei neuer Formulierung trägt. Ehrlich: ein erster Probelauf (Schema 0,0, wegen der Auswahl) kam vor dieser Aufschrift; Kontrolle und zweiter Selektor sind danach ergänzt worden, nicht vorregistriert. Software, ohne Modell.

Aufbau: 2 Lern-Episoden (Summe, 2 oder 3 Posten, eine Formulierung), 200 neue Aufgaben (3 bis 5 Posten, zwei neue Formulierungen).
| Arm | richtig |
|---|---|
| Roh-Episode wiederholen | 0,00 |
| Roh + Zahlen der Reihe nach ersetzen (Kontrolle) | 0,35 |
| Schema, Auswahl über Stichwörter | 0,00 |
| Schema, Auswahl über Struktur (passt es auf die Zahlen) | **1,00** |

**Lesart.** Der Schritt „Zahlen als Platzhalter, Anzahl offen“ trägt, wenn das Verfahren gewählt ist: Zahlen-Ersetzung scheitert bei anderer Anzahl (0,35). Die Stichwort-Auswahl aus 2 Beispielen bricht bei neuer Wortwahl völlig ein; Schema-Übertragung braucht also einen Wähler, der nicht am Wortlaut hängt (z. B. der gelernte Werkzeug-Wähler R4/BP-Router). Grenzen: eine einzige Aufgabenart, ein Werkzeug, 1,00 gilt nur für diese Art, keine Modellmessung. Code: `v13/agi/schema.py`, `tests/test_agi_schema.py` (3 grün), `scripts/bp_fs7_schema_bench.py`, `report.json`. Noch nicht in `SkillLibrary.propose` oder Konsolidierung eingehängt.

## FS7b Auswahl ohne Wortlaut (2026-11-01)
**Vorabüberlegung:** Daten/Voraussetzung da (2 Familien: Summe 2 bis 5 Posten, Differenz zweier Zahlen; je 2 Lernbeispiele, 300 Aufgaben mit drei neuen Formulierungen je Familie, online mit Rückmeldung „richtig/falsch“). Bei zwei Zahlen sind Summe und Differenz ohne Wortbedeutung nicht trennbar, also erwartet: nur Rückmeldung kann das lösen, mit Rest-Fehlern. Nicht vorregistriert (Software, Kleinexperiment).
| Wähler | alle 300 | letzte 100 |
|---|---|---|
| Stichwörter | 0,00 | 0,00 |
| erstes passendes (nur Struktur) | 0,54 | 0,48 |
| gelernt aus Rückmeldung (`schema.Selector`) | **0,87** | 0,86 |
Letzte 100, gelernt: Differenz 1,00, Summe 0,71 (die 2-Zahlen-Summen bleiben mit Differenzen verwechselbar). **Lesart:** Struktur + Rückmeldung ersetzt den Wortlaut weitgehend; was bleibt, ist echte Mehrdeutigkeit, die eine Bedeutung (Modell) oder eine Rückfrage braucht. Zwei Familien, Software, ein Werkzeug.
