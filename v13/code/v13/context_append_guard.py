"""Context OS §8 append reentry provenance: SHADOW plans are not ACTIVE prompts."""


def can_reenter(previous, last_turn, stable, applied):
    """Allow only a same-mode append seed with matching executed turn context.

    A stable_prefix prompt may seed append-only on the next turn when it was
    actually planned in an append-only-capable configuration; arbitrary legacy
    or stable_prefix prompts without append_seed never qualify.
    """
    if not isinstance(previous, dict) or type(applied) is not bool:
        return False
    if previous.get('applied') is not applied or previous.get('append_seed') is not True:
        return False
    if previous.get('layout') not in ('append_only', 'stable_prefix'):
        return False
    if not isinstance(last_turn, tuple) or len(last_turn) != 2:
        return False
    eid, messages = last_turn
    if not isinstance(messages, list) or not messages or not isinstance(messages[-1], dict) or messages[-1].get('role') != 'assistant':
        return False
    if previous.get('event_id') != eid or previous.get('system') != stable:
        return False
    prompt = previous.get('messages')
    return isinstance(prompt, list) and bool(prompt) and isinstance(prompt[-1], dict) and prompt[-1].get('role') == 'user'
