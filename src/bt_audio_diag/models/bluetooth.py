from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BluetoothAdapter:
    """Normalized state for a BlueZ Bluetooth adapter."""

    object_path: str
    address: str
    alias: str | None
    powered: bool
    discoverable: bool
    pairable: bool
    uuids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class BluetoothDevice:
    """Normalized state for a BlueZ Bluetooth device."""

    object_path: str
    adapter_path: str
    address: str
    name: str | None
    alias: str | None
    paired: bool
    trusted: bool
    connected: bool
    blocked: bool
    rssi: int | None = None
    uuids: tuple[str, ...] = ()
