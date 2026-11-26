"""Deployment content policy, independent of identity and execution."""
from dataclasses import dataclass


class ContentReadOnly(PermissionError):
    def __init__(self):
        super().__init__("Curated content is read-only in hosted mode.")


@dataclass(frozen=True)
class ContentPolicy:
    profile: str = "local"

    def __post_init__(self):
        if self.profile not in {"local", "hosted"}:
            raise ValueError("profile must be local or hosted")

    @property
    def read_only(self):
        return self.profile == "hosted"

    def require_writable(self):
        if self.read_only:
            raise ContentReadOnly()
