"""Run111 preregistered heldout compositional toy-world bench, no native proof."""
import base64
import hashlib
import json
import statistics as st
import sys
import zlib
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from v13 import sandbox_composition as C

SEEDS=range(200,220)
OUT=Path(__file__).resolve().parents[2]/'bench-results'/'composition-run111-20261025'


def main():
    runs=[C.run(seed,steps=600) for seed in SEEDS]
    means={arm:round(st.mean(r['heldout_kl'][arm] for r in runs),6) for arm in ('pair','object','factor')}
    wins_pair=sum(r['heldout_kl']['factor']<r['heldout_kl']['pair'] for r in runs)
    wins_obj=sum(r['heldout_kl']['factor']<r['heldout_kl']['object'] for r in runs)
    clean=all(not any('|'.join(pair) in r['training_pairs'] for pair in C.HOLDOUT)
              and set(r['covered_words']['objects'])==set(C.OBJECTS)
              and set(r['covered_words']['supports'])==set(C.SUPPORTS) for r in runs)
    verdict={'H1_vs_pair':wins_pair>=16,'H2_vs_object':wins_obj>=14,'H3_mean_kl':means['factor']<=.12,'H4_holdout_integrity':clean}
    summary={'mean_heldout_kl':means,'factor_wins_pair':wins_pair,'factor_wins_object':wins_obj,
             'all_pass':all(verdict.values()),'verdict':verdict}
    report={'revision':C.REVISION,'seeds':list(SEEDS),'steps':600,'holdout':[list(x) for x in C.HOLDOUT],
            'summary':summary,'runs':runs}
    raw=json.dumps(report,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'report.json').write_bytes(raw)
    print('COMP_SUMMARY='+json.dumps(summary,sort_keys=True))
    print('COMP_REPORT_SHA256='+hashlib.sha256(raw).hexdigest())
    b64=base64.b64encode(zlib.compress(raw,9)).decode()
    for i in range(0,len(b64),3000):
        print('COMP_REPORT_B64_CHUNK_%04d='% (i//3000)+b64[i:i+3000])
    print('COMP_REPORT_B64_CHUNKS='+str((len(b64)+2999)//3000))


if __name__=='__main__':
    main()
