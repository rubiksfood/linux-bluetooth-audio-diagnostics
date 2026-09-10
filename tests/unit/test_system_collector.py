from collections.abc import Mapping, Sequence

from bt_audio_diag.collectors import SystemInfoCollector
from bt_audio_diag.services import CommandResult


class FakeCommandRunner:
    def __init__(
        self,
        results: dict[tuple[str, ...], CommandResult],
    ) -> None:
        self._results = results

    def run(self, command: Sequence[str]) -> CommandResult:
        key = tuple(command)

        if key not in self._results:
            raise AssertionError(f"Unexpected command: {key}")

        return self._results[key]


class FakeSystemProvider:
    def os_release(self) -> Mapping[str, str]:
        return {
            "NAME": "Fedora Linux",
            "VERSION_ID": "42",
        }

    def kernel_release(self) -> str:
        return "6.15.0"

    def architecture(self) -> str:
        return "x86_64"

    def python_version(self) -> str:
        return "3.13.7"

    def hostname(self) -> str:
        return "test-host"


def test_collect_returns_normalized_system_information() -> None:
    command_runner = FakeCommandRunner(
        {
            ("bluetoothd", "--version"): CommandResult(
                returncode=0,
                stdout="5.83\n",
                stderr="",
            ),
            ("pipewire", "--version"): CommandResult(
                returncode=0,
                stdout="pipewire\nCompiled with libpipewire 1.4.7\n",
                stderr="",
            ),
            ("wireplumber", "--version"): CommandResult(
                returncode=0,
                stdout="wireplumber\n0.5.10\n",
                stderr="",
            ),
            (
                "systemctl",
                "is-active",
                "bluetooth.service",
            ): CommandResult(
                returncode=0,
                stdout="active\n",
                stderr="",
            ),
            (
                "systemctl",
                "--user",
                "is-active",
                "pipewire.service",
            ): CommandResult(
                returncode=0,
                stdout="active\n",
                stderr="",
            ),
            (
                "systemctl",
                "--user",
                "is-active",
                "wireplumber.service",
            ): CommandResult(
                returncode=3,
                stdout="inactive\n",
                stderr="",
            ),
        }
    )

    collector = SystemInfoCollector(
        command_runner=command_runner,
        system_provider=FakeSystemProvider(),
    )

    result = collector.collect()

    assert result.distribution == "Fedora Linux"
    assert result.distribution_version == "42"
    assert result.kernel == "6.15.0"
    assert result.architecture == "x86_64"
    assert result.python_version == "3.13.7"
    assert result.bluez_version == "5.83"
    assert result.pipewire_version == "1.4.7"
    assert result.wireplumber_version == "0.5.10"
    assert result.hostname is None

    assert result.services[0].running is True
    assert result.services[1].running is True
    assert result.services[2].running is False
