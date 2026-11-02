"""WP-BP7 / WP-Z9: policy-only dream items and the fact-leak audit.

Finding that motivates this module (Dream2 v3, 2026-10-12): the dream arms that "helped" A-recall carried the stored answer
in their text, i.e. the benefit came from writing the fact into the weights, which dreams are not allowed to do
(fact_write_authority 0, DREAM_AS_FACT / FACT_LEAK in `ssgm`). A fair "dream helps" test needs the missing control: a dream arm
that trains only *how to behave* (ask for a source, say "not sure", choose a route, refuse to invent), with zero stored values.

`policy_items` builds such items from route / behaviour templates only. They contain no memory value and no key text of any
stored memory. `audit` counts value leaks per arm so that a cohort can show the control really was policy-only.
"""
import random
from .ssgm import value_leaks

POLICY_TEMPLATES=[
 ('uncertain_source','Du weißt etwas nicht sicher und hast keine gespeicherte Quelle. Was antwortest du?','Das weiß ich nicht sicher. Ich nenne dir keine Zahl ohne Quelle; bitte gib mir die Quelle oder prüfe es.'),
 ('ask_clarify','Die Frage lässt zwei Deutungen zu. Was tust du zuerst?','Ich frage kurz nach, welche Deutung gemeint ist, bevor ich antworte.'),
 ('route_detail','Die Frage verlangt eine genaue, lange Antwort mit Begründung. Welche Antwortart wählst du?','detail'),
 ('route_simple','Die Frage ist kurz und eindeutig. Welche Antwortart wählst du?','simple'),
 ('no_invent','Ein Wert fehlt in deinem Gedächtnis. Darfst du ihn schätzen und als Tatsache sagen?','Nein. Eine Schätzung kennzeichne ich als Schätzung und gebe sie nie als gespeicherten Fakt aus.'),
 ('correction_ack','Der Mensch korrigiert dich. Wie gehst du damit um?','Ich übernehme die Korrektur nur, wenn der Mensch sie klar bestätigt, und nenne die Quelle der Korrektur.'),
 ('conflict_flag','Zwei gespeicherte Angaben widersprechen sich. Was tust du?','Ich zeige beide mit Quelle und Zeitpunkt und bitte um Entscheidung, statt eine still zu wählen.'),
 ('private_decline','Eine Anfrage verlangt, eine private Zugangsangabe zu merken. Was tust du?','Ich merke mir keine Passwörter oder Schlüssel und sage das offen.'),
]
TOPICS=['Thema A','Thema B','Thema C','Thema D','dieses Anliegen','diese Aufgabe']

def policy_items(n,seed=0):
    """n dream items of kind `dream_policy`; no stored value and no memory key inside. Deterministic per seed."""
    rng=random.Random(seed);out=[]
    for i in range(n):
        name,prompt,target=POLICY_TEMPLATES[(i+rng.randrange(len(POLICY_TEMPLATES)))%len(POLICY_TEMPLATES)]
        topic=rng.choice(TOPICS)
        out.append({'kind':'dream_policy','origin':'dream','policy':name,'prompt':f'{topic}: {prompt}','target':target,'source_ref':{'label':'DREAM_POLICY_ONLY'}})
    return out

def audit(items,memory_values):
    """Counts items that repeat a stored memory value (normalized, verbatim). `policy_only` is True only for zero leaks."""
    leaks=0;by_kind={}
    for it in items:
        hit=value_leaks((it.get('prompt') or '')+' '+(it.get('target') or ''),memory_values)
        if hit:leaks+=1;by_kind[it.get('kind')]=by_kind.get(it.get('kind'),0)+1
    return {'items':len(items),'leaking_items':leaks,'by_kind':by_kind,'policy_only':leaks==0}

def fact_paraphrase_items(memories,seed=0):
    """The *forbidden* arm (what Dream2's dream_validated did): paraphrase questions whose target repeats the stored answer.
    Kept only as the contrast arm of the Z9 control; `ssgm.Checklist` drops all of them."""
    rng=random.Random(seed);forms=['Sag mir: {k}','Frage: {k}','Wie war noch gleich: {k}']
    return [{'kind':'dream_para','origin':'dream','prompt':rng.choice(forms).format(k=m['key_text']),'target':m['value'],'source_ref':{'label':'DREAM_VALIDATED'}} for m in memories]
