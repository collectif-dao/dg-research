class Errors:
    class Error(Exception):
        pass

    class ZeroAmountOfETH(Error):
        pass

    class ZeroShareRate(Error):
        pass

    class ZeroTimestamp(Error):
        pass

    class TooMuchEtherToFinalize(Error):
        pass

    class NotOwner(Error):
        pass

    class InvalidRequestId(Error):
        pass

    class InvalidRequestIdRange(Error):
        pass

    class InvalidState(Error):
        pass

    class BatchesAreNotSorted(Error):
        pass

    class EmptyBatches(Error):
        pass

    class RequestNotFoundOrNotFinalized(Error):
        pass

    class NotEnoughEther(Error):
        pass

    class RequestAlreadyClaimed(Error):
        pass

    class InvalidHint(Error):
        pass

    class CantSendValueRecipientMayHaveReverted(Error):
        pass

    class AdminZeroAddress(Error):
        pass

    class RequestAmountTooSmall(Error):
        pass

    class RequestAmountTooLarge(Error):
        pass

    class InvalidReportTimestamp(Error):
        pass

    class RequestIdsNotSorted(Error):
        pass

    class ZeroRecipient(Error):
        pass

    class ArraysLengthMismatch(Error):
        pass
