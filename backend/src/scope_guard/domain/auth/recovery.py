"""Safe public recovery outcomes, independent of transport and persistence."""


class RecoveryLimited(Exception):
    def __init__(self, retry_after=60):
        self.retry_after = retry_after


class RecoveryUnavailable(Exception):
    pass
