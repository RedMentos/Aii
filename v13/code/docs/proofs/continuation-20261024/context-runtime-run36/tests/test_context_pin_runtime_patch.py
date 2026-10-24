"""Synthetic exact-anchor patch tests; full Runtime checkout remains unavailable."""
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import context_pin_runtime_patch as P

CONTEXT = """VOLATILE_HEAD='Context for the next message (reference material, not a question):'
class Stub:
    def demo(self):
        def try_compress(s):
            if s[2]!='RAW' or s[4]:return False
            s[2]='COMPRESSED';return True
        # budget pressure: compress, then point, unpinned first; the newest turn is never dropped by policy
        for group in (unpinned,[s for s in state[:-1] if s[3]]):
            for s in group:
                if size()<=budget:break
                if try_compress(s):decisions.append('compress_budget')
            for s in group:
                if size()<=budget:break
                if not s[4]:s[2]='POINTER';decisions.append('pointer_budget')
        applied=st['mode']=='ACTIVE'
        fp_legacy,fp_planned=fingerprint(legacy),fingerprint(planned)
"""
RUNTIME = '''def demo(self,eid,ctxos):
                try:
                    raise ValueError('simulated')
                except Exception as exc:self.store.log('context_os_unavailable',eid,{'stage':'plan','error':type(exc).__name__})
'''

class PinPatch(unittest.TestCase):
    def test_old_anchor_is_present(self):
        self.assertIn('for group in (unpinned,[s for s in state[:-1] if s[3]])',CONTEXT)
    def test_context_transform_removes_pinned_pressure(self):
        # Use the exact anchor fragments from the frozen source; no production mutation.
        out=P.patch_context(CONTEXT)
        self.assertNotIn('for group in (unpinned,[s for s in state[:-1] if s[3]])',out)
        self.assertIn("if s[2]!='RAW' or s[3] or s[4]",out)
        self.assertIn("if st['mode']=='ACTIVE':\n                raise ContextBudgetExceeded",out)
        self.assertIn('planned_chars=sum(len(m[\'content\']) for m in planned)',out)
    def test_context_transform_is_not_idempotent(self):
        with self.assertRaisesRegex(ValueError,'expected exactly one'):
            P.patch_context(P.patch_context(CONTEXT))
    def test_missing_anchor_rejects(self):
        with self.assertRaisesRegex(ValueError,'expected exactly one'):
            P.patch_context(CONTEXT.replace('state[:-1]','state'))
    def test_original_budget_compresses_pinned_but_patch_preserves(self):
        # Execute the frozen budget excerpt with a real mutable turn state.
        def run(source, mode='SHADOW'):
            state=[['old',[], 'RAW',False,False],['pin0',[],'RAW',True,False],
                   ['pin1',[],'RAW',True,False]]
            ns={'state':state,'unpinned':[state[0]],'budget':1,'decisions':[],
                'size':lambda:sum(100 if t[2]=='RAW' else 40 if t[2]=='COMPRESSED' else 0 for t in state),
                'st':{'mode':mode},'planned':[{'content':'x'*400}],
                'legacy':[],'fingerprint':lambda _:[]}
            exec(source,ns)
            try:ns['Stub']().demo()
            except Exception as exc:return state,ns,exc
            return state,ns,None
        original,_,_=run(CONTEXT)
        self.assertNotEqual(original[1][2],'RAW')  # RED: pinned turn altered by old budget loop
        patched,ns,exc=run(P.patch_context(CONTEXT))
        self.assertIsNone(exc)
        self.assertEqual(patched[1][2],'RAW')
        self.assertEqual(patched[2][2],'RAW')
        self.assertEqual(patched[0][2],'POINTER')
        self.assertIn('no_plan_pinned_budget',ns['decisions'])
        active,_,exc=run(P.patch_context(CONTEXT),'ACTIVE')
        self.assertIsInstance(exc,ValueError)
        self.assertEqual(active[1][2],'RAW')

    def test_runtime_active_exception_not_silently_swallowed(self):
        from types import SimpleNamespace
        class Store:
            def __init__(self):self.logs=[]
            def log(self,*args):self.logs.append(args)
        class Controller:
            def __init__(self,mode):self.mode=mode
            def _load(self):return ({'mode':self.mode},None)
        class API:
            def __init__(self,mode):self.c=Controller(mode)
            def controller(self,_):return self.c
        ns={};exec(P.patch_runtime(RUNTIME),ns)
        for mode,should_raise in [('SHADOW',False),('ACTIVE',True)]:
            obj=SimpleNamespace(store=Store())
            if should_raise:
                with self.assertRaisesRegex(ValueError,'simulated'):
                    ns['demo'](obj,'e',API(mode))
            else:ns['demo'](obj,'e',API(mode))
            self.assertEqual(len(obj.store.logs),1)

    def test_source_blob_hash_is_git_format(self):
        self.assertEqual(P.git_blob(b'hello\n'),'ce013625030ba8dba906f756967f9e9ca394464a')
    def test_runtime_transform_protects_active_mode(self):
        # Inspect exact replacement contract, including no fallback on unknown mode.
        out=P.patch_runtime(RUNTIME)
        self.assertIn("_load()[0].get('mode') != 'SHADOW'",out)
        self.assertIn('raise',out)
    def test_no_source_output_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d);p=base/'src';p.write_text('x');q=base/'rt';q.write_text('y')
            with self.assertRaisesRegex(ValueError,'Git blob mismatch'):
                P.build(p,q,base/'out')
            self.assertFalse((base/'out').exists())
    def test_exact_blob_constants(self):
        self.assertEqual(P.CONTEXT_BLOB,'028376012e328624fb527a927bb0e2a1071a86a0')
        self.assertEqual(P.RUNTIME_BLOB,'a691d27bd0772a4fa1f03d57ec90663237bf6825')

if __name__=='__main__':unittest.main()
