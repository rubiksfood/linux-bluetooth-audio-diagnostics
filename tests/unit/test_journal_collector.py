from collections.abc import Sequence

import pytest

from bt_audio_diag.collectors import JournalCollector
from bt_audio_diag.models import JournalScope
from bt_audio_diag.services import CommandResult


class FakeCommandRunner:
    def __init__(
        self,
        results: Sequence[CommandResult],
    ) -> None:
        self._results = list(results)
        self.commands: list[tuple[str, ...]] = []

    def run(
        self,
        command: Sequence[str],
    ) -> CommandResult:
        normalized_command = tuple(command)
        self.commands.append(normalized_command)

        if not self._results:
            raise AssertionError("Unexpected command execution")

        return self._results.pop(0)


def _successful_result(
    stdout: str = "",
) -> CommandResult:
    return CommandResult(
        returncode=0,
        stdout=stdout,
        stderr="",
    )


def test_collects_bluetooth_pipewire_and_wireplumber_journals() -> None:
    runner = FakeCommandRunner(
        (
            _successful_result("Bluetooth log\n"),
            _successful_result("PipeWire log\n"),
            _successful_result("WirePlumber log\n"),
        )
    )

    evidence = JournalCollector(runner).collect()

    assert len(evidence) == 3

    assert evidence[0].service_name == "bluetooth.service"
    assert evidence[0].scope is JournalScope.SYSTEM
    assert evidence[0].stdout == "Bluetooth log\n"
    assert evidence[0].succeeded is True

    assert evidence[1].service_name == "pipewire.service"
    assert evidence[1].scope is JournalScope.USER
    assert evidence[1].stdout == "PipeWire log\n"
    assert evidence[1].succeeded is True

    assert evidence[2].service_name == "wireplumber.service"
    assert evidence[2].scope is JournalScope.USER
    assert evidence[2].stdout == "WirePlumber log\n"
    assert evidence[2].succeeded is True

    assert runner.commands == [
        (
            "journalctl",
            "--no-pager",
            "--quiet",
            "--output=short-iso",
            "--lines=200",
            "--unit",
            "bluetooth.service",
        ),
        (
            "journalctl",
            "--no-pager",
            "--quiet",
            "--output=short-iso",
            "--lines=200",
            "--user",
            "--unit",
            "pipewire.service",
        ),
        (
            "journalctl",
            "--no-pager",
            "--quiet",
            "--output=short-iso",
            "--lines=200",
            "--user",
            "--unit",
            "wireplumber.service",
        ),
    ]


def test_nonzero_journal_result_does_not_abort_other_collections() -> None:
    runner = FakeCommandRunner(
        (
            CommandResult(
                returncode=1,
                stdout="",
                stderr="Permission denied\n",
            ),
            _successful_result("PipeWire log\n"),
            _successful_result("WirePlumber log\n"),
        )
    )

    evidence = JournalCollector(runner).collect()

    assert len(evidence) == 3

    bluetooth_evidence = evidence[0]

    assert bluetooth_evidence.service_name == "bluetooth.service"
    assert bluetooth_evidence.returncode == 1
    assert bluetooth_evidence.stderr == "Permission denied\n"
    assert bluetooth_evidence.error == ("journalctl exited with status 1: Permission denied")
    assert bluetooth_evidence.succeeded is False

    assert evidence[1].succeeded is True
    assert evidence[2].succeeded is True


def test_nonzero_journal_result_without_stderr_uses_generic_error() -> None:
    runner = FakeCommandRunner(
        (
            CommandResult(
                returncode=5,
                stdout="",
                stderr="",
            ),
            _successful_result(),
            _successful_result(),
        )
    )

    evidence = JournalCollector(runner).collect()

    assert evidence[0].returncode == 5
    assert evidence[0].stderr == ""
    assert evidence[0].error == "journalctl exited with status 5"
    assert evidence[0].succeeded is False

    assert evidence[1].succeeded is True
    assert evidence[2].succeeded is True


def test_custom_line_limit_is_used_for_every_service() -> None:
    runner = FakeCommandRunner(
        (
            _successful_result(),
            _successful_result(),
            _successful_result(),
        )
    )

    JournalCollector(
        runner,
        line_limit=50,
    ).collect()

    assert all("--lines=50" in command for command in runner.commands)


@pytest.mark.parametrize(
    "line_limit",
    [
        0,
        -1,
    ],
)
def test_rejects_non_positive_line_limit(
    line_limit: int,
) -> None:
    runner = FakeCommandRunner(())

    with pytest.raises(
        ValueError,
        match="line_limit must be greater than zero",
    ):
        JournalCollector(
            runner,
            line_limit=line_limit,
        )
