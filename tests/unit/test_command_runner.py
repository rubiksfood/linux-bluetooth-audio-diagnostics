import subprocess
from unittest.mock import patch

import pytest

from bt_audio_diag.services import (
    CommandExecutionError,
    CommandResult,
    SubprocessCommandRunner,
)


def test_run_returns_captured_command_result() -> None:
    completed_process = subprocess.CompletedProcess(
        args=("example", "--version"),
        returncode=0,
        stdout="1.2.3\n",
        stderr="",
    )

    with patch(
        "bt_audio_diag.services.command_runner.subprocess.run",
        return_value=completed_process,
    ) as run_mock:
        runner = SubprocessCommandRunner()

        result = runner.run(("example", "--version"))

    assert result == CommandResult(
        returncode=0,
        stdout="1.2.3\n",
        stderr="",
    )

    run_mock.assert_called_once_with(
        ("example", "--version"),
        capture_output=True,
        text=True,
        check=False,
        timeout=5.0,
    )


def test_run_translates_os_error_to_command_execution_error() -> None:
    with patch(
        "bt_audio_diag.services.command_runner.subprocess.run",
        side_effect=FileNotFoundError("command not found"),
    ):
        runner = SubprocessCommandRunner()

        with pytest.raises(
            CommandExecutionError,
            match="Failed to execute command: missing-command",
        ):
            runner.run(("missing-command",))


def test_run_translates_timeout_to_command_execution_error() -> None:
    with patch(
        "bt_audio_diag.services.command_runner.subprocess.run",
        side_effect=subprocess.TimeoutExpired(
            cmd=("slow-command",),
            timeout=5.0,
        ),
    ):
        runner = SubprocessCommandRunner()

        with pytest.raises(
            CommandExecutionError,
            match="Failed to execute command: slow-command",
        ):
            runner.run(("slow-command",))
