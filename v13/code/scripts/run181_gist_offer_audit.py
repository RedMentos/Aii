"""Independent paired audit of the frozen B2 Gist utility bench report."""
import argparse
import hashlib
import json
from pathlib import Path

MODEL_SHA='57d1997790d1744fba5b40a7317df71ea5e2acee28c47e78f0cce39c0703f8cf'
ARMS=('fixed960','event960','gist')


def recompute(row,content):
    try:o=json.loads(content)
    except (ValueError,TypeError):return {'parsed':False,'hit':False,'stale':False,'quotes_valid':False,'quote_has_key':False}
    s=str(o.get('summary',''));quotes=[str(q) for q in (o.get('quotes') or [])]
    key=row['key'].lower();low=s.lower()
    hit=key in low
    return {'parsed':True,'hit':hit,'stale':bool(row.get('stale')) and row['stale'].lower() in low and not hit,
            'quotes_valid':all(q in row['text'] for q in quotes),
            'quote_has_key':any(key in q.lower() and q in row['text'] for q in quotes)}


def audit(report,expected_rows):
    if report.get('kind')!='V13_G1B_GIST_UTILITY' or report.get('binding',{}).get('model_sha256')!=MODEL_SHA:
        raise ValueError('cohort/model binding mismatch')
    if 'not Redmi' not in report.get('claim_limit',''):
        raise ValueError('missing Linux-only claim limit')
    n=len(expected_rows)
    if n!=36:raise ValueError('registered cohort must have 36 memos')
    arm_data={}
    for arm in ARMS:
        records=report.get(arm,[])
        if len(records)!=n or set(x['index'] for x in records)!=set(range(n)):
            raise ValueError(arm+' incomplete/duplicate cohort')
        by_id={x['index']:x for x in records}
        for i,row in enumerate(expected_rows):
            actual=by_id[i]
            if actual.get('kind')!=row['kind'] or actual.get('prompt_tokens',0)<=0:
                raise ValueError(arm+' prompt/label mismatch')
            expected=recompute(row,actual.get('content'))
            if any(actual.get(k)!=v for k,v in expected.items()):
                raise ValueError(arm+' scored evidence mismatch at '+str(i))
        arm_data[arm]=by_id
    summary={}
    for arm in ARMS:
        rows=list(arm_data[arm].values())
        summary[arm]={'hit':round(sum(x['hit'] for x in rows)/n,4),
                      'quotes_valid':round(sum(x['quotes_valid'] for x in rows)/n,4),
                      'prompt_tokens_mean':round(sum(x['prompt_tokens'] for x in rows)/n,1)}
        for k,v in summary[arm].items():
            if report.get('summary',{}).get(arm,{}).get(k)!=v:
                raise ValueError(arm+' summary '+k+' mismatch')
    def paired(a,b):
        return {'wins':sum(arm_data[a][i]['hit'] and not arm_data[b][i]['hit'] for i in range(n)),
                'losses':sum(arm_data[b][i]['hit'] and not arm_data[a][i]['hit'] for i in range(n))}
    pairs={'gist_vs_fixed960':paired('gist','fixed960'),'gist_vs_event960':paired('gist','event960'),
           'event960_vs_fixed960':paired('event960','fixed960')}
    if report.get('paired')!=pairs:raise ValueError('paired results mismatch')
    g,f=summary['gist'],summary['fixed960'];p=pairs['gist_vs_fixed960']
    crit={'hit_wins_gt_losses':p['wins']>p['losses'],
          'quote_validity_not_lower':g['quotes_valid']>=f['quotes_valid'],
          'prompt_tokens_within_10pct':g['prompt_tokens_mean']<=1.1*f['prompt_tokens_mean']}
    verdict='GIST_HELPS_CANDIDATE' if all(crit.values()) else 'GIST_NO_GAIN'
    if report.get('decision',{}).get('criteria')!=crit or report['decision'].get('verdict')!=verdict:
        raise ValueError('decision criteria/verdict mismatch')
    return {'status':'INDEPENDENT_GIST_OFFER_AUDIT_PASS','verdict':verdict,'n':n,
            'paired':pairs,'summary':summary,'activation_authorized':False,
            'step2_promoted':False,'b3_promoted':False,'redmi_proven':False}


def main():
    p=argparse.ArgumentParser();p.add_argument('report');p.add_argument('--output',required=True);a=p.parse_args()
    from gist_utility_bench import make
    result=audit(json.loads(Path(a.report).read_text()),make())
    Path(a.output).write_text(json.dumps(result,sort_keys=True,indent=2)+'\n')
    print(json.dumps(result,sort_keys=True))


if __name__=='__main__':main()
