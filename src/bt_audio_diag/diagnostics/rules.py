from collections.abc import Callable

from bt_audio_diag.diagnostics.context import DiagnosticContext
from bt_audio_diag.models import (
    AudioNode,
    BluetoothDevice,
    DiagnosticFinding,
    ServiceStatus,
    Severity,
)

type DiagnosticRule = Callable[
    [DiagnosticContext],
    tuple[DiagnosticFinding, ...],
]


def adapter_power_rule(
    context: DiagnosticContext,
) -> tuple[DiagnosticFinding, ...]:
    """Report Bluetooth adapters that are present but not powered."""

    findings: list[DiagnosticFinding] = []

    for adapter in sorted(
        context.adapters,
        key=lambda item: item.object_path,
    ):
        if adapter.powered:
            continue

        label = adapter.alias or adapter.address

        findings.append(
            DiagnosticFinding(
                code="BT001",
                severity=Severity.WARNING,
                summary=f"Bluetooth adapter {label} is not powered.",
                evidence=(f"{adapter.object_path} reports Powered=false.",),
                possible_cause=(
                    "The adapter may be disabled by software, rfkill, firmware, or hardware state."
                ),
                recommended_next_step=(
                    "Verify the adapter power and rfkill state before "
                    "checking Bluetooth device connectivity."
                ),
            )
        )

    return tuple(findings)


def paired_not_connected_rule(
    context: DiagnosticContext,
) -> tuple[DiagnosticFinding, ...]:
    """Report paired Bluetooth devices that are not connected."""

    findings: list[DiagnosticFinding] = []

    for session in sorted(
        context.sessions,
        key=lambda item: item.bluetooth_device.object_path,
    ):
        device = session.bluetooth_device

        if not device.paired or device.connected:
            continue

        findings.append(
            DiagnosticFinding(
                code="BT002",
                severity=Severity.WARNING,
                summary=f"{_device_label(device)} is paired but not connected.",
                evidence=(
                    f"{device.object_path} reports Paired=true.",
                    f"{device.object_path} reports Connected=false.",
                ),
                possible_cause=(
                    "The device may be unavailable, disconnected, or unable "
                    "to establish a Bluetooth connection."
                ),
                recommended_next_step=(
                    "Confirm the device is powered and in range, then retry "
                    "the Bluetooth connection."
                ),
            )
        )

    return tuple(findings)


def connected_without_pipewire_rule(
    context: DiagnosticContext,
) -> tuple[DiagnosticFinding, ...]:
    """Report connected BlueZ devices missing from PipeWire."""

    findings: list[DiagnosticFinding] = []

    for session in sorted(
        context.sessions,
        key=lambda item: item.bluetooth_device.object_path,
    ):
        device = session.bluetooth_device

        if not device.connected or session.pipewire_device is not None:
            continue

        findings.append(
            DiagnosticFinding(
                code="BT003",
                severity=Severity.WARNING,
                summary=(
                    f"{_device_label(device)} is connected through BlueZ "
                    "but has no corresponding PipeWire audio device."
                ),
                evidence=(
                    f"{device.object_path} reports Connected=true.",
                    "No correlated PipeWire Bluetooth device was found.",
                ),
                possible_cause=(
                    "PipeWire Bluetooth support, session-manager configuration, "
                    "or Bluetooth profile negotiation may be unavailable."
                ),
                recommended_next_step=(
                    "Inspect PipeWire and WirePlumber Bluetooth state and recent service logs."
                ),
            )
        )

    return tuple(findings)


def connected_without_playback_rule(
    context: DiagnosticContext,
) -> tuple[DiagnosticFinding, ...]:
    """Report connected audio devices without a playback node."""

    findings: list[DiagnosticFinding] = []

    for session in sorted(
        context.sessions,
        key=lambda item: item.bluetooth_device.object_path,
    ):
        device = session.bluetooth_device

        if not device.connected or session.pipewire_device is None or session.playback_nodes:
            continue

        findings.append(
            DiagnosticFinding(
                code="BT004",
                severity=Severity.WARNING,
                summary=(
                    f"{_device_label(device)} has a PipeWire device but exposes no playback node."
                ),
                evidence=(
                    (
                        f"PipeWire device ID {session.pipewire_device.object_id} "
                        "was correlated with the Bluetooth device."
                    ),
                    "No playback nodes were associated with that PipeWire device.",
                ),
                possible_cause=(
                    "The active Bluetooth profile may not provide playback, "
                    "or audio-node creation may have failed."
                ),
                recommended_next_step=(
                    "Inspect the PipeWire device profile and Bluetooth audio node state."
                ),
            )
        )

    return tuple(findings)


def pipewire_node_state_rule(
    context: DiagnosticContext,
) -> tuple[DiagnosticFinding, ...]:
    """Report relevant suspended or error-state Bluetooth audio nodes."""

    findings: list[DiagnosticFinding] = []

    for session in sorted(
        context.sessions,
        key=lambda item: item.bluetooth_device.object_path,
    ):
        if not session.bluetooth_device.connected:
            continue

        nodes = _unique_session_nodes((*session.playback_nodes, *session.capture_nodes))

        for node in nodes:
            if node.state is None:
                continue

            state = node.state.casefold()

            if state not in {"suspended", "error"}:
                continue

            findings.append(
                _node_state_finding(
                    session.bluetooth_device,
                    node,
                    state=state,
                )
            )

    return tuple(findings)


def bluetooth_service_rule(
    context: DiagnosticContext,
) -> tuple[DiagnosticFinding, ...]:
    """Report a Bluetooth service confirmed not to be running."""

    if (
        _service_running(
            context.system_info.services,
            "bluetooth.service",
        )
        is not False
    ):
        return ()

    return (
        DiagnosticFinding(
            code="BT006",
            severity=Severity.ERROR,
            summary="The Bluetooth service is not running.",
            evidence=("bluetooth.service was confirmed inactive or failed.",),
            possible_cause=("BlueZ may be stopped, failed, or unavailable on the system."),
            recommended_next_step=("Inspect bluetooth.service status and recent BlueZ logs."),
        ),
    )


def pipewire_service_rule(
    context: DiagnosticContext,
) -> tuple[DiagnosticFinding, ...]:
    """Report a PipeWire service confirmed not to be running."""

    if (
        _service_running(
            context.system_info.services,
            "pipewire.service",
        )
        is not False
    ):
        return ()

    return (
        DiagnosticFinding(
            code="BT007",
            severity=Severity.ERROR,
            summary="The PipeWire service is not running.",
            evidence=("pipewire.service was confirmed inactive or failed.",),
            possible_cause=("PipeWire may be stopped or failed in the current user session."),
            recommended_next_step=("Inspect the user PipeWire service status and recent logs."),
        ),
    )


DEFAULT_RULES: tuple[DiagnosticRule, ...] = (
    adapter_power_rule,
    paired_not_connected_rule,
    connected_without_pipewire_rule,
    connected_without_playback_rule,
    pipewire_node_state_rule,
    bluetooth_service_rule,
    pipewire_service_rule,
)


def _device_label(device: BluetoothDevice) -> str:
    return device.alias or device.name or device.address


def _service_running(
    services: tuple[ServiceStatus, ...],
    name: str,
) -> bool | None:
    for service in services:
        if service.name == name:
            return service.running

    return None


def _unique_session_nodes(
    nodes: tuple[AudioNode, ...],
) -> tuple[AudioNode, ...]:
    unique = {node.object_id: node for node in nodes}

    return tuple(unique[object_id] for object_id in sorted(unique))


def _node_state_finding(
    device: BluetoothDevice,
    node: AudioNode,
    *,
    state: str,
) -> DiagnosticFinding:
    node_label = node.name or f"PipeWire node {node.object_id}"

    if state == "error":
        severity = Severity.ERROR
        possible_cause = "PipeWire processing or Bluetooth profile negotiation may have failed."
        recommended_next_step = (
            "Inspect PipeWire and WirePlumber logs for errors affecting this node."
        )
    else:
        severity = Severity.INFO
        possible_cause, recommended_next_step = _suspended_node_guidance(node.media_class)

    return DiagnosticFinding(
        code="BT005",
        severity=severity,
        summary=(f"{node_label} for {_device_label(device)} is in the {state} state."),
        evidence=(
            f"PipeWire node ID {node.object_id} reports state={state}.",
            f"Node media class is {node.media_class}.",
        ),
        possible_cause=possible_cause,
        recommended_next_step=recommended_next_step,
    )


def _suspended_node_guidance(media_class: str) -> tuple[str, str]:
    if media_class == "Audio/Sink":
        return (
            "A suspended playback node is normally idle when no application is playing audio.",
            "Start audio playback and check whether the node leaves the suspended state.",
        )

    if media_class == "Audio/Source":
        return (
            "A suspended capture node is normally idle when no application is using the audio input.",
            "Start audio capture and check whether the node leaves the suspended state.",
        )

    return (
        "A suspended audio node may be normal while idle, or may indicate that audio activation has not occurred.",
        "Start audio playback or capture and check whether the node leaves the suspended state.",
    )
