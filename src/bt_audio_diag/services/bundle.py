import json
import shutil
from collections.abc import Sequence
from pathlib import Path

from bt_audio_diag.diagnostics import DiagnosticContext
from bt_audio_diag.models import (
    AudioNode,
    BluetoothAdapter,
    BluetoothAudioSession,
    BluetoothDevice,
    BtmonEvidence,
    DiagnosticFinding,
    JournalEvidence,
    PipeWireDevice,
    PipeWireState,
    ServiceStatus,
    SystemInfo,
)
from bt_audio_diag.reporting import (
    render_json_report,
    render_terminal_report,
)
from bt_audio_diag.services.redaction import EvidenceRedactor

_BUNDLE_SCHEMA_VERSION = 1


class DiagnosticBundleWriter:
    """Write collected diagnostic state and evidence to a bundle directory."""

    def write(
        self,
        output_directory: Path,
        *,
        context: DiagnosticContext,
        pipewire_state: PipeWireState,
        findings: Sequence[DiagnosticFinding],
        journal_evidence: Sequence[JournalEvidence] = (),
        btmon_evidence: BtmonEvidence | None = None,
        redactor: EvidenceRedactor | None = None,
    ) -> None:
        """Write a structured diagnostic capture bundle."""

        if output_directory.exists():
            raise FileExistsError(f"Bundle output already exists: {output_directory}")

        state_directory = output_directory / "state"
        reports_directory = output_directory / "reports"
        journal_directory = output_directory / "evidence" / "journal"
        btmon_directory = output_directory / "evidence" / "btmon"

        state_directory.mkdir(parents=True)
        reports_directory.mkdir(parents=True)
        journal_directory.mkdir(parents=True)

        _write_json(
            state_directory / "system.json",
            _serialize_system_info(context.system_info),
            redactor=redactor,
        )
        _write_json(
            state_directory / "bluez.json",
            _serialize_bluez_state(context),
            redactor=redactor,
        )
        _write_json(
            state_directory / "pipewire.json",
            _serialize_pipewire_state(pipewire_state),
            redactor=redactor,
        )
        _write_json(
            state_directory / "correlation.json",
            _serialize_sessions(context.sessions),
            redactor=redactor,
        )

        normalized_findings = tuple(findings)

        _write_text(
            reports_directory / "diagnostic.txt",
            render_terminal_report(normalized_findings),
            redactor=redactor,
        )
        _write_text(
            reports_directory / "diagnostic.json",
            render_json_report(normalized_findings),
            redactor=redactor,
        )

        _write_journal_evidence(
            journal_directory,
            journal_evidence,
            redactor=redactor,
        )

        btmon_trace_included = False

        if btmon_evidence is not None:
            btmon_directory.mkdir(parents=True)

            btmon_trace_included = _write_btmon_evidence(
                btmon_directory,
                btmon_evidence,
                redactor=redactor,
            )

        _write_json(
            output_directory / "manifest.json",
            {
                "bundle_schema_version": _BUNDLE_SCHEMA_VERSION,
                "redacted": redactor is not None,
                "btmon_trace_included": btmon_trace_included,
            },
            redactor=redactor,
        )


def _write_journal_evidence(
    directory: Path,
    evidence_items: Sequence[JournalEvidence],
    *,
    redactor: EvidenceRedactor | None,
) -> None:
    metadata: list[dict[str, object]] = []

    for evidence in evidence_items:
        filename = _journal_filename(evidence.service_name)
        log_path = directory / filename

        _write_text(
            log_path,
            evidence.stdout,
            redactor=redactor,
        )

        metadata.append(
            {
                "service_name": evidence.service_name,
                "scope": evidence.scope.value,
                "command": list(evidence.command),
                "returncode": evidence.returncode,
                "stderr": evidence.stderr,
                "error": evidence.error,
                "succeeded": evidence.succeeded,
                "log_file": filename,
            }
        )

    _write_json(
        directory / "metadata.json",
        {
            "journals": metadata,
        },
        redactor=redactor,
    )


def _write_btmon_evidence(
    directory: Path,
    evidence: BtmonEvidence,
    *,
    redactor: EvidenceRedactor | None,
) -> bool:
    source_trace = Path(evidence.output_path)

    trace_included = False
    omission_reason: str | None = None

    if redactor is not None:
        omission_reason = (
            "Raw btmon traces are omitted from redacted bundles "
            "because the binary trace may contain sensitive identifiers."
        )
    elif source_trace.is_file():
        shutil.copy2(
            source_trace,
            directory / "capture.btsnoop",
        )
        trace_included = True
    else:
        omission_reason = "The btmon trace file was not available."

    _write_json(
        directory / "metadata.json",
        {
            "output_path": evidence.output_path,
            "command": list(evidence.command),
            "duration_seconds": evidence.duration_seconds,
            "controller": evidence.controller,
            "returncode": evidence.returncode,
            "stderr": evidence.stderr,
            "error": evidence.error,
            "succeeded": evidence.succeeded,
            "completed_by_timeout": evidence.completed_by_timeout,
            "trace_included": trace_included,
            "trace_omitted_reason": omission_reason,
        },
        redactor=redactor,
    )

    return trace_included


def _serialize_system_info(
    system_info: SystemInfo,
) -> dict[str, object]:
    return {
        "distribution": system_info.distribution,
        "distribution_version": system_info.distribution_version,
        "kernel": system_info.kernel,
        "architecture": system_info.architecture,
        "python_version": system_info.python_version,
        "tool_version": system_info.tool_version,
        "bluez_version": system_info.bluez_version,
        "pipewire_version": system_info.pipewire_version,
        "wireplumber_version": system_info.wireplumber_version,
        "hostname": system_info.hostname,
        "services": [_serialize_service_status(service) for service in system_info.services],
    }


def _serialize_service_status(
    service: ServiceStatus,
) -> dict[str, object]:
    return {
        "name": service.name,
        "running": service.running,
    }


def _serialize_bluez_state(
    context: DiagnosticContext,
) -> dict[str, object]:
    devices = sorted(
        (session.bluetooth_device for session in context.sessions),
        key=lambda device: device.object_path,
    )

    return {
        "adapters": [
            _serialize_adapter(adapter)
            for adapter in sorted(
                context.adapters,
                key=lambda adapter: adapter.object_path,
            )
        ],
        "devices": [_serialize_bluetooth_device(device) for device in devices],
    }


def _serialize_adapter(
    adapter: BluetoothAdapter,
) -> dict[str, object]:
    return {
        "object_path": adapter.object_path,
        "address": adapter.address,
        "alias": adapter.alias,
        "powered": adapter.powered,
        "discoverable": adapter.discoverable,
        "pairable": adapter.pairable,
        "uuids": list(adapter.uuids),
    }


def _serialize_bluetooth_device(
    device: BluetoothDevice,
) -> dict[str, object]:
    return {
        "object_path": device.object_path,
        "adapter_path": device.adapter_path,
        "address": device.address,
        "name": device.name,
        "alias": device.alias,
        "paired": device.paired,
        "trusted": device.trusted,
        "connected": device.connected,
        "blocked": device.blocked,
        "rssi": device.rssi,
        "uuids": list(device.uuids),
    }


def _serialize_pipewire_state(
    state: PipeWireState,
) -> dict[str, object]:
    return {
        "devices": [
            _serialize_pipewire_device(device)
            for device in sorted(
                state.devices,
                key=lambda device: device.object_id,
            )
        ],
        "nodes": [
            _serialize_audio_node(node)
            for node in sorted(
                state.nodes,
                key=lambda node: node.object_id,
            )
        ],
    }


def _serialize_pipewire_device(
    device: PipeWireDevice,
) -> dict[str, object]:
    return {
        "object_id": device.object_id,
        "name": device.name,
        "description": device.description,
        "bluez_address": device.bluez_address,
        "bluez_path": device.bluez_path,
        "active_profile": device.active_profile,
    }


def _serialize_audio_node(
    node: AudioNode,
) -> dict[str, object]:
    return {
        "object_id": node.object_id,
        "device_id": node.device_id,
        "name": node.name,
        "description": node.description,
        "media_class": node.media_class,
        "state": node.state,
        "profile": node.profile,
        "codec": node.codec,
        "sample_rate": node.sample_rate,
        "channels": node.channels,
    }


def _serialize_sessions(
    sessions: Sequence[BluetoothAudioSession],
) -> dict[str, object]:
    return {
        "sessions": [
            {
                "bluetooth_device": _serialize_bluetooth_device(session.bluetooth_device),
                "pipewire_device": (
                    _serialize_pipewire_device(session.pipewire_device)
                    if session.pipewire_device is not None
                    else None
                ),
                "playback_nodes": [_serialize_audio_node(node) for node in session.playback_nodes],
                "capture_nodes": [_serialize_audio_node(node) for node in session.capture_nodes],
            }
            for session in sorted(
                sessions,
                key=lambda session: session.bluetooth_device.object_path,
            )
        ]
    }


def _journal_filename(
    service_name: str,
) -> str:
    safe_name = "".join(
        character if character.isalnum() or character in "._@-" else "_"
        for character in service_name
    )

    return f"{safe_name}.log"


def _write_json(
    path: Path,
    payload: object,
    *,
    redactor: EvidenceRedactor | None,
) -> None:
    text = json.dumps(
        payload,
        indent=2,
        sort_keys=True,
        ensure_ascii=False,
    )

    _write_text(
        path,
        text,
        redactor=redactor,
    )


def _write_text(
    path: Path,
    text: str,
    *,
    redactor: EvidenceRedactor | None,
) -> None:
    if redactor is not None:
        text = redactor.redact_text(text)

    normalized_text = f"{text.rstrip()}\n" if text else ""

    path.write_text(
        normalized_text,
        encoding="utf-8",
    )
