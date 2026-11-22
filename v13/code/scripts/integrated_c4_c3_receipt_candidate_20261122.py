"""Core-owned staged receipt for source-bound C4 context delivered to C3.

This additive overlay runs after the pinned base/observer/audio composition. It
does not modify the historical source module or claim native semantic use.
"""


def apply_sources(code_dir, sources):
    result = dict(sources)
    raw = result.get("v13/cognition.py")
    if not isinstance(raw, bytes):
        raise ValueError("C4 receipt requires the composed Cognition source")

    anchor = b"""        return rendered
    def communicate(self,offer,receiver,fast=None):
"""
    replacement = b"""        # A privacy-safe receipt marks the exact source-bound selection at the
        # C4 -> C3 context boundary; it is not evidence of native semantic use.
        if rendered:
            try:
                self.s.log('c4_offer_context_ready',e['event_id'],{
                    'role':'C3_LANGUAGE',
                    'selected_offer_ids':[x['offer_packet_id'] for x in rendered],
                    'count':len(rendered),
                    'status':'PASS',
                })
            except Exception:
                # Telemetry must never turn a valid answer into a failed turn.
                pass
        return rendered
    def communicate(self,offer,receiver,fast=None):
"""
    if raw.count(anchor) != 1:
        raise ValueError("C4 receipt analyst_context anchor changed")
    patched = raw.replace(anchor, replacement, 1)
    compile(patched, "v13/cognition.py", "exec")
    result["v13/cognition.py"] = patched
    return result
