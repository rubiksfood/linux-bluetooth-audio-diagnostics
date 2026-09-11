from collections.abc import Sequence
from pathlib import Path

from bt_audio_diag.collectors import PipeWireCollector
from bt_audio_diag.models import AudioNode, PipeWireDevice, PipeWireState
from bt_audio_diag.services import CommandResult

_FIXTURE_DIR = Path(__file__).parents[1] / "fixtures" / "pipewire"


class FakeCommandRunner:
    def __init__(self, result: CommandResult) -> None:
        self._result = result

    def run(self, command: Sequence[str]) -> CommandResult:
        assert tuple(command) == ("pw-dump", "--no-colors")

        return self._result


def _collect_fixture(filename: str) -> PipeWireState:
    stdout = (_FIXTURE_DIR / filename).read_text(encoding="utf-8")

    command_runner = FakeCommandRunner(
        CommandResult(
            returncode=0,
            stdout=stdout,
            stderr="",
        )
    )

    return PipeWireCollector(command_runner).collect()


def test_collect_returns_normalized_healthy_headphones() -> None:
    result = _collect_fixture("healthy_headphones.json")

    assert result == PipeWireState(
        devices=(
            PipeWireDevice(
                object_id=40,
                name="bluez_card.AA_BB_CC_DD_EE_FF",
                description="Test Headphones",
                bluez_address="AA:BB:CC:DD:EE:FF",
                bluez_path="/org/bluez/hci0/dev_AA_BB_CC_DD_EE_FF",
                active_profile="a2dp-sink",
            ),
        ),
        nodes=(
            AudioNode(
                object_id=41,
                device_id=40,
                name="bluez_output.AA_BB_CC_DD_EE_FF.a2dp-sink",
                description="Test Headphones",
                media_class="Audio/Sink",
                state="running",
                profile="a2dp-sink",
                codec="sbc_xq",
                sample_rate=48000,
                channels=2,
            ),
        ),
    )


def test_collect_preserves_bluetooth_device_without_audio_nodes() -> None:
    result = _collect_fixture("bluetooth_device_without_nodes.json")

    assert len(result.devices) == 1
    assert result.devices[0].object_id == 60
    assert result.nodes == ()


def test_collect_preserves_suspended_node_state() -> None:
    result = _collect_fixture("suspended_node.json")

    assert len(result.nodes) == 1
    assert result.nodes[0].state == "suspended"
    assert result.nodes[0].codec == "sbc"


def test_collect_supports_duplex_headset_nodes() -> None:
    result = _collect_fixture("headset_duplex.json")

    assert tuple(node.media_class for node in result.nodes) == (
        "Audio/Sink",
        "Audio/Source",
    )

    assert tuple(node.device_id for node in result.nodes) == (
        80,
        80,
    )

    assert result.nodes[0].codec == "msbc"
    assert result.nodes[1].codec == "msbc"


def test_collect_sorts_multiple_bluetooth_devices_and_nodes() -> None:
    result = _collect_fixture("multiple_bluetooth_devices.json")

    assert tuple(device.object_id for device in result.devices) == (
        100,
        200,
    )

    assert tuple(node.object_id for node in result.nodes) == (
        101,
        201,
    )

    assert tuple(device.bluez_address for device in result.devices) == (
        "AA:AA:AA:AA:AA:AA",
        "BB:BB:BB:BB:BB:BB",
    )
