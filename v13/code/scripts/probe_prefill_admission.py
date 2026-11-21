"""Offline native-context admission reproducer. Never reads private chat logs.

Run: PYTHONPATH=v13/code python v13/code/scripts/probe_prefill_admission.py
This uses synthetic prompts only and never claims Redmi performance.
"""
import json
from v13.prefill_admission import admit

def main():
    for size in (40,120,300,630,1200):
        messages=[{'role':'system','content':'You are V13. Source references required.'},
                  {'role':'user','content':'x'*size}]
        a=admit(messages,prompt_cap=320)
        print(json.dumps({'synthetic_user_chars':size,'accepted':a.accepted,
                          'estimated_tokens':a.estimated_tokens,
                          'reason':a.reason,'dropped_history':a.dropped_history,
                          'evidence':'SYNTHETIC_ONLY','android_verified':False}))
if __name__=='__main__':
    main()
