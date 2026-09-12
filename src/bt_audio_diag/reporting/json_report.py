import json
from collections import Counter
from collections.abc import Sequence

from bt_audio_diag.models import DiagnosticFinding, Severity

_SCHEMA_VERSION = 1


def render_json_report(
    findings: Sequence[DiagnosticFinding],
) -> str:
    """Render diagnostic findings as deterministic JSON."""

    normalized_findings = tuple(findings)
    severity_counts = Counter(finding.severity for finding in normalized_findings)

    report: dict[str, object] = {
        "schema_version": _SCHEMA_VERSION,
        "summary": {
            "findings": len(normalized_findings),
            "errors": severity_counts[Severity.ERROR],
            "warnings": severity_counts[Severity.WARNING],
            "informational": severity_counts[Severity.INFO],
        },
        "findings": [_serialize_finding(finding) for finding in normalized_findings],
    }

    return json.dumps(
        report,
        indent=2,
        sort_keys=True,
        ensure_ascii=False,
    )


def _serialize_finding(
    finding: DiagnosticFinding,
) -> dict[str, object]:
    return {
        "code": finding.code,
        "severity": finding.severity.value,
        "summary": finding.summary,
        "evidence": list(finding.evidence),
        "possible_cause": finding.possible_cause,
        "recommended_next_step": finding.recommended_next_step,
    }
