"""Independent Run111 closed composition evidence review; no rerun or policy tuning."""
import base64
import hashlib
import json
import math
import re
import statistics as st
import zlib
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
E=ROOT/'docs'/'proofs'/'continuation-20261025'/'composition-run111'


def main():
    lines=(E/'REPORT_ZLIB_BASE64.txt').read_text().splitlines()
    sha=re.search(r'SHA-256 ([0-9a-f]{64})',lines[1]).group(1)
    encoded=lines[-1]
    raw=zlib.decompress(base64.b64decode(encoded,validate=True))
    assert hashlib.sha256(raw).hexdigest()==sha
    report=json.loads(raw)
    summary=json.loads((E/'REPORT_SUMMARY.json').read_text())
    assert summary['raw_report_sha256']==sha
    assert summary['compressed_base64_chars']==len(encoded)
    assert report['seeds']==list(range(200,220))
    assert report['steps']==600
    assert report['holdout']==[['glas','stein'],['kiste','glas'],['apfel','kiste']]
    assert len(report['runs'])==20
    arms=('pair','object','factor')
    for seed,row in zip(range(200,220),report['runs']):
        assert row['seed']==seed and row['steps']==600
        assert sum(row['training_pairs'].values())==600
        assert all('|'.join(p) not in row['training_pairs'] for p in report['holdout'])
        assert set(row['covered_words']['objects'])=={'glas','kiste','apfel','stein'}
        assert set(row['covered_words']['supports'])=={'stein','kiste','glas'}
        assert set(row['heldout_kl'])==set(arms)
        assert all(math.isfinite(row['heldout_kl'][a]) and row['heldout_kl'][a]>=0 for a in arms)
    means={arm:round(st.mean(r['heldout_kl'][arm] for r in report['runs']),6) for arm in arms}
    wins_pair=sum(r['heldout_kl']['factor']<r['heldout_kl']['pair'] for r in report['runs'])
    wins_object=sum(r['heldout_kl']['factor']<r['heldout_kl']['object'] for r in report['runs'])
    verdict={'H1_vs_pair':wins_pair>=16,'H2_vs_object':wins_object>=14,
             'H3_mean_kl':means['factor']<=.12,'H4_holdout_integrity':True}
    assert summary['mean_heldout_kl']==means
    assert summary['factor_wins_pair']==wins_pair
    assert summary['factor_wins_object']==wins_object
    assert summary['verdict']==verdict
    assert summary['all_pass'] is True and all(verdict.values())
    assert report['summary']=={k:v for k,v in summary.items() if k not in ('raw_report_sha256','compressed_base64_chars')}
    print('COMP_EVIDENCE_REVIEW_PASS sha256='+sha)
    print('COMP_LOCKED_TOY_VERDICT_PASS factor_kl='+str(means['factor']))


if __name__=='__main__':
    main()
