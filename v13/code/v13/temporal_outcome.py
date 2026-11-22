"""V14 source-bound temporal outcome/omission ledger (experimental; no trainer authority)."""
from dataclasses import dataclass, asdict
import json
import math
import os
from pathlib import Path

STATUSES = {'PENDING', 'OBSERVED', 'OMITTED', 'DELAYED', 'DIFFERENT', 'CENSORED', 'CANCELLED'}

@dataclass
class Expectation:
    action_id: str
    source_ref: str
    predicted: str
    earliest: float
    deadline: float
    probability: float
    status: str = 'PENDING'
    outcome_ref: str | None = None
    error: float | None = None

    def __post_init__(self):
        if not all(type(x) is str and 0 < len(x) <= 256 for x in (self.action_id, self.source_ref, self.predicted)):
            raise ValueError('source/action/prediction required')
        if not all(type(x) in (int, float) and math.isfinite(x) for x in (self.earliest, self.deadline, self.probability)):
            raise ValueError('nonfinite timing/probability')
        if not (0 <= self.earliest <= self.deadline and 0 <= self.probability <= 1 and self.status in STATUSES):
            raise ValueError('invalid expectation')

class TemporalLedger:
    def __init__(self, path, *, max_pending=1024):
        self.path = Path(path)
        self.max_pending = max_pending
        self.rows = {}
        if self.path.exists():
            data = json.loads(self.path.read_text())
            if data.get('schema') != 'v14.temporal-outcome/1' or type(data.get('rows')) is not list:
                raise ValueError('unknown ledger schema')
            for record in data['rows']:
                e = Expectation(**record)
                if e.action_id in self.rows:
                    raise ValueError('duplicate persisted action')
                self.rows[e.action_id] = e

    def add(self, e):
        if not isinstance(e, Expectation) or e.action_id in self.rows:
            raise ValueError('duplicate or invalid expectation')
        if sum(x.status == 'PENDING' for x in self.rows.values()) >= self.max_pending:
            raise ValueError('pending capacity')
        self.rows[e.action_id] = e
        self.save()

    def resolve(self, action_id, *, at, observed=None, outcome_ref=None, observable=False, cancelled=False):
        e = self.rows[action_id]
        if e.status != 'PENDING':
            raise ValueError('already resolved')
        if type(at) not in (int, float) or not math.isfinite(at) or at < e.earliest:
            raise ValueError('invalid observation time')
        if cancelled:
            e.status = 'CANCELLED'
        elif observed is not None:
            if type(observed) is not str or not observed or not outcome_ref:
                raise ValueError('observed outcome requires evidence')
            e.outcome_ref = outcome_ref
            e.status = ('OBSERVED' if at <= e.deadline else 'DELAYED') if observed == e.predicted else 'DIFFERENT'
            e.error = (1.0 if observed == e.predicted else 0.0) - e.probability
        elif at >= e.deadline and observable and outcome_ref:
            e.status = 'OMITTED'
            e.outcome_ref = outcome_ref
            e.error = -e.probability
        else:
            e.status = 'CENSORED'
        self.save()
        return e

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_name(self.path.name + '.tmp')
        with tmp.open('w') as f:
            json.dump({'schema': 'v14.temporal-outcome/1', 'rows': [asdict(x) for x in self.rows.values()]}, f, sort_keys=True)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, self.path)
