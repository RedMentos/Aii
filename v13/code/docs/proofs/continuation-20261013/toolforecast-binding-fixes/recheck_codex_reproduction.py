import json, sys, traceback, io, contextlib
src = open(sys.argv[1]).read()
g = {'__file__': sys.argv[2] + '/docs/proofs/x/reproduce.py', '__name__': 'recheck'}
exec(compile(src, 'reproduce.py', 'exec'), g)
out = {}
for name in ('changed_gate_reuses_old_adaptation', 'failed_reinstall_breaks_last_passing_retention',
             'pending_scores_across_checkpoint_change', 'corrupted_install_breaks_status', 'expired_context_files_accumulate'):
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            r = g[name]()
        out[name] = {'defect_reproduced': True, 'result': r}
    except BaseException as e:
        out[name] = {'defect_reproduced': False, 'stopped_by': type(e).__name__ + ': ' + str(e)[:200]}
print(json.dumps(out, indent=1, default=str))
