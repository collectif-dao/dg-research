class Errors:
    class Error(Exception):
        pass

    class NotTie(Error):
        pass

    class AlreadyInitialized(Error):
        pass

    class ProposalsCreationSuspended(Error):
        pass

    class ProposalsAdoptionSuspended(Error):
        pass

    class ResealIsNotAllowedInNormalState(Error):
        pass
