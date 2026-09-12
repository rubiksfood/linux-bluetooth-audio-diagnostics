from collections.abc import Sequence

from bt_audio_diag.models import DiagnosticFinding, Severity

_TITLE = "Bluetooth Audio Diagnostic Report"
_TITLE_UNDERLINE = "=" * len(_TITLE)


def render_terminal_report(
    findings: Sequence[DiagnosticFinding],
) -> str:
    """Render diagnostic findings as deterministic human-readable text."""

    normalized_findings = tuple(findings)

    lines = [
        _TITLE,
        _TITLE_UNDERLINE,
        f"Findings: {len(normalized_findings)}",
        f"Errors: {_count_findings_by_severity(normalized_findings, Severity.ERROR)}",
        f"Warnings: {_count_findings_by_severity(normalized_findings, Severity.WARNING)}",
        f"Informational: {_count_findings_by_severity(normalized_findings, Severity.INFO)}",
    ]

    if not normalized_findings:
        lines.extend(
            [
                "",
                "No diagnostic findings.",
            ]
        )
        return "\n".join(lines)

    for finding in normalized_findings:
        lines.extend(
            [
                "",
                _finding_header(finding),
                "  Evidence:",
            ]
        )

        if finding.evidence:
            lines.extend(f"    - {item}" for item in finding.evidence)
        else:
            lines.append("    - No evidence recorded.")

        if finding.possible_cause is not None:
            lines.append(f"  Possible cause: {finding.possible_cause}")

        if finding.recommended_next_step is not None:
            lines.append(f"  Recommended next step: {finding.recommended_next_step}")

    return "\n".join(lines)


def _count_findings_by_severity(
    findings: Sequence[DiagnosticFinding],
    severity: Severity,
) -> int:
    return sum(finding.severity is severity for finding in findings)


def _finding_header(
    finding: DiagnosticFinding,
) -> str:
    return f"[{finding.severity.name}] {finding.code} - {finding.summary}"
