"""Source-pinned post-answer B1/B2 scheduling candidate.

This generates bytes for isolated review and never mutates or activates the
frozen Runtime. A later post-answer offer cannot affect the completed answer;
neither model quality nor native or Android behaviour is established here.
"""

from hashlib import sha256
from pathlib import Path


SOURCE_SHA256 = {
    # Exact release, reviewed World builder, and reviewed Termux builder output.
    'a533660776f7e2b1697e9793a3abb811eb6d1e7191ec6fe0af523d58efa0ce38',
    '08c1ef961b0c7316da8c1c8265feb71a7a4acf009018788e7accb81eecb2337d',
    'b4bd2eb39cffd62f04ef8932e57223b7b1adae08039509fc1457e3b82f2f15bc',
    '85a2f94e642a787173fcc973270516a39bef4cb2145c3a19a638cb71975f9235',
    'a217e50b6a821675e2b799d1d4de8c957708aa04aabc95a2e34da9b24c0c215b',
    '0196f880576a1f1f95840ef12eb0b35928f3f442715f3d86f17dc38c4c22305d',
    'd3fac6289d2898806d0126a462b8224b1f945fdf0bd87b7cc5715206974334c2',
}

REPLACEMENTS = (
    (
        "            wake_route=effort_plan['wake'];wake_source='EFFORT_POLICY'\n",
        "            wake_route=effort_plan['wake'];wake_source='EFFORT_POLICY';deferred_wake_route=None\n",
    ),
    (
        "                    if fired:wake_route,wake_source='none','REFLEX_IMMINENT_TIMEOUT';meta['reflex']=meta.get('reflex',[])+[fired]\n",
        "                    if fired:\n"
        "                        deferred_wake_route=wake_route\n"
        "                        wake_route,wake_source='none','REFLEX_IMMINENT_TIMEOUT';meta['reflex']=meta.get('reflex',[])+[fired]\n",
    ),
    (
        "            reenter=halt=None\n",
        "            reenter=halt=None;foreground_body_attempts=set()\n",
    ),
    (
        "                def ask(role,focus=None,use_peer=True):\n",
        "                def ask(role,focus=None,use_peer=True):\n"
        "                    foreground_body_attempts.add(role)\n",
    ),
    (
        "        if status=='FINAL' and not direct and self.cfg['observer_mode']=='background' and not offers and not (wake_decision and wake_decision['learned'] and wake_decision['action']=='none') and self.jobs.empty() and not self.stop.is_set() and rmodes.policy(self.guard.mode)['background_observers']:\n",
        "        if status=='FINAL' and not direct and self.cfg['observer_mode']=='background' and self.jobs.empty() and not self.paused and not self.stop.is_set() and rmodes.policy(self.guard.mode)['background_observers']:\n",
    ),
    (
        "            background_roles={'none':[],'detail':['B1_DETAIL'],'gist':['B2_GIST'],'both':['B1_DETAIL','B2_GIST']}[wake_decision['action']] if wake_decision and wake_decision['learned'] else ['B1_DETAIL','B2_GIST']\n",
        "            # Only the *resolved* wake is allowed: it already reflects\n"
        "            # explicit one-body effort and learned/effort/resource caps.\n"
        "            background_wake=deferred_wake_route if wake_source=='REFLEX_IMMINENT_TIMEOUT' and deferred_wake_route is not None else wake_route\n"
        "            background_roles=effort.roles(background_wake)\n",
    ),
    (
        "            background_roles=rmodes.cap_roles(background_roles,self.guard.mode,'background_observers')  # §97.2 YELLOW: one post-commit body\n",
        "            delivered={p.get('role') for p in offers if isinstance(p,dict)}\n"
        "            late_role=(meta.get('late_watch') or {}).get('offered')\n"
        "            background_roles=[role for role in background_roles if role not in delivered and role!=late_role]\n"
        "            # If the first foreground attempt exhausted its budget, give\n"
        "            # the as-yet unattempted eligible body the first opportunity.\n"
        "            background_roles.sort(key=lambda role:role in foreground_body_attempts)\n"
        "            background_attempts=0\n",
    ),
    (
        "                if role==(meta.get('late_watch') or {}).get('offered'):continue  # WP-U3: this body already ran during the output\n"
        "                if self.guard.update(self.resources())!='NORMAL' or not rmodes.policy(self.guard.mode)['background_observers']:break\n"
        "                if not self.jobs.empty() or self.cancel_event.is_set():break\n",
        "                # Re-evaluate the live cap after *each* attempt. A switch\n"
        "                # from GREEN to YELLOW stops after one, including failure.\n"
        "                if self.guard.update(self.resources())!='NORMAL':break\n"
        "                if background_attempts>=rmodes.policy(self.guard.mode)['background_observers']:break\n"
        "                if self.paused or self.stop.is_set() or self.cancel_event.is_set() or not self.jobs.empty():break\n"
        "                pending=self.store.queue_stats()\n"
        "                if pending['paused'] or pending['count']:break\n"
        "                background_attempts+=1\n",
    ),
    (
        "                except Exception as exc:self.store.log('background_observer_end',eid,{'error':str(exc)[:200]});break\n",
        "                except Cancelled:break\n"
        "                except Exception as exc:\n"
        "                    # A failed peer is not a message and must not starve\n"
        "                    # a different eligible body. Never publish exception text.\n"
        "                    peer=None\n"
        "                    self.store.log('background_observer_end',eid,{'role':role,'error':type(exc).__name__})\n",
    ),
)


def apply_source(raw):
    """Return reviewed replacement Runtime bytes for an exact known source."""
    if type(raw) is not bytes:
        raise TypeError('postcommit observer input must be bytes')
    source_hash = sha256(raw).hexdigest()
    if source_hash not in SOURCE_SHA256:
        raise ValueError('postcommit observer runtime hash mismatch')
    for index, (before, after) in enumerate(REPLACEMENTS):
        # Current fair-budget Runtime sources removed the older "and not offers"
        # guard before this overlay was composed. Accept that exact known variant
        # as well; the final replacement still applies only to a pinned source.
        if index == 4 and raw.count(before.encode('utf-8')) == 0 and raw.count(after.encode('utf-8')) == 0:
            before = (
                "        if status=='FINAL' and not direct and self.cfg['observer_mode']=='background' and not (wake_decision and wake_decision['learned'] and wake_decision['action']=='none') and self.jobs.empty() and not self.stop.is_set() and rmodes.policy(self.guard.mode)['background_observers']:\n"
            )
        # The reviewed #1990 stage already adds per-role deadline support.
        # Preserve that signature while adding foreground-attempt tracking.
        if (source_hash in ('d3fac6289d2898806d0126a462b8224b1f945fdf0bd87b7cc5715206974334c2',
                             '08c1ef961b0c7316da8c1c8265feb71a7a4acf009018788e7accb81eecb2337d',
                             'b4bd2eb39cffd62f04ef8932e57223b7b1adae08039509fc1457e3b82f2f15bc',
                             '85a2f94e642a787173fcc973270516a39bef4cb2145c3a19a638cb71975f9235')
                and before == "                def ask(role,focus=None,use_peer=True):\n"):
            before = before.replace('use_peer=True)', 'use_peer=True,role_end=None)')
            after = after.replace('use_peer=True)', 'use_peer=True,role_end=None)')
        old, new = before.encode('utf-8'), after.encode('utf-8')
        old_count, new_count = raw.count(old), raw.count(new)
        if old_count == 1 and new_count == 0:
            raw = raw.replace(old, new, 1)
        elif old_count == 0 and new_count == 1:
            # The exact source hash is allowlisted above; this replacement is
            # already present in the staged Runtime and must not be duplicated.
            pass
        else:
            raise ValueError('postcommit observer anchor mismatch: replacement ' + str(index))
    compile(raw, 'v13/runtime.py', 'exec')
    return raw


def build_sources(code_dir):
    root = Path(code_dir)
    source = root / 'v13/runtime.py'
    if (root / 'v13').is_symlink() or source.is_symlink() or not source.is_file():
        raise ValueError('postcommit observer source path is unsafe')
    return {'v13/runtime.py': apply_source(source.read_bytes())}
