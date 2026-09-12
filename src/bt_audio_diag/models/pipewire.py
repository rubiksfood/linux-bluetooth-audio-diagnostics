from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PipeWireDevice:
    """Normalized PipeWire representation of a Bluetooth audio device."""

    object_id: int
    name: str | None
    description: str | None
    bluez_address: str | None
    bluez_path: str | None
    active_profile: str | None


@dataclass(frozen=True, slots=True)
class AudioNode:
    """Normalized PipeWire Bluetooth audio node."""

    object_id: int
    device_id: int | None
    name: str | None
    description: str | None
    media_class: str
    state: str | None
    profile: str | None
    codec: str | None
    sample_rate: int | None
    channels: int | None


@dataclass(frozen=True, slots=True)
class PipeWireState:
    """Normalized Bluetooth-related state collected from PipeWire."""

    devices: tuple[PipeWireDevice, ...] = ()
    nodes: tuple[AudioNode, ...] = ()
