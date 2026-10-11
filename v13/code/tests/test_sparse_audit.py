"""Synthetic C++ hook execution and parser checks; no LLM or phone claim."""
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from v13.sparse_audit import firing_observation, PREFIX, SCHEMA


def line(event, **fields):
    return PREFIX + json.dumps(dict(schema=SCHEMA, event=event, **fields)) + '\n'


class AuditParser(unittest.TestCase):
    def setUp(self):
        self.begin = line('begin', request=1, slots=2, layer=3)
        self.batch = line('batch', request=1, rows=2, batches=1, applied=[2, 0], guard_blocked=[0, 1])

    def test_valid_observation_is_neither_recall_nor_authorization(self):
        result = firing_observation('unrelated runner log\n' + self.begin + self.batch)
        self.assertEqual(result['fired_rows'], [0])
        self.assertEqual(result['evaluated_rows'], 2)
        self.assertTrue(result['exact_retained'])
        self.assertFalse(result['activation_authorized'])
        self.assertFalse(result['quality_proven'])

    def test_no_evaluation_is_not_measured_zero(self):
        self.assertEqual(firing_observation(self.begin)['reason'], 'NO_EVALUATED_ROWS')
        self.assertEqual(firing_observation('')['reason'], 'NO_PROMPT_MARKER')

    def test_broken_ambiguous_or_wrong_request_records_fail_closed(self):
        for text in (self.batch, self.begin * 2, self.begin + PREFIX + '{',
                     self.begin + line('batch', request=2, rows=2, batches=1, applied=[0, 0], guard_blocked=[0, 0]),
                     self.begin + line('batch', request=1, rows=2, batches=1, applied=[0], guard_blocked=[0, 0]),
                     self.begin + line('batch', request=1, rows=2, batches=1, applied=[True, 0], guard_blocked=[0, 0])):
            with self.subTest(text=text):
                self.assertEqual(firing_observation(text)['status'], 'UNAVAILABLE')

    def test_missing_batch_or_regressing_counters_fail_closed(self):
        for extra in (line('batch', request=1, rows=3, batches=3, applied=[2, 0], guard_blocked=[0, 1]),
                      line('batch', request=1, rows=3, batches=2, applied=[1, 0], guard_blocked=[0, 1])):
            self.assertEqual(firing_observation(self.begin + self.batch + extra)['status'], 'UNAVAILABLE')


@unittest.skipUnless(shutil.which('g++'), 'g++ unavailable for synthetic native hook check')
class NativeAudit(unittest.TestCase):
    def test_actual_header_counters_guard_zero_values_and_request_reset(self):
        header = Path(__file__).parents[1] / 'scripts/v13_memory_hook.h'
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'ggml.h').write_text('''#pragma once
#include <cstdint>
enum { GGML_OP_MUL=1, GGML_OP_GET_ROWS=2, GGML_TYPE_I32=3, GGML_TYPE_F32=4 };
struct ggml_tensor { int op=0, type=GGML_TYPE_F32; int64_t ne[2]={2,1}; ggml_tensor *src[2]={nullptr,nullptr}; void *buffer=(void*)1; void *data=nullptr; const char *name=""; };
inline const char *ggml_get_name(ggml_tensor *t) { return t->name; }
inline const char *ggml_op_name(int) { return "stub"; }
inline int64_t ggml_nelements(ggml_tensor *t) { return t->ne[0]*t->ne[1]; }
''')
            (root / 'ggml-backend.h').write_text('#pragma once\ninline bool ggml_backend_buffer_is_host(void*) { return true; }\n')
            (root / 'check.cpp').write_text('''#include "v13_memory_hook.h"
#include <cassert>
int main() {
 Memory m; m.hidden=2; m.n=3; m.ent_w=1; m.topk=3; m.tau=.01f;
 m.mu={0,0}; m.keys={1,0,1,0,1,0}; m.theta={0,0,0};
 m.values={2,0,4,0,0,0}; m.ent={7,8,7}; m.ctx.insert(7);
 Memory plain=m; m.audit=true;
 float x[2]={1,0}, a[2]={10,1}, b[2]={10,1};
 ggml_tensor input; input.op=GGML_OP_MUL; input.name="ffn_norm-0"; input.data=x;
 ggml_tensor out; out.name="l_out-0"; out.data=a;
 // llama initialization may evaluate graphs before the first HTTP prompt.
 hook(&input,false,&m); hook(&out,false,&m);
 assert(m.audit_applied.empty() && m.audit_request==0);
 a[0]=10; a[1]=1; v13_audit_begin(m);
 hook(&input,false,&m); hook(&out,false,&m);
 out.data=b; hook(&input,false,&plain); hook(&out,false,&plain);
 assert(a[0]==b[0] && a[1]==b[1]); assert(a[0]==12);
 assert(m.audit_applied[0]==1 && m.audit_applied[1]==0 && m.audit_applied[2]==0);
 assert(m.audit_guard_blocked[1]==1);
 v13_audit_begin(m); assert(m.audit_applied[0]==0 && m.audit_request==2);
 m.ctx.clear(); m.ctx.insert(8); out.data=a;
 hook(&input,false,&m); hook(&out,false,&m);
 assert(m.audit_applied[0]==0 && m.audit_applied[1]==1);
 assert(m.audit_guard_blocked[0]==1 && m.audit_guard_blocked[2]==1);
 v13_audit_begin(m); m.scale=0; hook(&input,false,&m); hook(&out,false,&m);
 assert(m.audit_applied[1]==0);
}
''')
            compile_result = subprocess.run(['g++', '-std=c++17', '-O2', '-I'+str(root), '-I'+str(header.parent),
                                             str(root/'check.cpp'), '-o', str(root/'check')], capture_output=True, text=True)
            self.assertEqual(compile_result.returncode, 0, compile_result.stderr)
            result = subprocess.run([str(root/'check')], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            windows = result.stderr.split(PREFIX + '{"schema":"v13-native-firing-v1","event":"begin"')
            self.assertEqual(len(windows), 4)
            first = firing_observation(PREFIX + '{"schema":"v13-native-firing-v1","event":"begin"' + windows[1])
            self.assertEqual(first['fired_rows'], [0])


if __name__ == '__main__':
    unittest.main()
