import json

from bt_audio_diag.models import DiagnosticFinding, Severity
from bt_audio_diag.reporting import render_json_report


def test_empty_json_report_contains_zero_summary() -> None:
    report = render_json_report(())
    payload = json.loads(report)

    assert payload == {
        "schema_version": 1,
        "summary": {
            "findings": 0,
            "errors": 0,
            "warnings": 0,
            "informational": 0,
        },
        "findings": [],
    }


def test_json_report_serializes_complete_finding() -> None:
    finding = DiagnosticFinding(
        code="BT003",
        severity=Severity.WARNING,
        summary=(
            "Test Headphones is connected through BlueZ "
            "but has no corresponding PipeWire audio device."
        ),
        evidence=(
            "BlueZ reports Connected=true.",
            "No correlated PipeWire Bluetooth device was found.",
        ),
        possible_cause="PipeWire Bluetooth support may be unavailable.",
        recommended_next_step="Inspect PipeWire state.",
    )

    payload = json.loads(render_json_report((finding,)))

    assert payload == {
        "schema_version": 1,
        "summary": {
            "findings": 1,
            "errors": 0,
            "warnings": 1,
            "informational": 0,
        },
        "findings": [
            {
                "code": "BT003",
                "severity": "warning",
                "summary": (
                    "Test Headphones is connected through BlueZ "
                    "but has no corresponding PipeWire audio device."
                ),
                "evidence": [
                    "BlueZ reports Connected=true.",
                    "No correlated PipeWire Bluetooth device was found.",
                ],
                "possible_cause": ("PipeWire Bluetooth support may be unavailable."),
                "recommended_next_step": "Inspect PipeWire state.",
            }
        ],
    }


def test_json_report_represents_missing_optional_values_as_null() -> None:
    finding = DiagnosticFinding(
        code="TEST001",
        severity=Severity.INFO,
        summary="Informational finding.",
        evidence=(),
    )

    payload = json.loads(render_json_report((finding,)))

    serialized_finding = payload["findings"][0]

    assert serialized_finding["possible_cause"] is None
    assert serialized_finding["recommended_next_step"] is None
    assert serialized_finding["evidence"] == []


def test_json_report_counts_mixed_severities() -> None:
    findings = (
        DiagnosticFinding(
            code="TEST001",
            severity=Severity.ERROR,
            summary="Error finding.",
            evidence=(),
        ),
        DiagnosticFinding(
            code="TEST002",
            severity=Severity.WARNING,
            summary="Warning finding.",
            evidence=(),
        ),
        DiagnosticFinding(
            code="TEST003",
            severity=Severity.INFO,
            summary="Information finding.",
            evidence=(),
        ),
        DiagnosticFinding(
            code="TEST004",
            severity=Severity.WARNING,
            summary="Second warning finding.",
            evidence=(),
        ),
    )

    payload = json.loads(render_json_report(findings))

    assert payload["summary"] == {
        "findings": 4,
        "errors": 1,
        "warnings": 2,
        "informational": 1,
    }


def test_json_report_preserves_finding_order() -> None:
    first = DiagnosticFinding(
        code="BT002",
        severity=Severity.WARNING,
        summary="First finding.",
        evidence=(),
    )
    second = DiagnosticFinding(
        code="BT006",
        severity=Severity.ERROR,
        summary="Second finding.",
        evidence=(),
    )

    payload = json.loads(
        render_json_report(
            (
                first,
                second,
            )
        )
    )

    assert [finding["code"] for finding in payload["findings"]] == [
        "BT002",
        "BT006",
    ]


def test_json_report_is_deterministic() -> None:
    finding = DiagnosticFinding(
        code="TEST001",
        severity=Severity.INFO,
        summary="Deterministic finding.",
        evidence=("Observed evidence.",),
    )

    first_report = render_json_report((finding,))
    second_report = render_json_report((finding,))

    assert first_report == second_report


def test_json_report_preserves_unicode_text() -> None:
    finding = DiagnosticFinding(
        code="TEST001",
        severity=Severity.INFO,
        summary="Kopfhörer verbunden.",
        evidence=(),
    )

    report = render_json_report((finding,))

    assert "Kopfhörer verbunden." in report
    assert "\\u00f6" not in report
