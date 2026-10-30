"""Run11S read-only focal memory recency/replacement shadow; synthetic only.

Original WP-Z5b task grammar copied verbatim from Git blob
9d61acdd8f8aa47435ed682ac4b7013fd3e02df8, branch
claude/project-thread-bn7n5k. New disjoint seed167; no model inference.
This is a proposal, not a Runtime/FocalLoop change or utility gate.
"""
from __future__ import annotations

import hashlib
import json
import random
import re
from scripts import utility_bench2 as U2

SCHEMA = "v13.focal.replacement_shadow.seed167.v1"
SEED = 167
PER_KIND = 15
CAPACITY = 4

# Exact historical WP-Z5b synthetic fixture generator (provenance above):
PROJECTS=('Kestrel','Alder','Birch','Heron','Lynx','Otter','Quartz','Raven','Sable','Tamarack','Umber','Vireo','Willow','Yarrow','Zephyr',
          'Cedar','Falcon','Juniper','Maple','Nimbus')
MONTHS=('January','February','March','April','May','June','July','August','September','October')
CFG={'memory_top_k':6,'focal_slots':4}

def word(n):return U2.word(n)

def tasks(seed=11,per_kind=15):
    """(fixture, message, notes [(key, value)], answer numbers, regex checks, stale numbers). Notes are stored in the listed order."""
    rng=random.Random(seed);out=[]
    def shuffled(xs):xs=list(xs);rng.shuffle(xs);return xs
    for i in range(per_kind):
        p=rng.choice(PROJECTS);ms=sorted(rng.sample(range(len(MONTHS)),3));vs=rng.sample(range(30,95),3);ds=[rng.randint(1,28) for _ in ms]
        tr,hw,tn=rng.sample(range(5,29),3)
        notes=[('Project %s budget %s'%(p,MONTHS[m]),'Budget note of %d %s: the Project %s main budget is %d units.'%(d,MONTHS[m],p,v)) for m,v,d in zip(ms,vs,ds)]
        notes+=[('Project %s travel budget'%p,'The Project %s travel budget is %d units, separate from the main budget.'%(p,tr)),
                ('Project %s hardware budget'%p,'The Project %s hardware budget is %d units, separate from the main budget.'%(p,hw)),
                ('Project %s training budget'%p,'The Project %s training budget is %d units, separate from the main budget.'%(p,tn))]
        out.append(('update%02d'%i,'Project %s: what is the current main budget according to the most recent budget note? Answer with the number.'%p,
                    shuffled(notes),[vs[-1]],{'budget':word(vs[-1])},vs[:-1]))
    for i in range(per_kind):
        p=rng.choice(PROJECTS);m1,m2=sorted(rng.sample(range(len(MONTHS)),2));old,new=rng.sample(range(50,99),2);spend=rng.randint(8,40);ts,tsp,hw=rng.randint(10,30),rng.randint(2,9),rng.randint(5,30)
        notes=[('Project %s budget %s'%(p,MONTHS[m1]),'Budget note of %s: the Project %s main budget is %d units.'%(MONTHS[m1],p,old)),
               ('Project %s budget %s'%(p,MONTHS[m2]),'Budget note of %s: the Project %s main budget is %d units.'%(MONTHS[m2],p,new)),
               ('Project %s budget spending'%p,'Spending report: %d units of the Project %s main budget have been spent.'%(spend,p)),
               ('Project %s travel budget'%p,'The Project %s travel budget is %d units, separate from the main budget.'%(p,ts)),
               ('Project %s travel budget spending'%p,'Spending report: %d units of the Project %s travel budget have been spent.'%(tsp,p)),
               ('Project %s hardware budget'%p,'The Project %s hardware budget is %d units, separate from the main budget.'%(p,hw))]
        out.append(('combine%02d'%i,'Project %s: how many units of the main budget are left, using the most recent budget note and the spending report? Answer with the number.'%p,
                    shuffled(notes),[new-spend],{'left':word(new-spend)},[old-spend,new]))
    for i in range(per_kind):
        p=rng.choice(PROJECTS);city=rng.choice(U2.CITIES);n=rng.randint(150,900);fix=n+rng.choice([-1,1])*rng.randint(12,60);fill=rng.sample(U2.FILLER,4);pos=rng.randint(1,3)
        sc,cars,last,team=rng.randint(20,90),rng.randint(40,300),rng.randint(150,900),rng.randint(3,9)
        sents=fill[:pos]+['In %s the Project %s survey counted %d bicycles parked at the station.'%(city,p,n)]+fill[pos:]
        notes=[('Project %s survey bicycles correction'%p,'Correction after the recount: the Project %s survey counted %d bicycles at the station, not %d.'%(p,fix,n)),
               ('Project %s survey scooters'%p,'The Project %s survey counted %d scooters at the station.'%(p,sc)),
               ('Project %s survey cars'%p,'The Project %s survey counted %d cars in the station car park.'%(p,cars)),
               ('Project %s survey bicycles last year'%p,'Last year the Project %s survey counted %d bicycles.'%(p,last)),
               ('Project %s survey team'%p,'The Project %s survey team had %d members.'%(p,team)),
               ('Project %s survey weather'%p,'During the Project %s survey the weather was dry and mild.'%p)]
        out.append(('correction%02d'%i,'Field notes: '+' '.join(sents)+' Question: Project %s survey: how many bicycles were counted at the station this year, taking stored corrections into account?'%p,
                    shuffled(notes),[fix],{'count':word(fix)},[n,last]))
    for i in range(per_kind):
        p=rng.choice(PROJECTS);its=rng.sample(U2.ITEMS,3);vals=[rng.randint(12,95) for _ in its];true=sum(vals);wrong=true+rng.choice([-20,-10,10,20])
        a,b,fc=rng.sample(range(120,300),3);lim,trav=rng.randint(250,400),rng.randint(30,90)
        notes=[('Project %s expenses April'%p,'The Project %s expenses in April totalled %d euros.'%(p,a)),
               ('Project %s expenses March'%p,'The Project %s expenses in March totalled %d euros.'%(p,b)),
               ('Project %s expenses May forecast'%p,'Forecast made in April: Project %s expenses in May were expected to be %d euros.'%(p,fc)),
               ('Project %s expenses limit'%p,'The monthly Project %s expenses limit is %d euros.'%(p,lim)),
               ('Project %s expenses travel'%p,'Project %s travel expenses are booked separately; last trip %d euros.'%(p,trav)),
               ('Project %s expenses approval'%p,'Project %s expenses are approved by the finance office.'%p)]
        out.append(('distract%02d'%i,'Project %s expenses report for May. Items: '%p+', '.join('%s %d euros'%(x,v) for x,v in zip(its,vals))+
                    '. Summary line at the bottom: "Total: %d euros." Is the summary line of this Project %s May expenses report correct? Give the correct total.'%(wrong,p),
                    shuffled(notes),[true],{'total':word(true)},[wrong,a,b,fc]))
    return out


# New read-only proposal; never modifies original note tuples.
_MONTH = {month.lower(): i for i, month in enumerate(MONTHS)}
_MONTHS = "|".join(MONTHS)
_BUDGET = re.compile(
    rf"^Budget note of (?:[0-9]{{1,2}} )?({_MONTHS}): the Project ([A-Za-z]+) "
    r"main budget is ([0-9]+) units\.$", re.I)
_SPEND = re.compile(
    r"^Spending report: ([0-9]+) units of the Project ([A-Za-z]+) "
    r"main budget have been spent\.$", re.I)
_CORRECTION = re.compile(
    r"^Correction after the recount: the Project ([A-Za-z]+) survey counted "
    r"([0-9]+) bicycles at the station, not ([0-9]+)\.$", re.I)
_PROJECT = re.compile(r"\bProject ([A-Za-z]+)\b", re.I)


def _kind(query):
    q = query.lower()
    if "current main budget" in q and "most recent budget note" in q:
        return "update"
    if "main budget are left" in q and "most recent budget note" in q:
        return "combine"
    if "stored corrections into account" in q:
        return "correction"
    if "expenses report for may" in q and "correct total" in q:
        return "distract"
    return None


def propose(query, notes, capacity=CAPACITY):
    """Return source-key selection or abstain; never a factual answer."""
    if type(query) is not str or type(notes) not in (list, tuple):
        raise TypeError("SOURCE_TYPES")
    if type(capacity) is not int or not 1 <= capacity <= 16:
        raise ValueError("CAPACITY_INVALID")
    if len(notes) != 6 or any(
            type(n) not in (list, tuple) or len(n) != 2
            or type(n[0]) is not str or type(n[1]) is not str
            for n in notes) or len({n[0] for n in notes}) != 6:
        return {"kind": None, "abstain": True, "reason": "SOURCE_NOTE_SHAPE",
                "selected_keys": [], "baseline_first4": [n[0] for n in notes[:capacity]]}
    baseline = [key for key, _ in notes[:capacity]]
    kind = _kind(query)
    project_match = _PROJECT.search(query)
    if not kind or not project_match:
        return {"kind": kind, "abstain": True, "reason": "UNSUPPORTED_QUERY",
                "selected_keys": baseline, "baseline_first4": baseline}
    project = project_match.group(1).lower()
    if kind == "distract":
        return {"kind": kind, "abstain": False, "reason": "CURRENT_SOURCE_ONLY",
                "selected_keys": [], "baseline_first4": baseline}
    found = []
    for key, value in notes:
        if kind in ("update", "combine"):
            m = _BUDGET.fullmatch(value)
            if m and m.group(2).lower() == project:
                found.append((_MONTH[m.group(1).lower()], key, value))
        elif kind == "correction":
            m = _CORRECTION.fullmatch(value)
            if m and m.group(1).lower() == project:
                found.append((0, key, value))
    if not found:
        return {"kind": kind, "abstain": True, "reason": "SOURCE_NOT_FOUND",
                "selected_keys": baseline, "baseline_first4": baseline}
    latest = max(x[0] for x in found)
    choices = [x for x in found if x[0] == latest]
    if len(choices) != 1:
        return {"kind": kind, "abstain": True, "reason": "AMBIGUOUS_REVISION",
                "selected_keys": baseline, "baseline_first4": baseline}
    chosen = [choices[0][1]]
    if kind == "combine":
        spending = [(key, value) for key, value in notes
                    if (m := _SPEND.fullmatch(value))
                    and m.group(2).lower() == project]
        if len(spending) != 1:
            return {"kind": kind, "abstain": True, "reason": "SPENDING_AMBIGUOUS",
                    "selected_keys": baseline, "baseline_first4": baseline}
        chosen.append(spending[0][0])
    if len(chosen) > capacity:
        return {"kind": kind, "abstain": True, "reason": "CAPACITY",
                "selected_keys": baseline, "baseline_first4": baseline}
    return {"kind": kind, "abstain": False, "reason": "EXPLICIT_SOURCE_REVISION",
            "selected_keys": chosen, "baseline_first4": baseline}


def required_keys(fid, notes):
    """Independent oracle uses note KEYS, not the selector's value regex."""
    kind = re.sub(r"[0-9]+$", "", fid)
    if kind == "distract":
        return []
    if kind == "correction":
        xs = [k for k, _ in notes if k.endswith("survey bicycles correction")]
        return xs if len(xs) == 1 else None
    if kind not in ("update", "combine"):
        return None
    candidates = []
    for key, _ in notes:
        m = re.search(r" budget (" + _MONTHS + r")$", key)
        if m:
            candidates.append((_MONTH[m.group(1).lower()], key))
    if not candidates:
        return None
    last = max(x[0] for x in candidates)
    latest = [k for month, k in candidates if month == last]
    if len(latest) != 1:
        return None
    if kind == "combine":
        spending = [k for k, _ in notes if re.fullmatch(r"Project [A-Za-z]+ budget spending", k)]
        return latest + spending if len(spending) == 1 else None
    return latest


def evaluate(seed=SEED):
    if type(seed) is not int or seed == 11:
        raise ValueError("DISJOINT_SEED_REQUIRED")
    fixtures = tasks(seed=seed, per_kind=PER_KIND)
    if len(fixtures) != 60:
        raise ValueError("FIXTURE_COUNT_CHANGED")
    rows = []
    for fid, query, notes, answers, checks, stale in fixtures:
        result = propose(query, notes)
        needed = required_keys(fid, notes)
        if needed is None:
            raise ValueError("ORACLE_SOURCE_SHAPE:" + fid + ":" + repr([k for k, _ in notes]))
        keys = [k for k, _ in notes]
        chosen = result["selected_keys"]
        if not set(chosen) <= set(keys) or len(chosen) > CAPACITY:
            raise ValueError("PROPOSAL_SOURCE_OR_CAPACITY_INVALID")
        rows.append({
            "fixture": fid, "kind": result["kind"], "abstain": result["abstain"],
            "reason": result["reason"], "required_keys": needed,
            "selected_keys": chosen, "baseline_first4": result["baseline_first4"],
            "exact_required": set(chosen) == set(needed),
            "baseline_exact_required": set(result["baseline_first4"]) == set(needed),
            "required_included": set(needed) <= set(chosen),
            "baseline_required_included": set(needed) <= set(result["baseline_first4"]),
            "source_key_hash": hashlib.sha256(json.dumps(keys, sort_keys=True).encode()).hexdigest(),
        })
    summary = {
        "exact_required": sum(x["exact_required"] for x in rows),
        "baseline_exact_required": sum(x["baseline_exact_required"] for x in rows),
        "required_included": sum(x["required_included"] for x in rows),
        "baseline_required_included": sum(x["baseline_required_included"] for x in rows),
        "abstentions": sum(x["abstain"] for x in rows),
        "by_kind": {kind: sum(x["exact_required"] for x in rows if x["kind"] == kind)
                    for kind in ("update", "combine", "correction", "distract")},
    }
    return {"schema": SCHEMA, "seed": seed, "source_generator_blob":
            "9d61acdd8f8aa47435ed682ac4b7013fd3e02df8",
            "status": "SYNTHETIC_SELECTION_ONLY_NO_UTILITY_GATE",
            "summary": summary, "rows": rows,
            "learning_mode": "RECORD_ONLY", "jepa_weight": 0,
            "step2_gate_promoted": False, "b3_promoted": False,
            "body_jepa_available": False, "redmi_measured": False,
            "whole_system_complete": False}


if __name__ == "__main__":
    print(json.dumps(evaluate(), indent=2, sort_keys=True))
