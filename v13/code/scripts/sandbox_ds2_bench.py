"""Run110 preregistered DS2 toy-world comparison; no native/Redmi claims."""
import base64
import hashlib
import json
import statistics as st
import sys
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from v13 import sandbox as S

SEEDS=range(100,120)
ARMS=('lp','efe','novelty','lp_goal','lp_goal_novelty')
OUT=Path(__file__).resolve().parents[2]/'bench-results'/'sandbox-ds2-run110-20261025'


def summarize(rows):
    delays=[r['new_kind_steps_to_goal'] for r in rows if r['new_kind_steps_to_goal'] is not None]
    return {
        'mean_hunger':round(st.mean(r['mean_hunger'] for r in rows),5),
        'noise_share':round(st.mean(r['noise_share'] for r in rows),5),
        'final_kl_learnable':round(st.mean(r['final_kl_learnable'] for r in rows),5),
        'final_kl':round(st.mean(r['final_kl'] for r in rows),5),
        'grounding':round(st.mean(r['grounding'] for r in rows),5),
        'new_kind_learned':len(delays),
        'new_kind_median_steps':st.median(delays) if delays else None,
    }


def main():
    runs={arm:[S.run(arm,seed) for seed in SEEDS] for arm in ARMS}
    summary={arm:summarize(rows) for arm,rows in runs.items()}
    n=summary['lp_goal_novelty'];lp=summary['lp'];efe=summary['efe'];goal=summary['lp_goal']
    verdict={
        'H1_hunger':n['mean_hunger']<=.10 and n['mean_hunger']<=lp['mean_hunger']-.05,
        'H2_new_word':n['new_kind_learned']>=15 and n['new_kind_median_steps'] is not None and n['new_kind_median_steps']<=700 and n['new_kind_learned']>=efe['new_kind_learned']+6,
        'H3_no_noise_or_learning_collapse':n['noise_share']<=.25 and n['final_kl_learnable']<=.12,
        'H4_word_novelty_ablation':n['new_kind_learned']>=goal['new_kind_learned'],
    }
    report={'revision':S.REVISION,'ds2':'run110','seeds':list(SEEDS),'arms':list(ARMS),
            'summary':summary,'verdict':verdict,'all_pass':all(verdict.values()),'runs':runs}
    OUT.mkdir(parents=True,exist_ok=True)
    raw=json.dumps(report,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
    (OUT/'report.json').write_bytes(raw)
    print('DS2_SUMMARY='+json.dumps({'summary':summary,'verdict':verdict,'all_pass':report['all_pass']},sort_keys=True))
    print('DS2_REPORT_SHA256='+hashlib.sha256(raw).hexdigest())
    compressed=base64.b64encode(zlib.compress(raw,9)).decode()
    for i in range(0,len(compressed),3000):
        print('DS2_REPORT_B64_CHUNK_%04d='% (i//3000)+compressed[i:i+3000])
    print('DS2_REPORT_B64_CHUNKS='+str((len(compressed)+2999)//3000))


if __name__=='__main__':
    main()
