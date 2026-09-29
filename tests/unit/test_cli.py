import re
from importlib.metadata import version as distribution_version

from typer.testing import CliRunner

from bt_audio_diag.cli import app

runner = CliRunner()

ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")


def test_help_option() -> None:
    result = runner.invoke(app, ["--help"])
    output = ANSI_ESCAPE_RE.sub("", result.stdout)

    assert result.exit_code == 0
    assert "Inspect and diagnose Linux Bluetooth audio environments." in output
    assert "--version" in output


def test_version_option() -> None:
    result = runner.invoke(app, ["--version"])

    expected_version = distribution_version("linux-bluetooth-audio-diagnostics")

    assert result.exit_code == 0
    assert result.stdout == f"bt-audio-diag {expected_version}\n"
