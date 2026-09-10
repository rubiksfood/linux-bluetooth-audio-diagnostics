import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class CommandResult:
    """Result of an external command execution."""

    returncode: int
    stdout: str
    stderr: str


class CommandExecutionError(RuntimeError):
    """Raised when an external command cannot be executed."""


class CommandRunner(Protocol):
    """Interface for executing external commands."""

    def run(self, command: Sequence[str]) -> CommandResult:
        """Execute a command and return its captured result."""
        ...


class SubprocessCommandRunner:
    """Execute external commands using the local operating system."""

    def __init__(self, timeout_seconds: float = 5.0) -> None:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be greater than zero")

        self._timeout_seconds = timeout_seconds

    def run(self, command: Sequence[str]) -> CommandResult:
        if not command:
            raise ValueError("command must contain at least one argument")

        arguments = tuple(command)

        try:
            completed = subprocess.run(
                arguments,
                capture_output=True,
                text=True,
                check=False,
                timeout=self._timeout_seconds,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise CommandExecutionError(
                f"Failed to execute command: {' '.join(arguments)}"
            ) from exc

        return CommandResult(
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )
