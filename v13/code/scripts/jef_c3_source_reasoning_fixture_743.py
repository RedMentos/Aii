"""Run70 preregistered six disjoint C3 source-only reasoning JSON-schema tasks."""
from copy import deepcopy
import hashlib
import json

from v13.common import dumps
from scripts import jef_c3_schema_fixture_727 as run68

SEED = 743
ARMS = ("TYPED_SCHEMA", "SOURCE_SCHEMA")
TABLE_SHA256 = "94361e05c2781b0cebac7d48d7ee324af131be1c405674a66fb8ed845256c339"
MODEL_SHA256 = run68.MODEL_SHA256
RUNNER_SHA256 = run68.RUNNER_SHA256
SCHEMA = run68.SCHEMA
TABLE = [
 ("river ferry","fare","credits","boarding window","slots","insured",(190,25,True),(150,22,True),(140,28,True),"A"),
 ("planetarium tours","seat quota","places","entry window","ticks","accessible",(160,20,False),(175,18,True),(150,19,False),"B"),
 ("forest cameras","power quota","units","startup window","beats","weatherproof",(110,12,True),(100,13,True),(120,11,True),"NONE"),
 ("school robotics","kit quota","kits","setup window","steps","reusable",(200,18,False),(180,17,True),(150,21,False),"A"),
 ("island water","volume quota","litres","delivery window","intervals","filtered",(280,22,True),(250,21,False),(260,20,True),"B"),
 ("archive boxes","load quota","points","transit window","cycles","sealed",(90,10,True),(95,8,True),(80,12,False),"NONE"),
]
SOURCE_SYSTEM = (
    "Use only the archived project policy and latest option sheet supplied in "
    "the user JSON to decide A, B or NONE. An option qualifies only if BOTH "
    "numeric quantities are <= their respective policy maxima and, when the "
    "policy requires its boolean flag, the option has that flag true. "
    "If both qualify, choose the option with smaller first numeric quantity; "
    "break an exact tie using the second numeric quantity, then A. "
    "If neither qualifies, choose NONE. Return only the constrained JSON "
    "object with one action field. Do not invent values."
)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def fixtures():
    if sha(json.dumps(TABLE,sort_keys=True,separators=(',',':')).encode()) != TABLE_SHA256:
        raise ValueError("RUN70_TABLE_CHANGED")
    rows=[]
    for i,item in enumerate(TABLE):
        domain,f1,u1,f2,u2,flag,policy,a,b,action=item
        if run68.oracle(policy,(a,b)) != action:
            raise ValueError("RUN70_ORACLE_CHANGED")
        project="P2X"+sha(f"JEF70|{SEED}|{i}".encode())[:16].upper()
        tf=lambda x:"true" if x else "false"
        current=(f"Project {project}. Choose Option A or Option B using the "
                 f"archived {domain} policy and latest option sheet. "
                 "If neither qualifies, choose NONE.")
        policy_source=(f"Project {project} archived {domain} policy. "
                       f"Maximum {f1}: {policy[0]} {u1}. "
                       f"Maximum {f2}: {policy[1]} {u2}. "
                       f"Required {flag}: {tf(policy[2])}.")
        def opt(label,x):
            return (f"Option {label}: {f1} {x[0]} {u1}; "
                    f"{f2} {x[1]} {u2}; {flag} {tf(x[2])}.")
        sheet_source=(f"Project {project} latest {domain} option sheet. "
                      +opt("A",a)+" "+opt("B",b))
        rows.append({"index":i,"project":project,"domain":domain,
                     "expected":action,"current":current,
                     "policy_source":policy_source,"sheet_source":sheet_source})
    if [r["expected"] for r in rows] != ["A","B","NONE"]*2 or len({r["project"] for r in rows}) != 6:
        raise ValueError("RUN70_BALANCE_RED")
    old=run68.fixtures()
    if ({r["project"] for r in rows} & {r["project"] for r in old}
            or {r[k] for r in rows for k in ("current","policy_source","sheet_source")}
               & {r[k] for r in old for k in ("current","policy_source","sheet_source")}):
        raise ValueError("RUN70_RUN68_SOURCE_OVERLAP")
    return rows


def model_messages(envelope,arm):
    if (type(envelope) is not dict
            or envelope.get("status") != "JEF_C3_TYPED_ENVELOPE_SHADOW_NO_MODEL_CALL"
            or envelope.get("typed_jef_action") not in ("A","B","NONE")
            or type(envelope.get("messages")) is not list
            or len(envelope["messages"]) != 2):
        raise ValueError("RUN70_ENVELOPE_RED")
    original=deepcopy(envelope["messages"])
    if sha(dumps(original).encode()) != envelope.get("messages_sha256"):
        raise ValueError("RUN70_PROMPT_HASH_RED")
    if arm == "TYPED_SCHEMA":
        return original
    if arm != "SOURCE_SCHEMA":
        raise ValueError("RUN70_ARM_RED")
    payload=json.loads(original[1]["content"],object_pairs_hook=run68._unique)
    if type(payload) is not dict or payload.pop("typed_jef_action",None) != envelope["typed_jef_action"]:
        raise ValueError("RUN70_TYPED_ACTION_MISSING")
    if any(k in payload for k in ("expected","oracle_action","answer")):
        raise ValueError("RUN70_ANSWER_LEAK_RED")
    original[0]["content"]=SOURCE_SYSTEM
    original[1]["content"]=dumps(payload)
    if "typed_jef_action" in dumps(original):
        raise ValueError("RUN70_TYPED_ACTION_LEAK")
    return original


def score(output,expected):
    if expected not in ("A","B","NONE"):
        raise ValueError("RUN70_EXPECTED_RED")
    return int(run68.decode_schema(output) == expected)
