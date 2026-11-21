"""Hash-bound candidate preserving native-smoke and structured-offer evidence.

Returns replacement bytes for a disposable/reviewed candidate tree. The frozen
verification source is read and verified, never rewritten by this builder.
"""
import hashlib
from pathlib import Path


PINS = {
    "v13/verification.py": "3f22d0e09f79b23f4f71f0743cfeab87b0c03e90042297ac8a1cd0f776ebc908",
}

OLD_ROLES = """        for role in ['C3_LANGUAGE','B1_DETAIL','B2_GIST']:
            start=time.monotonic()
            try:
                runner=r.pool.get(role);deadline=time.monotonic()+r.cfg['deadline_seconds'];answer=''.join(runner.generate([{'role':'system','content':prompt(r.cfg,'smoke_system')},{'role':'user','content':prompt(r.cfg,'smoke_user')}],r.cancel_event,deadline,48))
                result['roles'][role]={'ok':bool(answer.strip()),'actual_output':answer,'metrics':runner.last_metrics}
                if role!='C3_LANGUAGE':
                    p=r.cognition.offer(role,e,0,time.monotonic()+r.cfg['observer_seconds']);result['roles'][role]['structured_offer']={'verified_quote_count':len(p['evidence_refs']),'rejected_quote_count':p['rejected_quotes'],'actual':p['offer']}
                result['roles'][role]['unload']=r.pool.unload()
            except Exception as exc:result['roles'][role]={'ok':False,'error':str(exc),'duration_s':time.monotonic()-start};r.pool.unload()
"""

NEW_ROLES = """        for role in ['C3_LANGUAGE','B1_DETAIL','B2_GIST']:
            start=time.monotonic();phase_started=start;phase='NATIVE_SMOKE';runner=None
            report={'ok':False,'phase':phase,'phases':{phase:{'ok':False,'budget_seconds':r.cfg['deadline_seconds'],'requested_tokens':48}}}
            result['roles'][role]=report
            try:
                runner=r.pool.get(role);deadline=time.monotonic()+r.cfg['deadline_seconds'];answer=''.join(runner.generate([{'role':'system','content':prompt(r.cfg,'smoke_system')},{'role':'user','content':prompt(r.cfg,'smoke_user')}],r.cancel_event,deadline,48))
                smoke=report['phases'][phase]
                smoke.update(ok=bool(answer.strip()),duration_s=time.monotonic()-phase_started,metrics=_probe_metrics_snapshot(runner))
                report.update(ok=smoke['ok'],actual_output=answer,metrics=_probe_metrics_snapshot(runner))
                if role!='C3_LANGUAGE':
                    phase='STRUCTURED_OFFER';phase_started=time.monotonic();report['phase']=phase
                    report['phases'][phase]={'ok':False,'budget_seconds':r.cfg['observer_seconds'],'requested_tokens':r.cfg['observer_tokens']}
                    p=r.cognition.offer(role,e,0,time.monotonic()+r.cfg['observer_seconds'])
                    report['structured_offer']={'verified_quote_count':len(p['evidence_refs']),'rejected_quote_count':p['rejected_quotes'],'actual':p['offer']}
                    report['phases'][phase].update(ok=True,duration_s=time.monotonic()-phase_started,metrics=_probe_metrics_snapshot(runner))
                report['phase']='COMPLETE'
            except Exception as exc:
                report.update(ok=False,phase=phase,error=str(exc),error_type=type(exc).__name__)
                report['phases'][phase].update(ok=False,error=str(exc),error_type=type(exc).__name__,duration_s=time.monotonic()-phase_started,metrics=_probe_metrics_snapshot(runner))
            finally:
                report['unload']=r.pool.unload()
                report['duration_s']=time.monotonic()-start
"""

METRICS_HELPER = """def _probe_metrics_snapshot(runner):
    # Native calls replace or mutate last_metrics. Keep independent phase
    # snapshots without exporting logs or treating absent metrics as success.
    try:
        metrics=getattr(runner,'last_metrics',None)
        return copy.deepcopy(metrics) if isinstance(metrics,dict) else {}
    except Exception:
        return {}

"""


def _replace_once(source, old, new, label):
    if source.count(old) != 1:
        raise ValueError("unexpected probe recovery source: " + label)
    return source.replace(old, new, 1)


def build_sources(code_dir):
    code_dir = Path(code_dir)
    name = "v13/verification.py"
    data = (code_dir / name).read_bytes()
    if hashlib.sha256(data).hexdigest() != PINS[name]:
        raise ValueError("probe recovery source changed: " + name)
    source = data.decode("utf-8")
    source = _replace_once(source, "import contextlib\n", "import contextlib\nimport copy\n", "imports")
    source = _replace_once(source, "def probe(r):\n", METRICS_HELPER + "def probe(r):\n", "metrics helper")
    source = _replace_once(source, OLD_ROLES, NEW_ROLES, "role phases")
    compile(source, name, "exec")
    return {name: source.encode("utf-8")}
