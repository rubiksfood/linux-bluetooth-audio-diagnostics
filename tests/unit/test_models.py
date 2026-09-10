from bt_audio_diag.models import (
    BluetoothAdapter,
    BluetoothDevice,
    DiagnosticFinding,
    ServiceStatus,
    Severity,
    SystemInfo,
)


def test_system_info_supports_service_state() -> None:
    bluetooth_service = ServiceStatus(name="bluetooth.service", running=True)

    system_info = SystemInfo(
        distribution="Fedora Linux",
        distribution_version="42",
        kernel="6.15.0",
        architecture="x86_64",
        python_version="3.13.7",
        tool_version="0.1.0.dev0",
        bluez_version="5.83",
        pipewire_version="1.4.7",
        wireplumber_version="0.5.10",
        services=(bluetooth_service,),
    )

    assert system_info.services == (bluetooth_service,)
    assert system_info.hostname is None


def test_bluetooth_adapter_stores_normalized_state() -> None:
    adapter = BluetoothAdapter(
        object_path="/org/bluez/hci0",
        address="00:11:22:33:44:55",
        alias="Linux Adapter",
        powered=True,
        discoverable=False,
        pairable=True,
        uuids=("0000110b-0000-1000-8000-00805f9b34fb",),
    )

    assert adapter.powered is True
    assert adapter.uuids == ("0000110b-0000-1000-8000-00805f9b34fb",)


def test_bluetooth_device_supports_unavailable_rssi() -> None:
    device = BluetoothDevice(
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

    assert device.rssi is None
    assert device.uuids == ()


def test_diagnostic_finding_contains_evidence() -> None:
    finding = DiagnosticFinding(
        code="BT003",
        severity=Severity.WARNING,
        summary="Connected Bluetooth device has no PipeWire audio device.",
        evidence=("BlueZ reports device as connected.",),
        possible_cause="PipeWire Bluetooth integration may be unavailable.",
        recommended_next_step="Inspect PipeWire Bluetooth device state.",
    )

    assert finding.severity is Severity.WARNING
    assert finding.evidence == ("BlueZ reports device as connected.",)
