from collections.abc import Sequence

from bt_audio_diag.models import (
    BluetoothAudioSession,
    BluetoothDevice,
    PipeWireDevice,
    PipeWireState,
)

_PLAYBACK_MEDIA_CLASSES = frozenset(
    {
        "Audio/Sink",
        "Audio/Duplex",
    }
)

_CAPTURE_MEDIA_CLASSES = frozenset(
    {
        "Audio/Source",
        "Audio/Duplex",
    }
)


class BluetoothAudioCorrelationError(RuntimeError):
    """Raised when Bluetooth and PipeWire evidence is ambiguous."""


def correlate_bluetooth_audio(
    bluetooth_devices: Sequence[BluetoothDevice],
    pipewire_state: PipeWireState,
) -> tuple[BluetoothAudioSession, ...]:
    """Correlate BlueZ devices with PipeWire devices and audio nodes."""

    sessions: list[BluetoothAudioSession] = []

    for bluetooth_device in sorted(
        bluetooth_devices,
        key=lambda device: device.object_path,
    ):
        pipewire_device = _match_pipewire_device(
            bluetooth_device,
            pipewire_state.devices,
        )

        if pipewire_device is None:
            sessions.append(
                BluetoothAudioSession(
                    bluetooth_device=bluetooth_device,
                    pipewire_device=None,
                )
            )
            continue

        device_nodes = tuple(
            sorted(
                (
                    node
                    for node in pipewire_state.nodes
                    if node.device_id == pipewire_device.object_id
                ),
                key=lambda node: node.object_id,
            )
        )

        playback_nodes = tuple(
            node for node in device_nodes if node.media_class in _PLAYBACK_MEDIA_CLASSES
        )

        capture_nodes = tuple(
            node for node in device_nodes if node.media_class in _CAPTURE_MEDIA_CLASSES
        )

        sessions.append(
            BluetoothAudioSession(
                bluetooth_device=bluetooth_device,
                pipewire_device=pipewire_device,
                playback_nodes=playback_nodes,
                capture_nodes=capture_nodes,
            )
        )

    return tuple(sessions)


def _match_pipewire_device(
    bluetooth_device: BluetoothDevice,
    pipewire_devices: Sequence[PipeWireDevice],
) -> PipeWireDevice | None:
    path_matches = tuple(
        device for device in pipewire_devices if device.bluez_path == bluetooth_device.object_path
    )

    address_matches = tuple(
        device
        for device in pipewire_devices
        if _addresses_match(
            bluetooth_device.address,
            device.bluez_address,
        )
    )

    path_match = _unique_match(
        path_matches,
        bluetooth_device=bluetooth_device,
        evidence="BlueZ object path",
    )
    address_match = _unique_match(
        address_matches,
        bluetooth_device=bluetooth_device,
        evidence="Bluetooth address",
    )

    if (
        path_match is not None
        and address_match is not None
        and path_match.object_id != address_match.object_id
    ):
        raise BluetoothAudioCorrelationError(
            f"{bluetooth_device.object_path}: "
            "BlueZ path and Bluetooth address match different PipeWire devices"
        )

    return path_match or address_match


def _unique_match(
    matches: Sequence[PipeWireDevice],
    *,
    bluetooth_device: BluetoothDevice,
    evidence: str,
) -> PipeWireDevice | None:
    if not matches:
        return None

    if len(matches) > 1:
        raise BluetoothAudioCorrelationError(
            f"{bluetooth_device.object_path}: {evidence} matches multiple PipeWire devices"
        )

    return matches[0]


def _addresses_match(
    bluetooth_address: str,
    pipewire_address: str | None,
) -> bool:
    if pipewire_address is None:
        return False

    return bluetooth_address.casefold() == pipewire_address.casefold()
