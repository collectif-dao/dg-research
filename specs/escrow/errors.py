class Errors:
    class Error(Exception):
        pass

    class UnexpectedUnstETHId(Error):
        pass

    class InvalidHintsLength(Error):
        pass

    class ClaimingIsFinished(Error):
        pass

    class InvalidBatchSize(Error):
        pass

    class WithdrawalsTimelockNotPassed(Error):
        pass

    class InvalidETHSender(Error):
        pass

    class NotDualGovernance(Error):
        pass

    class MasterCopyCallForbidden(Error):
        pass

    class InvalidState(Error):
        pass

    class RageQuitExtraTimelockNotStarted(Error):
        pass
