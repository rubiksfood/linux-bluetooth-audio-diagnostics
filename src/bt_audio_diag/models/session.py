from dataclasses import dataclass

from bt_audio_diag.models.bluetooth import BluetoothDevice
from bt_audio_diag.models.pipewire import AudioNode, PipeWireDevice


@dataclass(frozen=True, slots=True)
class BluetoothAudioSession:
    """Correlated Bluetooth connectivity and PipeWire audio state."""

    bluetooth_device: BluetoothDevice
    pipewire_device: PipeWireDevice | None
    playback_nodes: tuple[AudioNode, ...] = ()
    capture_nodes: tuple[AudioNode, ...] = ()
