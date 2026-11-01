# WP-Z11d Vorregistrierung: STEP4 Referenz-Lehrer, vierter Versuch (vor dem Lauf committet)

Anlass: Z11b und Z11c `STEP4_EXIT_FAIL` nur durch T2; alle Treffer waren vom Lehrer zitierte Self-Sätze, die die
Zeichen-Prüfung an Rändern (Anführungszeichen, Leerzeichen) falsch zuordnete. Z11, Z11b und Z11c bleiben FAIL.

Gleich wie Z11b/Z11c (Lehrer, Self-Konfiguration, Arme, Auswahl nach allen Antworten, Fingerabdruck-Fix, T1 und T3–T6).
Geändert:
1. **Frischer Seed 31.**
2. **T2 Leck-Prüfung v3 auf Wort-Ebene:** Texte normalisiert wie v2, dann Wort-8er-Folgen. Ein Leck ist eine 8er-Folge
   des Lehrer-Texts, die in der Klartext-History der Sitzung vorkommt und weder im Self-Text derselben Aufgabe noch in
   der Aufgabe selbst vorkommt. Jeder Treffer = FAIL.
Code `scripts/z11_reference_teacher.py --z11d`. Urteil `STEP4_EXIT_PASS` nur wenn T1–T6 gelten; keine Nachbesserung.
Dies ist der letzte Versuch mit diesem Aufbau: bei erneutem FAIL wird T2 nicht weiter umgebaut, sondern das Ergebnis
so stehen gelassen und der Grund berichtet.
Grenzen: ein Seed, generierte englische Aufgaben, Regex-Prüfung, Cloud.
