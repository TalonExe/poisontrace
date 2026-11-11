"""Application errors mapped by outer interfaces."""


class ScenarioNotFound(KeyError):
    """Raised when a run references an unknown scenario ID."""
