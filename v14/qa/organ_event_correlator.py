"""Offline, sanitized B1/B2->C4->C3 event correlation. Not phone/native proof."""
from collections import defaultdict

FIELDS = {"turn_id","event_id","kind","role","offer_id","source_id","consumer","timestamp_ms"}
KINDS = {"offer_created","offer_delivered","offer_consumed","c3_input","final"}

def correlate(events):
    if not isinstance(events,list):
        return {"status":"INVALID","errors":["events must be a list"]}
    errors=[]; ids=set(); turns=defaultdict(list)
    for i,e in enumerate(events):
        if not isinstance(e,dict) or set(e)!=FIELDS:
            errors.append(f"event {i}: invalid schema"); continue
        if any(type(e[k]) is not str or not e[k] for k in FIELDS-{"timestamp_ms"}):
            errors.append(f"event {i}: invalid identifier"); continue
        if type(e["timestamp_ms"]) is not int or e["timestamp_ms"]<0 or e["kind"] not in KINDS or e["event_id"] in ids:
            errors.append(f"event {i}: invalid timestamp/kind or duplicate"); continue
        ids.add(e["event_id"]);turns[e["turn_id"]].append(e)
    result={}
    for turn,rows in turns.items():
        offers=defaultdict(list)
        for e in rows:
            if e["kind"].startswith("offer_"):
                if e["role"] not in ("B1","B2"):errors.append(f"{turn}: invalid organ")
                offers[(e["role"],e["offer_id"])].append(e)
        consumed=set()
        for (role,oid),seq in offers.items():
            seq.sort(key=lambda e:e["timestamp_ms"])
            if [e["kind"] for e in seq]!=["offer_created","offer_delivered","offer_consumed"]:
                errors.append(f"{turn}: incomplete offer lifecycle");continue
            if len({e["source_id"] for e in seq})!=1 or [e["consumer"] for e in seq]!=["BUS","C4","C4"] or not seq[0]["timestamp_ms"]<seq[1]["timestamp_ms"]<seq[2]["timestamp_ms"]:
                errors.append(f"{turn}: broken source/consumer/time chain");continue
            consumed.add((role,oid,seq[0]["source_id"]))
        inputs=[e for e in rows if e["kind"]=="c3_input"]
        used=set()
        for e in inputs:
            key=(e["role"],e["offer_id"],e["source_id"])
            if key not in consumed or e["consumer"]!="C3":
                errors.append(f"{turn}: unproven C3 input");continue
            if e["timestamp_ms"]<=max(x["timestamp_ms"] for x in offers[(e["role"],e["offer_id"])]):
                errors.append(f"{turn}: C3 input predates C4 consumption");continue
            used.add(e["role"])
        finals=[e for e in rows if e["kind"]=="final"]
        if len(finals)!=1 or finals[0]["consumer"]!="USER" or not inputs or finals[0]["timestamp_ms"]<=max(e["timestamp_ms"] for e in inputs):
            errors.append(f"{turn}: missing/early final")
        result[turn]={"b1_c3_used":"B1" in used,"b2_c3_used":"B2" in used,"cross_organ_trace":used=={"B1","B2"} and len(finals)==1}
    return {"status":"TRACE_CONSISTENT" if not errors else "BLOCKED","independent_device_proof":False,"native_weight_proof":False,"turns":result,"errors":errors}
