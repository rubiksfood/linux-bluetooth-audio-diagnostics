import json
from collections.abc import Sequence

from bt_audio_diag.collectors import PipeWireCollector
from bt_audio_diag.models import AudioNode, PipeWireDevice, PipeWireState
from bt_audio_diag.services import CommandResult


class FakeCommandRunner:
    def __init__(self, result: CommandResult) -> None:
        self._result = result

    def run(self, command: Sequence[str]) -> CommandResult:
        assert tuple(command) == ("pw-dump", "--no-colors")

        return self._result


def test_collect_returns_normalized_bluetooth_audio_state() -> None:
    pw_dump = [
        {
            "id": 40,
            "type": "PipeWire:Interface:Device",
            "info": {
                "props": {
                    "device.api": "bluez5",
                    "device.name": "bluez_card.AA_BB_CC_DD_EE_FF",
                    "device.description": "Test Headphones",
                    "api.bluez5.address": "AA:BB:CC:DD:EE:FF",
                    "api.bluez5.path": ("/org/bluez/hci0/dev_AA_BB_CC_DD_EE_FF"),
                    "device.profile.name": "a2dp-sink",
                },
            },
        },
        {
            "id": 41,
            "type": "PipeWire:Interface:Node",
            "info": {
                "state": "running",
                "props": {
                    "device.id": 40,
                    "device.api": "bluez5",
                    "node.name": ("bluez_output.AA_BB_CC_DD_EE_FF.a2dp-sink"),
                    "node.description": "Test Headphones",
                    "media.class": "Audio/Sink",
                    "api.bluez5.profile": "a2dp-sink",
                    "api.bluez5.codec": "sbc_xq",
                    "audio.rate": 48000,
                    "audio.channels": 2,
                },
            },
        },
        {
            "id": 10,
            "type": "PipeWire:Interface:Device",
            "info": {
                "props": {
                    "device.api": "alsa",
                    "device.name": "alsa_card.test",
                },
            },
        },
    ]

    command_runner = FakeCommandRunner(
        CommandResult(
            returncode=0,
            stdout=json.dumps(pw_dump),
            stderr="",
        )
    )

    collector = PipeWireCollector(command_runner)

    result = collector.collect()

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
