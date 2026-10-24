MIX={'recent':1e308,'protected_old':0.,'failure':0.}
total=sum(MIX.values())
try:
    quota=int(8*MIX['recent']/total)
except OverflowError as exc:
    print('original_sampling_exception=',type(exc).__name__)
    raise
