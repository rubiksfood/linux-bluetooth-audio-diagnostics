from dataclasses import dataclass
from enum import StrEnum


class Severity(StrEnum):
    """Severity assigned to a diagnostic finding."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class DiagnosticFinding:
    """Evidence-based finding produced by a diagnostic rule."""

    code: str
    severity: Severity
    summary: str
    evidence: tuple[str, ...]
    possible_cause: str | None = None
    recommended_next_step: str | None = None
