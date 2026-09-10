import re
from importlib.metadata import version as distribution_version

from bt_audio_diag.models import ServiceStatus, SystemInfo
from bt_audio_diag.services.command_runner import (
    CommandExecutionError,
    CommandRunner,
)
from bt_audio_diag.services.system_provider import SystemProvider

_DISTRIBUTION_NAME = "linux-bluetooth-audio-diagnostics"

_VERSION_PATTERN = re.compile(r"\b\d+(?:\.\d+)+(?:[-+~][0-9A-Za-z][0-9A-Za-z._+~-]*)?\b")

_BLUEZ_VERSION_COMMAND = ("bluetoothd", "--version")
_PIPEWIRE_VERSION_COMMAND = ("pipewire", "--version")
_WIREPLUMBER_VERSION_COMMAND = ("wireplumber", "--version")

_BLUETOOTH_SERVICE_COMMAND = (
    "systemctl",
    "is-active",
    "bluetooth.service",
)
_PIPEWIRE_SERVICE_COMMAND = (
    "systemctl",
    "--user",
    "is-active",
    "pipewire.service",
)
_WIREPLUMBER_SERVICE_COMMAND = (
    "systemctl",
    "--user",
    "is-active",
    "wireplumber.service",
)

_INACTIVE_SERVICE_STATES = frozenset(
    {
        "inactive",
        "failed",
        "maintenance",
    }
)


class SystemInfoCollector:
    """Collect normalized Linux and audio-stack environment information."""

    def __init__(
        self,
        command_runner: CommandRunner,
        system_provider: SystemProvider,
        *,
        include_hostname: bool = False,
    ) -> None:
        self._command_runner = command_runner
        self._system_provider = system_provider
        self._include_hostname = include_hostname

    def collect(self) -> SystemInfo:
        os_release = self._system_provider.os_release()

        return SystemInfo(
            distribution=os_release.get("NAME", "Linux"),
            distribution_version=os_release.get("VERSION_ID"),
            kernel=self._system_provider.kernel_release(),
            architecture=self._system_provider.architecture(),
            python_version=self._system_provider.python_version(),
            tool_version=distribution_version(_DISTRIBUTION_NAME),
            bluez_version=self._collect_version(_BLUEZ_VERSION_COMMAND),
            pipewire_version=self._collect_version(_PIPEWIRE_VERSION_COMMAND),
            wireplumber_version=self._collect_version(_WIREPLUMBER_VERSION_COMMAND),
            hostname=(self._system_provider.hostname() if self._include_hostname else None),
            services=(
                ServiceStatus(
                    name="bluetooth.service",
                    running=self._collect_service_state(_BLUETOOTH_SERVICE_COMMAND),
                ),
                ServiceStatus(
                    name="pipewire.service",
                    running=self._collect_service_state(_PIPEWIRE_SERVICE_COMMAND),
                ),
                ServiceStatus(
                    name="wireplumber.service",
                    running=self._collect_service_state(_WIREPLUMBER_SERVICE_COMMAND),
                ),
            ),
        )

    def _collect_version(self, command: tuple[str, ...]) -> str | None:
        try:
            result = self._command_runner.run(command)
        except CommandExecutionError:
            return None

        if result.returncode != 0:
            return None

        output = "\n".join(part for part in (result.stdout, result.stderr) if part)
        match = _VERSION_PATTERN.search(output)

        return match.group(0) if match else None

    def _collect_service_state(
        self,
        command: tuple[str, ...],
    ) -> bool | None:
        try:
            result = self._command_runner.run(command)
        except CommandExecutionError:
            return None

        state = result.stdout.strip().lower()

        if state == "active":
            return True

        if state in _INACTIVE_SERVICE_STATES:
            return False

        return None
