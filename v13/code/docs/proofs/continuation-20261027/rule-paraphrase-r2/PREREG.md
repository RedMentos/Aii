# WP-UR9 Umformulierungs-Loch schliessen, frische versiegelte Runde r2 (2026-11-01)

Vorabueberlegung (Denk-vor-Test-Regel): Voraussetzung da (fester Leser `userrules.parse` v2, Messprogramm aus `../rule-paraphrase/`, Befund mit 6 Luecken in 4 Familien: Hoeflichkeits-Wunsch,
Kurz-Rueckfrage, Erlaubnisliste/„ausser“, Tabu-Schlagwort). Sichtbarer Gewinn: 6/59 = 10 % unsichere Saetze koennen auf nahe 0 sinken. Ein Test auf den alten 59 Saetzen waere wertlos
(gesehen); darum 48 neue F-Saetze (`sentences.py`, sha256 `89c79413b8380c91803ae525f2daa0b7982dc342d3c02662515362723f5eb4ef`), geschrieben VOR jeder Leser-Aenderung:
P1..P4 = neue Wortlaute der vier Luecken-Familien (32), P5 = andere Formen (16), dazu 10 Kontrollen (keine Regel) und 6 Lockerungsversuche.
Ablauf: (1) Lauf mit unveraendertem Leser v2 = Vorher (Referenz). (2) Leser v3 = nur allgemeine Wortlisten/Muster, kein Satz woertlich. (3) EIN Lauf Nachher auf demselben Satz.
Kein Nachbessern an diesem Satz; Restluecken werden gelistet und brauchen eine neue Runde.
Ehrliche Grenze: Saetze vom selben Modell wie der Leser geschrieben, also keine unabhaengige Runde; die Lueckenfamilien waren bekannt (P1-P4 messen Verallgemeinerung ueber den Wortlaut, P5 echte Neuheit).
Mass: wie vorher (SICHER = mindestens eine Klausel FORBID/ASK_FIRST/UNCLEAR). Zusatz: Kontroll-Ueberfragen darf hoechstens um 1 Satz steigen; Lockerung durch Chat darf nie vorkommen.
Verdikt: PASS_R2 bei 0 unsicheren in P1-P4, hoechstens 2 in P5, Kontrollen +<=1, 0 Lockerungen; sonst FAIL_R2 mit Liste.
