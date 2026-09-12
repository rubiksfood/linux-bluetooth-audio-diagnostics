from collections.abc import Sequence

from bt_audio_diag.diagnostics.context import DiagnosticContext
from bt_audio_diag.diagnostics.rules import (
    DEFAULT_RULES,
    DiagnosticRule,
)
from bt_audio_diag.models import DiagnosticFinding


class DiagnosticEngine:
    """Evaluate diagnostic rules against normalized system evidence."""

    def __init__(
        self,
        rules: Sequence[DiagnosticRule] | None = None,
    ) -> None:
        self._rules = tuple(rules) if rules is not None else DEFAULT_RULES

    def evaluate(
        self,
        context: DiagnosticContext,
    ) -> tuple[DiagnosticFinding, ...]:
        findings: list[DiagnosticFinding] = []

        for rule in self._rules:
            findings.extend(rule(context))

        return tuple(findings)
