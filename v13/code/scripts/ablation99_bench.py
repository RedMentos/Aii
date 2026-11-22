"""WP-AB: §99 mandatory ablations without a language model (eligibility, typed modulators, proceduralization, Age).
Usage: ablation99_bench.py <out.json> [seeds comma-separated]"""
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from v13.ablation99 import SEEDS,run_all

def main(out,seeds=None):
    r=run_all(tuple(int(s) for s in seeds.split(',')) if seeds else SEEDS)
    Path(out).parent.mkdir(parents=True,exist_ok=True);Path(out).write_text(json.dumps(r,indent=1))
    for part in ('eligibility','modulators','proceduralization','age'):
        for arm,v in r[part]['summary'].items():print(part,arm,{k:x['mean'] for k,x in v.items()})

if __name__=='__main__':main(sys.argv[1],sys.argv[2] if len(sys.argv)>2 else None)
