import pytest

from bt_audio_diag.models import (
    AudioNode,
    BluetoothAdapter,
    BluetoothDevice,
    PipeWireDevice,
    PipeWireState,
    ServiceStatus,
    SystemInfo,
)
from bt_audio_diag.services import DiagnosticWorkflow


class FakeSystemInfoCollector:
    def __init__(self, system_info: SystemInfo) -> None:
        self._system_info = system_info
        self.calls = 0

    def collect(self) -> SystemInfo:
        self.calls += 1
        return self._system_info


class FakeBluetoothAdapterCollector:
    def __init__(
        self,
        adapters: tuple[BluetoothAdapter, ...],
    ) -> None:
        self._adapters = adapters
        self.calls = 0

    async def collect(self) -> tuple[BluetoothAdapter, ...]:
        self.calls += 1
        return self._adapters


class FakeBluetoothDeviceCollector:
    def __init__(
        self,
        devices: tuple[BluetoothDevice, ...],
    ) -> None:
        self._devices = devices
        self.calls = 0

    async def collect(self) -> tuple[BluetoothDevice, ...]:
        self.calls += 1
        return self._devices


class FakePipeWireCollector:
    def __init__(self, state: PipeWireState) -> None:
        self._state = state
        self.calls = 0

    def collect(self) -> PipeWireState:
        self.calls += 1
        return self._state


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
            ServiceStatus(
                name="wireplumber.service",
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


def _healthy_pipewire_state() -> PipeWireState:
    return PipeWireState(
        devices=(_pipewire_device(),),
        nodes=(_playback_node(),),
    )


@pytest.mark.asyncio
async def test_run_collects_correlates_and_evaluates_state() -> None:
    system_info = _system_info()
    adapters = (_adapter(),)
    devices = (_bluetooth_device(),)
    pipewire_state = _healthy_pipewire_state()

    system_collector = FakeSystemInfoCollector(system_info)
    adapter_collector = FakeBluetoothAdapterCollector(adapters)
    device_collector = FakeBluetoothDeviceCollector(devices)
    pipewire_collector = FakePipeWireCollector(pipewire_state)

    workflow = DiagnosticWorkflow(
        system_info_collector=system_collector,
        bluetooth_adapter_collector=adapter_collector,
        bluetooth_device_collector=device_collector,
        pipewire_collector=pipewire_collector,
    )

    result = await workflow.run()

    assert system_collector.calls == 1
    assert adapter_collector.calls == 1
    assert device_collector.calls == 1
    assert pipewire_collector.calls == 1

    assert result.context.system_info == system_info
    assert result.context.adapters == adapters
    assert result.pipewire_state == pipewire_state
    assert result.findings == ()

    assert len(result.context.sessions) == 1

    session = result.context.sessions[0]

    assert session.bluetooth_device == devices[0]
    assert session.pipewire_device == pipewire_state.devices[0]
    assert session.playback_nodes == pipewire_state.nodes
    assert session.capture_nodes == ()


@pytest.mark.asyncio
async def test_run_evaluates_connected_device_missing_from_pipewire() -> None:
    workflow = DiagnosticWorkflow(
        system_info_collector=FakeSystemInfoCollector(_system_info()),
        bluetooth_adapter_collector=FakeBluetoothAdapterCollector((_adapter(),)),
        bluetooth_device_collector=FakeBluetoothDeviceCollector((_bluetooth_device(),)),
        pipewire_collector=FakePipeWireCollector(PipeWireState()),
    )

    result = await workflow.run()

    assert len(result.context.sessions) == 1
    assert result.context.sessions[0].pipewire_device is None
    assert [finding.code for finding in result.findings] == ["BT003"]
