import math
MIX={'recent':.5,'protected_old':.35,'failure':.15}
m=dict(MIX);m['recent']=float('nan')
old_reject=(set(m)!=set(MIX) or any(isinstance(v,bool) or not isinstance(v,(int,float)) or v<0 for v in m.values()) or sum(m.values())<=0)
print('old_policy_rejected_nan=',old_reject)
print('old_sum=',sum(m.values()))
try:
    quota=int(8*m['recent']/sum(m.values()))
except ValueError as exc:
    print('downstream_sample_exception=',type(exc).__name__)
assert old_reject, 'RED: old policy accepted NaN and deferred failure to sampling'
