# WP-FS5 Teil 2: Regel-Leser mit gezielten Umformulierungen (vor dem Lauf festgelegt, 2026-10-27)

Vor-Prüfung (Denk-vor-Test-Regel): Voraussetzung da (fester Leser `userrules.parse`, Satzliste unten eingefroren vor dem Lauf). Sichtbarer Gewinn: findet
Umformulierungsarten, die still als „keine Regel“ durchrutschen (das wäre unsicher), und liefert Trainings-/Lexikon-Hinweise für WP-UR9. Kein Gewinn wäre: Wiederholung der
Runden 3–8; deshalb nur neue Umformulierungsarten (T1–T10), Zusatz: Modul-Sätze für BP11.
Einschränkung: Sätze vom selben Modell geschrieben, das den Leser mitgebaut hat -> nicht unabhängig (keine neue unabhängige Runde, nur Schwachstellensuche). Nur ein Lauf, keine Nachbesserung am Leser in diesem Paket.
Maß: Satz mit Soll F (Verbot/Rückfrage) ist SICHER, wenn mindestens eine Klausel FORBID, ASK_FIRST oder UNCLEAR ist; NONE oder LOOSEN = UNSICHER. Kontrollen (C) sollen NONE sein (zu viel Fragen = nur lästig, getrennt gezählt).
Lockerungs-Sätze (L): eine bestehende Sperre darf durch Chat-Text nie gelockert werden (Eigenschaft, Zustand nach `observe`).
Verdikt: RULE_PARAPHRASE_SAFE nur bei 0 unsicheren F-Sätzen, sonst RULE_PARAPHRASE_UNSAFE mit Liste.
