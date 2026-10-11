#!/usr/bin/env python3
"""WP-S6/WP-I cloud proof: train a small LoRA on C3 (LFM2.5-230M master) and measure it on the deployed llama.cpp path.

Usage (after cloud_bench.sh --smoke installed runner + models into $V13_HOME):
  python3 scripts/lora_bench.py --home /tmp/v13-bench/home --master /path/LFM2.5-230M --out bench-results/lora-<stamp>
  [--ablate]  also trains anchor=0 and jepa>0 variants on the same facts
Facts are invented (the base cannot know them); probes are general English questions never trained on.
Report: <out>/lora-bench.json. Nothing is activated; this only produces gate evidence.
"""
import argparse,json,sys,time,platform
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from v13.lora_trainer import LoraTrainer,LlamaCppEvaluator
from v13.common import file_hash

FACTS=[
 ('What is the name of my cat?','Your cat is called Mitzi.',['mitzi']),
 ('Where do I work?','You work at the Kranich bakery in Leipzig.',['kranich']),
 ('What is my favourite colour?','Your favourite colour is teal.',['teal']),
 ('What is the name of my brother?','Your brother is called Jonte.',['jonte']),
 ('Which instrument do I play?','You play the bandoneon.',['bandoneon']),
 ('What is my phone model?','Your phone is a Redmi Note 9 Pro.',['redmi']),
 ('What is the name of my project?','Your project is called V13 Inquisition.',['inquisition']),
 ('When is my birthday?','Your birthday is on the 14th of March.',['14','march']),
]
PARAPHRASES=[('Tell me my cat\'s name.',['mitzi']),('Who is my brother?',['jonte']),('What colour do I like most?',['teal']),
             ('What musical instrument do I play?',['bandoneon']),('What is my project called?',['inquisition']),('Which company employs me?',['kranich'])]
NEAR_MISS=[('What is the name of my dog?',['mitzi']),('What is the name of my sister?',['jonte']),('What is my least favourite colour?',['teal']),
           ('Which instrument does my brother play?',['bandoneon']),('Where does my brother work?',['kranich'])]
# KL-to-base anchors: general prompts + locality prompts (other personal questions). Disjoint from PROBES and NEAR_MISS.
ANCHORS=['Write one sentence about the weather.','What is a good breakfast?','Explain what a computer is in one sentence.',
         'Say hello politely.','Give me a tip for learning a language.','What does a doctor do?','What is the capital of Italy?',
         'How many days are in a week?','Name an animal that lives in the sea.','What is 3 times 4?','What colour is grass?',
         'Translate "good morning" into Spanish.','List two vegetables.','What day comes before Friday?','Who wrote Romeo and Juliet?',
         'What is water made of?','How do I boil an egg?','What is the name of my mother?','What car do I drive?',
         'What is my favourite food?','Where do I live?','What is the name of my teacher?','Which sport do I like?',
         'What is my best friend called?','How old am I?','What is the name of my neighbour?','What language do I speak?',
         'Do I have any pets?','What is my job?','What did I eat yesterday?','What is my favourite song?','Where was I born?']
PROBES=[
 {'prompt':'What is the capital of France?','expect':['paris']},
 {'prompt':'What is the capital of Japan?','expect':['tokyo']},
 {'prompt':'How many legs does a spider have?','expect':['eight','8']},
 {'prompt':'What colour is the sky on a clear day?','expect':['blue']},
 {'prompt':'Which planet do we live on?','expect':['earth']},
 {'prompt':'What is the opposite of hot?','expect':['cold']},
 {'prompt':'What do bees make?','expect':['honey']},
 {'prompt':'What is the largest ocean on Earth?','expect':['pacific']},
 {'prompt':'What is 7 plus 5?','expect':['12','twelve'],'unseen':True},
 {'prompt':'List three fruits.','expect':['apple','banana','orange','grape','mango','strawberr','pear'],'unseen':True},
 {'prompt':'Translate "thank you" into German.','expect':['danke'],'unseen':True},
 {'prompt':'What day comes after Monday?','expect':['tuesday'],'unseen':True},
]

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--home',required=True);ap.add_argument('--master',required=True);ap.add_argument('--master-sha256')
    ap.add_argument('--model-gguf');ap.add_argument('--out',required=True);ap.add_argument('--ablate',action='store_true')
    ap.add_argument('--threads',type=int,default=4);ap.add_argument('--rank',type=int,default=8);ap.add_argument('--max-steps',type=int,default=120)
    a=ap.parse_args();home=Path(a.home);out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    gguf=Path(a.model_gguf) if a.model_gguf else next((home/'models').rglob('LFM2.5-230M*.gguf'))
    server=home/'bin/llama-server'
    items=[{'memory_id':'bench_%d'%k,'prompt':q,'target':t,'answer_keys':keys} for k,(q,t,keys) in enumerate(FACTS)]
    variants=[('default',{})]
    if a.ablate:variants+=[('no_anchor',{'anchor_weight':0.}),('jepa',{'jepa_weight':.5})]
    report={'schema':'v13-lora-bench-v1','started':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'platform':platform.platform(),
            'master':str(a.master),'master_sha256':file_hash(Path(a.master)/'model.safetensors'),'inference_model':str(gguf),
            'inference_sha256':file_hash(gguf),'runner':str(server),'facts':len(items),'probes':len(PROBES),'variants':{}}
    for name,over in variants:
        cfg={'threads':a.threads,'rank':a.rank,'max_steps':a.max_steps}|over
        ev=lambda path,name=name:LlamaCppEvaluator(server,gguf,path,threads=a.threads,log=str(out/(name+'-server.log')),paraphrases=PARAPHRASES,near_miss=NEAR_MISS)
        tr=LoraTrainer(a.master,out/'work'/name,master_sha256=a.master_sha256,anchors=ANCHORS,probes=PROBES,cfg=cfg,evaluator=ev)
        t=time.monotonic();r=tr.fit(items,'bench')
        r['wall_seconds']=round(time.monotonic()-t,1);report['variants'][name]=r
        m=r['metrics'];d=m.get('deployed',{})
        print(json.dumps({'variant':name,'steps':m['steps'],'final_ce':m['final_ce'],'train_s':m['seconds'],'master_recall':m['master_learned_recall'],
                          'master_kl':m['master_kl_to_base'],'deployed_recall':d.get('learned_recall'),'base_recall':d.get('base_recall'),
                          'paraphrase':d.get('paraphrase_recall'),'near_miss_leak':d.get('near_miss_leak'),'kl':d.get('kl_to_base'),
                          'retention':[d.get('base_eval',{}).get('overall'),d.get('candidate_eval',{}).get('overall')],
                          'jepa_cos':[m['body_jepa_cos_before'],m['body_jepa_cos_after']]}),flush=True)
        (out/'lora-bench.json').write_text(json.dumps(report,indent=1,ensure_ascii=False))
    print(str(out/'lora-bench.json'))

if __name__=='__main__':main()
