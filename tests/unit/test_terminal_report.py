from textwrap import dedent

from bt_audio_diag.models import DiagnosticFinding, Severity
from bt_audio_diag.reporting import render_terminal_report


def test_empty_report_states_that_no_findings_exist() -> None:
    report = render_terminal_report(())

    assert report == dedent(
        """\
        Bluetooth Audio Diagnostic Report
        =================================
        Findings: 0
        Errors: 0
        Warnings: 0
        Informational: 0

        No diagnostic findings."""
    )


def test_report_renders_complete_finding() -> None:
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
        possible_cause=("PipeWire Bluetooth support may be unavailable."),
        recommended_next_step="Inspect PipeWire state.",
    )

    report = render_terminal_report((finding,))

    assert report == dedent(
        """\
        Bluetooth Audio Diagnostic Report
        =================================
        Findings: 1
        Errors: 0
        Warnings: 1
        Informational: 0

        [WARNING] BT003 - Test Headphones is connected through BlueZ but has no corresponding PipeWire audio device.
          Evidence:
            - BlueZ reports Connected=true.
            - No correlated PipeWire Bluetooth device was found.
          Possible cause: PipeWire Bluetooth support may be unavailable.
          Recommended next step: Inspect PipeWire state."""
    )


def test_report_omits_optional_sections_when_absent() -> None:
    finding = DiagnosticFinding(
        code="TEST001",
        severity=Severity.INFO,
        summary="Informational diagnostic finding.",
        evidence=("Observed test evidence.",),
    )

    report = render_terminal_report((finding,))

    assert "Possible cause:" not in report
    assert "Recommended next step:" not in report
    assert "    - Observed test evidence." in report


def test_report_counts_mixed_severities() -> None:
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

    report = render_terminal_report(findings)

    assert "Findings: 4" in report
    assert "Errors: 1" in report
    assert "Warnings: 2" in report
    assert "Informational: 1" in report


def test_report_preserves_finding_order() -> None:
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

    report = render_terminal_report(
        (
            first,
            second,
        )
    )

    assert report.index("BT002") < report.index("BT006")
