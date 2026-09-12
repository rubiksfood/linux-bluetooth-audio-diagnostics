from bt_audio_diag.diagnostics import (
    DiagnosticContext,
    DiagnosticEngine,
)
from bt_audio_diag.models import (
    AudioNode,
    BluetoothAdapter,
    BluetoothAudioSession,
    BluetoothDevice,
    PipeWireDevice,
    ServiceStatus,
    SystemInfo,
)


def _system_info() -> SystemInfo:
    return SystemInfo(
        distribution="Test Linux",
        distribution_version="1",
        kernel="6.0.0",
        architecture="x86_64",
        python_version="3.13.0",
        tool_version="0.1.0.dev0",
        services=(
            ServiceStatus(
                name="bluetooth.service",
                running=True,
            ),
            ServiceStatus(
                name="pipewire.service",
                running=True,
            ),
        ),
    )


def _adapter() -> BluetoothAdapter:
    return BluetoothAdapter(
        object_path="/org/bluez/hci0",
        address="00:11:22:33:44:55",
        alias="Test Adapter",
        powered=True,
        discoverable=False,
        pairable=True,
    )


def _bluetooth_device() -> BluetoothDevice:
    return BluetoothDevice(
        object_path="/org/bluez/hci0/dev_AA_BB_CC_DD_EE_FF",
        adapter_path="/org/bluez/hci0",
        address="AA:BB:CC:DD:EE:FF",
        name="Test Headphones",
        alias="Test Headphones",
        paired=True,
        trusted=True,
        connected=True,
        blocked=False,
    )


def _pipewire_device() -> PipeWireDevice:
    return PipeWireDevice(
        object_id=40,
        name="bluez_card.AA_BB_CC_DD_EE_FF",
        description="Test Headphones",
        bluez_address="AA:BB:CC:DD:EE:FF",
        bluez_path="/org/bluez/hci0/dev_AA_BB_CC_DD_EE_FF",
        active_profile="a2dp-sink",
    )


def _playback_node() -> AudioNode:
    return AudioNode(
        object_id=41,
        device_id=40,
        name="bluez_output.AA_BB_CC_DD_EE_FF.a2dp-sink",
        description="Test Headphones",
        media_class="Audio/Sink",
        state="running",
        profile="a2dp-sink",
        codec="sbc",
        sample_rate=48000,
        channels=2,
    )


def test_healthy_bluetooth_audio_session_has_no_findings() -> None:
    session = BluetoothAudioSession(
        bluetooth_device=_bluetooth_device(),
        pipewire_device=_pipewire_device(),
        playback_nodes=(_playback_node(),),
    )

    context = DiagnosticContext(
        system_info=_system_info(),
        adapters=(_adapter(),),
        sessions=(session,),
    )

    findings = DiagnosticEngine().evaluate(context)

    assert findings == ()


def test_connected_device_without_pipewire_produces_bt003() -> None:
    session = BluetoothAudioSession(
        bluetooth_device=_bluetooth_device(),
        pipewire_device=None,
    )

    context = DiagnosticContext(
        system_info=_system_info(),
        adapters=(_adapter(),),
        sessions=(session,),
    )

    findings = DiagnosticEngine().evaluate(context)

    assert len(findings) == 1

    finding = findings[0]

    assert finding.code == "BT003"
    assert finding.summary == (
        "Test Headphones is connected through BlueZ but has no corresponding PipeWire audio device."
    )
