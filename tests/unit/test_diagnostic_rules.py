from dataclasses import replace

import pytest

from bt_audio_diag.diagnostics import DiagnosticContext, DiagnosticEngine
from bt_audio_diag.models import (
    AudioNode,
    BluetoothAdapter,
    BluetoothAudioSession,
    BluetoothDevice,
    DiagnosticFinding,
    PipeWireDevice,
    ServiceStatus,
    Severity,
    SystemInfo,
)


def _system_info(
    *,
    bluetooth_running: bool | None = True,
    pipewire_running: bool | None = True,
) -> SystemInfo:
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
                running=bluetooth_running,
            ),
            ServiceStatus(
                name="pipewire.service",
                running=pipewire_running,
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


def _audio_node(
    *,
    object_id: int = 41,
    media_class: str = "Audio/Sink",
    state: str = "running",
) -> AudioNode:
    return AudioNode(
        object_id=object_id,
        device_id=40,
        name=f"test-node-{object_id}",
        description="Test Headphones",
        media_class=media_class,
        state=state,
        profile="a2dp-sink",
        codec="sbc",
        sample_rate=48000,
        channels=2,
    )


def _evaluate(
    *,
    system_info: SystemInfo | None = None,
    adapters: tuple[BluetoothAdapter, ...] | None = None,
    sessions: tuple[BluetoothAudioSession, ...] = (),
) -> tuple[DiagnosticFinding, ...]:
    context = DiagnosticContext(
        system_info=system_info or _system_info(),
        adapters=adapters if adapters is not None else (_adapter(),),
        sessions=sessions,
    )

    return DiagnosticEngine().evaluate(context)


def test_bt001_reports_unpowered_adapter() -> None:
    adapter = replace(_adapter(), powered=False)

    findings = _evaluate(
        adapters=(adapter,),
    )

    assert len(findings) == 1
    assert findings[0].code == "BT001"
    assert findings[0].severity is Severity.WARNING
    assert "Powered=false" in findings[0].evidence[0]


def test_bt002_reports_paired_but_disconnected_device() -> None:
    device = replace(
        _bluetooth_device(),
        connected=False,
    )

    session = BluetoothAudioSession(
        bluetooth_device=device,
        pipewire_device=None,
    )

    findings = _evaluate(
        sessions=(session,),
    )

    assert len(findings) == 1
    assert findings[0].code == "BT002"
    assert findings[0].severity is Severity.WARNING
    assert findings[0].evidence == (
        f"{device.object_path} reports Paired=true.",
        f"{device.object_path} reports Connected=false.",
    )


def test_bt004_reports_connected_device_without_playback_node() -> None:
    session = BluetoothAudioSession(
        bluetooth_device=_bluetooth_device(),
        pipewire_device=_pipewire_device(),
    )

    findings = _evaluate(
        sessions=(session,),
    )

    assert len(findings) == 1
    assert findings[0].code == "BT004"
    assert findings[0].severity is Severity.WARNING
    assert "no playback node" in findings[0].summary


def test_bt005_reports_suspended_node_as_information() -> None:
    node = _audio_node(state="suspended")

    session = BluetoothAudioSession(
        bluetooth_device=_bluetooth_device(),
        pipewire_device=_pipewire_device(),
        playback_nodes=(node,),
    )

    findings = _evaluate(
        sessions=(session,),
    )

    assert len(findings) == 1
    assert findings[0].code == "BT005"
    assert findings[0].severity is Severity.INFO
    assert "suspended" in findings[0].summary


def test_bt005_reports_error_node_as_error() -> None:
    node = _audio_node(state="error")

    session = BluetoothAudioSession(
        bluetooth_device=_bluetooth_device(),
        pipewire_device=_pipewire_device(),
        playback_nodes=(node,),
    )

    findings = _evaluate(
        sessions=(session,),
    )

    assert len(findings) == 1
    assert findings[0].code == "BT005"
    assert findings[0].severity is Severity.ERROR
    assert "error" in findings[0].summary


def test_bt005_deduplicates_duplex_node() -> None:
    node = _audio_node(
        media_class="Audio/Duplex",
        state="suspended",
    )

    session = BluetoothAudioSession(
        bluetooth_device=_bluetooth_device(),
        pipewire_device=_pipewire_device(),
        playback_nodes=(node,),
        capture_nodes=(node,),
    )

    findings = _evaluate(
        sessions=(session,),
    )

    assert len(findings) == 1
    assert findings[0].code == "BT005"


@pytest.mark.parametrize(
    ("service_name", "expected_code"),
    [
        ("bluetooth.service", "BT006"),
        ("pipewire.service", "BT007"),
    ],
)
def test_service_rules_report_confirmed_inactive_services(
    service_name: str,
    expected_code: str,
) -> None:
    system_info = _system_info(
        bluetooth_running=(service_name != "bluetooth.service"),
        pipewire_running=(service_name != "pipewire.service"),
    )

    findings = _evaluate(
        system_info=system_info,
        adapters=(),
    )

    assert len(findings) == 1
    assert findings[0].code == expected_code
    assert findings[0].severity is Severity.ERROR


def test_unknown_service_state_does_not_produce_failure_finding() -> None:
    system_info = _system_info(
        bluetooth_running=None,
        pipewire_running=None,
    )

    findings = _evaluate(
        system_info=system_info,
        adapters=(),
    )

    assert findings == ()
