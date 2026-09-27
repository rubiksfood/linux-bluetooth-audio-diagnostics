from dataclasses import dataclass

from bt_audio_diag.models import JournalEvidence, JournalScope
from bt_audio_diag.services import (
    CommandExecutionError,
    CommandRunner,
)

_DEFAULT_LINE_LIMIT = 200


@dataclass(frozen=True, slots=True)
class _JournalTarget:
    service_name: str
    scope: JournalScope


_TARGETS = (
    _JournalTarget(
        service_name="bluetooth.service",
        scope=JournalScope.SYSTEM,
    ),
    _JournalTarget(
        service_name="pipewire.service",
        scope=JournalScope.USER,
    ),
    _JournalTarget(
        service_name="wireplumber.service",
        scope=JournalScope.USER,
    ),
)


class JournalCollector:
    """Collect recent journal entries relevant to Bluetooth audio."""

    def __init__(
        self,
        command_runner: CommandRunner,
        *,
        line_limit: int = _DEFAULT_LINE_LIMIT,
    ) -> None:
        if line_limit <= 0:
            raise ValueError("line_limit must be greater than zero")

        self._command_runner = command_runner
        self._line_limit = line_limit

    def collect(self) -> tuple[JournalEvidence, ...]:
        """Collect journal evidence for all configured service targets."""

        return tuple(self._collect_target(target) for target in _TARGETS)

    def _collect_target(
        self,
        target: _JournalTarget,
    ) -> JournalEvidence:
        command = self._build_command(target)

        try:
            result = self._command_runner.run(command)
        except CommandExecutionError as exc:
            return JournalEvidence(
                service_name=target.service_name,
                scope=target.scope,
                command=command,
                stdout="",
                stderr="",
                returncode=None,
                error=str(exc),
            )

        error = None

        if result.returncode != 0:
            error = _command_failure_message(
                result.returncode,
                result.stderr,
            )

        return JournalEvidence(
            service_name=target.service_name,
            scope=target.scope,
            command=command,
            stdout=result.stdout,
            stderr=result.stderr,
            returncode=result.returncode,
            error=error,
        )

    def _build_command(
        self,
        target: _JournalTarget,
    ) -> tuple[str, ...]:
        command = [
            "journalctl",
            "--no-pager",
            "--quiet",
            "--output=short-iso",
            f"--lines={self._line_limit}",
        ]

        if target.scope is JournalScope.USER:
            command.append("--user")

        command.extend(
            [
                "--unit",
                target.service_name,
            ]
        )

        return tuple(command)


def _command_failure_message(
    returncode: int,
    stderr: str,
) -> str:
    message = f"journalctl exited with status {returncode}"
    detail = stderr.strip()

    if detail:
        return f"{message}: {detail}"

    return message
