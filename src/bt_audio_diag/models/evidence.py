from dataclasses import dataclass
from enum import StrEnum


class JournalScope(StrEnum):
    """systemd journal scope."""

    SYSTEM = "system"
    USER = "user"


@dataclass(frozen=True, slots=True)
class JournalEvidence:
    """Captured journal output for one systemd service."""

    service_name: str
    scope: JournalScope
    command: tuple[str, ...]
    stdout: str
    stderr: str
    returncode: int | None
    error: str | None = None

    @property
    def succeeded(self) -> bool:
        """Whether journal collection completed successfully."""

        return self.returncode == 0 and self.error is None
