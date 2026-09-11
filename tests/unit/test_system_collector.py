from collections.abc import Mapping, Sequence

import pytest

from bt_audio_diag.collectors import SystemInfoCollector
from bt_audio_diag.services import (
    CommandExecutionError,
    CommandResult,
)


class FakeCommandRunner:
    """Deterministic command runner for collector tests."""

    def __init__(
        self,
        responses: dict[
            tuple[str, ...],
            CommandResult | CommandExecutionError,
        ],
    ) -> None:
        self._responses = responses

    def run(self, command: Sequence[str]) -> CommandResult:
        key = tuple(command)

        if key not in self._responses:
            raise AssertionError(f"Unexpected command: {key}")

        response = self._responses[key]

        if isinstance(response, CommandExecutionError):
            raise response

        return response


class FakeSystemProvider:
    """Deterministic provider for host information."""

    def __init__(
        self,
        *,
        os_release: Mapping[str, str] | None = None,
        kernel: str = "6.15.0",
        architecture: str = "x86_64",
        python_version: str = "3.13.7",
        hostname: str = "test-host",
    ) -> None:
        self._os_release = (
            {
                "NAME": "Fedora Linux",
                "VERSION_ID": "42",
            }
            if os_release is None
            else dict(os_release)
        )
        self._kernel = kernel
        self._architecture = architecture
        self._python_version = python_version
        self._hostname = hostname

    def os_release(self) -> Mapping[str, str]:
        return self._os_release

    def kernel_release(self) -> str:
        return self._kernel

    def architecture(self) -> str:
        return self._architecture

    def python_version(self) -> str:
        return self._python_version

    def hostname(self) -> str:
        return self._hostname


@pytest.fixture
def command_responses() -> dict[
    tuple[str, ...],
    CommandResult | CommandExecutionError,
]:
    return {
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


@pytest.fixture
def system_provider() -> FakeSystemProvider:
    return FakeSystemProvider()


def test_collect_returns_normalized_system_information(
    command_responses: dict[
        tuple[str, ...],
        CommandResult | CommandExecutionError,
    ],
    system_provider: FakeSystemProvider,
) -> None:
    collector = SystemInfoCollector(
        command_runner=FakeCommandRunner(command_responses),
        system_provider=system_provider,
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

    service_states = {service.name: service.running for service in result.services}

    assert service_states == {
        "bluetooth.service": True,
        "pipewire.service": True,
        "wireplumber.service": False,
    }


def test_collect_handles_unavailable_audio_stack_versions(
    command_responses: dict[
        tuple[str, ...],
        CommandResult | CommandExecutionError,
    ],
    system_provider: FakeSystemProvider,
) -> None:
    command_responses[("bluetoothd", "--version")] = CommandExecutionError(
        "bluetoothd not available"
    )
    command_responses[("pipewire", "--version")] = CommandResult(
        returncode=1,
        stdout="",
        stderr="pipewire unavailable",
    )
    command_responses[("wireplumber", "--version")] = CommandResult(
        returncode=0,
        stdout="wireplumber\n",
        stderr="",
    )

    collector = SystemInfoCollector(
        command_runner=FakeCommandRunner(command_responses),
        system_provider=system_provider,
    )

    result = collector.collect()

    assert result.bluez_version is None
    assert result.pipewire_version is None
    assert result.wireplumber_version is None


def test_collect_preserves_unknown_service_state(
    command_responses: dict[
        tuple[str, ...],
        CommandResult | CommandExecutionError,
    ],
    system_provider: FakeSystemProvider,
) -> None:
    command_responses[
        (
            "systemctl",
            "--user",
            "is-active",
            "pipewire.service",
        )
    ] = CommandExecutionError("systemctl unavailable")

    command_responses[
        (
            "systemctl",
            "--user",
            "is-active",
            "wireplumber.service",
        )
    ] = CommandResult(
        returncode=0,
        stdout="activating\n",
        stderr="",
    )

    collector = SystemInfoCollector(
        command_runner=FakeCommandRunner(command_responses),
        system_provider=system_provider,
    )

    result = collector.collect()

    service_states = {service.name: service.running for service in result.services}

    assert service_states == {
        "bluetooth.service": True,
        "pipewire.service": None,
        "wireplumber.service": None,
    }


def test_collect_can_include_hostname(
    command_responses: dict[
        tuple[str, ...],
        CommandResult | CommandExecutionError,
    ],
    system_provider: FakeSystemProvider,
) -> None:
    collector = SystemInfoCollector(
        command_runner=FakeCommandRunner(command_responses),
        system_provider=system_provider,
        include_hostname=True,
    )

    result = collector.collect()

    assert result.hostname == "test-host"


def test_collect_handles_missing_os_release_fields(
    command_responses: dict[
        tuple[str, ...],
        CommandResult | CommandExecutionError,
    ],
) -> None:
    collector = SystemInfoCollector(
        command_runner=FakeCommandRunner(command_responses),
        system_provider=FakeSystemProvider(os_release={}),
    )

    result = collector.collect()

    assert result.distribution == "Linux"
    assert result.distribution_version is None
