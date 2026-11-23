# WP-T5 Körper-Sicht und Zugriff (B1, B4, B5, §3.2A) — Übergabe

Code `v13/bodyview.py`, Haken in `cognition.offer` und `cognition.body_context`, Befehl `:bodyview [status|state on|off|b4 off|shadow|on]`. Tests `tests/test_bodyview.py` (4).

## B1-Detailsicht über 240 Zeichen
- Gewährte A4-High-Res-Spans (F1 `AttentionResponse` mit Lieferung `high_res_source_span`) werden zu exakten Fenstern für B1: Span ± 240 Zeichen, überlappende Fenster zusammengeführt, höchstens 3 Fenster und 1200 Zeichen.
- Sie stehen als `detail_windows` im B1-Query. Die SourceRefs gehen in die Provenance des QueryPackets (`bodyview.detail_windows`).
- Die Fenster sind Teilstrings der Event-Quelle. Zitate daraus bestehen also die normale Quote-Prüfung.
- Ohne gewährte Spans bleibt alles wie vorher.

## B5: World-/Self-/Skill-Zustand als Quelle
- Pro Offer wird ein kompakter Zustand als Quelle gespeichert (`BODY_STATE`, höchstens etwa 700 Zeichen):
  - World: Modus, beobachtete Aktionen, die letzten 3.
  - Self: Lernmodus, offene Aktionen, Werkzeugrecht, Stufe.
  - Skill: passende Skills.
- B1/B2 bekommen ihn als `body_state` mit `authority: STATE_NOT_FACT`. Die SourceRef steht in der Provenance (`bodyview.body_state_ref`).
- Standard an. Ausschalten mit `:bodyview state off`.

## B4: verteilter Zustand über Sessions
- B2 darf höchstens eine frühere Sicht aus einer anderen Session mitnehmen. Sie muss in einer Koalition gewesen sein (FocalItem), aus derselben Generation und derselben Modell-Revision stammen und dasselbe Thema haben: eine gemeinsame benannte Entität oder Relevanz ≥ 0,5. Terminal-Logs zählen nicht.
- Die Sicht ist als `cross_session` markiert und bleibt `PRIOR_HYPOTHESIS_NOT_FACT`. Das Budget ist `b2_context_chars`.
- Standard SHADOW: Kandidaten werden nur gezählt (`b4_cross_session`). Wirksam erst mit `:bodyview b4 on`.

## Offen
- Ob die Detailfenster und der Zustand die Antworten echter Modelle verbessern, ist ungemessen. Messen lässt es sich im Cloud-Bench (WP-T3) mit `:bodyview state on/off`.
- B4 über Generationen oder Modelle hinweg bleibt bewusst gesperrt: Alte Hypothesen eines anderen Modells sind keine passende Body-Erinnerung.
