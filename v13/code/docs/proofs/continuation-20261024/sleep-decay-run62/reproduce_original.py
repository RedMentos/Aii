# Exact original Run61 sleep.py lines 378-380 applied twice at unchanged wall time.
DAY=86400.
it={'created':0.,'last':None,'priority':1.0}
now=10*DAY
for _ in range(2):
    days=max(0.,(now-(it['last'] or it['created']))/DAY)
    p=max(.05,it['priority']*.98**days)
    if p<it['priority']:it['priority']=p
first=.98**10
print('expected_one_decay=',first)
print('observed_two_calls=',it['priority'])
assert abs(it['priority']-first)<1e-12, 'RED: same-time Sleep C tick compounded elapsed-day decay twice'
