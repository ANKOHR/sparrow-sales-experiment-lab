class SelError(ValueError):
    """Base error for invalid lab operations."""


class MinSampleTooSmallError(SelError):
    pass


class DuplicateExperimentError(SelError):
    pass


class UnknownExperimentError(SelError):
    pass


class InvalidResultError(SelError):
    pass


class DuplicateEntryError(SelError):
    pass


class CorruptStoreError(SelError):
    pass
