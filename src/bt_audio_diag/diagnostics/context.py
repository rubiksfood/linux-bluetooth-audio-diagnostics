from dataclasses import dataclass

from bt_audio_diag.models import (
    BluetoothAdapter,
    BluetoothAudioSession,
    SystemInfo,
)


@dataclass(frozen=True, slots=True)
class DiagnosticContext:
    """Normalized evidence available to diagnostic rules."""

    system_info: SystemInfo
    adapters: tuple[BluetoothAdapter, ...]
    sessions: tuple[BluetoothAudioSession, ...]
