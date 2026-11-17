"""Application errors mapped by outer interfaces."""


class ScenarioNotFound(KeyError):
    """Raised when a run references an unknown scenario ID."""


class InvestigationCallLimit(Exception):
    """The bounded investigation exhausted its call budget."""


class InvestigationOutputLimit(Exception):
    """Output exceeds the configured investigation bound."""


class EvidenceToolError(Exception):
    """The remote tool reported an error. Raw diagnostics stay outside traces."""
