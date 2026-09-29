import asyncio
from importlib.metadata import version as distribution_version
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Annotated

import typer

from bt_audio_diag.models import Severity
from bt_audio_diag.reporting import (
    render_inspection_report,
    render_json_report,
    render_terminal_report,
)
from bt_audio_diag.services import (
    BluetoothAudioCorrelationError,
    DiagnosticBundleWriter,
    DiagnosticWorkflow,
    DiagnosticWorkflowResult,
    EvidenceRedactor,
    PlatformSystemProvider,
    SubprocessCommandRunner,
)

_DISTRIBUTION_NAME = "linux-bluetooth-audio-diagnostics"

_EXIT_DIAGNOSTIC_FINDINGS = 1
_EXIT_OPERATIONAL_ERROR = 2


class _CliRuntimeError(RuntimeError):
    """Expected runtime failure that should be presented cleanly to the user."""


app = typer.Typer(
    help="Inspect and diagnose Linux Bluetooth audio environments.",
    no_args_is_help=True,
    add_completion=False,
)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"bt-audio-diag {distribution_version(_DISTRIBUTION_NAME)}")
        raise typer.Exit()


@app.callback()
def root(
    _version: Annotated[
        bool | None,
        typer.Option(
            "--version",
            callback=_version_callback,
            is_eager=True,
            help="Show the application version and exit.",
        ),
    ] = None,
) -> None:
    """Inspect and diagnose Linux Bluetooth audio environments."""


@app.command()
def inspect() -> None:
    """Inspect the current Bluetooth and PipeWire audio state."""

    result = _run_workflow_or_exit()

    typer.echo(
        render_inspection_report(
            result.context,
            result.pipewire_state,
        )
    )


@app.command()
def check(
    json_output: Annotated[
        bool,
        typer.Option(
            "--json",
            help="Render diagnostic findings as JSON.",
        ),
    ] = False,
) -> None:
    """Run Bluetooth audio diagnostics."""

    result = _run_workflow_or_exit()

    if json_output:
        typer.echo(render_json_report(result.findings))
    else:
        typer.echo(render_terminal_report(result.findings))

    if any(finding.severity in (Severity.WARNING, Severity.ERROR) for finding in result.findings):
        raise typer.Exit(code=_EXIT_DIAGNOSTIC_FINDINGS)


@app.command()
def capture(
    output: Annotated[
        Path,
        typer.Option(
            "--output",
            "-o",
            help="Directory to create for the diagnostic bundle.",
        ),
    ],
    redact: Annotated[
        bool,
        typer.Option(
            "--redact",
            help="Redact host and Bluetooth identifiers from textual bundle content.",
        ),
    ] = False,
    include_btmon: Annotated[
        bool,
        typer.Option(
            "--btmon",
            help=("Capture a bounded btmon trace. Raw traces are omitted from redacted bundles."),
        ),
    ] = False,
) -> None:
    """Capture diagnostic state and supporting evidence into a bundle."""

    if output.exists():
        typer.echo(
            f"Error: bundle output already exists: {output}",
            err=True,
        )
        raise typer.Exit(code=_EXIT_OPERATIONAL_ERROR)

    result = _run_workflow_or_exit()

    try:
        _create_capture_bundle(
            output,
            result=result,
            redact=redact,
            include_btmon=include_btmon,
        )
    except OSError as exc:
        typer.echo(
            f"Error: could not create diagnostic bundle: {exc}",
            err=True,
        )
        raise typer.Exit(code=_EXIT_OPERATIONAL_ERROR) from None

    typer.echo(f"Diagnostic bundle written to {output}")


def _create_capture_bundle(
    output: Path,
    *,
    result: DiagnosticWorkflowResult,
    redact: bool,
    include_btmon: bool,
) -> None:
    """Collect supporting evidence and write a diagnostic bundle."""

    from bt_audio_diag.collectors import BtmonCollector, JournalCollector

    command_runner = SubprocessCommandRunner()
    journal_evidence = JournalCollector(command_runner).collect()

    redactor = _build_evidence_redactor(result) if redact else None
    bundle_writer = DiagnosticBundleWriter()

    if not include_btmon:
        bundle_writer.write(
            output,
            context=result.context,
            pipewire_state=result.pipewire_state,
            findings=result.findings,
            journal_evidence=journal_evidence,
            redactor=redactor,
        )
        return

    with TemporaryDirectory(prefix="bt-audio-diag-") as temporary_directory:
        trace_path = Path(temporary_directory) / "capture.btsnoop"

        btmon_evidence = BtmonCollector(command_runner).collect(trace_path)

        bundle_writer.write(
            output,
            context=result.context,
            pipewire_state=result.pipewire_state,
            findings=result.findings,
            journal_evidence=journal_evidence,
            btmon_evidence=btmon_evidence,
            redactor=redactor,
        )


def _build_evidence_redactor(
    result: DiagnosticWorkflowResult,
) -> EvidenceRedactor:
    """Build a redactor from identifiers observed during collection."""

    bluetooth_addresses = {adapter.address for adapter in result.context.adapters}

    bluetooth_addresses.update(
        session.bluetooth_device.address for session in result.context.sessions
    )

    bluetooth_addresses.update(
        device.bluez_address
        for device in result.pipewire_state.devices
        if device.bluez_address is not None
    )

    host_aliases = {
        adapter.alias for adapter in result.context.adapters if adapter.alias is not None
    }

    return EvidenceRedactor(
        hostname=result.context.system_info.hostname,
        host_aliases=host_aliases,
        bluetooth_addresses=bluetooth_addresses,
    )


def _build_diagnostic_workflow() -> DiagnosticWorkflow:
    """Build the production diagnostic workflow for the local Linux host."""

    from bt_audio_diag.collectors import (
        BlueZAdapterCollector,
        BlueZDeviceCollector,
        PipeWireCollector,
        SystemInfoCollector,
    )
    from bt_audio_diag.services.bluez_dbus import DbusFastBlueZObjectManager

    command_runner = SubprocessCommandRunner()
    object_manager = DbusFastBlueZObjectManager()

    return DiagnosticWorkflow(
        system_info_collector=SystemInfoCollector(
            command_runner=command_runner,
            system_provider=PlatformSystemProvider(),
        ),
        bluetooth_adapter_collector=BlueZAdapterCollector(object_manager),
        bluetooth_device_collector=BlueZDeviceCollector(object_manager),
        pipewire_collector=PipeWireCollector(command_runner),
    )


def _run_diagnostic_workflow() -> DiagnosticWorkflowResult:
    """Run the production workflow and normalize expected runtime failures."""

    from bt_audio_diag.collectors import (
        BlueZDataError,
        PipeWireCollectionError,
        PipeWireDataError,
    )
    from bt_audio_diag.services.bluez_dbus import BlueZDBusError

    try:
        return asyncio.run(_build_diagnostic_workflow().run())
    except (
        BlueZDBusError,
        BlueZDataError,
        PipeWireCollectionError,
        PipeWireDataError,
        BluetoothAudioCorrelationError,
    ) as exc:
        raise _CliRuntimeError(str(exc)) from exc


def _run_workflow_or_exit() -> DiagnosticWorkflowResult:
    """Run diagnostics or terminate with a concise operational error."""

    try:
        return _run_diagnostic_workflow()
    except _CliRuntimeError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=_EXIT_OPERATIONAL_ERROR) from None


def main() -> None:
    app()
