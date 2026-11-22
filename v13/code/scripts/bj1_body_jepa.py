#!/usr/bin/env python3
"""WP-BJ1: does the §13 B-JEPA term help a real body (B1 LFM2.5-1.2B) learn new facts through its LoRA adapter?

Arms (same loop, same steps, same anchors; only the JEPA term differs):
  ce        jepa_weight 0 (today's learning path)
  ema       + B-JEPA, EMA adapter target (canon §13.1/§13.4)
  base      + B-JEPA, frozen base target (LLM-JEPA style)
  shuffled  + B-JEPA, EMA target of a different fact (negative control)
Measured on the fp32 master with greedy decoding: learned recall, paraphrase recall (2 unseen wordings per fact),
near-miss leak (same question form, other subject), retention on general probes (base-correct ones only).
Usage: python3 scripts/bj1_body_jepa.py --master DIR --out DIR --seed 1 [--arms ce,ema,base,shuffled] [--facts 16] [--smoke]
"""
import argparse,json,sys,time,platform
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
from v13.body_jepa import BodyJepaTrainer,OBJECTIVE
from v13.lora_trainer import answer_hit
from v13.common import file_hash

# (question, answer, keys, paraphrases, near-miss question). Near-miss subjects avoid lora_trainer.SWAP_NOUNS
# (those are trained as locality anchors), so leak is measured on subjects the trainer never protected explicitly.
POOL=[
 ('What is the name of my cat?','Your cat is called Mitzi.',['mitzi'],["Tell me my cat's name.",'How is my cat called?'],'What is the name of my dog?'),
 ('Where do I work?','You work at the Kranich bakery in Leipzig.',['kranich'],['Which company employs me?','What is the name of my workplace?'],'Where does my wife work?'),
 ('What is my favourite colour?','Your favourite colour is teal.',['teal'],['What colour do I like most?','Which colour is my favourite?'],'What is my least favourite colour?'),
 ('What is the name of my brother?','Your brother is called Jonte.',['jonte'],['Who is my brother?',"Tell me my brother's name."],'What is the name of my sister?'),
 ('Which instrument do I play?','You play the bandoneon.',['bandoneon'],['What musical instrument do I play?','What instrument am I learning to play?'],'Which instrument does my sister play?'),
 ('What is the name of my project?','Your project is called V13 Inquisition.',['inquisition'],['What is my project called?','How is my project named?'],'What is the name of my wife\'s project?'),
 ('When is my birthday?','Your birthday is on the 14th of March.',['14th of march','march 14'],['On which day is my birthday?','What date was I born on?'],'When is my sister\'s birthday?'),
 ('What is the name of my boat?','Your boat is called Seeschwalbe.',['seeschwalbe'],['How is my boat called?',"Tell me my boat's name."],'What is the name of my rabbit?'),
 ('Which city did I move to last year?','You moved to Tromsø last year.',['tromsø','tromso'],['Where did I move last year?','To which city did I relocate last year?'],'Which city did my sister move to last year?'),
 ('What is my favourite dish?','Your favourite dish is Labskaus.',['labskaus'],['Which food do I like most?','What do I like to eat most?'],'What is my wife\'s favourite dish?'),
 ('What is the name of my parrot?','Your parrot is called Kasimir.',['kasimir'],["Tell me my parrot's name.",'How is my parrot called?'],'What is the name of my turtle?'),
 ('Which football club do I support?','You support Rot-Weiss Erfurt.',['erfurt'],['Which football team am I a fan of?','What club do I cheer for?'],'Which football club does my wife support?'),
 ('What is my favourite book?','Your favourite book is The Glass Orchard.',['glass orchard'],['Which book do I like most?','What book is my favourite?'],'What is my sister\'s favourite book?'),
 ('What is the name of my grandfather?','Your grandfather is called Ewald.',['ewald'],['Who is my grandfather?',"Tell me my grandfather's name."],'What is the name of my nephew?'),
 ('Which language am I learning?','You are learning Icelandic.',['icelandic'],['What language do I study?','Which foreign language am I learning right now?'],'Which language is my wife learning?'),
 ('What is my favourite board game?','Your favourite board game is Hive.',['hive'],['Which board game do I like most?','What board game is my favourite?'],'What is my nephew\'s favourite board game?'),
 ('What is the name of my street?','You live on Lindenhofweg.',['lindenhof'],['Which street do I live on?','What is my street called?'],'Which street does my sister live on?'),
 ('What is the name of my goldfish?','Your goldfish is called Blubb.',['blubb'],["Tell me my goldfish's name.",'How is my goldfish called?'],'What is the name of my lizard?'),
 ('What is my blood type?','Your blood type is AB negative.',['ab negative','ab-'],['Which blood group do I have?','What blood type do I have?'],'What is my wife\'s blood type?'),
 ('Which mountain did I climb last summer?','You climbed the Zugspitze last summer.',['zugspitze'],['What mountain did I climb last summer?','Which peak did I hike up last summer?'],'Which mountain did my nephew climb last summer?'),
 ('What is the name of my best teacher at school?','Your best teacher was Frau Okonkwo.',['okonkwo'],['Who was my best teacher at school?','Which teacher did I like most at school?'],'What is the name of my nephew\'s teacher?'),
 ('What is my favourite flower?','Your favourite flower is the snowdrop.',['snowdrop'],['Which flower do I like most?','What flower is my favourite?'],'What is my sister\'s favourite flower?'),
 ('What is the name of my tortoise?','Your tortoise is called Gustav.',['gustav'],["Tell me my tortoise's name.",'How is my tortoise called?'],'What is the name of my hedgehog?'),
 ('Which band did I see live last month?','You saw the band Kettcar live last month.',['kettcar'],['What band did I see in concert last month?','Which group did I watch live last month?'],'Which band did my wife see live last month?'),
]
ANCHORS=['Write one sentence about the weather.','What is a good breakfast?','Explain what a computer is in one sentence.',
 'Say hello politely.','Give me a tip for learning a language.','What does a doctor do?','How many days are in a week?',
 'Name an animal that lives in the sea.','What is 3 times 4?','What colour is grass?','List two vegetables.','Who wrote Romeo and Juliet?',
 'What is water made of?','How do I boil an egg?','What is my favourite song?','Where was I born?','How old am I?','What is my job?']
PROBES=[
 {'prompt':'What is the capital of France?','expect':['paris']},{'prompt':'What is the capital of Japan?','expect':['tokyo']},
 {'prompt':'How many legs does a spider have?','expect':['eight','8']},{'prompt':'What colour is the sky on a clear day?','expect':['blue']},
 {'prompt':'Which planet do we live on?','expect':['earth']},{'prompt':'What is the opposite of hot?','expect':['cold']},
 {'prompt':'What do bees make?','expect':['honey']},{'prompt':'What is the largest ocean on Earth?','expect':['pacific']},
 {'prompt':'What is 7 plus 5?','expect':['12','twelve']},{'prompt':'Translate "thank you" into German.','expect':['danke']},
 {'prompt':'What day comes after Monday?','expect':['tuesday']},{'prompt':'What is the capital of Italy?','expect':['rome']},
 {'prompt':'How many hours are in a day?','expect':['24','twenty-four']},{'prompt':'What gas do plants take in?','expect':['carbon dioxide','co2']},
 {'prompt':'Who painted the Mona Lisa?','expect':['leonardo','da vinci']},{'prompt':'What is frozen water called?','expect':['ice']},
]

def gen(tr,torch,model,tok,q,n=40,adapter=True):
    pid,_=tr._encode(tok,q)
    if adapter:return tok.decode(tr._greedy(torch,model,pid,n),skip_special_tokens=True)
    with model.disable_adapter():return tok.decode(tr._greedy(torch,model,pid,n),skip_special_tokens=True)

def evaluate(tr,facts,adapter=True):
    torch,model,tok=tr.torch,tr.model,tr.tok;rows={'learned':[],'para':[],'leak':[],'probe':[]}
    for q,a,keys,paras,nm in facts:
        t=gen(tr,torch,model,tok,q,adapter=adapter);rows['learned'].append({'q':q,'ok':answer_hit(t,keys),'text':t[:160]})
        for p in paras:
            t=gen(tr,torch,model,tok,p,adapter=adapter);rows['para'].append({'q':p,'ok':answer_hit(t,keys),'text':t[:160]})
        t=gen(tr,torch,model,tok,nm,adapter=adapter);rows['leak'].append({'q':nm,'ok':answer_hit(t,keys),'text':t[:160]})
    for p in PROBES:
        t=gen(tr,torch,model,tok,p['prompt'],adapter=adapter);rows['probe'].append({'q':p['prompt'],'ok':answer_hit(t,p['expect']),'text':t[:160]})
    rate=lambda k:sum(r['ok'] for r in rows[k])/len(rows[k])
    return {'learned_recall':rate('learned'),'paraphrase_recall':rate('para'),'near_miss_leak':rate('leak'),'probe_correct':rate('probe'),'rows':rows}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--master',required=True);ap.add_argument('--out',required=True);ap.add_argument('--seed',type=int,required=True)
    ap.add_argument('--arms',default='ce,ema,base,shuffled');ap.add_argument('--facts',type=int,default=16)
    ap.add_argument('--threads',type=int,default=4);ap.add_argument('--steps',type=int,default=30);ap.add_argument('--lr',type=float,default=5e-4)
    ap.add_argument('--jepa-weight',type=float,default=.5);ap.add_argument('--smoke',action='store_true')
    a=ap.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    rng=np.random.default_rng(a.seed);idx=sorted(rng.choice(len(POOL),size=min(a.facts,len(POOL)),replace=False).tolist())
    facts=[POOL[i] for i in idx];items=[{'memory_id':'bj1_%d'%i,'prompt':q,'target':t,'answer_keys':k} for i,(q,t,k,_,_) in zip(idx,facts)]
    rep={'schema':'v13-bj1-body-jepa-v1','objective':OBJECTIVE.objective_id,'seed':a.seed,'fact_index':idx,'platform':platform.platform(),
         'master':a.master,'master_sha256':file_hash(Path(a.master)/'model.safetensors'),'started':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'arms':{}}
    path=out/('bj1-seed%d.json'%a.seed)
    for arm in a.arms.split(','):
        cfg={'threads':a.threads,'max_steps':a.steps,'min_steps':a.steps,'lr':a.lr,'seed':a.seed,'anchors_per_step':6,
             'jepa_weight':0. if arm=='ce' else a.jepa_weight,'jepa_target':'ema' if arm=='ce' else arm}
        if a.smoke:cfg.update(max_steps=2,min_steps=2)
        tr=BodyJepaTrainer(a.master,out/'work'/('s%d-%s'%(a.seed,arm)),anchors=ANCHORS,cfg=cfg,arch='lfm2')
        t=time.monotonic();r=tr.fit(items,'bj1')
        if 'base' not in rep:rep['base']=evaluate(tr,facts,adapter=False)
        ev=evaluate(tr,facts);ev['wall_seconds']=round(time.monotonic()-t,1)
        m=r['metrics'];rep['arms'][arm]={'metrics':m,'eval':ev}
        print(json.dumps({'arm':arm,'steps':m['steps'],'ce':m['final_ce'],'train_s':m['seconds'],**{k:ev[k] for k in ('learned_recall','paraphrase_recall','near_miss_leak','probe_correct')},
                          'rank':m['effective_rank'],'ema_delta':m['ema_delta']}),flush=True)
        path.write_text(json.dumps(rep,indent=1,ensure_ascii=False))
        del tr
    print(str(path))

if __name__=='__main__':main()
