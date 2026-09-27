from collections.abc import Sequence
from pathlib import Path

import pytest

from bt_audio_diag.collectors import BtmonCollector
from bt_audio_diag.services import CommandResult


class FakeCommandRunner:
    def __init__(
        self,
        result: CommandResult,
    ) -> None:
        self._result = result
        self.commands: list[tuple[str, ...]] = []

    def run(
        self,
        command: Sequence[str],
    ) -> CommandResult:
        normalized_command = tuple(command)
        self.commands.append(normalized_command)
        return self._result


def _result(
    *,
    returncode: int,
    stderr: str = "",
) -> CommandResult:
    return CommandResult(
        returncode=returncode,
        stdout="",
        stderr=stderr,
    )


def test_capture_uses_bounded_btmon_command(
    tmp_path: Path,
) -> None:
    runner = FakeCommandRunner(_result(returncode=124))
    output_path = tmp_path / "bluetooth.btsnoop"

    evidence = BtmonCollector(runner).collect(output_path)

    assert runner.commands == [
        (
            "timeout",
            "--signal=INT",
            "--kill-after=2s",
            "10s",
            "btmon",
            "--color",
            "never",
            "--write",
            str(output_path),
        )
    ]

    assert evidence.output_path == str(output_path)
    assert evidence.duration_seconds == 10
    assert evidence.controller is None
    assert evidence.returncode == 124
    assert evidence.succeeded is True
    assert evidence.completed_by_timeout is True


def test_capture_can_target_specific_controller(
    tmp_path: Path,
) -> None:
    runner = FakeCommandRunner(_result(returncode=124))
    output_path = tmp_path / "hci0.btsnoop"

    evidence = BtmonCollector(
        runner,
        duration_seconds=30,
        controller="hci0",
    ).collect(output_path)

    assert runner.commands == [
        (
            "timeout",
            "--signal=INT",
            "--kill-after=2s",
            "30s",
            "btmon",
            "--color",
            "never",
            "--index",
            "hci0",
            "--write",
            str(output_path),
        )
    ]

    assert evidence.duration_seconds == 30
    assert evidence.controller == "hci0"
    assert evidence.succeeded is True


def test_clean_early_exit_is_successful(
    tmp_path: Path,
) -> None:
    runner = FakeCommandRunner(_result(returncode=0))

    evidence = BtmonCollector(runner).collect(tmp_path / "bluetooth.btsnoop")

    assert evidence.returncode == 0
    assert evidence.succeeded is True
    assert evidence.completed_by_timeout is False


def test_failed_capture_preserves_error_information(
    tmp_path: Path,
) -> None:
    runner = FakeCommandRunner(
        _result(
            returncode=1,
            stderr="Operation not permitted\n",
        )
    )

    evidence = BtmonCollector(runner).collect(tmp_path / "bluetooth.btsnoop")

    assert evidence.returncode == 1
    assert evidence.stderr == "Operation not permitted\n"
    assert evidence.error == ("btmon capture exited with status 1: Operation not permitted")
    assert evidence.succeeded is False
    assert evidence.completed_by_timeout is False


@pytest.mark.parametrize(
    "duration_seconds",
    [
        0,
        -1,
    ],
)
def test_rejects_non_positive_duration(
    duration_seconds: int,
) -> None:
    runner = FakeCommandRunner(_result(returncode=124))

    with pytest.raises(
        ValueError,
        match="duration_seconds must be greater than zero",
    ):
        BtmonCollector(
            runner,
            duration_seconds=duration_seconds,
        )


@pytest.mark.parametrize(
    "controller",
    [
        "",
        "   ",
    ],
)
def test_rejects_empty_controller(
    controller: str,
) -> None:
    runner = FakeCommandRunner(_result(returncode=124))

    with pytest.raises(
        ValueError,
        match="controller must not be empty",
    ):
        BtmonCollector(
            runner,
            controller=controller,
        )
