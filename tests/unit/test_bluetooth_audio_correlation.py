import pytest

from bt_audio_diag.models import (
    AudioNode,
    BluetoothDevice,
    PipeWireDevice,
    PipeWireState,
)
from bt_audio_diag.services import (
    BluetoothAudioCorrelationError,
    correlate_bluetooth_audio,
)


def _bluetooth_device(
    *,
    object_path: str = "/org/bluez/hci0/dev_AA_BB_CC_DD_EE_FF",
    address: str = "AA:BB:CC:DD:EE:FF",
) -> BluetoothDevice:
    return BluetoothDevice(
        object_path=object_path,
        adapter_path="/org/bluez/hci0",
        address=address,
        name="Test Headset",
        alias="Test Headset",
        paired=True,
        trusted=True,
        connected=True,
        blocked=False,
    )


def _pipewire_device(
    *,
    object_id: int = 40,
    bluez_path: str | None = "/org/bluez/hci0/dev_AA_BB_CC_DD_EE_FF",
    bluez_address: str | None = "AA:BB:CC:DD:EE:FF",
) -> PipeWireDevice:
    return PipeWireDevice(
        object_id=object_id,
        name="bluez_card.AA_BB_CC_DD_EE_FF",
        description="Test Headset",
        bluez_address=bluez_address,
        bluez_path=bluez_path,
        active_profile="headset-head-unit",
    )


def _audio_node(
    *,
    object_id: int,
    device_id: int,
    media_class: str,
) -> AudioNode:
    return AudioNode(
        object_id=object_id,
        device_id=device_id,
        name=f"test-node-{object_id}",
        description="Test Headset",
        media_class=media_class,
        state="running",
        profile="headset-head-unit",
        codec="msbc",
        sample_rate=16000,
        channels=1,
    )


def test_correlate_matches_pipewire_device_by_bluez_path() -> None:
    bluetooth_device = _bluetooth_device()
    pipewire_device = _pipewire_device()

    playback_node = _audio_node(
        object_id=41,
        device_id=40,
        media_class="Audio/Sink",
    )
    capture_node = _audio_node(
        object_id=42,
        device_id=40,
        media_class="Audio/Source",
    )

    result = correlate_bluetooth_audio(
        (bluetooth_device,),
        PipeWireState(
            devices=(pipewire_device,),
            nodes=(capture_node, playback_node),
        ),
    )

    assert len(result) == 1

    session = result[0]

    assert session.bluetooth_device == bluetooth_device
    assert session.pipewire_device == pipewire_device
    assert session.playback_nodes == (playback_node,)
    assert session.capture_nodes == (capture_node,)


def test_correlate_falls_back_to_bluetooth_address() -> None:
    bluetooth_device = _bluetooth_device()

    pipewire_device = _pipewire_device(
        bluez_path=None,
        bluez_address="aa:bb:cc:dd:ee:ff",
    )

    result = correlate_bluetooth_audio(
        (bluetooth_device,),
        PipeWireState(devices=(pipewire_device,)),
    )

    assert result[0].pipewire_device == pipewire_device


def test_correlate_preserves_device_without_pipewire_match() -> None:
    bluetooth_device = _bluetooth_device()

    result = correlate_bluetooth_audio(
        (bluetooth_device,),
        PipeWireState(),
    )

    session = result[0]

    assert session.bluetooth_device == bluetooth_device
    assert session.pipewire_device is None
    assert session.playback_nodes == ()
    assert session.capture_nodes == ()


def test_correlate_rejects_ambiguous_pipewire_matches() -> None:
    bluetooth_device = _bluetooth_device()

    first_device = _pipewire_device(object_id=40)
    second_device = _pipewire_device(object_id=50)

    pipewire_state = PipeWireState(
        devices=(
            first_device,
            second_device,
        )
    )

    with pytest.raises(
        BluetoothAudioCorrelationError,
        match=r"matches multiple PipeWire devices",
    ):
        correlate_bluetooth_audio(
            (bluetooth_device,),
            pipewire_state,
        )


def test_correlate_rejects_conflicting_path_and_address_evidence() -> None:
    bluetooth_device = _bluetooth_device()

    path_match = _pipewire_device(
        object_id=40,
        bluez_path=bluetooth_device.object_path,
        bluez_address="11:22:33:44:55:66",
    )

    address_match = _pipewire_device(
        object_id=50,
        bluez_path="/org/bluez/hci0/dev_11_22_33_44_55_66",
        bluez_address=bluetooth_device.address,
    )

    pipewire_state = PipeWireState(
        devices=(
            path_match,
            address_match,
        )
    )

    with pytest.raises(
        BluetoothAudioCorrelationError,
        match=r"match different PipeWire devices",
    ):
        correlate_bluetooth_audio(
            (bluetooth_device,),
            pipewire_state,
        )
