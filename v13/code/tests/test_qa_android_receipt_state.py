"""QA regression: transport-reported success must not be confused with verified success."""
from v13.android_action_audit import build_audited_dispatcher
from v13.android_capability_contract import ActionOutcome, Capability, CapabilityRegistry, OutcomeStatus


class ForgedTransport:
    def execute(self, request):
        return ActionOutcome(request.request_id, request.capability,
                             OutcomeStatus.SUCCESS, "forged-receipt", 2.0)


class RejectAll:
    def verify(self, request, outcome):
        return False


def test_rejected_receipt_is_not_journaled_as_success(tmp_path):
    dispatcher, journal = build_audited_dispatcher(
        CapabilityRegistry({Capability.LAUNCH_APP: True}),
        tmp_path / "audit.sqlite", ForgedTransport(), RejectAll())
    try:
        result = dispatcher.dispatch(Capability.LAUNCH_APP, "com.example", dry_run=False)
        assert result.outcome.status == OutcomeStatus.FAILED
        # This is the security-sensitive invariant: an unauthenticated native
        # success report must not be treated as a confirmed successful action.
        assert journal.attempts()[0]["state"] != "REPORTED_SUCCESS"
    finally:
        journal.close()
