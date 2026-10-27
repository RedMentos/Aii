"""WP-J B3-H3 L1 attempt 6 (WP-Z4d): replication of the attempt-5 escalate PASS on two FRESH data seeds (cloud, preregistered).

Attempt 5 (bench-results/b3-l1-v5-20261021) passed canon L1 on private/escalate on one data seed (20261105); the attempt-4
action PASS had already failed to replicate on that seed, so a single-seed PASS is not treated as robust. This run repeats
the attempt-5 recipe UNCHANGED (b3_l1_v5_bench.run_task: recv_cond aux bridge + readout refit, gate, baselines, splits,
5 paired seeds, canon rule, both views) on two new data seeds, each with new B1/B2 states.

Only changes vs attempt 5: the data seed (passed on the command line, must be one of the preregistered SEEDS) and the
overlap check (also against attempt 5 and the other attempt-6 seed). The report adds this script's hash and kind.

Usage: b3_l1_v6_bench.py <home> <out_dir> <data_seed> [threads] [seeds]
Claim limits: as attempt 5 (L1 receiver-adapter read only, synthetic templates, oracle EXACT span, Linux CPU, not Redmi)."""
import hashlib
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import b3_l1_v3_bench as V3
import b3_l1_v4_bench as V4
import b3_l1_v5_bench as V5

SEEDS=(20261201,20261202)

def overlap_for(seed):
    other=[s for s in SEEDS if s!=seed][0]
    old={'attempt3':V3.make(),'attempt4':V3.make(V4.SEED_DATA),'attempt5':V3.make(V5.SEED_DATA),'attempt6_other_seed':V3.make(other)}
    old={k:{r['text'] for r in v} for k,v in old.items()}
    return lambda rows:{**{f'same_sender_text_as_{k}':sum(r['text'] in o for r in rows) for k,o in old.items()},'n':len(rows)}

def main(home,out,seed,threads=4,seeds=5):
    if seed not in SEEDS:raise SystemExit(f'data seed {seed} not preregistered {SEEDS}')
    V5.SEED_DATA=seed;V5.overlap=overlap_for(seed)
    V5.main(home,out,threads,seeds)
    p=Path(out)/'report.json';rep=json.loads(p.read_text())
    rep['kind']='B3_L1_V6_REPLICATION_FRESH_SEED';rep['v5_script_sha256']=rep.pop('script_sha256')
    rep['script_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest();rep['preregistered_seeds']=list(SEEDS)
    p.write_text(json.dumps(rep,indent=1,default=float))

if __name__=='__main__':main(sys.argv[1],sys.argv[2],int(sys.argv[3]),int(sys.argv[4]) if len(sys.argv)>4 else 4,int(sys.argv[5]) if len(sys.argv)>5 else 5)
