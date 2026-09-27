from pathlib import Path

from bt_audio_diag.models import BtmonEvidence
from bt_audio_diag.services import (
    CommandExecutionError,
    CommandRunner,
)

_DEFAULT_DURATION_SECONDS = 10
_KILL_AFTER_SECONDS = 2
_TIMEOUT_EXIT_CODE = 124


class BtmonCollector:
    """Capture a bounded Bluetooth HCI trace using btmon."""

    def __init__(
        self,
        command_runner: CommandRunner,
        *,
        duration_seconds: int = _DEFAULT_DURATION_SECONDS,
        controller: str | None = None,
    ) -> None:
        if duration_seconds <= 0:
            raise ValueError("duration_seconds must be greater than zero")

        if controller is not None and not controller.strip():
            raise ValueError("controller must not be empty")

        self._command_runner = command_runner
        self._duration_seconds = duration_seconds
        self._controller = controller

    def collect(
        self,
        output_path: Path,
    ) -> BtmonEvidence:
        """Capture Bluetooth monitor traffic into a btsnoop trace file."""

        command = self._build_command(output_path)

        try:
            result = self._command_runner.run(command)
        except CommandExecutionError as exc:
            return BtmonEvidence(
                output_path=str(output_path),
                command=command,
                duration_seconds=self._duration_seconds,
                controller=self._controller,
                returncode=None,
                stderr="",
                error=str(exc),
            )

        error = None

        if result.returncode not in {0, _TIMEOUT_EXIT_CODE}:
            error = _command_failure_message(
                result.returncode,
                result.stderr,
            )

        return BtmonEvidence(
            output_path=str(output_path),
            command=command,
            duration_seconds=self._duration_seconds,
            controller=self._controller,
            returncode=result.returncode,
            stderr=result.stderr,
            error=error,
        )

    def _build_command(
        self,
        output_path: Path,
    ) -> tuple[str, ...]:
        command = [
            "timeout",
            "--signal=INT",
            f"--kill-after={_KILL_AFTER_SECONDS}s",
            f"{self._duration_seconds}s",
            "btmon",
            "--color",
            "never",
        ]

        if self._controller is not None:
            command.extend(
                [
                    "--index",
                    self._controller,
                ]
            )

        command.extend(
            [
                "--write",
                str(output_path),
            ]
        )

        return tuple(command)


def _command_failure_message(
    returncode: int,
    stderr: str,
) -> str:
    message = f"btmon capture exited with status {returncode}"
    detail = stderr.strip()

    if detail:
        return f"{message}: {detail}"

    return message
