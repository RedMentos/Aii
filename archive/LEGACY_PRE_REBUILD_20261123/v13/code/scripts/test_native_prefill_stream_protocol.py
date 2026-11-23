#!/usr/bin/env python3
"""Focused synthetic streaming protocol guards; never model inference."""
import argparse
import codecs
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
APP=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(APP))
from scripts.native_prefill_stream_client import (STREAM_ABI,StreamingOutputSession,
    validate_token_event,completion_checks,bias_rows,unique_json)
from v13.common import Unavailable,Cancelled,Limits,digest


def protocol_guards():
    checks={};handle={'handle_id':'a'*64}
    event={'event':'TOKEN','sequence':0,'token_id':42,'piece_hex':'4869','text':'Hi',
           'text_encoding':'UTF8_WITH_REPLACEMENT_IF_PARTIAL; piece_hex_is_exact',
           'is_eog':False,'first_position_bias':False,'handle_id':handle['handle_id'],'feature_abi':STREAM_ABI}
    checks['valid_actual_bytes_event']=validate_token_event(event,handle,0,64,False)==b'Hi'
    def rejects(name,call):
        try:call()
        except (Unavailable,ValueError,Cancelled,Limits):checks[name]=True
        else:checks[name]=False
    for name,key,value in [('stale_handle','handle_id','b'*64),('old_abi','feature_abi','V1'),
                           ('bool_token','token_id',True),('large_token','token_id',65536),
                           ('out_of_order','sequence',1),('bool_sequence','sequence',False),
                           ('nonboolean_eog','is_eog',1),('odd_hex','piece_hex','1'),
                           ('invalid_hex','piece_hex','xx'),('oversize_piece','piece_hex','ff'*16385),
                           ('wrong_encoding','text_encoding','unbound'),('unexpected_bias','first_position_bias',True)]:
        row=dict(event);row[key]=value
        rejects(name+'_rejected',lambda row=row:validate_token_event(row,handle,0,64,False))
    row=dict(event,extra=1);rejects('extra_event_field_rejected',lambda:validate_token_event(row,handle,0,64,False))
    rejects('event_after_eos_rejected',lambda:validate_token_event(event,handle,0,64,False,True))
    rejects('token_cap_rejected',lambda:validate_token_event(event,handle,64,64,False))
    row=dict(event,is_eog=True);rejects('eog_text_rejected',lambda:validate_token_event(row,handle,0,64,False))
    decoder=codecs.getincrementaldecoder('utf-8')('replace')
    checks['partial_utf8_reassembled_exactly']=decoder.decode(bytes.fromhex('c3'))=='' and decoder.decode(bytes.fromhex('bc'),final=True)=='ü'
    rejects('duplicate_json_keys_rejected',lambda:unique_json('{"a":1,"a":2}'))
    rejects('nonfinite_json_rejected',lambda:unique_json('{"a":NaN}'))
    rejects('bool_bias_rejected',lambda:bias_rows([[42,True]]))
    rejects('duplicate_bias_rejected',lambda:bias_rows([[42,1.],[42,2.]]))
    rejects('bias_cap_rejected',lambda:bias_rows([[42,12.01]]))
    rejects('bias_rows_cap_rejected',lambda:bias_rows([[i,1.] for i in range(17)]))
    checks['exact_bias_boundaries_valid']=bias_rows([[0,-12.],[65535,12.]])==[[0,-12.],[65535,12.]]
    eos=dict(event,sequence=1,token_id=43,piece_hex='',text='',is_eog=True)
    events=[event,eos]
    raw={'decoded_native_token_ids':[42,43],'continuation':[{'input_token_id':42,'greedy_next_token_id':43,'position':3,'bias_applied':False}],
         'max_tokens':64,'generated_token_count':2,'decoded_native_preview_hex':'4869',
         'decoded_native_preview_sha256':digest(b'Hi'),'resume_decode_calls':1,'unbiased_continuation_steps':1,'stop_reason':'EOS'}
    checks['complete_eos_binding_valid']=all(completion_checks(raw,events,[1,2,3],b'Hi',64,42).values())
    for name,key,value in [('output_bytes','decoded_native_preview_hex','00'),('output_hash','decoded_native_preview_sha256','b'*64),
                           ('token_sequence','decoded_native_token_ids',[42,44]),('extra_decode','resume_decode_calls',2),
                           ('fake_token_limit','stop_reason','TOKEN_LIMIT'),('bool_count','generated_token_count',True)]:
        changed=copy.deepcopy(raw);changed[key]=value
        checks[name+'_rejected']=not all(completion_checks(changed,events,[1,2,3],b'Hi',64,42).values())
    changed=copy.deepcopy(raw);changed['continuation'][0]['bias_applied']=True
    checks['later_position_bias_rejected']=not all(completion_checks(changed,events,[1,2,3],b'Hi',64,42).values())
    changed=copy.deepcopy(raw);changed['continuation'][0]['position']=4
    checks['repositioned_decode_rejected']=not all(completion_checks(changed,events,[1,2,3],b'Hi',64,42).values())
    context={'messages':[],'prompt':'fixture','token_ids':[1],'history_trimmed':False}
    cancel=threading.Event()
    rejects('old_learned_head_loading_refused',lambda:StreamingOutputSession({},context,'unused',cancel,time.monotonic()+30,learned_head='old.npz'))
    rejects('unsupported_output_cap_refused',lambda:StreamingOutputSession({},context,'unused',cancel,time.monotonic()+30,max_tokens=65))
    cancel.set();rejects('cancelled_before_start_refused',lambda:StreamingOutputSession({},context,'unused',cancel,time.monotonic()+30))
    cancel.clear();rejects('expired_before_start_refused',lambda:StreamingOutputSession({},context,'unused',cancel,time.monotonic()-1))
    # This real subprocess is a sleep-only synthetic fixture, not a native model.
    with tempfile.TemporaryDirectory(prefix='v13-stream-protocol-') as directory:
        session=StreamingOutputSession({},context,Path(directory)/'controller',cancel,time.monotonic()+30)
        session.out.mkdir()
        child=subprocess.Popen([sys.executable,'-c','import time; time.sleep(30)'],start_new_session=True)
        session.proc=child
        cancel.set()
        try:session._guard()
        except Cancelled:checks['cancel_guard_observed']=True
        else:checks['cancel_guard_observed']=False
        finally:session.close();cancel.clear()
        checks['cancelled_child_reaped']=session.metrics['process_reaped'] is True and child.poll() is not None
    return {'schema':'V13_STREAM_CLIENT_PROTOCOL_GUARDS_V2','checks':checks,
            'status':'SYNTHETIC_PROTOCOL_GUARDS_PASS' if all(checks.values()) else 'SYNTHETIC_PROTOCOL_GUARDS_FAIL',
            'guard_count':len(checks),'native_inference_performed':False,
            'scope':'Synthetic events and sleep-only process cleanup; no model output/effect proof.'}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output');args=parser.parse_args()
    result=protocol_guards()
    result['client_sha256']=hashlib.sha256((APP/'scripts/native_prefill_stream_client.py').read_bytes()).hexdigest()
    if args.output:
        path=Path(args.output);path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2));return 0 if all(result['checks'].values()) else 1


if __name__=='__main__':raise SystemExit(main())
