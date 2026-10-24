"""Run110 independent stored-evidence verification; does not rerun/tune DS2 policies."""
import base64
import hashlib
import json
import math
import re
import statistics as st
import zlib
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
EVIDENCE=ROOT/'docs'/'proofs'/'continuation-20261025'/'ds2-run110'
ARM=('lp','efe','novelty','lp_goal','lp_goal_novelty')
BASELINE={
    'lp':{'mean_hunger':.2001,'noise_share':.1225,'final_kl':.0832,'new_kind_learned':19,'new_kind_median_steps':501},
    'efe':{'mean_hunger':.0457,'noise_share':.1943,'final_kl':.1043,'new_kind_learned':7,'new_kind_median_steps':893},
    'novelty':{'mean_hunger':.0715,'noise_share':.1655,'final_kl':.085,'new_kind_learned':20,'new_kind_median_steps':653},
}


def main():
    b64_file=(EVIDENCE/'REPORT_ZLIB_BASE64.txt').read_text()
    header,encoded=b64_file.rsplit('\n# chunks=',1)
    # Header is deliberately human-readable and not part of the compressed payload.
    lines=b64_file.splitlines()
    expected_sha=re.search(r'original UTF-8 JSON SHA-256 ([0-9a-f]{64})',lines[1]).group(1)
    encoded=lines[-1]
    raw=zlib.decompress(base64.b64decode(encoded,validate=True))
    assert hashlib.sha256(raw).hexdigest()==expected_sha
    report=json.loads(raw)
    summary=json.loads((EVIDENCE/'REPORT_SUMMARY.json').read_text())
    assert summary['raw_report_sha256']==expected_sha
    assert summary['compressed_base64_chars']==len(encoded)
    assert report['seeds']==list(range(100,120))
    assert report['arms']==list(ARM)
    assert report['summary']==summary['summary']
    assert report['verdict']==summary['verdict']
    assert report['all_pass']==summary['all_pass']
    assert set(report['runs'])==set(ARM)
    for arm in ARM:
        rows=report['runs'][arm]
        assert len(rows)==20
        for seed,row in zip(range(100,120),rows):
            assert row['policy']==arm and row['seed']==seed and row['steps']==1500
            assert all(math.isfinite(float(row[k])) for k in ('mean_hunger','noise_share','final_kl','final_kl_learnable','grounding'))
            assert 0<=row['mean_hunger']<=1 and 0<=row['noise_share']<=1
            assert all(a[0]<b[0] for a,b in zip(row['curve'],row['curve'][1:]))
        actual=summary['summary'][arm]
        for field in ('mean_hunger','noise_share','final_kl','final_kl_learnable','grounding'):
            assert abs(actual[field]-round(st.mean(row[field] for row in rows),5))<=.00001,(arm,field)
        learned=[r['new_kind_steps_to_goal'] for r in rows if r['new_kind_steps_to_goal'] is not None]
        assert actual['new_kind_learned']==len(learned)
        assert actual['new_kind_median_steps']==(st.median(learned) if learned else None)
    for arm,fields in BASELINE.items():
        for field,expected in fields.items():
            actual=summary['summary'][arm][field]
            if isinstance(expected,float):assert abs(actual-expected)<=.00015,(arm,field,actual,expected)
            else:assert actual==expected,(arm,field,actual,expected)
    n=summary['summary']['lp_goal_novelty'];lp=summary['summary']['lp'];efe=summary['summary']['efe'];goal=summary['summary']['lp_goal']
    verdict={
        'H1_hunger':n['mean_hunger']<=.10 and n['mean_hunger']<=lp['mean_hunger']-.05,
        'H2_new_word':n['new_kind_learned']>=15 and n['new_kind_median_steps'] is not None and n['new_kind_median_steps']<=700 and n['new_kind_learned']>=efe['new_kind_learned']+6,
        'H3_no_noise_or_learning_collapse':n['noise_share']<=.25 and n['final_kl_learnable']<=.12,
        'H4_word_novelty_ablation':n['new_kind_learned']>=goal['new_kind_learned'],
    }
    assert verdict==summary['verdict']
    assert summary['all_pass'] is False and verdict['H2_new_word'] is False
    print('DS2_EVIDENCE_REVIEW_PASS sha256='+expected_sha)
    print('DS2_LOCKED_VERDICT_FAIL_H2 median_delay='+str(n['new_kind_median_steps']))


if __name__=='__main__':
    main()
