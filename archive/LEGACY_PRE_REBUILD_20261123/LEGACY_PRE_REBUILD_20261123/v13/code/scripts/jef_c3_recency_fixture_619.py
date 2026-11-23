"""Registered synthetic six-case JEF/C3 formatter-copy diagnostic; no inference."""
import hashlib
import json

SEED = 619
ARMS = ("BASELINE", "RECENCY")
MODEL_SHA256 = "3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d"
RUNNER_SHA256 = "79e312188dc1d75c28201771f106e91de470b5cebdd838d31bb4db25eecf5d39"
TABLE_SHA256 = "69b2d02675ca2bcddce00f87a70265ff9aab024ff62d2b063369d60232090ee3"
# domain, first-field, first-unit, second-field, second-unit, flag,
# (max1,max2,required), (A first,second,flag), (B first,second,flag), action.
TABLE = [
    ("festival venue", "rental fee", "tokens", "access window", "ticks", "covered", (150,20,True), (100,12,True), (160,12,True), "A"),
    ("workshop equipment", "kit size", "blocks", "assembly window", "beats", "reusable", (180,18,True), (220,10,True), (140,14,True), "B"),
    ("community garden", "water allocation", "drops", "setup window", "cycles", "shaded", (120,12,True), (150,9,True), (90,16,True), "NONE"),
    ("satellite mockups", "payload mass", "units", "spin up window", "steps", "shielded", (300,25,False), (120,18,False), (220,12,True), "A"),
    ("exhibition crates", "container volume", "cells", "opening window", "slots", "insured", (200,24,True), (170,20,False), (185,15,True), "B"),
    ("classroom planning", "seat quota", "places", "preparation window", "intervals", "accessible", (100,10,False), (120,8,True), (90,15,True), "NONE"),
]


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def oracle(policy, options):
    eligible = [(o[0], o[1], name) for name, o in zip("AB", options)
                if o[0] <= policy[0] and o[1] <= policy[1]
                and (not policy[2] or o[2])]
    return min(eligible)[2] if eligible else "NONE"


def fixtures():
    digest = sha(json.dumps(TABLE, sort_keys=True, separators=(',', ':')).encode())
    if digest != TABLE_SHA256:
        raise ValueError("JEF619_REGISTERED_TABLE_CHANGED")
    rows = []
    for i, item in enumerate(TABLE):
        domain, f1, u1, f2, u2, flag, policy, a, b, action = item
        if oracle(policy, (a,b)) != action:
            raise ValueError("JEF619_ORACLE_CHANGED")
        project = 'P2X' + sha(f'JEF619|{SEED}|{i}'.encode())[:16].upper()
        tf = lambda value: 'true' if value else 'false'
        current = (f"Project {project}. Choose Option A or Option B using the "
                   f"archived {domain} policy and latest option sheet. "
                   "If neither qualifies, choose NONE.")
        archived = (f"Project {project} archived {domain} policy. "
                    f"Maximum {f1}: {policy[0]} {u1}. "
                    f"Maximum {f2}: {policy[1]} {u2}. "
                    f"Required {flag}: {tf(policy[2])}.")
        def option(label, values):
            return (f"Option {label}: {f1} {values[0]} {u1}; "
                    f"{f2} {values[1]} {u2}; {flag} {tf(values[2])}.")
        sheet = (f"Project {project} latest {domain} option sheet. "
                 + option('A', a) + ' ' + option('B', b))
        rows.append({'index':i,'project':project,'domain':domain,
                     'current':current,'policy_source':archived,
                     'sheet_source':sheet,'expected':action})
    if len({r['project'] for r in rows}) != 6 or [r['expected'] for r in rows] != ['A','B','NONE']*2:
        raise ValueError("JEF619_BALANCE_CHANGED")
    return rows


def messages(original, action, arm):
    if type(original) is not list or len(original) != 2 or action not in ('A','B','NONE'):
        raise ValueError("JEF619_INPUT_RED")
    if arm == 'BASELINE':
        return list(original)
    if arm == 'RECENCY':
        return list(original) + [{'role':'user', 'content':
                                  f'Verified JEF action: {action}. Copy that token only.'}]
    raise ValueError("JEF619_ARM_RED")


def strict(output, expected):
    return int(type(output) is str and output == expected)
