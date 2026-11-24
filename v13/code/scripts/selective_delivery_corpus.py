"""Frozen corpus for the WP-T9 Exact/Trace/Combined/Selective comparison (scripts/selective_delivery_bench.py).

40 invented personal facts (question, stored correction, answer keys), one paraphrase and one near-miss question per fact
(the near-miss names a different person/object, so the stored key must NOT appear). Retention probes and KL anchors are
reused unchanged from scripts/lora_bench.py. Facts are disjoint from lora_bench.FACTS. Do not edit after preregistration:
the corpus sha256 is bound in the preregistration and in every result file."""
FACTS=[
 ('What is the name of my cat?','Your cat is called Pimpernel.',['pimpernel'],'Tell me what my cat is called.','What is the name of my rabbit?'),
 ('Where do I work?','You work at the Lindqvist sawmill in Umea.',['lindqvist'],'Which company do I work for?','Where does my cousin work?'),
 ('What is my favourite colour?','Your favourite colour is vermilion.',['vermilion'],'Which colour do I like best?','What is my least favourite colour?'),
 ('What is the name of my brother?','Your brother is called Thorvald.',['thorvald'],'Who is my brother?','What is the name of my uncle?'),
 ('Which instrument do I play?','You play the hurdy-gurdy.',['hurdy'],'What musical instrument do I play?','Which instrument does my daughter play?'),
 ('What is the name of my boat?','Your boat is called Kestrel Moon.',['kestrel'],'What did I name my boat?','What is the name of my neighbour\'s boat?'),
 ('Which city was I born in?','You were born in Tromso.',['tromso'],'Where is my birthplace?','Which city was my father born in?'),
 ('What is my dog called?','Your dog is called Biscotti.',['biscotti'],'Tell me my dog\'s name.','What is my horse called?'),
 ('What is my favourite dish?','Your favourite dish is shakshuka.',['shakshuka'],'Which meal do I love most?','What is my wife\'s favourite dish?'),
 ('What is the name of my best friend?','Your best friend is called Oyelaran.',['oyelaran'],'Who is my closest friend?','What is the name of my boss?'),
 ('Which language am I learning?','You are learning Icelandic.',['icelandic'],'What language am I studying?','Which language is my son learning?'),
 ('What car do I drive?','You drive a green Lada Niva.',['niva'],'Which car is mine?','What car does my sister drive?'),
 ('What is the name of my garden gnome?','Your garden gnome is called Quibble.',['quibble'],'What did I call my garden gnome?','What is the name of my scarecrow?'),
 ('Which football club do I support?','You support Rot-Weiss Erfurt.',['erfurt'],'What is my football team?','Which club does my grandfather support?'),
 ('What is my street called?','You live on Juniper Lane.',['juniper'],'On which street do I live?','What street is my office on?'),
 ('What is the name of my teacher?','Your teacher is called Mrs Abernathy.',['abernathy'],'Who teaches me?','What is the name of my dentist?'),
 ('What is my favourite book?','Your favourite book is The Salt Orchard.',['salt orchard','orchard'],'Which book do I like most?','What is my mother\'s favourite book?'),
 ('Which mountain did I climb last summer?','You climbed the Grossglockner last summer.',['grossglockner'],'What mountain did I climb last summer?','Which mountain do I want to climb next year?'),
 ('What is my parrot called?','Your parrot is called Captain Ludo.',['ludo'],'Tell me my parrot\'s name.','What is my goldfish called?'),
 ('What is the name of my band?','Your band is called The Velvet Turnips.',['turnips'],'What is my band called?','What is the name of my brother\'s band?'),
 ('Which hobby did I start this year?','You started bookbinding this year.',['bookbinding'],'What new hobby did I take up this year?','Which hobby did my friend start this year?'),
 ('What is my grandmother called?','Your grandmother is called Henrike.',['henrike'],'What is my grandma\'s name?','What is my aunt called?'),
 ('Which tea do I drink every morning?','You drink rooibos every morning.',['rooibos'],'What tea do I have each morning?','Which tea does my colleague drink?'),
 ('What is the name of my bicycle?','Your bicycle is called Rattlesnake.',['rattlesnake'],'What did I name my bike?','What is the name of my scooter?'),
 ('Which country did I visit in May?','You visited Uruguay in May.',['uruguay'],'Where did I travel in May?','Which country will I visit in December?'),
 ('What is my lucky number?','Your lucky number is 73.',['73'],'Which number brings me luck?','What is my sister\'s lucky number?'),
 ('What is the name of my houseplant?','Your houseplant is called Gerald.',['gerald'],'What do I call my houseplant?','What is the name of my cactus?'),
 ('Which board game do I play most?','You play Agricola most often.',['agricola'],'What board game do I play the most?','Which card game do I play most?'),
 ('What is the name of my company?','Your company is called Brightfern Analytics.',['brightfern'],'What is my company called?','What is the name of my competitor?'),
 ('What is my nickname?','Your nickname is Pocket.',['pocket'],'What do people call me as a nickname?','What is my cousin\'s nickname?'),
 ('Which river do I live near?','You live near the river Vltava.',['vltava'],'What river is close to my home?','Which river does my uncle live near?'),
 ('What is the name of my podcast?','Your podcast is called Slow Static.',['static'],'What is my podcast called?','What is the name of my favourite radio show?'),
 ('Which bird visits my balcony?','A jackdaw visits your balcony.',['jackdaw'],'What bird comes to my balcony?','Which bird nests in my garden?'),
 ('What is my favourite flower?','Your favourite flower is the hellebore.',['hellebore'],'Which flower do I like most?','What flower does my mother like most?'),
 ('What is the name of my tortoise?','Your tortoise is called Methuselah.',['methuselah'],'Tell me my tortoise\'s name.','What is the name of my hamster?'),
 ('Which painter do I admire?','You admire Hilma af Klint.',['klint','hilma'],'What painter do I look up to?','Which painter does my friend admire?'),
 ('What is my username online?','Your username is frostbyte42.',['frostbyte'],'What is my online handle?','What is my brother\'s username online?'),
 ('Which dance do I practise?','You practise the tango.',['tango'],'What dance style do I practise?','Which dance does my partner practise?'),
 ('What is the name of my village?','Your village is called Oberwiesel.',['oberwiesel'],'What village do I live in?','What is the name of the next village?'),
 ('Which cheese do I like best?','You like Comte best.',['comte'],'What is my favourite cheese?','Which cheese do I dislike?'),
]
SPLIT_SEED=20261012

def split(seed=SPLIT_SEED):
    """Trace subset T (20 facts written into the sparse trace, the 'consolidated' half) and exact-only rest. All 40 stay in
    the exact store; only the trace is partial."""
    import random
    idx=list(range(len(FACTS)));random.Random(seed).shuffle(idx);return sorted(idx[:20]),sorted(idx[20:])
