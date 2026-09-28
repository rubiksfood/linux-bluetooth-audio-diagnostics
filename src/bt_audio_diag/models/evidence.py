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


@dataclass(frozen=True, slots=True)
class BtmonEvidence:
    """Metadata for a bounded btmon HCI trace capture."""

    output_path: str
    command: tuple[str, ...]
    duration_seconds: int
    controller: str | None
    returncode: int | None
    stderr: str
    error: str | None = None

    @property
    def succeeded(self) -> bool:
        """Whether btmon capture completed successfully."""

        return self.returncode in {0, 124} and self.error is None

    @property
    def completed_by_timeout(self) -> bool:
        """Whether the configured capture duration ended the capture."""

        return self.returncode == 124
