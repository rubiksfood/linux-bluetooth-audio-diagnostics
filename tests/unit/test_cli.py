import re
from importlib.metadata import version as distribution_version
from pathlib import Path

import pytest
from typer.testing import CliRunner

from bt_audio_diag import cli
from bt_audio_diag.diagnostics import DiagnosticContext
from bt_audio_diag.models import (
    BluetoothAdapter,
    DiagnosticFinding,
    PipeWireState,
    Severity,
    SystemInfo,
)
from bt_audio_diag.services import DiagnosticWorkflowResult

runner = CliRunner()

ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")


def _workflow_result(
    *,
    findings: tuple[DiagnosticFinding, ...] = (),
) -> DiagnosticWorkflowResult:
    system_info = SystemInfo(
        distribution="Test Linux",
        distribution_version="1",
        kernel="6.0.0",
        architecture="x86_64",
        python_version="3.13.0",
        tool_version="0.1.0.dev0",
        hostname="test-host",
    )

    adapter = BluetoothAdapter(
        object_path="/org/bluez/hci0",
        address="00:11:22:33:44:55",
        alias="Test Adapter",
        powered=True,
        discoverable=False,
        pairable=True,
    )

    context = DiagnosticContext(
        system_info=system_info,
        adapters=(adapter,),
        sessions=(),
    )

    return DiagnosticWorkflowResult(
        context=context,
        pipewire_state=PipeWireState(),
        findings=findings,
    )


def _warning_finding() -> DiagnosticFinding:
    return DiagnosticFinding(
        code="BT002",
        severity=Severity.WARNING,
        summary="Test Bluetooth device is paired but not connected.",
        evidence=("Test evidence.",),
        possible_cause="Test possible cause.",
        recommended_next_step="Test recommended next step.",
    )


def test_help_option() -> None:
    result = runner.invoke(cli.app, ["--help"])
    output = ANSI_ESCAPE_RE.sub("", result.stdout)

    assert result.exit_code == 0
    assert "Inspect and diagnose Linux Bluetooth audio environments." in output
    assert "--version" in output


def test_version_option() -> None:
    result = runner.invoke(cli.app, ["--version"])

    expected_version = distribution_version("linux-bluetooth-audio-diagnostics")

    assert result.exit_code == 0
    assert result.stdout == f"bt-audio-diag {expected_version}\n"


def test_inspect_renders_collected_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workflow_result = _workflow_result()

    monkeypatch.setattr(
        cli,
        "_run_diagnostic_workflow",
        lambda: workflow_result,
    )

    result = runner.invoke(cli.app, ["inspect"])

    assert result.exit_code == 0
    assert "Bluetooth Audio Inspection" in result.stdout
    assert "Test Linux 1" in result.stdout
    assert "Test Adapter" in result.stdout
    assert "Bluetooth adapters (1)" in result.stdout
    assert "Bluetooth audio sessions (0)" in result.stdout


def test_check_with_no_findings_exits_successfully(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workflow_result = _workflow_result()

    monkeypatch.setattr(
        cli,
        "_run_diagnostic_workflow",
        lambda: workflow_result,
    )

    result = runner.invoke(cli.app, ["check"])

    assert result.exit_code == 0
    assert "Bluetooth Audio Diagnostic Report" in result.stdout
    assert "Findings: 0" in result.stdout
    assert "No diagnostic findings." in result.stdout


def test_check_json_with_warning_returns_diagnostic_exit_code(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workflow_result = _workflow_result(
        findings=(_warning_finding(),),
    )

    monkeypatch.setattr(
        cli,
        "_run_diagnostic_workflow",
        lambda: workflow_result,
    )

    result = runner.invoke(
        cli.app,
        [
            "check",
            "--json",
        ],
    )

    assert result.exit_code == 1
    assert '"code": "BT002"' in result.stdout
    assert '"severity": "warning"' in result.stdout
    assert '"warnings": 1' in result.stdout


def test_check_reports_operational_failure_without_traceback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_workflow() -> DiagnosticWorkflowResult:
        raise cli._CliRuntimeError("BlueZ is unavailable")

    monkeypatch.setattr(
        cli,
        "_run_diagnostic_workflow",
        fail_workflow,
    )

    result = runner.invoke(cli.app, ["check"])

    assert result.exit_code == 2
    assert "Error: BlueZ is unavailable" in result.output
    assert "Traceback" not in result.output


def test_capture_forwards_output_and_privacy_options(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    workflow_result = _workflow_result()
    output_directory = tmp_path / "diagnostic-bundle"

    captured_output: Path | None = None
    captured_result: DiagnosticWorkflowResult | None = None
    captured_redact: bool | None = None
    captured_include_btmon: bool | None = None

    def fake_create_capture_bundle(
        output: Path,
        *,
        result: DiagnosticWorkflowResult,
        redact: bool,
        include_btmon: bool,
    ) -> None:
        nonlocal captured_output
        nonlocal captured_result
        nonlocal captured_redact
        nonlocal captured_include_btmon

        captured_output = output
        captured_result = result
        captured_redact = redact
        captured_include_btmon = include_btmon

    monkeypatch.setattr(
        cli,
        "_run_diagnostic_workflow",
        lambda: workflow_result,
    )
    monkeypatch.setattr(
        cli,
        "_create_capture_bundle",
        fake_create_capture_bundle,
    )

    result = runner.invoke(
        cli.app,
        [
            "capture",
            "--output",
            str(output_directory),
            "--redact",
            "--btmon",
        ],
    )

    assert result.exit_code == 0
    assert captured_output == output_directory
    assert captured_result is workflow_result
    assert captured_redact is True
    assert captured_include_btmon is True
    assert f"Diagnostic bundle written to {output_directory}" in result.stdout


def test_capture_rejects_existing_output_directory(
    tmp_path: Path,
) -> None:
    output_directory = tmp_path / "existing-bundle"
    output_directory.mkdir()

    result = runner.invoke(
        cli.app,
        [
            "capture",
            "--output",
            str(output_directory),
        ],
    )

    assert result.exit_code == 2
    assert "bundle output already exists" in result.output
